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


def test_get_themes(theme_repo, mock_context):
    response = lambda_handler(
        {"path": "/themes"},
        mock_context,
        theme_repo,
        useGlobal=False,
    )
    assert response["statusCode"] == 200


def test_get_theme(theme_repo, mock_context):
    response = lambda_handler(
        {"path": "/themes/whats+the+best+way+to+add+google+id+with+cognito%3F"},
        mock_context,
        theme_repo,
        useGlobal=False,
    )
    assert response["statusCode"] == 200


def test_get_themes_with_invalid_params(theme_repo, mock_context):
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "made_up_sort_field", "max": 20},
        },
        mock_context,
        theme_repo,
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
        useGlobal=False,
    )
    assert response["statusCode"] == 400


def test_get_themes_with_params(theme_repo, mock_context):
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "count_association", "max": 20},
        },
        mock_context,
        theme_repo,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "updated_at", "max": 20},
        },
        mock_context,
        theme_repo,
        useGlobal=False,
    )
    assert response["statusCode"] == 200
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "recently_browsed", "max": 20},
        },
        mock_context,
        theme_repo,
        useGlobal=False,
    )
    assert (
        response["statusCode"] == 200
    ), "should be able to get themes by recently browsed"
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
        useGlobal=False,
    )
    theme_repo.get_recent.assert_called_with(2, [ThemeType.CUSTOM])
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
        useGlobal=False,
    )
    theme_repo.get_recent.assert_called_with(2, [ThemeType.CUSTOM, ThemeType.TOP])
    assert response["statusCode"] == 200
