from datetime import datetime
import json
from aws_lambda_powertools.logging import correlation_paths
import boto3
import os
from botocore.exceptions import ClientError
from dassie_logger import logger

# Initialize AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

BUCKET_NAME = os.environ["BUCKET_NAME"]


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(event, context):
    for record in event["Records"]:
        # Ensure this is a REMOVE event
        if record["eventName"] != "REMOVE":
            continue

        try:
            # Extract the old image (the deleted item)
            old_image = record["dynamodb"]["OldImage"]

            # Convert DynamoDB JSON to regular JSON
            item_data = json.dumps(convert_dynamodb_to_json(old_image))

            # Generate a unique key for S3
            item_id = old_image["id"]["S"]
            timestamp = old_image.get("timestamp", {}).get("S")
            if timestamp:
                # Convert JavaScript timestamp (milliseconds) to seconds
                dt = datetime.fromtimestamp(float(timestamp) / 1000)
                s3_key = (
                    f"archived/{dt.year}/{dt.month:02d}/{dt.day:02d}_{item_id}.json"
                )
            else:
                # Fallback to current date if timestamp is not available
                now = datetime.utcnow()
                s3_key = f"archived/bad_timestamp/{now.year}/{now.month:02d}/{now.day:02d}/{item_id}.json"

            # Upload to S3
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=item_data,
                ContentType="application/json",
            )

            logger.info(
                f"Successfully archived item {item_id} to S3",
                extra={"item_id": item_id, "s3_key": s3_key},
            )

        except ClientError as e:
            logger.exception(
                f"Error archiving item", extra={"item_id": item_id, "s3_key": s3_key}
            )
            # Depending on the error, you might want to re-raise to trigger a Lambda retry
            raise

        except Exception as e:
            logger.exception(
                f"Unexpected error", extra={"item_id": item_id, "s3_key": s3_key}
            )
            # For unexpected errors, it's often safer to raise and let Lambda retry
            raise


def convert_dynamodb_to_json(dynamodb_dict):
    """Convert DynamoDB JSON to regular JSON"""
    result = {}
    for key, value in dynamodb_dict.items():
        if "S" in value:
            result[key] = value["S"]
        elif "N" in value:
            result[key] = float(value["N"])
        elif "BOOL" in value:
            result[key] = value["BOOL"]
        elif "NULL" in value:
            result[key] = None
        elif "L" in value:
            result[key] = [convert_dynamodb_to_json(item) for item in value["L"]]
        elif "M" in value:
            result[key] = convert_dynamodb_to_json(value["M"])
    return result
