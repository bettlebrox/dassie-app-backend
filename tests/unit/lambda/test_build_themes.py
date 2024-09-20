import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pytest
from build_themes import lambda_handler
from models.theme import Theme, ThemeType
from models.browse import Browse
from models.article import Article
from services.openai_client import LLMResponseException


@pytest.fixture
def mock_theme_service():
    return MagicMock()


@pytest.fixture
def mock_browse_repo():
    return MagicMock()


@pytest.fixture
def mock_theme_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def mock_context():
    return MagicMock()


def test_lambda_handler_success(
    mock_theme_service, mock_browse_repo, mock_theme_repo, mock_context
):
    # Setup
    mock_theme_service.theme_repo = mock_theme_repo
    mock_theme = Theme(original_title="Test Theme")
    mock_article = Article(original_title="Test Article", url="https://example.com")
    mock_article._created_at = datetime.now()
    mock_theme.related = [mock_article]
    mock_theme_repo.get.return_value = [mock_theme]

    mock_browse = Browse(title="Test Browse", tab_id="123")
    mock_browse._articles = [mock_article, mock_article, mock_article, mock_article]
    mock_browse_repo.get_recently_browsed.return_value = [mock_browse]

    # Execute
    result = lambda_handler(
        {},
        mock_context,
        theme_service=mock_theme_service,
        browse_repo=mock_browse_repo,
        useGlobal=False,
    )
    # Assert
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["processed_top_themes"] == 1
    assert body["processed_browses"] == 1
    assert body["errors_top_themes"] == 0
    assert body["errors_browses"] == 0


def test_lambda_handler_llm_exception(
    mock_theme_service, mock_browse_repo, mock_theme_repo, mock_context
):
    # Setup
    mock_theme_service.theme_repo = mock_theme_repo
    mock_theme = Theme(original_title="Test Theme")
    mock_article = Article(original_title="Test Article", url="https://example.com")
    mock_article._created_at = datetime.now()
    mock_theme.related = [mock_article]
    mock_theme_repo.get.return_value = [mock_theme]

    mock_theme_service.build_theme_from_related_articles.side_effect = (
        LLMResponseException("LLM Error")
    )

    # Execute
    result = lambda_handler(
        {},
        mock_context,
        theme_service=mock_theme_service,
        browse_repo=mock_browse_repo,
        useGlobal=False,
    )

    # Assert
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["processed_top_themes"] == 0
    assert body["errors_top_themes"] == 1


def test_lambda_handler_general_exception(
    mock_theme_service, mock_browse_repo, mock_theme_repo, mock_context
):
    # Setup
    mock_theme_service.theme_repo = mock_theme_repo
    mock_theme_repo.get.side_effect = Exception("General Error")

    # Execute
    result = lambda_handler(
        {},
        mock_context,
        theme_service=mock_theme_service,
        browse_repo=mock_browse_repo,
        useGlobal=False,
    )

    # Assert
    assert result["statusCode"] == 500
    body = json.loads(result["body"])
    assert "Internal server error" in body["message"]


def test_lambda_handler_no_recent_articles(
    mock_theme_service, mock_browse_repo, mock_theme_repo, mock_context
):
    # Setup
    mock_theme_service.theme_repo = mock_theme_repo
    mock_theme = Theme(original_title="Test Theme")
    mock_article = Article(original_title="Test Article", url="https://example.com")
    mock_article._created_at = datetime.now() - timedelta(hours=2)  # Older than 1 hour
    mock_theme.related = [mock_article]
    mock_theme_repo.get_top.return_value = [mock_theme]

    # Execute
    result = lambda_handler(
        {},
        mock_context,
        theme_service=mock_theme_service,
        browse_repo=mock_browse_repo,
        useGlobal=False,
    )

    # Assert
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["processed_top_themes"] == 0
    assert body["errors_top_themes"] == 0
