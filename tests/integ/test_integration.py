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
GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture()
def apiEndpoint() -> str:
    return get_api_endpoint()


@pytest.fixture()
def apiThemeEndpoint() -> str:
    return get_api_endpoint("themes")


@pytest.fixture()
def apiArticleEndpoint() -> str:
    return get_api_endpoint("articles")


"""Tests getting all navlogs from the API endpoint.

Verifies the endpoint returns 200 status and the expected response.
"""


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_get_theme(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    # Testing getting all todos
    response = http.request("GET", apiThemeEndpoint + "/sometitle")
    assert (
        200 == response.status
    ), f"""
    Http status not as expected
    body: {response.data}"""


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_get_all_themes(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    # Testing getting all todos
    response = http.request("GET", apiThemeEndpoint)
    assert (
        200 == response.status
    ), f"""
    Http status not as expected
    body: {response.data}"""


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_add_theme(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    global random_title
    random_title = "the meaning of life, the universe and everything"
    theme = json.dumps(
        {
            "title": random_title,
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


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_add_ontheme_theme(apiThemeEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    global random_title
    random_title = "aws cdk and its use in python"
    theme = json.dumps(
        {
            "id": str(uuid4()),
            "title": random_title,
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
    assert (
        json.loads(response.data.decode("utf-8"))["themes"][0]["original_title"]
        == random_title
    )


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_get_all_articles(apiArticleEndpoint: str):
    http = urllib3.PoolManager(num_pools=3)
    response = http.request("GET", apiArticleEndpoint)
    assert (
        200 == response.status
    ), f"""
    Http status not as expected
    body: {response.data}"""


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
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
            "image": "data:image/jpeg;base64,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",
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


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def get_api_endpoint(resourcename="navlogs"):
    apiEndpoint = LOCAL_API  # PRD_API  # LOCAL_API
    if apiEndpoint.startswith("http://127.0.0.1"):
        warnings.warn(
            "Using local API endpoint for testing. Ensure sam local start-api is running before running tests."
        )
    return apiEndpoint + "/{}".format(resourcename)
