import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""
lambda_handler is the entry point for the Lambda function.

It retrieves all items from the DynamoDB table specified in the 
DDB_TABLE environment variable, and returns them in the response.

If any errors occur, it will return a 500 status code with the 
error message.
"""


def lambda_handler(event, context):
    try:
        logger.info("Event: {}".format(event))
        table_name = os.getenv("DDB_TABLE")
        bucket_name = os.getenv("BUCKET_NAME")
        if not table_name:
            raise Exception("Table name missing")
        dynamodb = boto3.resource("dynamodb")
        ddb_table = dynamodb.Table(table_name)
        logger.info("Scanning table: {}".format(table_name))
        items = ddb_table.scan()
        logger.info("DDB Response: {}".format(items))
        if "Items" in items:
            navlogs = add_presignedurls(items["Items"], bucket_name)
            response = {"statusCode": 200, "body": json.dumps(navlogs)}
        else:
            response = {"statusCode": items["HTTPStatusCode"]}
        logger.info("Response: %s", response)
        return response
    except Exception as error:
        logger.info("Error: {}".format(error))
        return {"statusCode": 500, "body": {"message": error}}


def add_presignedurls(navlogs, bucket_name):
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
                logger.error(f"Error getting presigned url {error}", exc_info=True)
    return navlogs
