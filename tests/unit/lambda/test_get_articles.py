import json
from unittest.mock import MagicMock

import pytest
from get_articles import lambda_handler
from models.article import Article


@pytest.fixture(scope="function")
def article_repo():
    article_repo = MagicMock()
    return article_repo


@pytest.fixture(scope="function")
def openai_client():
    openai_client = MagicMock()
    return openai_client


@pytest.fixture(scope="function")
def mock_context():
    return MagicMock()


def test_get_articles_with_query_params(article_repo, openai_client, mock_context):
    event = {
        "queryStringParameters": {"max": "5", "sortField": "created_at"},
        "path": "/articles",
    }
    response = lambda_handler(
        event, mock_context, article_repo=article_repo, openai_client=openai_client
    )
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert response["body"].startswith("[") and response["body"].endswith("]")


def test_get_specific_article(article_repo, openai_client, mock_context):
    event = {"path": "/articles/123"}
    test_article = Article("test article", "https://bob.com")
    test_article._id = 123
    article_repo.get_by_id.return_value = test_article
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert json.loads(response["body"])["id"] == str(test_article.id)


def test_get_non_existent_article(article_repo, openai_client, mock_context):
    event = {"path": "/articles/999"}
    article_repo.get_by_id.return_value = None
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 404
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert response["body"] is None


def test_get_articles_with_invalid_query_params(
    article_repo, openai_client, mock_context
):
    event = {
        "queryStringParameters": {"max": "invalid", "sortField": "invalid_field"},
        "path": "/articles",
    }
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 400
    assert "message" in response["body"]


def test_get_articles_with_no_query_params(article_repo, openai_client, mock_context):
    event = {"path": "/articles"}
    article_repo.get.return_value = [Article("test article", "https://bob.com")]
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert len(json.loads(response["body"])) > 0


def test_get_articles_with_database_error(article_repo, openai_client, mock_context):
    event = {"path": "/articles"}
    article_repo.get.side_effect = Exception("Database connection error")
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 500
    assert "message" in response["body"]
    assert "Database connection error" in response["body"]["message"]


def test_get_articles_with_sort_order(article_repo, openai_client, mock_context):
    event = {
        "queryStringParameters": {"sortField": "created_at", "sortOrder": "ASC"},
        "path": "/articles",
    }
    article_repo.get.return_value = [Article("test article", "https://example.com")]
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    article_repo.get.assert_called_with(
        limit=10,
        sort_by="created_at",
        descending=False,
        filter_embedding=None,
        min_token_count=0,
    )


def test_get_articles_with_invalid_sort_order(
    article_repo, openai_client, mock_context
):
    event = {
        "queryStringParameters": {"sortOrder": "INVALID"},
        "path": "/articles",
    }
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 400
    assert "Invalid sort order" in response["body"]["message"]


def test_get_articles_with_invalid_sort_field(
    article_repo, openai_client, mock_context
):
    event = {
        "queryStringParameters": {"sortField": "invalid_field"},
        "path": "/articles",
    }
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 400
    assert "Invalid sort field" in response["body"]["message"]


def test_get_articles_with_default_params(article_repo, openai_client, mock_context):
    event = {"path": "/articles", "queryStringParameters": None}
    article_repo.get.return_value = [Article("test article", "https://example.com")]
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    article_repo.get.assert_called_with(
        limit=10,
        sort_by="updated_at",
        descending=True,
        filter_embedding=None,
        min_token_count=0,
    )


def test_get_articles_empty_result(article_repo, openai_client, mock_context):
    event = {"path": "/articles"}
    article_repo.get.return_value = []
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    assert response["body"] == "[]"


def test_get_articles_with_filter_embedding(article_repo, openai_client, mock_context):
    event = {"path": "/articles"}
    test_article = Article("test article", "https://example.com")
    article_repo.get.return_value = [test_article]
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    assert response["body"] == f"[{test_article.json()}]"


def test_get_articles_by_browse(article_repo, openai_client, mock_context):
    event = {
        "path": "/articles",
        "queryStringParameters": {"sortField": "browse"},
    }
    test_article = Article("test article", "https://example.com")
    article_repo.get.return_value = [test_article]
    response = lambda_handler(
        event,
        mock_context,
        article_repo=article_repo,
        openai_client=openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    assert response["body"] == f"[{test_article.json()}]"
