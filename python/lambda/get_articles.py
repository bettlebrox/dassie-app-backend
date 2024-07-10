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
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        article_id = event["path"].split("/")[-1]
        logger.debug("Event: {} Context: {}".format(event, context))
        article_repo = ArticleRepository(
            secret["username"],
            secret["password"],
            secret["dbname"],
            os.environ["DB_CLUSTER_ENDPOINT"],
        )
        result = []
        response["body"] = None
        if article_id != "articles":
            # get a specific article
            article = article_repo.get_by_id(article_id)
            if article is not None:
                response["body"] = article.json()
                return response
        result = article_repo.get_last_7days()
        response["body"] = "[{}]".format(
            ",".join([article.json() for article in result])
        )
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["body"] = {"message": str(error)}
        response["statusCode"] = 500
    return response
