from unittest.mock import MagicMock
import pytest
from get_themes import lambda_handler

from models.theme import ThemeType


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.fixture
def theme_repo():
    return MagicMock()


@pytest.fixture(scope="function")
def openai_client():
    openai_client = MagicMock()
    return openai_client


def test_get_themes(theme_repo, openai_client, mock_context):
    response = lambda_handler(
        {"path": "/themes"},
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200


def test_get_theme(theme_repo, openai_client, mock_context):
    response = lambda_handler(
        {"path": "/themes/whats+the+best+way+to+add+google+id+with+cognito%3F"},
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200


def test_get_themes_with_invalid_params(theme_repo, openai_client, mock_context):
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "made_up_sort_field", "max": 20},
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 400
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"source": "made_up_type", "max": 20},
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 400


def test_get_themes_with_params(theme_repo, openai_client, mock_context):
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "count_association", "max": 20},
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    theme_repo.get.assert_called_with(
        20,
        [ThemeType.TOP],  # default is TOP
        filter_embedding=None,
        sort_by="count_association",
        recent_browsed_days=0,
    )
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "updated_at", "max": 20},
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    theme_repo.get.assert_called_with(
        20,
        [ThemeType.TOP],  # default is TOP
        filter_embedding=None,
        sort_by="updated_at",
        recent_browsed_days=0,
    )
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "recently_browsed", "max": 20},
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    assert (
        response["statusCode"] == 200
    ), "should be able to get themes by recently browsed"
    theme_repo.get.assert_called_with(
        20,
        [ThemeType.TOP],  # default is TOP
        filter_embedding=None,
        sort_by="recently_browsed",
        recent_browsed_days=14,
    )
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {
                "sortField": "updated_at",
                "source": "custom",
                "max": 2,
            },
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    theme_repo.get.assert_called_with(
        2,
        [ThemeType.CUSTOM],
        filter_embedding=None,
        sort_by="updated_at",
        recent_browsed_days=0,
    )
    assert response["statusCode"] == 200
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {
                "sortField": "updated_at",
                "source": "custom,top",
                "max": 2,
            },
        },
        mock_context,
        theme_repo,
        openai_client,
        useGlobal=False,
    )
    theme_repo.get.assert_called_with(
        2,
        [ThemeType.CUSTOM, ThemeType.TOP],
        filter_embedding=None,
        sort_by="updated_at",
        recent_browsed_days=0,
    )
    assert response["statusCode"] == 200
