from datetime import datetime, timedelta
from theme_repo import ThemeRepository
from repos import BrowsedRepository
from article_repo import ArticleRepository
from browse_repo import BrowseRepository
from services.navlogs_service import NavlogService
from services.articles_service import ArticlesService
from services.openai_client import OpenAIClient
from tqdm.auto import tqdm
import boto3
import json
import os
from aws_lambda_powertools import Logger

logger = Logger(service="sumit", log_record_order=["message"])


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
    browsed_repo = BrowsedRepository(
        secret["username"],
        secret["password"],
        "dassie",
        os.getenv("DB_CLUSTER_ENDPOINT"),
    )
    openai_client = OpenAIClient(
        os.environ["OPENAI_API_KEY"], os.environ["LANGFUSE_KEY"]
    )
    article_service = ArticlesService(
        article_repo, theme_repo, browse_repo, browsed_repo, openai_client
    )
    for navlog in tqdm(navlogs, total=len(navlogs)):
        try:
            if (
                len(navlog["body_text"]) < 100
                or "url" not in navlog
                or datetime.strptime(navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                < datetime.now() - timedelta(days=7)
            ):
                continue
            article_service.process_navlog(navlog)
        except Exception as error:
            logger.exception(
                f"Error processing navlog", extra={"navlog": navlog, "error": error}
            )


if __name__ == "__main__":
    main()
