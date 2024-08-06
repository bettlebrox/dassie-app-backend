from datetime import datetime, timedelta
from theme_repo import ThemeRepository
from models import Article
from repos import ArticleRepository
from services.navlogs_service import NavlogService
from services.articles_service import ArticlesService
from services.openai_client import OpenAIClient
from tqdm.auto import tqdm
import boto3
import json
import os
import logging
import weave

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logger = logging.getLogger()
handler = logging.FileHandler("/tmp/sumit.log")
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def main():
    weave.init("sumit")
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
    openai_client = OpenAIClient(os.environ["OPENAI_API_KEY"])
    article_service = ArticlesService(article_repo, theme_repo, openai_client)
    for navlog in tqdm(navlogs, total=len(navlogs)):
        try:
            body = navlog["body_text"]
            if (
                len(body) < 100
                or "url" not in navlog
                or datetime.strptime(navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                < datetime.now() - timedelta(days=30)
            ):
                continue
            article = article_repo.upsert(
                Article(
                    navlog["title"],
                    navlog["url"],
                    text=body,
                )
            )
            if article.summary == "" or article.created_at > datetime.now() - timedelta(
                days=10
            ):
                article_service.build_article(article, navlog)
                logger.info("Built article {}".format(article.title))
        except Exception as error:
            logger.error(error, exc_info=True)


if __name__ == "__main__":
    main()
