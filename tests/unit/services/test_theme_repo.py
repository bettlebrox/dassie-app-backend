from typing import Any
from unittest.mock import MagicMock
from sqlalchemy import func
import pytest
from theme_repo import ThemeRepository
from models.models import Association
from models.article import Article
from models.browse import Browse
from models.theme import Theme, ThemeType


@pytest.fixture
def repo():
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = MagicMock()
    return repo


@pytest.fixture
def mock_query(repo: ThemeRepository) -> Any:
    return repo._session.return_value.query.return_value


@pytest.fixture
def get_top_mock_query(mock_query: Any) -> Any:
    return (
        mock_query.join.return_value.group_by.return_value.having.return_value.order_by.return_value.limit
    )


@pytest.fixture
def get_filter_embedding_mock_query(mock_query: Any) -> Any:
    return (
        mock_query.join.return_value.group_by.return_value.where.return_value.having.return_value.order_by.return_value.limit
    )


@pytest.fixture
def get_top_mock_query_with_source(mock_query: Any) -> Any:
    return (
        mock_query.join.return_value.group_by.return_value.filter.return_value.having.return_value.order_by.return_value.limit
    )


def test_get_recently_browsed_themes(repo: ThemeRepository, mock_query: Any):
    # Mock the query result
    art1 = Article(original_title="Test Article 1", url="https://example.com")
    art2 = Article(original_title="Test Article 2", url="https://example.com")
    art1._id = 1
    art2._id = 2
    article_query = (
        mock_query.join.return_value.filter.return_value.group_by.return_value.all
    )
    article_query.return_value = [
        (art1._id,),
        (art2._id,),
    ]
    theme_query = (
        mock_query.join.return_value.filter.return_value.group_by.return_value.having.return_value.order_by.return_value.limit
    )
    theme_query.return_value = [Theme(original_title="Test Theme")]
    results = repo.get(1, recent_browsed_days=1, sort_by="recently_browsed")
    assert len(results) == 1
    assert results[0].original_title == "Test Theme"
    assert (Association.article_id.in_([art1._id, art2._id])).compare(
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
    mock_query.options.return_value.filter.return_value.first.return_value = Theme(
        original_title="Test Theme"
    )

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
    theme._id = 1
    mock_query.options.return_value.filter.return_value.first.return_value = None
    repo._session.return_value.merge.return_value = theme
    # Create a new article and theme
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    article._id = 1
    repo._session.return_value.query.return_value.filter.return_value.first.return_value = (
        None
    )
    # Call the add_related method
    association = repo.add_related(article, ["Test Theme"])

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
    mock_query.options.return_value.filter.return_value.first.return_value = None
    new_theme = Theme(original_title="New Theme")
    repo._session.return_value.merge.return_value = new_theme

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


def test_get_top_themes(
    repo: ThemeRepository, get_top_mock_query: Any, mock_query: Any
):
    # Mock the query result
    mock_query.join.return_value.group_by.return_value.order_by.return_value.statement.compile.return_value = (
        "SELECT * FROM themes"
    )
    get_top_mock_query.return_value = [
        Theme(original_title="Popular Theme 1"),
        Theme(original_title="Popular Theme 2"),
        Theme(original_title="Popular Theme 3"),
    ]

    # Call the get_top method
    top_themes = repo.get(3)

    # Assert the results
    assert len(top_themes) == 3
    assert top_themes[0].original_title == "Popular Theme 1"
    assert top_themes[1].original_title == "Popular Theme 2"
    assert top_themes[2].original_title == "Popular Theme 3"

    # Verify the query construction
    mock_query.join.assert_called_once_with(Association)
    mock_query.join.return_value.group_by.assert_called_once_with(Theme._id)
    assert (
        func.count(Association.article_id)
        .desc()
        .compare(
            mock_query.join.return_value.group_by.return_value.having.return_value.order_by.call_args[
                0
            ][
                0
            ]
        )
    )
    mock_query.join.return_value.group_by.return_value.having.return_value.order_by.return_value.limit.assert_called_once_with(
        3
    )


def test_get_top_themes_with_custom_limit(
    repo: ThemeRepository, mock_query: Any, get_top_mock_query: Any
):
    # Mock the query result
    get_top_mock_query.return_value = [
        Theme(original_title="Popular Theme 1"),
        Theme(original_title="Popular Theme 2"),
    ]

    # Call the get_top method with a custom limit
    top_themes = repo.get(2)

    # Assert the results
    assert len(top_themes) == 2
    assert top_themes[0].original_title == "Popular Theme 1"
    assert top_themes[1].original_title == "Popular Theme 2"

    # Verify the query construction with custom limit
    mock_query.join.return_value.group_by.return_value.having.return_value.order_by.return_value.limit.assert_called_once_with(
        2
    )


def test_get_top_themes_empty_result(repo: ThemeRepository, get_top_mock_query: Any):
    # Mock an empty query result
    get_top_mock_query.return_value = []

    # Call the get_top method
    top_themes = repo.get(5)

    # Assert the results
    assert len(top_themes) == 0


def test_get_top_themes_with_source_type(
    repo: ThemeRepository, mock_query: Any, get_top_mock_query_with_source: Any
):
    # Mock the query result
    get_top_mock_query_with_source.return_value = [
        Theme(original_title="Popular Theme 1"),
        Theme(original_title="Popular Theme 2"),
    ]

    # Call the get_top method with a source type
    top_themes = repo.get(2, source=[ThemeType.ARTICLE])

    # Assert the results
    assert len(top_themes) == 2
    assert top_themes[0].original_title == "Popular Theme 1"
    assert top_themes[1].original_title == "Popular Theme 2"

    # Verify the query construction with source type filter
    mock_query.join.assert_called_once_with(Association)
    assert (Theme._source.in_([ThemeType.ARTICLE])).compare(
        mock_query.join.return_value.group_by.return_value.filter.call_args[0][0]
    )
    mock_query.join.return_value.group_by.assert_called_once_with(Theme._id)
    assert (
        func.count(Association.article_id)
        .desc()
        .compare(
            mock_query.join.return_value.group_by.return_value.filter.return_value.having.return_value.order_by.call_args[
                0
            ][
                0
            ]
        )
    )
    mock_query.join.return_value.group_by.return_value.filter.return_value.having.return_value.order_by.return_value.limit.assert_called_once_with(
        2
    )


def test_get_top_themes_without_source_type(
    repo: ThemeRepository, mock_query: Any, get_top_mock_query: Any
):
    # Mock the query result
    get_top_mock_query.return_value = [
        Theme(original_title="Popular Theme 1"),
        Theme(original_title="Popular Theme 2"),
    ]

    # Call the get_top method without a source type
    top_themes = repo.get(2)

    # Assert the results
    assert len(top_themes) == 2
    assert top_themes[0].original_title == "Popular Theme 1"
    assert top_themes[1].original_title == "Popular Theme 2"

    # Verify the query construction without source type filter
    mock_query.join.assert_called_once_with(Association)
    mock_query.join.return_value.filter.assert_not_called()
    mock_query.join.return_value.group_by.assert_called_once_with(Theme._id)
    assert (
        func.count(Association.article_id)
        .desc()
        .compare(
            mock_query.join.return_value.group_by.return_value.having.return_value.order_by.call_args[
                0
            ][
                0
            ]
        )
    )
    mock_query.join.return_value.group_by.return_value.having.return_value.order_by.return_value.limit.assert_called_once_with(
        2
    )


def test_get_query_with_embedding(
    repo: ThemeRepository, get_filter_embedding_mock_query: Any
):
    get_filter_embedding_mock_query.return_value = [
        (Theme(original_title="Test Theme"), 0.9)
    ]
    result = repo.get(filter_embedding=[0.1, 0.2, 0.3])

    (result_theme, result_score) = result[0]
    assert result_theme.original_title == "Test Theme"
    assert result_score == 0.9
