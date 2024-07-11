from urllib.parse import unquote_plus
import logging
import boto3
import os
import json
from models import ThemeType
from repos import ThemeRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)
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


def lambda_handler(event, context):
    logger.debug("Event: {} Context: {}".format(event, context))
    logger.info("getting secret value: " + os.environ["DB_SECRET_ARN"])
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
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
        response["body"] = None
        if title != "themes":
            theme = theme_repo.get_by_title(unquote_plus(title))
            if theme is not None:
                response["body"] = theme.json(related=True)
                return response

        # return all themes
        if sort_field == "count_association":
            result = theme_repo.get_top(max, source)
        elif sort_field == "updated_at":
            result = theme_repo.get_recent(max, source)
        else:
            raise ValueError("Invalid sort field: {}".format(sort_field))
        response["body"] = "[{}]".format(",".join([theme.json() for theme in result]))
    except ValueError as error:
        logger.error("ValueError: {}".format(error))
        response["statusCode"] = 400
        response["body"] = {"message": str(error)}
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    return response
