import json
import boto3
from boto3.dynamodb.conditions import Key


class NavlogService:
    TABLE_NAME = "TodoAppBackendStack-nwbxl-navlogDB0A59EC5D-CJ3HCDHHL44L"

    def __init__(self) -> None:
        self.dynamodb = boto3.resource("dynamodb")

    def get_navlogs(self):
        ddb_table = self.dynamodb.Table(self.TABLE_NAME)
        items = ddb_table.scan()
        return json.dumps(items["Items"])

    def put_navlog(self, navlog):
        ddb_table = self.dynamodb.Table(self.TABLE_NAME)
        ddb_table.put_item(Item=navlog)
        return json.dumps(navlog)

    def get_content_navlogs(self):
        ddb_table = self.dynamodb.Table(self.TABLE_NAME)
        items = ddb_table.query(
            IndexName="type-index", KeyConditionExpression=Key("type").eq("content")
        )
        return items["Items"]
