from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Query
from contextlib import closing
import logging
import boto3
import os
import json

from models import Theme

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secretsmanager = boto3.client("secretsmanager")
get_secret_value_response = secretsmanager.get_secret_value(
    SecretId=os.environ["DB_SECRET_ARN"]
)
secret = json.loads(get_secret_value_response["SecretString"])
# Connect to Aurora
engine = create_engine(
    f"postgresql://{secret['username']}:{secret['password']}@{os.environ['DB_CLUSTER_ENDPOINT']}/{secret['dbname']}",
    pool_timeout=30,
)
Session = sessionmaker(bind=engine)


def lambda_handler(event, context):
    with closing(Session()) as session:
        try:
            logger.debug("Event: {} Context: {}".format(event, context))
            result = Query(Theme, session=session).all()
            return {
                "statusCode": 200,
                "body": "[{}]".format(",".join([theme.to_json() for theme in result])),
            }
        except Exception as error:
            logger.info("Error: {}".format(error))
            return {"statusCode": 500, "body": {"message": str(error)}}
