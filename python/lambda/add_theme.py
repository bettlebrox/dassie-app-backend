from contextlib import closing
import json
import os
import logging
import boto3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Theme, ThemeType
from repos import ArticleRepository, ThemeRepository
from services.openai_client import OpenAIClient
from services.themes_service import ThemesService


logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    secretsmanager = boto3.client("secretsmanager")
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId=os.environ["DB_SECRET_ARN"]
    )
    secret = json.loads(get_secret_value_response["SecretString"])
except Exception as error:
    logger.error("Aurora Setup Error: {}".format(error))


def lambda_handler(event, context):
    try:
        logger.info("Event: {} Context: {}".format(event, context))
        theme_repo = ThemeRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        article_repo = ArticleRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        try:
            payload = json.loads(event["body"])
            logger.info("Payload: {}".format(payload))
            title = payload["title"]
        except Exception as error:
            logger.error(
                "error: {}".format(error.msg if type(error) == ValueError else error)
            )
            return {"statusCode": 400, "body": json.dumps({"message": "Bad Request"})}
        openai_client = OpenAIClient(os.environ["OPENAI_API_KEY"])
        themes_service = ThemesService(theme_repo, article_repo, openai_client)
        embedding = openai_client.get_embedding(title)
        related = article_repo.get_by_theme_embedding(embedding)
        themes = themes_service.build_themes_from_articles(
            related, ThemeType.CUSTOM, title
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"themes": [theme.json() for theme in themes]}),
        }
    except Exception as error:
        logger.error("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": str(error)}}
