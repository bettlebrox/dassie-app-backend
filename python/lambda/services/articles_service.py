import logging
from datetime import datetime, timedelta

from models.models import Browse, Browsed
from models.article import Article

logger = logging.getLogger()


class ArticlesService:
    # threshold for regenerating a summary
    STALE_ARTICLE_THRESHOLD = 90

    def __init__(
        self, article_repo, theme_repo, browse_repo, browsed_repo, openai_client
    ):
        self._article_repo = article_repo
        self._theme_repo = theme_repo
        self._browse_repo = browse_repo
        self._browsed_repo = browsed_repo
        self._llm_client = openai_client

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
        if article.summary == "" or article.created_at < datetime.now() - timedelta(
            days=self.STALE_ARTICLE_THRESHOLD
        ):
            article = self._build_article_from_navlog(article, navlog)
            self._add_llm_summarisation(
                article,
                self._llm_client.get_article_summarization(article.text),
                self._llm_client.get_embedding(article.text),
                self._llm_client.count_tokens(article.text),
            )
            logger.info("Built article {}".format(article.title))
        self._track_browsing(article, navlog)

    def _add_llm_summarisation(
        self, current_article, article_summary, embedding, token_count
    ):
        if article_summary is None:
            return
        logger.debug(f"Adding article summary: {article_summary}")
        if "summary" in article_summary and article_summary["summary"] is not None:
            current_article.summary = article_summary["summary"]
            current_article.embedding = embedding
            current_article.token_count = token_count
            current_article.updated_at = datetime.now()
            self._article_repo.update(current_article)
        if "themes" in article_summary and article_summary["themes"] is not None:
            self._theme_repo.add_related(current_article, article_summary["themes"])

    def get_search_terms_from_article(self, article):
        if article.original_title.endswith("- Google Search"):
            return article.original_title.split("- Google Search")[0].strip()
        return None

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
