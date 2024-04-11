from unittest.mock import MagicMock
import sys
import os
from urllib.parse import quote_plus

sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python/lambda")
)
from models import Article, Theme
from repos import ArticleRepository, ThemeRepository


def test_get_all_articles():
    # Create a mock session and query
    mock_session = MagicMock()
    mock_session.return_value.query.return_value.all.return_value = [
        Article(
            title="Test Article 1",
            summary="This is a test article",
            url="https://example.com",
        ),
        Article(
            title="Test Article 2",
            summary="This is another test article",
            url="https://example.com",
        ),
    ]

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Call the get_all method
    articles = repo.get_all()

    # Assert the result
    assert articles[0]._title == quote_plus("Test Article 1")
    assert articles[1]._title == quote_plus("Test Article 2")


def test_get_article_by_id():
    # Create a mock session
    mock_session = MagicMock()
    mock_session.return_value.query.return_value.get.return_value = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Call the get_by_id method
    article = repo.get_by_id(1)

    # Assert the result
    assert article._title == quote_plus("Test Article")


def test_add_article():
    # Create a mock session
    mock_session = MagicMock()
    mock_session.return_value.merge.return_value = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Create a new article
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Call the add method
    added_article = repo.add(article)

    # Assert the result
    assert added_article.get_original_title() == "Test Article"


def test_delete_article():
    # Create a mock session
    mock_session = MagicMock()

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Create a new article
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Call the delete method
    repo.delete(article)

    # Assert that the session's delete and commit methods were called
    mock_session.return_value.delete.assert_called_with(article)
    mock_session.return_value.commit.assert_called()


def test_update_article():
    # Create a mock session
    mock_session = MagicMock()

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Create a new article
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Call the update method
    repo.update(article)

    # Assert that the session's merge and commit methods were called
    mock_session.return_value.merge.assert_called_with(article)
    mock_session.return_value.commit.assert_called()


def test_get_article_by_url():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Mock the query result
    mock_query.filter_by.return_value.all.return_value = [
        Article(
            title="Test Article",
            url="https://example.com",
            summary="This is a test article",
        )
    ]

    # Call the get_by_url method
    articles = repo.get_by_url("https://example.com")

    # Assert the result
    assert len(articles) == 1
    assert articles[0].get_original_title() == "Test Article"


def test_upsert_article():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Mock the query result
    mock_query.filter_by.return_value.all.return_value = []

    # Create a new article
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Call the upsert method
    upserted_article = repo.upsert(article)

    # Assert the result
    assert upserted_article.get_original_title() == "Test Article"


def test_enhance_article():
    # Create a mock session
    mock_session = MagicMock()

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Create a new article, themes, and embedding
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    themes = [Theme(title="Theme 1"), Theme(title="Theme 2")]
    embedding = [1, 2, 3]

    # Call the enhance method
    enhanced_article = repo.enhance(article, themes, embedding)

    # Assert that the associations were added and the article was merged
    mock_session.return_value.add.assert_called()
    mock_session.return_value.commit.assert_called()
    mock_session.return_value.merge.assert_called_with(article)
    assert len(mock_session.return_value.add.call_args_list) == 2
    assert enhanced_article.embedding == embedding


def test_get_all_themes():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Mock the query result
    mock_query.all.return_value = [
        Theme(title="Test Theme 1"),
        Theme(title="Test Theme 2"),
    ]

    # Call the get_all method
    themes = repo.get_all()

    # Assert the result
    assert len(themes) == 2
    assert themes[0].get_original_title() == "Test Theme 1"
    assert themes[1].get_original_title() == "Test Theme 2"


def test_get_theme_by_title():
    # Create a mock session
    mock_session = MagicMock()
    mock_session.return_value.query.return_value.filter.return_value.all.return_value = [
        Theme(title="Test Theme")
    ]

    # Create the repository and set the mock session
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Call the get_by_title method
    theme = repo.get_by_title("Test Theme")

    # Assert the result
    assert theme.get_original_title() == "Test Theme"


def test_get_theme_by_titles():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Mock the query result
    mock_query.filter.return_value.all.return_value = [Theme(title="Test Theme")]

    # Call the get_by_titles method
    themes = repo.get_by_titles(["Test Theme"])

    # Assert the result
    assert len(themes) == 1
    assert themes[0].get_original_title() == "Test Theme"


def test_add_related_theme():
    # Create a mock session
    mock_session = MagicMock()

    # Create the repository and set the mock session
    repo = ThemeRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Create a new article and theme
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    theme = Theme(title="Test Theme")

    # Call the add_related method
    association = repo.add_realted(article, ["Test Theme"])

    # Assert that the theme was added and the association was created
    mock_session.return_value.add.assert_called()
    mock_session.return_value.commit.assert_called()
    assert association.article_id == article._id
    assert association.theme_id == theme._id
