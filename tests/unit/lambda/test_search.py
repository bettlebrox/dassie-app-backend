import json
import unittest
from unittest.mock import MagicMock, patch

import pytest
from search import lambda_handler


@pytest.fixture(autouse=True)
def mock_context():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_article_repo():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_theme_repo():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_openai_client():
    return MagicMock()


def test_search_with_query(
    mock_context, mock_article_repo, mock_theme_repo, mock_openai_client
):
    event = {"pathParameters": {"query": "test query"}}

    mock_openai_client.get_embedding.return_value = [0.1, 0.2, 0.3]

    mock_article = MagicMock()
    mock_article.json.return_value = {"id": "1", "title": "Test Article"}
    mock_article_repo.get.return_value = [(mock_article, 0.9)]

    mock_theme = MagicMock()
    mock_theme.json.return_value = {"id": "1", "title": "Test Theme"}
    mock_theme_repo.get.return_value = [(mock_theme, 0.9)]

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        theme_repo=mock_theme_repo,
        openai_client=mock_openai_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    search_result = json.loads(response["body"])
    assert "articles" in search_result
    assert "themes" in search_result
    assert len(search_result["articles"]) == 1
    assert len(search_result["themes"]) == 1


def test_search_without_query(
    mock_context, mock_article_repo, mock_theme_repo, mock_openai_client
):
    event = {"pathParameters": {}}

    mock_openai_client.get_embedding.return_value = [0.1, 0.2, 0.3]

    mock_article_repo.get.return_value = []
    mock_theme_repo.get.return_value = []

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        theme_repo=mock_theme_repo,
        openai_client=mock_openai_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 200
    search_result = json.loads(response["body"])
    assert "articles" in search_result
    assert "themes" in search_result
    assert len(search_result["articles"]) == 0
    assert len(search_result["themes"]) == 0


def test_search_with_exception(
    mock_context, mock_article_repo, mock_theme_repo, mock_openai_client
):
    event = {"pathParameters": {"query": "test query"}}

    mock_openai_client.get_embedding.side_effect = Exception("Test exception")

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        theme_repo=mock_theme_repo,
        openai_client=mock_openai_client,
        useGlobal=False,
    )

    assert response["statusCode"] == 500
    assert "message" in response["body"]
    assert response["body"]["message"] == "Test exception"
