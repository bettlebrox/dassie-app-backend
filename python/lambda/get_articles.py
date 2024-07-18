import logging
import boto3
import os
import json
from repos import ArticleRepository
from services.openai_client import OpenAIClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VALID_SORT_ORDERS = ["asc", "desc"]
VALID_SORT_FIELDS = [
    "title",
    "updated_at",
    "created_at",
    "logged_at",
    "count_association",
]


def init(article_repo=None, openai_client=None):
    secretsmanager = boto3.client("secretsmanager")
    if article_repo is None:
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"]
        )
        secret = json.loads(get_secret_value_response["SecretString"])
        article_repo = ArticleRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
    if openai_client is None:
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId=os.environ["OPENAIKEY_SECRET_ARN"]
        )
        openaikey_secret = json.loads(get_secret_value_response["SecretString"])
        openai_client = (
            (
                OpenAIClient(openaikey_secret["OPENAI_API_KEY"])
                if openai_client is None
                else openai_client
            )
            if openai_client is None
            else openai_client
        )
    return article_repo, openai_client


def lambda_handler(event, context, article_repo=None, openai_client=None):
    article_repo, openai_client = init(article_repo, openai_client)
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        sort_field = "updated_at"
        max = 10
        sort_order = "desc"
        filter = ""
        filter_embedding = None
        params = (
            event["queryStringParameters"]
            if "queryStringParameters" in event
            and event["queryStringParameters"] is not None
            else {"max": max, "sortField": sort_field}
        )
        sort_field = (
            params["sortField"].lower() if "sortField" in params else sort_field
        )
        sort_order = (
            params["sortOrder"].lower() if "sortOrder" in params else sort_order
        )
        filter = params["filter"] if "filter" in params else filter
        max = int(params["max"]) if "max" in params else max
        if sort_order not in VALID_SORT_ORDERS:
            raise ValueError("Invalid sort order")
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
        if filter is not None and filter != "":
            filter_embedding = openai_client.get_embedding(filter)
        logger.info("filter: {}".format(filter))
        result = article_repo.get(
            limit=max,
            sort_by=sort_field,
            descending=sort_order == "desc",
            filter_embedding=filter_embedding,
        )
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
