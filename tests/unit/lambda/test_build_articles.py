import json
from unittest.mock import MagicMock
from datetime import datetime, timedelta

import pytest
from build_articles import lambda_handler


@pytest.fixture(scope="function")
def article_service():
    return MagicMock()


@pytest.fixture(scope="function")
def navlog_service():
    return MagicMock()


@pytest.fixture(scope="function")
def mock_context():
    return MagicMock()


def test_build_articles_success(article_service, navlog_service, mock_context):
    event = {}

    navlog = {
        "body_text": "This is a test body text that is long enough to be processed. this must be longer than 100 characters",
        "url": "https://example.com",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    navlog_service.get_content_navlogs.return_value = [navlog]

    response = lambda_handler(
        event,
        mock_context,
        article_service=article_service,
        navlog_service=navlog_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    article_service.process_navlog.assert_called_once_with(navlog)


def test_build_articles_skip_short_text(article_service, navlog_service, mock_context):
    event = {}

    navlog = {
        "body_text": "Short",
        "url": "https://example.com",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    navlog_service.get_content_navlogs.return_value = [navlog]

    response = lambda_handler(
        event,
        mock_context,
        article_service=article_service,
        navlog_service=navlog_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    article_service.process_navlog.assert_not_called()


def test_build_articles_skip_old_navlog(article_service, navlog_service, mock_context):
    event = {}

    old_date = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S.%f")
    navlog = {
        "body_text": "This is a test body text that is long enough to be processed.",
        "url": "https://example.com",
        "created_at": old_date,
    }
    navlog_service.get_content_navlogs.return_value = [navlog]

    response = lambda_handler(
        event,
        mock_context,
        article_service=article_service,
        navlog_service=navlog_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    article_service.process_navlog.assert_not_called()


def test_build_articles_error_handling(article_service, navlog_service, mock_context):
    event = {}

    navlog = {
        "body_text": "This is a test body text that is long enough to be processed. this must be longer than 100 characters",
        "url": "https://example.com",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    navlog_service.get_content_navlogs.return_value = [navlog]
    article_service.process_navlog.side_effect = Exception("Test error")

    response = lambda_handler(
        event,
        mock_context,
        article_service=article_service,
        navlog_service=navlog_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 207
    assert "body" in response
    assert "message" in response["body"]
    body = json.loads(response["body"])
    assert str(body["message"]) == "Articles processed successfully"
    assert str(body["errors"]) == "1"
