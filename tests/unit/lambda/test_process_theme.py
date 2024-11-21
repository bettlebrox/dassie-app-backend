import pytest
import json
from unittest.mock import MagicMock
from process_theme import lambda_handler
from models.theme import Theme, ThemeType
from models.article import Article


@pytest.fixture
def mock_context():
    mock_context = MagicMock()
    mock_context.function_name = "process_theme"
    mock_context.function_version = "1"
    return mock_context


@pytest.fixture
def mock_article_repo():
    return MagicMock()


@pytest.fixture
def mock_openai_client():
    return MagicMock()


@pytest.fixture
def mock_theme_service():
    return MagicMock()


@pytest.fixture
def mock_boto_event_client():
    return MagicMock()


def test_process_theme_success(
    mock_context,
    mock_article_repo,
    mock_openai_client,
    mock_theme_service,
    mock_boto_event_client,
):
    event = {"body": json.dumps({"title": "Test Theme"})}

    test_theme = Theme("Test Theme", source=ThemeType.CUSTOM)
    mock_theme_service.get_theme_by_title.return_value = test_theme

    mock_openai_client.get_embedding.return_value = [0.1, 0.2, 0.3]

    related_articles = [
        Article("Related Article 1", "https://example.com/article1"),
        Article("Related Article 2", "https://example.com/article2"),
    ]
    mock_article_repo.get.return_value = related_articles

    processed_theme = Theme(
        "Test Theme", source=ThemeType.CUSTOM, summary="Processed summary"
    )
    mock_theme_service.build_theme_from_related_articles.return_value = processed_theme

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        openai_client=mock_openai_client,
        theme_service=mock_theme_service,
        useGlobal=False,
        boto_event_client=mock_boto_event_client,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["original_title"] == "Test Theme"
    assert json.loads(response["body"])["summary"] == "Processed summary"


def test_process_theme_not_found(
    mock_context, mock_article_repo, mock_openai_client, mock_theme_service
):
    event = {"body": json.dumps({"title": "Non-existent Theme"})}

    mock_theme_service.get_theme_by_title.return_value = None

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        openai_client=mock_openai_client,
        theme_service=mock_theme_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 404
    assert json.loads(response["body"])["message"] == "Theme not found"


def test_process_theme_failure(
    mock_context, mock_article_repo, mock_openai_client, mock_theme_service
):
    event = {"body": json.dumps({"title": "Test Theme"})}

    test_theme = Theme("Test Theme", source=ThemeType.CUSTOM)
    mock_theme_service.get_theme_by_title.return_value = test_theme

    mock_openai_client.get_embedding.return_value = [0.1, 0.2, 0.3]

    related_articles = [
        Article("Related Article 1", "https://example.com/article1"),
        Article("Related Article 2", "https://example.com/article2"),
    ]
    mock_article_repo.get.return_value = related_articles

    mock_theme_service.build_theme_from_related_articles.return_value = None

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        openai_client=mock_openai_client,
        theme_service=mock_theme_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"])["message"] == "Failed to process theme"


def test_process_theme_exception(
    mock_context, mock_article_repo, mock_openai_client, mock_theme_service
):
    event = {"body": json.dumps({"title": "Test Theme"})}

    mock_theme_service.get_theme_by_title.side_effect = Exception("Unexpected error")

    response = lambda_handler(
        event,
        mock_context,
        article_repo=mock_article_repo,
        openai_client=mock_openai_client,
        theme_service=mock_theme_service,
        useGlobal=False,
    )

    assert response["statusCode"] == 500
    assert "Unexpected error" in json.loads(response["body"])["message"]
