from typing import Any
from unittest.mock import MagicMock

import pytest
from theme_repo import ThemeRepository
from models.models import Association
from models.article import Article
from models.theme import Theme
from sqlalchemy.orm.exc import NoResultFound


@pytest.fixture
def repo():
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = MagicMock()
    return repo


@pytest.fixture
def mock_query(repo: ThemeRepository) -> Any:
    return repo._session.return_value.query.return_value


def test_get_recently_browsed_themes(repo: ThemeRepository, mock_query: Any):
    # Mock the query result
    art1 = Article(original_title="Test Article 1", url="https://example.com")
    art2 = Article(original_title="Test Article 2", url="https://example.com")
    art1._id = 1
    art2._id = 2
    article_query = (
        mock_query.filter.return_value.join.return_value.group_by.return_value.all
    )
    article_query.return_value = [
        art1,
        art2,
    ]
    theme_query = (
        mock_query.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit
    )
    theme_query.return_value = [Theme(original_title="Test Theme")]
    results = repo.get_recently_browsed()
    assert len(results) == 1
    assert results[0].original_title == "Test Theme"
    assert (Association.article_id.in_([art.id for art in [art1, art2]])).compare(
        mock_query.join.return_value.filter.call_args[0][0]
    )
    article_query.assert_called_once()
    theme_query.assert_called_once()


def test_get_all_themes(repo: ThemeRepository, mock_query: Any):
    # Mock the query result
    mock_query.all.return_value = [
        Theme(original_title="Test Theme 1"),
        Theme(original_title="Test Theme 2"),
    ]

    # Call the get_all method
    themes = repo.get_all()

    # Assert the result
    assert len(themes) == 2
    assert themes[0].original_title == "Test Theme 1"
    assert themes[1].original_title == "Test Theme 2"


def test_get_theme_by_title(repo: ThemeRepository, mock_query: Any):
    mock_query.options.return_value.filter.return_value.first.return_value = [
        Theme(original_title="Test Theme")
    ]

    # Call the get_by_title method
    theme = repo.get_by_title("test+theme")

    # Assert the result
    assert theme.original_title == "Test Theme"


def test_get_theme_by_titles(repo: ThemeRepository, mock_query: Any):
    # Mock the query result
    mock_query.filter.return_value.all.return_value = [
        Theme(original_title="Test Theme")
    ]

    # Call the get_by_titles method
    themes = repo.get_by_original_titles(["Test Theme"])

    # Assert the result
    assert len(themes) == 1
    assert themes[0].original_title == "Test Theme"


def test_add_related_theme(repo: ThemeRepository, mock_query: Any):
    theme = Theme(original_title="Test Theme")
    mock_query.options.return_value.filter.return_value.first.return_value = [theme]
    mock_query.filter.return_value.first.return_value = None

    # Create a new article and theme
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Call the add_related method
    association = repo.add_related(article, ["test+theme"])

    # Assert that the theme was added and the association was created
    repo._session.return_value.add.assert_called()
    repo._session.return_value.commit.assert_called()
    assert association[0].article_id == article._id
    assert association[0].theme_id == theme._id


def test_del_related_article(repo: ThemeRepository, mock_query: Any):
    theme = Theme(original_title="Test Theme")
    test_article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    theme.related = [test_article]
    repo.del_related(test_article.id, theme)
    assert (Association.article_id == test_article._id).compare(
        mock_query.filter.call_args[0][0]
    )
    assert (Association.theme_id == theme._id).compare(
        mock_query.filter.call_args[0][1]
    )
    mock_query.filter.return_value.delete.assert_called()


def test_upsert_existing_theme(repo: ThemeRepository, mock_query: Any):
    existing_theme = Theme(original_title="Existing Theme")
    existing_theme._id = 1
    mock_query.options.return_value.filter.return_value.one.return_value = (
        existing_theme
    )

    updated_theme = Theme(original_title="Updated Theme")
    updated_theme._id = 1
    repo._session.return_value.merge.return_value = updated_theme
    result = repo.upsert(updated_theme)

    assert result.original_title == "Updated Theme"
    repo._session.return_value.merge.assert_called_once_with(updated_theme)
    repo._session.return_value.commit.assert_called_once()


def test_upsert_new_theme(repo: ThemeRepository, mock_query: Any):
    mock_query.options.return_value.filter.return_value.one.side_effect = (
        NoResultFound()
    )

    new_theme = Theme(original_title="New Theme")
    new_theme._id = 1

    result = repo.upsert(new_theme)

    assert result.original_title == "New Theme"
    repo._session.return_value.add.assert_called_once_with(new_theme)
    repo._session.return_value.commit.assert_called_once()


def test_upsert_with_none_id(repo: ThemeRepository, mock_query: Any):
    theme_without_id = Theme(original_title="Theme Without ID")
    theme_without_id._id = None
    repo._session.return_value.merge.return_value = theme_without_id

    result = repo.upsert(theme_without_id)

    assert result.original_title == "Theme Without Id"
    repo._session.return_value.merge.assert_called_once_with(theme_without_id)
    repo._session.return_value.commit.assert_called_once()
