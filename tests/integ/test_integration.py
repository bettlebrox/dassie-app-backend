from random import random
from uuid import uuid4
import boto3
import json
import urllib3
import sys
import os
import warnings


import pytest

test_id = ""
random_title = ""
LOCAL_API = "http://127.0.0.1:3000/api"
PRD_API = "https://p5cgnlejzk.execute-api.eu-west-1.amazonaws.com/prod"


@pytest.fixture()
def apiEndpoint() -> str:
    return get_api_endpoint()


@pytest.fixture()
def apiThemeEndpoint() -> str:
    return get_api_endpoint("themes")


"""Tests getting all navlogs from the API endpoint.

Verifies the endpoint returns 200 status and the expected response.
"""


def test_get_theme(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    # Testing getting all todos
    response = http.request("GET", apiThemeEndpoint + "/sometitle")
    assert (
        200 == response.status
    ), f"""
    Http status not as expected
    body: {response.data}"""


def test_get_all_themes(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    # Testing getting all todos
    response = http.request("GET", apiThemeEndpoint)
    assert (
        200 == response.status
    ), f"""
    Http status not as expected
    body: {response.data}"""


def test_add_theme(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    global random_title
    random_title = "Integration Testing {}".format(uuid4().hex)
    theme = json.dumps(
        {
            "id": str(uuid4()),
            "title": random_title,
            "summary": "some summary of {}".format(random_title),
            "url": "https://bob.com",
        }
    )
    response = http.request(
        "POST",
        apiThemeEndpoint,
        headers={"Content-Type": "application/json"},
        body=theme,
    )
    assert (
        response.status == 201
    ), f"""
        body: {response.data}
        """


def test_add_navlog(apiEndpoint: str):
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
        """


def get_api_endpoint(resourcename="navlogs"):
    apiEndpoint = LOCAL_API  # PRD_API  # LOCAL_API
    if apiEndpoint.startswith("http://127.0.0.1"):
        warnings.warn(
            "Using local API endpoint for testing. Ensure sam local start-api is running before running tests."
        )
    return apiEndpoint + "/{}".format(resourcename)
