import logging
import boto3
import os
import json
from repos import ArticleRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VALID_SORT_FIELDS = [
    "title",
    "updated_at",
    "created_at",
    "logged_at",
    "count_association",
]


def init_article_repo():
    secretsmanager = boto3.client("secretsmanager")
    get_secret_value_response = secretsmanager.get_secret_value(
        SecretId=os.environ["DB_SECRET_ARN"]
    )
    secret = json.loads(get_secret_value_response["SecretString"])
    return ArticleRepository(
        secret["username"],
        secret["password"],
        secret["dbname"],
        os.environ["DB_CLUSTER_ENDPOINT"],
    )


def lambda_handler(event, context, article_repo=None):
    article_repo = init_article_repo() if article_repo is None else article_repo
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
        max = int(params["max"]) if "max" in params else max
        if sort_field not in VALID_SORT_FIELDS:
            raise ValueError("Invalid sort field")
        article_id = event["path"].split("/")[-1]
        logger.debug("Event: {} Context: {}".format(event, context))
        result = []
        response["body"] = None
        if article_id != "articles":
            # get a specific article
            article = article_repo.get_by_id(article_id)
            if article is not None:
                response["body"] = article.json()
            else:
                response["statusCode"] = 404
            return response
        result = article_repo.get(limit=max, sort_by=sort_field)
        response["body"] = "[{}]".format(
            ",".join([article.json() for article in result])
        )
    except ValueError as error:
        logger.error("ValueError: {}".format(error), exc_info=True)
        response["body"] = {"message": str(error)}
        response["statusCode"] = 400
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["body"] = {"message": str(error)}
        response["statusCode"] = 500
    return response
