import json
import logging
import os
import datetime
import boto3
import uuid
import base64
import io

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REQUIRED_KEYS = ["title", "type", "tabId", "timestamp", "documentId"]
BUCKET_NAME = "todoappbackendstack-nwbxl-navlogimages0c68e55c-3ywwdtenerym"

"""
lambda_handler handles the API request to add a new navlog item to DynamoDB.

It validates the request body contains the required keys, constructs a navlog item, 
and saves it to DynamoDB. Returns 201 on success, 400 for bad requests, or 500 on errors.
"""


def lambda_handler(event, context):
    try:
        logger.info("Event: {}".format(event))
        identity = "unauthorized"
        if (
            "requestContext" in event
            and "identity" in event["requestContext"]
            and "cognitoIdentityId" in event["requestContext"]["identity"]
        ):
            token = event["requestContext"]["identity"]["cognitoIdentityId"]
            logger.info("requestContext : {}".format(token))
            identity = token.replace(":", "_")
        table_name = os.getenv("DDB_TABLE")
        bucket_name = os.getenv("BUCKET_NAME")
        if not table_name:
            raise Exception("Table name missing")
        dynamodb = boto3.resource("dynamodb")
        ddb_table = dynamodb.Table(table_name)
        logger.info("Adding navlog to table: {}".format(table_name))
        try:
            payload = json.loads(event["body"])
        except Exception as error:
            logger.error(
                "error: {}".format(error.msg if type(error) == ValueError else error)
            )
            return {"statusCode": 400, "body": json.dumps({"message": "Bad Request"})}
        keys = payload.keys()
        missing_keys = [x for x in REQUIRED_KEYS if x not in keys]
        if len(missing_keys) > 0:
            logger.error("Missing required keys: {}".format(missing_keys))
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"message": "Missing required keys:{0}".format(missing_keys)}
                ),
            }
        navlog = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.datetime.now().isoformat(),
            "title": payload["title"],
            "type": payload["type"],
            "tabId": payload["tabId"],
            "timestamp": payload["timestamp"],
            "documentId": payload["documentId"],
            "body_inner_html": (
                payload["body_inner_html"] if payload["type"] == "content" else None
            ),
            "body_text": (
                payload["body_text"] if payload["type"] == "content" else None
            ),
            "url": payload["url"],
        }
        if "image" in payload:
            image_key = save_to_s3(
                bucket_name, payload["image"], navlog["id"], identity
            )
            navlog["image"] = image_key
        ddb_response = ddb_table.put_item(Item=navlog)
        logger.info("DDB Response: {}".format(ddb_response))
        response = {"statusCode": 201, "body": json.dumps(navlog)}
        logger.info("Response: %s", response)
        return response

    except Exception as error:
        logger.error("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": error}}


def save_to_s3(
    bucket_name,
    base64_string,
    uuid,
    iam_id="unauthorized",
):
    try:
        # assume simple format for now
        bb64 = base64_string.split("data:image/jpeg;base64,")[1]
        binary = base64.b64decode(bb64)
        s3 = boto3.client("s3")
        key = f"{iam_id}/{uuid}.jpg"
        s3.upload_fileobj(io.BytesIO(binary), bucket_name, key)
        return f"s3://{bucket_name}/{key}"
    except Exception as error:
        logger.error(f"Error: {error}", exc_info=True)
