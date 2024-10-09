import os
import boto3
import re
from langfuse.decorators import langfuse_context
from langfuse.decorators import observe

from dassie_logger import logger
from models.article import Article
from models.theme import Theme


class NeptuneClient:
    _endpoint = "https://127.0.0.1:8182"

    def __init__(self, endpoint, langfuse_key, langfuse_enabled=True):
        self._endpoint = endpoint
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
    def query(
        self,
        query,
    ):
        try:
            query = self._remove_unsupported_from_query(query)
            logger.info(f"Neptune query: {query}")
            response = self.client.execute_open_cypher_query(openCypherQuery=query)
            logger.info(f"Neptune query response: {response}")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error querying Neptune: {e}")
            raise e

    @observe()
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

    @observe()
    def upsert_article_graph(self, article: Article, trace_id: str):
        self._upsert_article(article, trace_id)
        self._scope_updated_graph(article.id, trace_id)

    @observe()
    def _scope_updated_graph(self, article_id: str, trace_id: str):
        try:
            response = self.client.execute_open_cypher_query(
                openCypherQuery=f"""
                match (n)
                where n.domain is null
                set n.domain = "dassie_subject"
                with n
                match (a:Article {{id: "{article_id}"}})
                with a, n
                merge (a)-[:SOURCE_OF {{ domain: "dassie_browse", trace_id: "{trace_id}" }}]->(n)
                """
            )
            logger.debug(f"Neptune query response: {response}")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error scoping updated graph: {e}")
            raise e

    @observe()
    def _upsert_article(self, article: Article, trace_id: str):
        query = f"""
        merge (a:Article {{id: "{article.id}"}})
        on create set a.domain = "dassie_browse", a.title = "{article.title}", a.url = "{article.url}", a.created_at = "{article.created_at}", a.updated_at = "{article.updated_at}", a.trace_id = "{trace_id}"
        on match set a.domain = "dassie_browse", a.title = "{article.title}", a.url = "{article.url}", a.created_at = "{article.created_at}", a.updated_at = "{article.updated_at}", a.trace_id = a.trace_id + ",{trace_id}"
        """
        try:
            response = self.client.execute_open_cypher_query(openCypherQuery=query)
            logger.debug(f"Neptune query response: {response}")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error upserting article: {e} query: {query}")
            raise e

    @observe()
    def _upsert_theme(self, theme: Theme, trace_id: str):
        query = f"""
        merge (t:Theme {{id: "{theme.id}"}})
        on create set t.domain = "dassie_browse", t.source = "{theme.source}", t.created_at = "{theme.created_at}", t.name = "{theme.original_title}", t.title = "{theme.title}", t.trace_id = "{trace_id}"
        on match set t.domain = "dassie_browse", t.source = "{theme.source}", t.created_at = "{theme.created_at}", t.name = "{theme.original_title}", t.title = "{theme.title}", t.trace_id = t.trace_id + ",{trace_id}"
        """
        for i, article in enumerate(theme.related):
            query += f'merge (t)-[:RELATED_TO]->(a{i}:Article {{id: "{article.id}"}})\n'
        try:
            print(query)
            response = self.client.execute_open_cypher_query(openCypherQuery=query)
            logger.debug(f"Neptune query response: {response}")
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                raise Exception(
                    f"Neptune query failed with status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
            return response["results"]
        except Exception as e:
            logger.error(f"Error upserting theme: {e} query: {query}")
            raise e
