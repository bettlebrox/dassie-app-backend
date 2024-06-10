from urllib.parse import unquote_plus
import logging
import boto3
import os
import json
from models import ThemeType
from repos import ThemeRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def init():
    secretsmanager = boto3.client("secretsmanager")
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
    return theme_repo


def lambda_handler(event, context, theme_repo=None):
    logger.debug("Event: {} Context: {}".format(event, context))
    try:
        theme_repo = init() if theme_repo is None else theme_repo
        sort_field = "updated_at"
        max = 10
        params = (
            event["queryStringParameters"]
            if "queryStringParameters" in event
            and event["queryStringParameters"] is not None
            else {"max": max, "sortField": sort_field}
        )
        sort_field = params["sortField"] if "sortField" in params else sort_field
        source = ThemeType(params["source"]) if "source" in params else ThemeType.TOP
        result = []
        max = int(params["max"]) if "max" in params else "max"
        title = event["path"].split("/")[-1]
        success_response = {"statusCode": 200, "body": None}
        if title != "themes":
            theme = theme_repo.get_by_title(unquote_plus(title))
            if theme is not None:
                success_response["body"] = theme.json(related=True)
                return success_response

        # return all themes
        if sort_field == "count_association":
            result = theme_repo.get_top(max, source)
        elif sort_field == "updated_at":
            result = theme_repo.get_recent(max, source)
        else:
            raise ValueError("Invalid sort field: {}".format(sort_field))
        success_response["body"] = "[{}]".format(
            ",".join([theme.json() for theme in result])
        )
        return success_response
    except ValueError as error:
        logger.error("ValueError: {}".format(error))
        return {"statusCode": 400, "body": {"message": str(error)}}
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        return {"statusCode": 500, "body": {"message": str(error)}}
