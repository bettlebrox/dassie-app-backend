from models import Theme, ThemeType
from repos import ArticleRepository, ThemeRepository
from services.openai_client import OpenAIClient
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
    articles = article_repo.get_last_days(15)
    logger.info("Got {} articles".format(len(articles)))
    themes_service.build_themes_from_articles(articles, ThemeType.TOP)


if __name__ == "__main__":
    main()
