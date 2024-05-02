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
import wandb

logger = logging.getLogger("root")
logger.addHandler(logging.FileHandler("/tmp/sumit.log"))
logger.setLevel(logging.DEBUG)

DB_CLUSTER_ENDPOINT = "todoappbackendstack-nwbxl-dassie2b404273-65op3qscf7nd.cluster-c9w86oa4s60z.eu-west-1.rds.amazonaws.com"
DDB_TABLE = "TodoAppBackendStack-nwbxl-navlogDB0A59EC5D-CJ3HCDHHL44L"
BUCKET_NAME = "todoappbackendstack-nwbxl-navlogimages0c68e55c-3ywwdtenerym"


def main():
    wandb.init(project="sumit")
    navlog_service = NavlogService(BUCKET_NAME, DDB_TABLE)
    navlogs = navlog_service.get_content_navlogs()
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
    for navlog in tqdm(navlogs, total=len(navlogs)):
        try:
            article = article_repo.upsert(Article(navlog["title"], "", navlog["url"]))
            if article.summary == "" or article.created_at < datetime.now() - timedelta(
                days=7
            ):
                body = navlog["body_text"]
                if len(body) < 100:
                    pass
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
