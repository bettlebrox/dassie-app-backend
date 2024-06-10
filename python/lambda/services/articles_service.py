import logging
from datetime import datetime

logger = logging.getLogger()


class ArticlesService:
    def __init__(self, article_repo, theme_repo, openai_client):
        self._article_repo = article_repo
        self._theme_repo = theme_repo
        self._openai_client = openai_client

    def build_article(self, current_article, navlog):
        article_summary = self._openai_client.get_article_summarization(
            navlog["body_text"]
        )
        current_article.source_navlog = navlog["id"]
        embedding = self._openai_client.get_embedding(navlog["body_text"])
        current_article.embedding = embedding
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
        if article_summary is not None:
            current_article.summary = article_summary["summary"]
        current_article.logged_at = datetime.strptime(
            navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
        )
        current_article.text = navlog["body_text"]
        current_article.token_count = self._openai_client.count_tokens(
            navlog["body_text"]
        )
        if "image" in navlog and navlog["image"] is not None:
            current_article.image = navlog["image"]
        current_article = self._article_repo.update(current_article)
        if article_summary is not None:
            self._theme_repo.add_related(current_article, article_summary["themes"])
        return current_article
