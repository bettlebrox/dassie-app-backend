from unittest.mock import MagicMock

import pytest
from lambda_init_context import LambdaInitContext
from process_theme_graph import lambda_handler
from dotenv import load_dotenv
import os

GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.skipif(GITHUB_ACTIONS, reason="no environment yet")
def test_process_theme_graph_success():
    assert load_dotenv("tests/integ/lambda/local.env")
    init_context = LambdaInitContext(release="test")
    context = MagicMock()
    response = lambda_handler(
        {"body": '{"title": "history+prediction+markets"}'},
        context,
        article_repo=init_context.article_repo,
        neptune_client=init_context.neptune_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
