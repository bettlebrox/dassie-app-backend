import json
import boto3
from boto3.dynamodb.conditions import Key
from dassie_logger import logger


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

    def delete_navlog(self, navlog_id):
        ddb_table = self._dynamodb.Table(self._table_name)
        ddb_table.delete_item(Key={"id": navlog_id})
        return True

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

    def _add_presigned_urls(self, navlogs):
        for navlog in navlogs:
            if "image" in navlog and navlog["image"] is not None:
                image_key = navlog["image"]
                _, key = image_key.replace("s3://", "").split("/", 1)
                try:
                    navlog["image"] = boto3.client("s3").generate_presigned_url(
                        "get_object",
                        Params={
                            "Bucket": self._bucket_name,
                            "Key": key,
                        },
                    )
                except Exception:
                    logger.exception("Error getting presigned url")
        return navlogs
