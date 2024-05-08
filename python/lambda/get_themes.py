from urllib.parse import unquote_plus
import logging
import boto3
import os
import json
from repos import ThemeRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secretsmanager = boto3.client("secretsmanager")
get_secret_value_response = secretsmanager.get_secret_value(
    SecretId=os.environ["DB_SECRET_ARN"]
)
secret = json.loads(get_secret_value_response["SecretString"])


def lambda_handler(event, context):
    try:
        params = event["queryStringParameters"]
        sort_field = (
            params["sortField"]
            if params is not None and "sortField" in params
            else "top"
        )
        title = event["path"].split("/")[-1]
        logger.debug("Event: {} Context: {}".format(event, context))
        theme_repo = ThemeRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        result = []
        success_response = {"statusCode": 200, "body": None}
        if title != "themes":
            theme = theme_repo.get_by_title(unquote_plus(title))
            if theme is not None:
                success_response["body"] = theme.json(related=True)
                return success_response

        # return all themes
        if sort_field == "top":
            result = theme_repo.get_top(10)
        else:
            result = theme_repo.get_recent(15)
        success_response["body"] = "[{}]".format(
            ",".join([theme.json() for theme in result])
        )
        return success_response
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        return {"statusCode": 500, "body": {"message": str(error)}}
