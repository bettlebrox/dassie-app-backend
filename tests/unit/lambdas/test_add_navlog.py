"""
File: test_add_todo.py
Description: Runs a test for our 'add_todo' Lambda
"""

import os
import boto3
import json
import pytest
from moto import mock_aws
from add_navlog import lambda_handler


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["DDB_TABLE"] = "DDB_TABLE"


def test_initialization(aws_credentials):
    event = {}
    context = None

    os.environ["DDB_TABLE"] = ""

    payload = lambda_handler(event, context)

    assert payload["statusCode"] == 500


def test_empty_event(aws_credentials):
    event = {}
    context = None

    payload = lambda_handler(event, context)

    assert payload["statusCode"] == 400


@mock_aws
def test_missing_title(aws_credentials):
    event = {"body": '{ "not_title": "test" }'}
    context = None

    payload = lambda_handler(event, context)

    body = json.loads(payload["body"])

    assert (
        body["message"]
        == "Missing required keys:['title', 'type', 'tabId', 'timestamp', 'documentId']"
    )


@mock_aws
def test_valid_navlog_request(aws_credentials):
    event = {
        "body": '{"type":"content","title":"New Tab","tabId":"529522941","body_text":"some text","body_inner_html":"\\"\\"<script aria-hidden=\\"true\\" nonce=\\"\\">window.wiz_progress&&window.wiz_progress(); ", "timestamp":"1710432439145.628","documentId":"BCD99AE78F0EAA0A1D1B4BE9D1AE9825","url":"chrome://new-tab-page/","transitionType":"typed"}'
    }
    context = None
    create_mock_ddb_table()

    os.environ["DDB_TABLE"] = "DDB_TABLE"

    payload = lambda_handler(event, context)

    assert payload["statusCode"] == 201
    json_payload_body = json.loads(payload["body"])
    json_event_body = json.loads(event["body"])
    assert json_payload_body["body_text"] == json_event_body["body_text"]


@mock_aws
def test_valid_navlog_nobodyhtml_request(aws_credentials):
    event = {
        "body": '{"type":"navigation","title":"New Tab","tabId":"529522941", "timestamp":"1710432439145.628","documentId":"BCD99AE78F0EAA0A1D1B4BE9D1AE9825","url":"chrome://new-tab-page/","transitionType":"typed"}'
    }
    context = None
    create_mock_ddb_table()
    os.environ["DDB_TABLE"] = "DDB_TABLE"
    payload = lambda_handler(event, context)
    assert payload["statusCode"] == 201


@mock_aws
def create_mock_ddb_table():
    mock_ddb = boto3.resource("dynamodb")
    mock_ddb.create_table(
        TableName="DDB_TABLE",
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
    )
    mock_ddb_table = mock_ddb.Table("DDB_TABLE")

    todo = {
        "id": "123",
        "completed": False,
        "created_at": "2022-10-20T18:58:52.548072",
        "title": "Testing",
    }

    mock_ddb_table.put_item(Item=todo)

    return mock_ddb_table
