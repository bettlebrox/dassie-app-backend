from random import random
from uuid import uuid4
import boto3
import json
import urllib3
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../"))

from app import stack_name
import pytest

test_id = ""
random_title = ""


@pytest.fixture()
def apiEndpoint() -> str:
    return get_api_endpoint(stack_name)


"""Tests getting all navlogs from the API endpoint.

Verifies the endpoint returns 200 status and the expected response.
"""


def test_get_all_navlogs(apiEndpoint: str):

    stackName = stack_name
    http = urllib3.PoolManager(num_pools=3)

    if not apiEndpoint:
        apiEndpoint = get_api_endpoint(stackName)

    # Testing getting all todos
    response = http.request("GET", apiEndpoint)

    assert response.status == 200


def test_add_todo(apiEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)

    global random_title
    random_title = "Integration Testing {}".format(uuid4().hex)

    todo = json.dumps(
        {
            "type": "content",
            "title": random_title,
            "tabId": "529522941",
            "timestamp": "1710432439145.628",
            "documentId": "BCD99AE78F0EAA0A1D1B4BE9D1AE9825",
            "transitionType": "typed",
            "body_text": "some text from doc",
            "url": "https://bob.com",
            "body_inner_html": '\\"\\"<script aria-hidden=\\"true\\" nonce=\\"\\">window.wiz_progress&&window.wiz_progress;',
        }
    )

    response = http.request(
        "POST", apiEndpoint, headers={"Content-Type": "application/json"}, body=todo
    )

    assert (
        response.status == 201
    ), f"""
        body: {response.data}
        {response.status} != 201
        """


def get_api_endpoint(stackName):
    cloudFormationClient = boto3.client("cloudformation", region_name="eu-west-1")
    stack = cloudFormationClient.describe_stacks(StackName=stackName)

    stack = stack["Stacks"][0]

    apiEndpoint = next(
        item for item in stack["Outputs"] if item["OutputKey"] == "ApiEndpoint"
    )

    apiEndpoint = apiEndpoint["OutputValue"] + "/api"

    return apiEndpoint + "/navlogs"
