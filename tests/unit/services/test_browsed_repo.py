from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
from repos import BrowsedRepository
from models.models import Browsed


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def browsed_repo(mock_session):
    repo = BrowsedRepository("username", "password", "dbname", "endpoint")
    repo._session = mock_session
    return repo


def test_get_by_browse_and_article(browsed_repo, mock_session):
    # Arrange
    browse_id = "test_browse_id"
    article_id = "test_article_id"
    mock_browsed = Browsed(
        article_id=article_id, browse_id=browse_id, logged_at=datetime.now()
    )
    mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = (
        mock_browsed
    )

    # Act
    result = browsed_repo.get_by_browse_and_article(browse_id, article_id)

    # Assert
    mock_session.return_value.query.assert_called_once_with(Browsed)
    mock_session.return_value.query.return_value.filter_by.assert_called_once_with(
        _browse_id=browse_id, _article_id=article_id
    )
    assert result == mock_browsed


def test_get_by_browse_and_article_not_found(browsed_repo, mock_session):
    # Arrange
    browse_id = "test_browse_id"
    article_id = "test_article_id"
    mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = (
        None
    )

    # Act
    result = browsed_repo.get_by_browse_and_article(browse_id, article_id)

    # Assert
    mock_session.return_value.query.assert_called_once_with(Browsed)
    mock_session.return_value.query.return_value.filter_by.assert_called_once_with(
        _browse_id=browse_id, _article_id=article_id
    )
    assert result is None


def test_add_browsed(browsed_repo, mock_session):
    # Arrange
    mock_browsed = MagicMock(spec=Browsed)
    mock_browsed.title = "Test Browsed"

    # Act
    result = browsed_repo.add(mock_browsed)

    # Assert
    mock_session.return_value.add.assert_called_once_with(mock_browsed)
    mock_session.return_value.commit.assert_called_once()
    assert result == mock_session.return_value.merge.return_value


def test_update_browsed(browsed_repo, mock_session):
    # Arrange
    mock_browsed = MagicMock(spec=Browsed)
    mock_browsed.title = "Test Browsed"

    # Act
    result = browsed_repo.update(mock_browsed)

    # Assert
    mock_session.return_value.merge.assert_called_once_with(mock_browsed)
    mock_session.return_value.commit.assert_called_once()
    assert result == mock_session.return_value.merge.return_value


def test_delete_browsed(browsed_repo, mock_session):
    # Arrange
    mock_browsed = Browsed(
        article_id="test_article_id",
        browse_id="test_browse_id",
        logged_at=datetime.now(),
    )
    # Act
    try:
        browsed_repo.delete(mock_browsed)
    except Exception as e:
        pass

    # Assert
    mock_session.return_value.delete.assert_called_once_with(mock_browsed)
    mock_session.return_value.commit.assert_called_once()
