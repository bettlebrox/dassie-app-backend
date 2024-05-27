from datetime import datetime, timedelta
from models import Article
from repos import ArticleRepository, ThemeRepository
from services.navlogs_service import NavlogService
from services.openai_client import OpenAIClient
from tqdm.auto import tqdm
import boto3
import json
import os
import logging
import weave

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logger = logging.getLogger("root")
handler = logging.FileHandler("/tmp/sumit.log")
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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
    for navlog in tqdm(navlogs, total=len(navlogs)):
        try:
            body = navlog["body_text"]
            if len(body) < 100:
                pass
            article = article_repo.upsert(Article(navlog["title"], "", navlog["url"]))
            if article.summary == "" or article.created_at < datetime.now() - timedelta(
                days=30
            ):
                article_summary = openai_client.get_article_summarization(
                    navlog["body_text"]
                )
                article.source_navlog = navlog["id"]
                embedding = openai_client.get_embedding(navlog["body_text"])
                article.embedding = embedding
                if article_summary is not None:
                    article.summary = article_summary["summary"]
                article.logged_at = datetime.strptime(
                    navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
                )
                article.text = navlog["body_text"]
                if "image" in navlog and navlog["image"] is not None:
                    article.image = navlog["image"]
                article = article_repo.update(article)
                if article_summary is not None:
                    theme_repo.add_related(article, article_summary["themes"])
        except Exception as error:
            logger.error(error, exc_info=True)


if __name__ == "__main__":
    main()
