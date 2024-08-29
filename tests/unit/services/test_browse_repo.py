import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy import func
from models.models import Browse, Browsed
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
    mock_query.group_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.limit.return_value.all.return_value = [
        Browse(tab_id="test_tab_1"),
        Browse(tab_id="test_tab_2"),
    ]

    result = browse_repo.get_recently_browsed(limit=2, days=7)

    assert len(result) == 2
    assert result[0].tab_id == "test_tab_1"
    assert result[1].tab_id == "test_tab_2"
    mock_query.join.assert_called_once_with(Browsed)
    mock_query.group_by.assert_called_once_with(Browse._id)
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

    mock_query = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.group_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.limit.return_value.all.return_value = [Browse(tab_id="test_tab")]

    browse_repo.get_recently_browsed(days=7)

    expected_date = mock_now - timedelta(days=7)
    mock_query.filter.assert_called_once()
    filter_arg = mock_query.filter.call_args[0][0]
    assert filter_arg.compare(func.max(Browsed._logged_at) > expected_date)
