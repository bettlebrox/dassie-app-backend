import json
import os
import logging
import boto3

from lambda_init_context import LambdaInitContext
from theme_repo import ThemeRepository
from models import ThemeType
from repos import ArticleRepository
from services.openai_client import OpenAIClient
from services.themes_service import ThemesService


logger = logging.getLogger()
logger.setLevel(logging.INFO)


init_context = None


def lambda_handler(
    event,
    context,
    article_repo=None,
    openai_client=None,
    theme_service=None,
    useGlobal=True,
):
    try:
        logger.info("Event: {} Context: {}".format(event, context))
        response = {"statusCode": 201, "headers": {"Access-Control-Allow-Origin": "*"}}
        global init_context
        if init_context is None or not useGlobal:
            init_context = LambdaInitContext(
                article_repo=article_repo,
                openai_client=openai_client,
                theme_service=theme_service,
            )
        article_repo = init_context.article_repo
        openai_client = init_context.openai_client
        theme_service = init_context.theme_service
        try:
            payload = json.loads(event["body"])
            logger.info("Payload: {}".format(payload))
            title = payload["title"]
        except Exception as error:
            logger.error(
                "error: {}".format(error.msg if type(error) == ValueError else error)
            )
            response["body"] = json.dumps({"message": "Bad Request"})
            response["statusCode"] = 400
            return response
        embedding = openai_client.get_embedding(title)
        related = article_repo.get_by_theme_embedding(embedding)
        themes = theme_service.build_themes_from_related_articles(
            related, ThemeType.CUSTOM, title, embedding
        )
        response["body"] = '{{"themes": [{}]}}'.format(
            ",".join(theme.json() for theme in themes)
        )
        return response
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["statusCode"] = 500
        response["body"] = json.dumps({"message": str(error)})
        return response
