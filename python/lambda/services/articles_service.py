import logging
from datetime import datetime

logger = logging.getLogger()


class ArticlesService:
    def __init__(self, article_repo, theme_repo):
        self._article_repo = article_repo
        self._theme_repo = theme_repo

    def add_llm_summarisation(
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

    def build_article_from_navlog(self, current_article, navlog):
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
