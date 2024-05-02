import json
import boto3
from boto3.dynamodb.conditions import Key
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class NavlogService:

    def __init__(self, bucket_name, table_name) -> None:
        self._dynamodb = boto3.resource("dynamodb")
        self._bucket_name = bucket_name
        self._table_name = table_name

    def get_navlogs(self):
        ddb_table = self._dynamodb.Table(self._table_name)
        items = ddb_table.scan()
        return json.dumps(items["Items"])

    def put_navlog(self, navlog):
        ddb_table = self._dynamodb.Table(self._table_name)
        ddb_table.put_item(Item=navlog)
        return json.dumps(navlog)

    def get_content_navlogs(self):
        ddb_table = self._dynamodb.Table(self._table_name)
        response = ddb_table.query(
            IndexName="type-index", KeyConditionExpression=Key("type").eq("content")
        )
        items = response["Items"]

        while "LastEvaluatedKey" in response:
            response = ddb_table.query(
                IndexName="type-index",
                KeyConditionExpression=Key("type").eq("content"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items += response["Items"]

        return items

    def _add_presignedurls(self, navlogs):
        for navlog in navlogs:
            if "image" in navlog and navlog["image"] is not None:
                image_key = navlog["image"]
                bucket_name, key = image_key.replace("s3://", "").split("/", 1)
                try:
                    navlog["image"] = boto3.client("s3").generate_presigned_url(
                        "get_object",
                        Params={
                            "Bucket": self._bucket_name,
                            "Key": key,
                        },
                    )
                except Exception as error:
                    logger.error(f"Error getting presigned url {error}", exc_info=True)
        return navlogs
