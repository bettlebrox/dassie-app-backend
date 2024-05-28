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


def init(article_repo=None, theme_repo=None, openai_client=None, themes_service=None):
    try:
        secretsmanager = boto3.client("secretsmanager")
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"]
        )
        secret = json.loads(get_secret_value_response["SecretString"])
        db_params = (
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        article_repo = (
            ArticleRepository(*db_params) if article_repo is None else article_repo
        )
        theme_repo = ThemeRepository(*db_params) if theme_repo is None else theme_repo
        return (
            article_repo,
            (
                openai_client
                if openai_client is not None
                else OpenAIClient(os.environ["OPENAI_API_KEY"])
            ),
            (
                themes_service
                if themes_service is not None
                else ThemesService(theme_repo, article_repo, openai_client)
            ),
        )
    except Exception as error:
        logger.error("Aurora Setup Error: {}".format(error))


def lambda_handler(
    event,
    context,
    article_repo=None,
    theme_repo=None,
    openai_client=None,
    themes_service=None,
):
    try:
        logger.info("Event: {} Context: {}".format(event, context))
        article_repo, openai_client, themes_service = init(
            article_repo, theme_repo, openai_client, themes_service
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
        embedding = openai_client.get_embedding(title)
        related = article_repo.get_by_theme_embedding(embedding)
        themes = themes_service.build_themes_from_articles(
            related, ThemeType.CUSTOM, title
        )
        return {
            "statusCode": 201,
            "body": json.dumps({"themes": [theme.json() for theme in themes]}),
        }
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        return {"statusCode": 500, "body": {"message": str(error)}}
