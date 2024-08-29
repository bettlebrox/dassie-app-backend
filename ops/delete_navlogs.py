import boto3
from boto3.dynamodb.conditions import Attr


def delete_all_items(table_name):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Scan the table
    response = table.scan()
    items = response["Items"]

    # Delete items in batches
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={"id": item["id"]}  # Assuming 'id' is your primary key
            )

    # Check if there are more items to scan
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items = response["Items"]
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"id": item["id"]})

    print("All items have been deleted.")


# Usage
table_name = "TodoAppBackendStack-nwbxl-navlogDB0A59EC5D-CJ3HCDHHL44L"
delete_all_items(table_name)
