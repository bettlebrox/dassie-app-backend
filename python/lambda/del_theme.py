import json
import os
import logging
from urllib.parse import unquote_plus
import boto3
from repos import ThemeRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)
secretsmanager = boto3.client("secretsmanager")


def lambda_handler(event, context):
    logger.info("Event: {} Context: {}".format(event, context))
    logger.info("getting secret value: " + os.environ["DB_SECRET_ARN"])
    logger.info(secretsmanager)
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId=os.environ["DB_SECRET_ARN"]
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    theme_repo = ThemeRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.environ["DB_CLUSTER_ENDPOINT"],
    )
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        title = event["path"].split("/")[-1]
        if title != "themes":
            theme = theme_repo.get_by_title(unquote_plus(title))
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
