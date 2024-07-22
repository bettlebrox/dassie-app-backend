import logging
import boto3
from lambda_init_context import LambdaInitContext

logger = logging.getLogger()
logger.setLevel(logging.INFO)
secretsmanager = boto3.client("secretsmanager")

init_context = None


def lambda_handler(event, context, theme_repo=None):
    logger.info("Event: {} Context: {}".format(event, context))
    global init_context
    if init_context is None:
        init_context = LambdaInitContext(theme_repo=theme_repo)
    theme_repo = init_context.theme_repo
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        title = event["path"].split("/")[-1]
        if title != "themes":
            theme = theme_repo.get_by_title(title.lower())
            if theme is None:
                response["statusCode"] = 404
                response["body"] = {"message": "Theme not found"}
                return response
            theme_repo.delete(theme)
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    return response
