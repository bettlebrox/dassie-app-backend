"""
File: test_add_todo.py
Description: Runs a test for our 'add_todo' Lambda
"""

import os
from unittest.mock import MagicMock
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


@pytest.fixture(scope="function")
def mock_context():
    context = MagicMock()
    context.function_name = "test"
    context.memory_limit_in_mb = "128"
    context.aws_request_id = "1234567890123456789"
    context.log_group_name = "test"
    context.log_stream_name = "test"
    return context


def test_initialization(mock_context):
    event = {}

    os.environ["DDB_TABLE"] = ""

    payload = lambda_handler(event, mock_context)

    assert payload["statusCode"] == 500


def test_empty_event(aws_credentials, mock_context):
    event = {}

    payload = lambda_handler(event, mock_context)

    assert payload["statusCode"] == 400


@mock_aws
def test_missing_title(aws_credentials, mock_context):
    event = {"body": '{ "not_title": "test" }'}

    payload = lambda_handler(event, mock_context)

    body = json.loads(payload["body"])

    assert (
        body["message"]
        == "Missing required keys:['title', 'type', 'tabId', 'timestamp', 'documentId']"
    )


@mock_aws
def test_valid_navlog_request(aws_credentials, mock_context):
    event = {
        "body": '{"type":"content","title":"New Tab","tabId":"529522941","body_text":"some text","body_inner_html":"\\"\\"<script aria-hidden=\\"true\\" nonce=\\"\\">window.wiz_progress&&window.wiz_progress(); ", "timestamp":"1710432439145.628","documentId":"BCD99AE78F0EAA0A1D1B4BE9D1AE9825","url":"chrome://new-tab-page/","transitionType":"typed"}'
    }
    create_mock_ddb_table()

    os.environ["DDB_TABLE"] = "DDB_TABLE"

    payload = lambda_handler(event, mock_context)

    assert payload["statusCode"] == 201
    json_payload_body = json.loads(payload["body"])
    json_event_body = json.loads(event["body"])
    assert json_payload_body["body_text"] == json_event_body["body_text"]


@mock_aws
def test_valid_navlog_nobodyhtml_request(aws_credentials, mock_context):
    event = {
        "body": '{"type":"navigation","title":"New Tab","tabId":"529522941", "timestamp":"1710432439145.628","documentId":"BCD99AE78F0EAA0A1D1B4BE9D1AE9825","url":"chrome://new-tab-page/","transitionType":"typed"}'
    }
    create_mock_ddb_table()
    os.environ["DDB_TABLE"] = "DDB_TABLE"
    payload = lambda_handler(event, mock_context)
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
