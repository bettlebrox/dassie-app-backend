import json
from unittest.mock import MagicMock
from datetime import datetime, timedelta

import pytest
from build_articles import lambda_handler
from models.article import Article


@pytest.fixture(scope="function")
def navlog_service():
    return MagicMock()


@pytest.fixture(scope="function")
def mock_context():
    return MagicMock()


@pytest.fixture(scope="function")
def article_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def theme_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def browse_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def browsed_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def openai_client():
    return MagicMock()


@pytest.fixture(scope="function")
def neptune_client():
    return MagicMock()


@pytest.fixture(scope="function")
def opencypher_translator_client():
    return MagicMock()


def test_build_articles_success(
    navlog_service,
    mock_context,
    article_repo,
    theme_repo,
    browse_repo,
    browsed_repo,
    openai_client,
    neptune_client,
    opencypher_translator_client,
):
    event = {}

    navlog = {
        "body_text": "This is a test body text that is long enough to be processed. this must be longer than 100 characters",
        "url": "https://example.com",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "id": "123",
        "title": "Test Title",
        "tabId": "123",
    }
    navlog_service.get_content_navlogs.return_value = [navlog]
    new_article = Article(
        navlog["title"], navlog["url"], navlog["body_text"], navlog["created_at"]
    )
    new_article._created_at = datetime.strptime(
        navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
    )
    new_article._updated_at = datetime.strptime(
        navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f"
    )
    article_repo.get_or_insert.return_value = new_article
    neptune_client.get_article_graph.return_value = []
    response = lambda_handler(
        event,
        mock_context,
        navlog_service=navlog_service,
        article_repo=article_repo,
        theme_repo=theme_repo,
        browse_repo=browse_repo,
        browsed_repo=browsed_repo,
        openai_client=openai_client,
        neptune_client=neptune_client,
        opencypher_translator_client=opencypher_translator_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    opencypher_translator_client.generate_article_graph.assert_called_once()


def test_build_articles_skip_short_text(
    navlog_service,
    mock_context,
    article_repo,
    theme_repo,
    browse_repo,
    browsed_repo,
    openai_client,
    neptune_client,
    opencypher_translator_client,
):
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
        navlog_service=navlog_service,
        article_repo=article_repo,
        theme_repo=theme_repo,
        browse_repo=browse_repo,
        browsed_repo=browsed_repo,
        openai_client=openai_client,
        neptune_client=neptune_client,
        opencypher_translator_client=opencypher_translator_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    opencypher_translator_client.generate_article_graph.assert_not_called()


def test_build_articles_skip_old_navlog(
    navlog_service,
    mock_context,
    article_repo,
    theme_repo,
    browse_repo,
    browsed_repo,
    openai_client,
    neptune_client,
    opencypher_translator_client,
):
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
        navlog_service=navlog_service,
        article_repo=article_repo,
        theme_repo=theme_repo,
        browse_repo=browse_repo,
        browsed_repo=browsed_repo,
        openai_client=openai_client,
        neptune_client=neptune_client,
        opencypher_translator_client=opencypher_translator_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    opencypher_translator_client.generate_article_graph.assert_not_called()


def test_build_articles_error_handling(
    navlog_service,
    mock_context,
    article_repo,
    theme_repo,
    browse_repo,
    browsed_repo,
    openai_client,
    neptune_client,
    opencypher_translator_client,
):
    event = {}

    navlog = {
        "body_text": "This is a test body text that is long enough to be processed. this must be longer than 100 characters",
        "url": "https://example.com",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    }
    navlog_service.get_content_navlogs.return_value = [navlog]
    article_repo.get_or_insert.side_effect = Exception("Test error")

    response = lambda_handler(
        event,
        mock_context,
        navlog_service=navlog_service,
        article_repo=article_repo,
        theme_repo=theme_repo,
        browse_repo=browse_repo,
        browsed_repo=browsed_repo,
        openai_client=openai_client,
        neptune_client=neptune_client,
        opencypher_translator_client=opencypher_translator_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 207
    assert "body" in response
    assert "message" in response["body"]
    body = json.loads(response["body"])
    assert str(body["message"]) == "Articles processed successfully"
    assert str(body["errors"]) == "1"
