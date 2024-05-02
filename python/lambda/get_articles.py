import logging
import boto3
import os
import json
from repos import ArticleRepository

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
        sort_order = (
            params["sortOrder"]
            if params is not None and "sortOrder" in params
            else "asc"
        )
        article_id = event["path"].split("/")[-1]
        logger.debug("Event: {} Context: {}".format(event, context))
        article_repo = ArticleRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        result = []
        success_response = {"statusCode": 200, "body": None}
        if article_id != "articles":
            # get a specific article
            article = article_repo.get_by_id(article_id)
            if article is not None:
                success_response["body"] = article.json()
                return success_response

        result = article_repo.get_last_7days()
        success_response["body"] = "[{}]".format(
            ",".join([article.json() for article in result])
        )
        return success_response
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        return {"statusCode": 500, "body": {"message": str(error)}}
