from contextlib import closing
import json
import os
import logging
import boto3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Theme


logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
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
    Base.metadata.create_all(engine)
except Exception as error:
    logger.error("Aurora Setup Error: {}".format(error))


def lambda_handler(event, context):
    try:
        logger.info("Event: {} Context: {}".format(event, context))
        try:
            payload = json.loads(event["body"])
            logger.info("Payload: {}".format(payload))
        except Exception as error:
            logger.error(
                "error: {}".format(error.msg if type(error) == ValueError else error)
            )
            return {"statusCode": 400, "body": json.dumps({"message": "Bad Request"})}
        with closing(Session()) as session:
            theme = Theme(payload["title"], payload["summary"])
            session.add(theme)
            session.commit()
            return {"statusCode": 201, "body": theme.json()}
    except Exception as error:
        logger.error("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": str(error)}}
