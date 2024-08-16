from datetime import datetime, timedelta
from theme_repo import ThemeRepository
from models.article import Article
from repos import (
    ArticleRepository,
    BasePostgresRepository,
    BrowseRepository,
    BrowsedRepository,
)
from services.navlogs_service import NavlogService
from services.articles_service import ArticlesService
from services.openai_client import OpenAIClient
from tqdm.auto import tqdm
import boto3
import json
import os
import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logger = logging.getLogger()
handler = logging.FileHandler("/tmp/sumit_long.log")
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def main():
    navlog_service = NavlogService(os.getenv("BUCKET_NAME"), os.getenv("DDB_TABLE"))
    navlogs = navlog_service.get_content_navlogs()
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
    browse_repo = BrowseRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    browsed_repo = BrowsedRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    openai_client = OpenAIClient(
        os.environ["OPENAI_API_KEY"], os.environ["LANGFUSE_KEY"]
    )
    article_service = ArticlesService(
        article_repo, theme_repo, browse_repo, browsed_repo
    )
    for navlog in tqdm(navlogs, total=len(navlogs)):
        try:
            body = navlog["body_text"]
            if (
                len(body) < 100
                or "url" not in navlog
                or datetime.strptime(navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                < datetime.now() - timedelta(days=90)
            ):
                continue
            article = article_repo.get_or_insert(
                Article(
                    navlog["title"],
                    navlog["url"],
                    text=body,
                )
            )
            if article.summary == "" or article.created_at < datetime.now() - timedelta(
                days=90
            ):
                article = article_service.build_article_from_navlog(article, navlog)
                article_service.add_llm_summarisation(
                    article,
                    openai_client.get_article_summarization(article.text),
                    openai_client.get_embedding(article.text),
                    openai_client.count_tokens(article.text),
                )
                logger.info("Built article {}".format(article.title))
            article_service.track_browsing(article, navlog)
        except Exception as error:
            logger.error(f"{error} navlog:{navlog}", exc_info=True)


if __name__ == "__main__":
    main()
