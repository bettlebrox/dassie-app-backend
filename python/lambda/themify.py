from datetime import datetime, timedelta
from theme_repo import ThemeRepository
from browse_repo import BrowseRepository
from models.theme import ThemeType
from article_repo import ArticleRepository
from services.openai_client import LLMResponseException, OpenAIClient
import boto3
import json
import os
from services.themes_service import ThemesService
from aws_lambda_powertools import Logger
import logging

logger = Logger(service="themify", log_record_order=["message"])
logger.addHandler(logging.FileHandler("/tmp/themify.log"))
logger.setLevel(logging.INFO)

CONTEXT_WINDOW_SIZE = 16000


def main():
    secretsmanager = boto3.client("secretsmanager")
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId=os.getenv("DB_SECRET_ARN")
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    article_repo = ArticleRepository(
        secret["username"],
        secret["password"],
        "dassie",
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    theme_repo = ThemeRepository(
        secret["username"],
        secret["password"],
        "dassie",
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    browse_repo = BrowseRepository(
        secret["username"],
        secret["password"],
        "dassie",
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    openai_client = OpenAIClient(
        os.environ["OPENAI_API_KEY"], os.environ["LANGFUSE_KEY"]
    )
    themes_service = ThemesService(theme_repo, article_repo, openai_client)
    top_themes = theme_repo.get_top(100)
    for theme in top_themes:
        try:
            if (
                theme.source == ThemeType.TOP
                and theme.updated_at > datetime.now() - timedelta(days=30)
            ):
                logger.info(
                    "Skipping theme",
                    extra={
                        "theme_title": theme.original_title,
                        "reason": "updated_recently",
                    },
                )
                continue
            themes_service.build_theme_from_related_articles(
                theme.related, ThemeType.TOP, theme.original_title
            )
        except LLMResponseException as e:
            logger.exception(
                "Failed to build themes from related articles",
                extra={
                    "theme_title": theme.original_title,
                    "error": str(e),
                },
            )
    recent_browses = browse_repo.get_recently_browsed(days=7)
    for browse in recent_browses:
        if len(browse.articles) > 5:
            if browse.title is None:
                themes_service.build_theme_from_related_articles(
                    browse.articles, ThemeType.TAB_THREAD
                )
            else:
                themes_service.build_theme_from_related_articles(
                    browse.articles, ThemeType.SEARCH_TERM, browse.title
                )


if __name__ == "__main__":
    main()
