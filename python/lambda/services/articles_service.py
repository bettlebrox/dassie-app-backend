from datetime import datetime, timedelta
from article_repo import ArticleRepository
from browse_repo import BrowseRepository
from dassie_logger import logger
from langfuse.decorators import observe
from langfuse.decorators import langfuse_context
from models.browse import Browse
from models.models import Browsed
from models.article import Article
from repos import BrowsedRepository
from services.neptune_client import NeptuneClient
from services.openai_client import OpenAIClient
from theme_repo import ThemeRepository


class ArticlesService:
    # threshold for regenerating a summary
    STALE_ARTICLE_THRESHOLD = 90

    def __init__(
        self,
        article_repo: ArticleRepository,
        theme_repo: ThemeRepository,
        browse_repo: BrowseRepository,
        browsed_repo: BrowsedRepository,
        openai_client: OpenAIClient,
        neptune_client: NeptuneClient,
    ):
        self._article_repo = article_repo
        self._theme_repo = theme_repo
        self._browse_repo = browse_repo
        self._browsed_repo = browsed_repo
        self._llm_client = openai_client
        self._neptune_client = neptune_client

    def process_navlog(self, navlog):
        article = self._article_repo.get_or_insert(
            Article(
                navlog["title"],
                navlog["url"],
                text=navlog["body_text"],
                logged_at=datetime.strptime(
                    navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
                ),
            )
        )
        if article.summary is None or article.created_at < datetime.now() - timedelta(
            days=self.STALE_ARTICLE_THRESHOLD
        ):
            article = self._build_article_from_navlog(article, navlog)
            self._add_llm_summarisation(
                article,
                self._llm_client.get_article_summarization(article.text),
                self._llm_client.get_embedding(article.text),
                self._llm_client.count_tokens(article.text),
            )
            logger.info("Built article", extra={"title": article.title})
        self._track_browsing(article, navlog)

    def _add_llm_summarisation(
        self, current_article, article_summary, embedding, token_count
    ):
        if article_summary is None:
            return
        if "summary" in article_summary and article_summary["summary"] is not None:
            logger.info(
                "Adding article summary",
                extra={
                    "summary": article_summary,
                    "token_count": token_count,
                    "embedding_length": len(embedding),
                },
            )
            current_article.summary = article_summary["summary"]
            current_article.embedding = embedding
            current_article.token_count = token_count
            current_article.updated_at = datetime.now()
            self._article_repo.update(current_article)
        themes = []
        themes = [
            theme.original_title
            for theme, _ in self._theme_repo.get(filter_embedding=embedding, limit=3)
        ]
        if (
            "themes" in article_summary
            and article_summary["themes"] is not None
            and len(themes) < 3
        ):
            themes = list(set(article_summary["themes"]).union(set(themes)))
        if sorted(themes) != sorted(
            [theme for theme in current_article.themes if theme is not None]
        ):
            self._theme_repo.add_related(current_article, themes)

    def get_search_terms_from_article(self, article):
        if article.original_title.endswith("- Google Search"):
            return article.original_title.split("- Google Search")[0].strip()
        return None

    @observe(name="process_article_graph")
    def _process_article_graph(self, article: Article):
        logger.info("Processing article graph", extra={"article": article.id})
        current_graph = self._neptune_client.get_article_graph(article.id)
        if current_graph != [] and article.updated_at > datetime.now() - timedelta(
            days=self.STALE_ARTICLE_THRESHOLD
        ):
            logger.info("Article graph already exists", extra={"article": article.id})
            return current_graph
        graph_opencypher = self._llm_client.generate_article_graph(
            article.text, article.id
        )
        if graph_opencypher is None:
            return None
        self._neptune_client.upsert_article_graph(
            article, graph_opencypher, langfuse_context.get_current_trace_id()
        )
        return graph_opencypher

    def _track_browsing(self, article, navlog):
        search = self.get_search_terms_from_article(article)
        browse = self._browse_repo.get_or_insert(Browse(tab_id=navlog["tabId"]))
        if search is not None and browse.title is None:
            browse.title = search
        if browse.logged_at is None:
            browse.logged_at = navlog["created_at"]
        self._browse_repo.update(browse)
        browsed = self._browsed_repo.get_by_browse_and_article(
            article_id=article.id, browse_id=browse.id
        )
        if browsed is None:
            self._browsed_repo.add(
                Browsed(
                    article_id=article.id,
                    browse_id=browse.id,
                    logged_at=navlog["created_at"],
                )
            )
        else:
            browsed.count += 1
            self._browsed_repo.update(browsed)

    def _build_article_from_navlog(self, current_article, navlog):
        current_article.source_navlog = navlog["id"]
        current_article.tab_id = navlog["tabId"]
        current_article.document_id = (
            navlog["documentId"]
            if "documentId" in navlog and navlog["documentId"] != "undefined"
            else None
        )
        current_article.parent_document_id = (
            navlog["parentDocumentId"]
            if "parentDocumentId" in navlog
            and navlog["parentDocumentId"] != "undefined"
            else None
        )
        current_article.logged_at = datetime.strptime(
            navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
        )
        current_article.updated_at = datetime.now()
        current_article.text = navlog["body_text"]
        if "image" in navlog and navlog["image"] is not None:
            current_article.image = navlog["image"]
        current_article = self._article_repo.update(current_article)
        return current_article
