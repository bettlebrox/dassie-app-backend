from models import Article
from repos import ArticleRepository, ThemeRepository
from services.navlogs_service import NavlogService
from services.openai_client import OpenAIClient


def main():
    navlog_service = NavlogService()
    navlogs = navlog_service.get_content_navlogs()
    for navlog in navlogs:
        article_repo = ArticleRepository()
        theme_repo = ThemeRepository()
        openai_client = OpenAIClient()
        article_summ = openai_client.get_article_summarization(navlog["body_text"])
        embedding = openai_client.get_embedding(navlog["body_text"])
        article_repo.upsert(
            Article(navlog["title"], article_summ["summary"], navlog["url"])
        )
        theme_repo.add_realted(article_summ["themes"])


if __name__ == "__main__":
    main()
