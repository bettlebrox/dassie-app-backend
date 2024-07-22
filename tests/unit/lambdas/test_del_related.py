from unittest.mock import MagicMock

import pytest
from del_related import lambda_handler


@pytest.fixture(scope="function")
def theme_repo():
    theme_repo = MagicMock()
    return theme_repo


def test_del_related_article(theme_repo):
    theme_repo.get_by_title.return_value = MagicMock(
        title="whats+the+best+way+to+add+google+id+with+cognito"
    )
    lambda_handler(
        {
            "path": "/themes/whats+the+best+way+to+add+google+id+with+cognito/related_articles/1234123-2afdsdf-2323-1234",
            "pathParameters": {
                "title": "whats+the+best+way+to+add+google+id+with+cognito",
                "article_id": "1234123-2afdsdf-2323-1234",
            },
        },
        {},
        theme_repo,
        useGlobal=False,
    )
    theme_repo.del_related.assert_called_once()


def test_del_related_theme_not_found(theme_repo):
    event = {
        "pathParameters": {
            "title": "non_existent_theme",
            "article_id": "1234123-2afdsdf-2323-1234",
        }
    }
    theme_repo.get_by_title.return_value = None

    response = lambda_handler(event, {}, theme_repo, useGlobal=False)

    assert response["statusCode"] == 404
    assert response["body"] == {"message": "Theme not found"}


def test_del_related_success(theme_repo):
    event = {
        "pathParameters": {
            "title": "existing_theme",
            "article_id": "1234123-2afdsdf-2323-1234",
        }
    }
    mock_theme = MagicMock()
    mock_theme._id = "theme_id_123"
    theme_repo.get_by_title.return_value = mock_theme

    response = lambda_handler(event, {}, theme_repo, useGlobal=False)

    assert response["statusCode"] == 204
    theme_repo.del_related.assert_called_with(
        theme=mock_theme, article_id="1234123-2afdsdf-2323-1234"
    )


def test_del_related_exception(theme_repo):
    event = {
        "pathParameters": {
            "title": "existing_theme",
            "article_id": "1234123-2afdsdf-2323-1234",
        }
    }
    theme_repo.get_by_title.side_effect = Exception("Database error")

    response = lambda_handler(event, {}, theme_repo, useGlobal=False)

    assert response["statusCode"] == 500
    assert response["body"] == {"message": "Database error"}
