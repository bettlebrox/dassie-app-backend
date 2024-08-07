from datetime import datetime
from unittest.mock import MagicMock
from urllib.parse import quote_plus
import pytest
from models import Article, Theme
from repos import ArticleRepository
from theme_repo import ThemeRepository


@pytest.fixture
def article_repo():
    return ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")


@pytest.fixture
def article_repo_query(article_repo):
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    article_repo.session = mock_session
    return mock_query


@pytest.fixture
def article_repo_get_query(article_repo_query):
    return article_repo_query.options.return_value.order_by


def test_get_articles(article_repo, article_repo_get_query):
    article_repo.get()
    assert article_repo_get_query.call_args is not None, "order_by should be called"
    assert Article._logged_at.desc().compare(article_repo_get_query.call_args[0][0])


def test_get_articles_by_created_at(article_repo, article_repo_get_query):
    article_repo.get(sort_by="created_at")
    assert Article._created_at.desc().compare(article_repo_get_query.call_args[0][0])


def test_get_articles_by_theme(article_repo, article_repo_query):
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    query_embedding = [
        -0.023027408868074417,
        0.012609250843524933,
        -0.004424053709954023,
    ]
    articles = [
        Article(
            title="Test Article",
            summary="This is a test article",
            url="https://example.com",
        )
        for _ in range(10)
    ]
    article_repo_query.where.return_value.order_by.return_value.limit.return_value.all.return_value = (
        articles
    )
    articles = article_repo.get_by_theme_embedding(query_embedding)
    assert len(articles) > 0
    assert article_repo_query.where.call_args[0][0].compare(
        (1 - Article._embedding.cosine_distance(query_embedding)) > 0.8
    )


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
    mock_session.return_value.merge.return_value = article
    # Call the enhance method
    enhanced_article = repo.enhance(article, themes, embedding)

    # Assert that the associations were added and the article was merged
    mock_session.return_value.add.assert_called()
    mock_session.return_value.commit.assert_called()
    mock_session.return_value.merge.assert_called_with(article)

    assert len(mock_session.return_value.add.call_args_list) == 2
    assert enhanced_article.embedding == embedding


def test_get_articles_with_custom_limit(article_repo, article_repo_get_query):
    limit_mock = article_repo_get_query.return_value.limit
    article_repo.get(limit=50)
    limit_mock.assert_called_with(50)


def test_get_articles_with_custom_sort_by(article_repo, article_repo_get_query):
    article_repo.get(sort_by="title")
    assert Article._title.desc().compare(article_repo_get_query.call_args[0][0])


def test_get_articles_ascending_order(article_repo, article_repo_get_query):
    article_repo.get(descending=False)
    assert Article._logged_at.asc().compare(article_repo_get_query.call_args[0][0])


def test_get_articles_invalid_sort_by(article_repo, article_repo_get_query):
    article_repo.get(sort_by="invalid_field")
    assert Article._logged_at.desc().compare(article_repo_get_query.call_args[0][0])


def test_get_articles_empty_result(article_repo, article_repo_get_query):
    article_repo_get_query.return_value.limit.return_value.all.return_value = []
    result = article_repo.get()
    assert len(result) == 0


def test_get_articles_exception_handling(article_repo, article_repo_query):
    article_repo_query.options.side_effect = Exception("Database error")
    with pytest.raises(Exception):
        article_repo.get()


def test_get_articles_with_embedding():
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    embedding = [0.1, 0.2, 0.3]
    repo.get(filter_embedding=embedding, threshold=0.7)

    mock_query.where.assert_called()


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
    article.logged_at = datetime.strptime(
        "2024-03-23T09:21:54.524395", "%Y-%m-%dT%H:%M:%S.%f"
    )
    # Call the upsert method
    mock_session.return_value.merge.return_value = article
    upserted_article = repo.upsert(article)

    # Assert the result
    assert upserted_article.original_title == "Test Article"
    assert upserted_article.logged_at == datetime.strptime(
        "2024-03-23T09:21:54.524395", "%Y-%m-%dT%H:%M:%S.%f"
    )


def test_get_article_by_url():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo.session = mock_session

    # Mock the query result
    mock_query.options.return_value.filter_by.return_value.all.return_value = [
        Article(
            title="Test Article",
            url="https://example.com",
            summary="This is a test article",
        )
    ]
    mock_session.return_value.merge.return_value = Article(
        title="Test Article",
        url="https://example.com",
        summary="This is a test article",
    )

    # Call the get_by_url method
    article = repo.get_by_url("https://example.com")

    # Assert the result
    assert article.original_title == "Test Article"


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
    assert added_article.original_title == "Test Article"


def test_get_article_by_id():
    # Create a mock session
    mock_session = MagicMock()
    mock_session.return_value.query.return_value.options.return_value.filter.return_value.one.return_value = Article(
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
