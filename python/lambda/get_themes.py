from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker
import logging
import boto3
import os
import json
import datetime
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, uuid.UUID):
                # if the obj is uuid, we simply return the value of uuid
                return str(obj)
            elif isinstance(obj, datetime):
                # if obj is a datetime, convert it to a string in ISO 8601 format
                return obj.isoformat()
        except Exception as error:
            logger.error("Encoder error: {}".format(error))
        return super().default(obj)


def lambda_handler(event, context):
    try:
        logger.info("Event wenny themes: {}".format(event))
        secretsmanager = boto3.client("secretsmanager")
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"]
        )
        secret = json.loads(get_secret_value_response["SecretString"])
        # Connect to Aurora
        engine = create_engine(
            f"postgresql://{secret['username']}:{secret['password']}@{os.environ['DB_CLUSTER_ENDPOINT']}/{secret['dbname']}"
        )
        Session = sessionmaker(bind=engine)
        session = Session()
        metadata = MetaData()
        theme = Table("theme", metadata, autoload_with=engine)
        result = session.query(theme).all()
        logger.info("Result: {}".format(result[0]))
        return {
            "statusCode": 200,
            "body": "really good good good good",
        }
    except Exception as error:
        logger.info("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": str(error)}}
