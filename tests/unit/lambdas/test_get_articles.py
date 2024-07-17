import json
from unittest.mock import MagicMock, patch

import pytest
from get_articles import lambda_handler
from models import Article


@pytest.fixture(scope="function")
def article_repo():
    article_repo = MagicMock()
    return article_repo


def test_get_articles_with_query_params(article_repo):
    event = {
        "queryStringParameters": {"max": "5", "sortField": "created_at"},
        "path": "/articles",
    }
    context = {}
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert response["body"].startswith("[") and response["body"].endswith("]")


def test_get_specific_article(article_repo):
    event = {"path": "/articles/123"}
    context = {}
    test_article = Article("test article", "https://bob.com")
    test_article._id = 123
    article_repo.get_by_id.return_value = test_article
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert json.loads(response["body"])["id"] == str(test_article.id)


def test_get_non_existent_article(article_repo):
    event = {"path": "/articles/999"}
    context = {}
    article_repo.get_by_id.return_value = None
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 404
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert response["body"] is None


def test_get_articles_with_invalid_query_params(article_repo):
    event = {
        "queryStringParameters": {"max": "invalid", "sortField": "invalid_field"},
        "path": "/articles",
    }
    context = {}
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 400
    assert "message" in response["body"]


def test_get_articles_with_no_query_params(article_repo):
    event = {"path": "/articles"}
    context = {}
    article_repo.get.return_value = [Article("test article", "https://bob.com")]
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert len(json.loads(response["body"])) > 0


def test_get_articles_with_database_error(article_repo):
    event = {"path": "/articles"}
    context = {}
    article_repo.get.side_effect = Exception("Database connection error")
    response = lambda_handler(event, context, article_repo=article_repo)
    assert response["statusCode"] == 500
    assert "message" in response["body"]
    assert "Database connection error" in response["body"]["message"]
