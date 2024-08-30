import json
import os
import boto3
from dassie_logger import logger

"""
lambda_handler is the entry point for the Lambda function.

It retrieves all items from the DynamoDB table specified in the 
DDB_TABLE environment variable, and returns them in the response.

If any errors occur, it will return a 500 status code with the 
error message.
"""


def lambda_handler(event, context):
    try:
        logger.debug("get_navlogs")
        table_name = os.getenv("DDB_TABLE")
        bucket_name = os.getenv("BUCKET_NAME")
        if not table_name:
            raise Exception("Table name missing")
        dynamodb = boto3.resource("dynamodb")
        ddb_table = dynamodb.Table(table_name)
        logger.debug("Scanning table", extra={"table_name": table_name})
        items = ddb_table.scan()
        logger.debug("DDB Response", extra={"items": items})
        if "Items" in items:
            navlogs = add_presigned_urls(items["Items"], bucket_name)
            response = {"statusCode": 200, "body": json.dumps(navlogs)}
        else:
            response = {"statusCode": items["HTTPStatusCode"]}
        logger.debug("Response", extra={"response": response})
        return response
    except Exception as error:
        logger.exception("Error")
        return {"statusCode": 500, "body": {"message": error}}


def add_presigned_urls(navlogs, bucket_name):
    for navlog in navlogs:
        if "image" in navlog:
            image_key = navlog["image"]
            try:
                navlog["image"] = boto3.client("s3").generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": bucket_name,
                        "Key": image_key,
                    },
                )
            except Exception as error:
                logger.exception("Error getting presigned url", extra={"error": error})
    return navlogs
