import json
import os
import logging
import boto3
import psycopg2
import uuid
import sys
import pkg_resources


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        logger.info("Event: {}".format(event))
        installed_packages = pkg_resources.working_set
        installed_packages_list = sorted(
            ["%s==%s" % (i.key, i.version) for i in installed_packages]
        )
        logger.info("packages:{}".format(installed_packages_list))
        logger.info("path: {}".format(sys.path))
        logger.info("Getting secret {}".format(os.environ["DB_SECRET_ARN"]))
        secretsmanager = boto3.client("secretsmanager")
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"]
        )
        secret = json.loads(get_secret_value_response["SecretString"])
        # Connect to Aurora
        conn = psycopg2.connect(
            host=os.environ["DB_CLUSTER_ENDPOINT"],
            user=secret["username"],
            password=secret["password"],
            dbname=secret["dbname"],
        )
        try:
            payload = json.loads(event["body"])
            logger.info("Payload: {}".format(payload))
        except Exception as error:
            logger.error(
                "error: {}".format(error.msg if type(error) == ValueError else error)
            )
            return {"statusCode": 400, "body": json.dumps({"message": "Bad Request"})}
        with open("ddl.sql", "r") as file:
            ddl_query = file.read()
        cur = conn.cursor()
        logger.info("Creating themes table")
        cur.execute(ddl_query)
        logger.info("Table created")
        # Insert JSON into a table
        insert_query = (
            """INSERT INTO theme (id,title,summary,url) VALUES (%s,%s,%s,%s)"""
        )
        id = str(uuid.uuid4())
        cur = conn.cursor()
        cur.execute(
            insert_query,
            (id, payload["title"], payload["summary"], payload["url"]),
        )
        conn.commit()
        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "id": id,
                    "title": payload["title"],
                    "summary": payload["summary"],
                    "url": payload["url"],
                }
            ),
        }
    except Exception as error:
        logger.error("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": str(error)}}
