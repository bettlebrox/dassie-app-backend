import os
from typing import Literal
import boto3
import re
import json
from dassie_logger import logger
from models.article import Article
from models.theme import Theme
from langfuse.decorators import langfuse_context
from langfuse.decorators import observe


class NeptuneClient:
    _endpoint = "https://127.0.0.1:8182"

    def __init__(self, endpoint, langfuse_key, langfuse_enabled=True, session=None):
        self._endpoint = endpoint
        if session is None:
            session = boto3.Session()
        self.client = session.client("neptunedata", endpoint_url=endpoint, verify=False)
        release = "dev"
        try:
            release = os.environ["DD_TAGS"]
        except KeyError:
            pass
        langfuse_context.configure(
            secret_key=langfuse_key,
            public_key="pk-lf-b2888d04-2d31-4b07-8f53-d40d311d4d13",
            host="https://cloud.langfuse.com",
            release=release,
            enabled=langfuse_enabled,
        )

    @observe()
    def execute(self, query: str, rewrite_query: bool = True):
        """Executes a query with langfuse observability tracking.
        This decorator adds langfuse tracing to track query execution performance and metadata.
        """
        return self.query(query, rewrite_query)

    def query(
        self,
        query: str,
        rewrite_query: bool = True,
    ):
        try:
            if rewrite_query:
                query = self._remove_unsupported_from_query(query)
            logger.debug(f"""Neptune query: {query}""")
            response = self.client.execute_open_cypher_query(openCypherQuery=query)
            logger.debug(f"""Neptune query response: {response}""")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error querying Neptune: {e}", extra={"query": query})
            raise e

    def _remove_unsupported_from_query(self, query):
        query = re.sub(r"(date|datetime|duration)\((('|\").*?('|\"))\)", r"\2", query)
        query = re.sub(
            r"\[\'(.*?\,?.*?)\]",
            lambda m: "'"
            + m.group(1).replace("'", "").replace('"', "").replace(", ", ",")
            + "'",
            query,
        )
        return query

    def upsert_article_graph(self, article: Article, subject_graph: str, trace_id: str):
        self._upsert_article(article, trace_id)
        self.execute(subject_graph)
        dups = self._get_duplicate_labels_and_names()
        self._merge_duplicate_nodes(dups)
        self._scope_updated_graph(article.id, trace_id)

    def _get_unscoped_graph(self, article_id: str, trace_id: str):
        logger.debug(
            "_get_unscoped_graph",
            extra={"article_id": article_id, "trace_id": trace_id},
        )
        return self.query(
            f"""
                match (a:Article {{id: "{article_id}", trace_id: "{trace_id}"}})-[r:SOURCE_OF]->(b)
                where not exists(a.domain)
                return b.name,labels(b)
                """
        )

    def _scope_updated_graph(self, article_id: str, trace_id: str):
        logger.debug(
            "_scope_updated_graph",
            extra={"article_id": article_id, "trace_id": trace_id},
        )
        return self.query(
            f"""
                match (a:Article {{trace_id: "{trace_id}"}})-[r:SOURCE_OF]->(b)
                set b.domain = "dassie_subject"
                """
        )

    def _upsert_article(self, article: Article, trace_id: str):
        query = self._generate_article_merge_query(article, trace_id)
        return self.execute(query)

    def _generate_article_merge_query(
        self, article: Article, trace_id: str, idx: int = 0
    ):
        query = f"""
        merge (a{idx}:Article {{id: "{article.id}"}})
        on create set a{idx}.domain = "dassie_browse", a{idx}.title = "{article.title}", a{idx}.url = "{article.url}", a{idx}.created_at = "{article.created_at}", a{idx}.updated_at = "{article.updated_at}", a{idx}.trace_id = "{trace_id}"
        on match set a{idx}.domain = "dassie_browse", a{idx}.title = "{article.title}", a{idx}.url = "{article.url}", a{idx}.created_at = "{article.created_at}", a{idx}.updated_at = "{article.updated_at}", a{idx}.trace_id = a{idx}.trace_id + ",{trace_id}"
        """
        return query

    def _upsert_theme(self, theme: Theme, trace_id: str):
        query = f"""
        merge (t:Theme {{id: "{theme.id}"}})
        on create set t.domain = "dassie_browse", t.source = "{theme.source}", t.created_at = "{theme.created_at}", t.name = "{theme.original_title}", t.title = "{theme.title}", t.trace_id = "{trace_id}"
        on match set t.domain = "dassie_browse", t.source = "{theme.source}", t.created_at = "{theme.created_at}", t.name = "{theme.original_title}", t.title = "{theme.title}", t.trace_id = t.trace_id + ",{trace_id}"
        """
        for i, article in enumerate(theme.related):
            query += self._generate_article_merge_query(article, trace_id, i)
            query += f"merge (t)-[:RELATED_TO]->(a{i})\n"
        return self.execute(query)

    def _get_duplicate_labels_and_names(self):
        logger.debug("_get_duplicate_labels_and_names")
        return self.query(
            f"""
            match (n)
            where not exists(n.name) and exists(n.label)
            set n.name = n.label
            with count(*) as dummy
            match (m)
where not exists(m.name) and not exists(m.label)
            set m.name = m.id
            with count(*) as dummy
            match (a)
            with a.name as name,labels(a) as labels, count(a) as cbr
            where cbr >1
            return name,labels
            """
        )

    def _construct_copy_duplicates_relations_query(self, primary_node_id, relations):
        logger.debug(
            "_construct_copy_duplicates_relations_query",
            extra={"primary_node_id": primary_node_id, "relations": relations},
        )
        query = ""
        for i, rel in enumerate(relations):
            relName = rel["r"].replace(":", "").replace("-", "")
            if rel["a"] in rel["dups"]:
                query += f"match (a{i}),(b{i}) where id(a{i}) = '{primary_node_id}' and id(b{i}) = '{rel['b']}' merge (a{i})-[:{relName}]->(b{i})\n with a{i},b{i}\n"
            else:
                query += f"match (a{i}),(b{i}) where id(a{i}) = '{rel['a']}' and id(b{i}) = '{primary_node_id}' merge (a{i})-[:{relName}]->(b{i})\n with a{i},b{i}\n"
        return query

    def _construct_delete_duplicate_nodes_query(self, dups):
        logger.debug("_construct_delete_duplicate_nodes_query", extra={"dups": dups})
        query = f"match (n) where id(n) in {dups} detach delete n"
        return query

    def _get_duplicates(self, label, node_name):
        logger.debug("_get_duplicates", extra={"label": label, "node_name": node_name})
        match_query = f"""MATCH (n:{label} {{name: "{node_name}"}})"""
        if node_name is None:
            match_query = f"""MATCH (n:{label}) where not exists(n.name)"""
        query = f"""
            WITH COLLECT(n) AS nodes
            WITH nodes[0] AS firstNode, TAIL(nodes) AS duplicateNodes
            UNWIND duplicateNodes as duplicate
            SET firstNode += duplicate
            with firstNode,collect(id(duplicate)) as dups
            match (a)-[r]->(b)
            where id(b) in dups or id(a) in dups
            return id(a) as a,type(r) as r,id(b) as b,id(firstNode) as firstNode,dups
            """
        return self.query(match_query + query)

    def _merge_duplicate_nodes(self, dups):
        logger.debug("_merge_duplicate_nodes", extra={"dups": dups})
        for dup in dups:
            res = self._get_duplicates(dup["labels"][0], dup["name"])
            logger.debug(f"Found {len(res)} duplicates for {dup['name']}")
            if len(res) > 0:
                query = ""
                primary_node_id = res[0]["firstNode"]
                query += self._construct_copy_duplicates_relations_query(
                    primary_node_id, res
                )
                query += self._construct_delete_duplicate_nodes_query(res[0]["dups"])
                logger.debug(f"Merging duplicates for {dup['name']}: {query}")
                self.execute(query, rewrite_query=False)

    def get_theme_graph(self, theme_title: str):
        return self._convert_to_react_flow_format(
            self.query(
                f"""MATCH (t:Theme {{name: "{theme_title}"}})-[r:RELATED_TO]->(a:Article)-[s:SOURCE_OF]-(entity)-[entity_rel]-(related_entity)
WITH entity, entity_rel, related_entity, COUNT(a) AS articleCount
WHERE articleCount > 3 and type(entity_rel) <> "SOURCE_OF"
RETURN COLLECT(DISTINCT entity) AS entities, COLLECT(DISTINCT entity_rel) AS rels, COLLECT(DISTINCT related_entity) AS rel_entities"""
            )
        )

    def _convert_to_react_flow_format(self, results):
        graph = results[0]
        entities = graph["entities"] + graph["rel_entities"]
        nodes = [
            {
                "id": node["~id"],
                "type": "entity",
                "position": {"x": 0, "y": 0},
                "data": node,
            }
            for node in entities
        ]
        edges = [
            {"id": rel["~id"], "source": rel["~start"], "target": rel["~end"]}
            for rel in graph["rels"]
        ]
        return {"nodes": nodes, "edges": edges}
