from models import Theme, ThemeType
from repos import ArticleRepository, ThemeRepository
from services.openai_client import OpenAIClient
import boto3
import json
import os
import logging
import wandb
from services.themes_service import ThemesService

logger = logging.getLogger()
logger.addHandler(logging.FileHandler("/tmp/themify.log"))
logger.setLevel(logging.INFO)
CONTEXT_WINDOW_SIZE = 16000


def main():
    wandb.init(project="themify")
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
    try:
        window = []
        window_size = 0
        article_window_size = OpenAIClient.CONTEXT_WINDOW_SIZE // 8
        for i, art in enumerate(articles):
            art_text = art.text
            article_size = openai_client.count_tokens(art_text)
            if OpenAIClient.CONTEXT_WINDOW_SIZE - window_size < article_window_size:
                article_window_size = OpenAIClient.CONTEXT_WINDOW_SIZE - window_size
            while article_size > article_window_size:
                art_text = art_text[: len(art_text) // 2]
                article_size = openai_client.count_tokens(art_text)
                logger.info(
                    f"window size: {window_size}, target article window size:{article_window_size}. Reducing article size to {len(art_text)} token size {article_size}"
                )
            window.append(art_text)
            window_size = window_size + article_size
            if (
                window_size
                >= OpenAIClient.CONTEXT_WINDOW_SIZE
                - OpenAIClient.CONTEXT_WINDOW_SIZE // 8
                or len(articles) == i + 1
            ):
                summary = openai_client.get_theme_summarization(window)
                if summary is not None:
                    theme = Theme(title=summary["title"], summary=summary["summary"])
                    theme.source = ThemeType.TOP
                    themes_service.build_theme_from_summary(theme, summary)
                window = []
                window_size = 0
                article_window_size = OpenAIClient.CONTEXT_WINDOW_SIZE // 8
            else:
                logger.info(
                    f"Window not full, articles processed:{i} window size: {window_size}"
                )
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)


if __name__ == "__main__":
    main()
