from theme_repo import ThemeRepository
from models import ThemeType
from repos import ArticleRepository
from services.openai_client import LLMResponseException, OpenAIClient
import boto3
import json
import os
import logging
import weave
from services.themes_service import ThemesService

logger = logging.getLogger()
logger.addHandler(logging.FileHandler("/tmp/themify.log"))
logger.setLevel(logging.INFO)
CONTEXT_WINDOW_SIZE = 16000


def main():
    weave.init("themify")
    secretsmanager = boto3.client("secretsmanager")
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId=os.getenv("DB_SECRET_ARN")
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    article_repo = ArticleRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    theme_repo = ThemeRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    openai_client = OpenAIClient(os.environ["OPENAI_API_KEY"])
    themes_service = ThemesService(theme_repo, article_repo, openai_client)
    top_themes = theme_repo.get_top(100)
    for theme in top_themes:
        embedding = (
            theme.embedding
            if theme.embedding is not None
            else openai_client.get_embedding(theme.original_title)
        )
        articles = article_repo.get_by_theme_embedding(embedding)
        try:
            themes_service.build_themes_from_related_articles(articles, ThemeType.TOP)
        except LLMResponseException as e:
            logger.error(f"Failed to build themes from related articles: {e}")


if __name__ == "__main__":
    main()
