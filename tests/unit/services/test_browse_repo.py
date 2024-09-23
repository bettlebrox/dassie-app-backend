import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from models.browse import Browse
from models.article import Article
from models.theme import Theme
from browse_repo import BrowseRepository


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def browse_repo(mock_session):
    repo = BrowseRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session
    return repo


def test_get_by_tab_id(browse_repo, mock_session):
    mock_query = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    mock_query.options.return_value.filter_by.return_value.first.return_value = Browse(
        tab_id="test_tab_id"
    )

    result = browse_repo.get_by_tab_id("test_tab_id")

    assert result.tab_id == "test_tab_id"
    mock_query.options.assert_called_once()
    mock_query.options.return_value.filter_by.assert_called_once_with(
        _tab_id="test_tab_id"
    )


def test_get_recently_browsed(browse_repo, mock_session):
    mock_query = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.limit.return_value.all.return_value = [
        Browse(tab_id="test_tab_1"),
        Browse(tab_id="test_tab_2"),
    ]
    mock_subquery = MagicMock()
    mock_session.return_value.query.return_value.group_by.return_value.subquery.return_value = (
        mock_subquery
    )
    mock_subquery.c.max_logged_at = datetime.now()
    mock_subquery.c._browse_id = Browse._id
    result = browse_repo.get_recently_browsed(limit=2, days=7)

    assert len(result) == 2
    assert result[0].tab_id == "test_tab_1"
    assert result[1].tab_id == "test_tab_2"
    mock_query.join.assert_called_once()
    mock_query.filter.assert_called_once()
    mock_query.options.assert_called_once()
    mock_query.limit.assert_called_once_with(2)


def test_get_or_insert_existing(browse_repo):
    existing_browse = Browse(tab_id="existing_tab")
    browse_repo.get_by_tab_id = MagicMock(return_value=existing_browse)

    result = browse_repo.get_or_insert(Browse(tab_id="existing_tab"))

    assert result == existing_browse
    browse_repo.get_by_tab_id.assert_called_once_with("existing_tab")


def test_get_or_insert_new(browse_repo):
    browse_repo.get_by_tab_id = MagicMock(return_value=None)
    browse_repo.add = MagicMock(return_value=Browse(tab_id="new_tab"))

    new_browse = Browse(tab_id="new_tab")
    result = browse_repo.get_or_insert(new_browse)

    assert result.tab_id == "new_tab"
    browse_repo.get_by_tab_id.assert_called_once_with("new_tab")
    browse_repo.add.assert_called_once_with(new_browse)


@patch("browse_repo.datetime")
def test_get_recently_browsed_date_filter(mock_datetime, browse_repo, mock_session):
    mock_now = datetime(2023, 1, 1, 12, 0, 0)
    mock_datetime.now.return_value = mock_now
    mock_subquery = MagicMock()
    mock_session.return_value.query.return_value.filter.return_value.subquery.return_value = (
        mock_subquery
    )
    mock_session.return_value.query.return_value.join.return_value.options.return_value.limit.return_value.all.return_value = [
        Browse(tab_id="test_tab")
    ]
    browse = browse_repo.get_recently_browsed(days=7)
    assert browse[0].tab_id == "test_tab"
    assert (Browse._id == mock_subquery.c._browse_id).compare(
        mock_session.return_value.query.return_value.join.call_args[0][1]
    )
