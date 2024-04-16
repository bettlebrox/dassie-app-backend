from datetime import datetime, timedelta
from models import Theme, ThemeType
from repos import ArticleRepository, ThemeRepository
from services.navlogs_service import NavlogService
from services.openai_client import OpenAIClient
from tqdm.auto import tqdm
import boto3
import json
import os
import logging

logger = logging.getLogger()
logger.addHandler(logging.FileHandler("/tmp/themify.log"))
logger.setLevel(logging.INFO)
CONEXT_WINDOW_SIZE = 16000
DB_CLUSTER_ENDPOINT = "todoappbackendstack-nwbxl-dassie2b404273-65op3qscf7nd.cluster-c9w86oa4s60z.eu-west-1.rds.amazonaws.com"


def main():
    secretsmanager = boto3.client("secretsmanager")
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId="dassieSecret79403E04-ffZ6841JZBj3"
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    article_repo = ArticleRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        DB_CLUSTER_ENDPOINT,
    )
    theme_repo = ThemeRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        DB_CLUSTER_ENDPOINT,
    )
    openai_client = OpenAIClient(os.environ["OPENAI_API_KEY"])
    articles = article_repo.get_last_days(15)
    try:
        window = []
        window_size = 0
        article_window_size = OpenAIClient.CONEXT_WINDOW_SIZE // 8
        for i, art in enumerate(articles):
            art_text = art.text
            article_size = openai_client.count_tokens(art_text)
            if OpenAIClient.CONEXT_WINDOW_SIZE - window_size < article_window_size:
                article_window_size = OpenAIClient.CONEXT_WINDOW_SIZE - window_size
            while article_size > article_window_size:
                art_text = art_text[: len(art_text) // 2]
                article_size = openai_client.count_tokens(art_text)
            logger.info(
                f"Processing article tokens: {len(art_text)} of {len(art.text)}"
            )
            window.append(art_text)
            window_size = window_size + article_size
            if window_size >= OpenAIClient.CONEXT_WINDOW_SIZE or len(articles) == i + 1:
                summ = openai_client.get_theme_summarization(window)
                if summ is not None:
                    theme = Theme(title=summ["title"], summary=summ["summary"])
                    theme_embedding = openai_client.get_embedding(theme.title)
                    theme.source = ThemeType.TOP
                    related_articles = article_repo.get_by_theme_embedding(
                        theme_embedding
                    )
                    theme.related_articles = related_articles
                    theme_repo.add(theme)
                    logger.info("Added theme: {}".format(theme.title))
                window = []
                window_size = 0
                article_window_size = OpenAIClient.CONEXT_WINDOW_SIZE // 8
            else:
                logger.info(
                    f"Window too short, articles processed:{i} window size: {window_size}"
                )
    except Exception as error:
        logger.error("Error: {}".format(error))


if __name__ == "__main__":
    main()
