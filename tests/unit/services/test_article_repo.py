from datetime import datetime
from unittest.mock import MagicMock
from urllib.parse import quote_plus
import pytest
from sqlalchemy import func
from models.article import Article
from models.models import Browsed
from models.browse import Browse
from models.theme import Theme
from article_repo import ArticleRepository


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def article_repo(mock_session):
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session
    return repo


@pytest.fixture
def mock_query(article_repo):
    mock_query = MagicMock()
    article_repo._session.return_value.query.return_value = mock_query
    return mock_query


@pytest.fixture
def mock_simple_order_by(mock_query):
    return mock_query.order_by


@pytest.fixture
def mock_simple_limit(mock_simple_order_by):
    return mock_simple_order_by.return_value.options.return_value.limit


@pytest.fixture
def mock_where(mock_query):
    return mock_query.where


def test_get_articles(article_repo, mock_simple_order_by):
    article_repo.get()
    assert mock_simple_order_by.call_args is not None, "order_by should be called"
    assert Article._logged_at.desc().compare(mock_simple_order_by.call_args[0][0])


def test_get_articles_by_created_at(article_repo, mock_simple_order_by):
    article_repo.get(sort_by="created_at")
    assert Article._created_at.desc().compare(mock_simple_order_by.call_args[0][0])


def test_get_articles_by_theme(article_repo, mock_where):
    query_embedding = [
        -0.023027408868074417,
        0.012609250843524933,
        -0.004424053709954023,
    ]
    articles = [
        Article(
            original_title="Test Article",
            summary="This is a test article",
            url="https://example.com",
        )
        for _ in range(10)
    ]
    mock_where.return_value.order_by.return_value.options.return_value.limit.return_value.all.return_value = (
        articles
    )
    articles = article_repo.get(
        filter_embedding=query_embedding,
        sort_by="embedding",
        include_score_in_results=True,
    )
    assert len(articles) > 0
    assert mock_where.call_args[0][0].compare(
        (1 - Article._embedding.cosine_distance(query_embedding)) > 0.8
    )
    assert mock_where.return_value.order_by.call_args[0][0].compare(
        (1 - Article._embedding.cosine_distance(query_embedding)).desc()
    )


def test_enhance_article():
    # Create a mock session
    mock_session = MagicMock()

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session

    # Create a new article, themes, and embedding
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    themes = [Theme(original_title="Theme 1"), Theme(original_title="Theme 2")]
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


def test_get_articles_with_custom_limit(article_repo, mock_simple_order_by):
    limit_mock = mock_simple_order_by.return_value.options.return_value.limit
    article_repo.get(limit=50)
    limit_mock.assert_called_with(50)


def test_get_articles_with_custom_sort_by(article_repo, mock_simple_order_by):
    article_repo.get(sort_by="title")
    assert Article._title.desc().compare(mock_simple_order_by.call_args[0][0])


def test_get_articles_ascending_order(article_repo, mock_simple_order_by):
    article_repo.get(descending=False)
    assert Article._logged_at.asc().compare(mock_simple_order_by.call_args[0][0])


def test_get_articles_invalid_sort_by(article_repo, mock_simple_order_by):
    article_repo.get(sort_by="invalid_field")
    assert Article._logged_at.desc().compare(mock_simple_order_by.call_args[0][0])


def test_get_articles_empty_result(article_repo, mock_simple_order_by):
    mock_simple_order_by.return_value.limit.return_value.all.return_value = []
    result = article_repo.get()
    assert len(result) == 0


def test_get_articles_exception_handling(article_repo):
    article_repo._session.return_value.query.side_effect = Exception("Database error")
    with pytest.raises(Exception):
        article_repo.get()


def test_get_articles_with_embedding(article_repo, mock_where):
    embedding = [0.1, 0.2, 0.3]
    article_repo.get(
        filter_embedding=embedding, threshold=0.7, include_score_in_results=True
    )

    mock_where.assert_called()


def test_upsert_article():
    # Create a mock session and query
    mock_query = MagicMock()
    mock_session = MagicMock()
    mock_session.return_value.query.return_value = mock_query

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session

    # Mock the query result
    mock_query.filter_by.return_value.all.return_value = []

    # Create a new article
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    article.logged_at = datetime.strptime(
        "2024-03-23T09:21:54.524395", "%Y-%m-%dT%H:%M:%S.%f"
    )
    # Call the upsert method
    mock_session.return_value.merge.return_value = article
    upserted_article = repo.get_or_insert(article)

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
    repo._session = mock_session

    # Mock the query result
    mock_query.options.return_value.filter_by.return_value.all.return_value = [
        Article(
            original_title="Test Article",
            url="https://example.com",
            summary="This is a test article",
        )
    ]
    mock_session.return_value.merge.return_value = Article(
        original_title="Test Article",
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
    repo._session = mock_session

    # Create a new article
    article = Article(
        original_title="Test Article",
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
    repo._session = mock_session

    # Create a new article
    article = Article(
        original_title="Test Article",
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
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session

    # Create a new article
    article = Article(
        original_title="Test Article",
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
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session

    # Call the get_by_id method
    article_id = "550e8400-e29b-41d4-a716-446655440000"  # Mocked UUID
    article = repo.get_by_id(article_id)

    # Assert the result
    assert article._title == quote_plus("Test Article").lower()


def test_get_all_articles():
    # Create a mock session and query
    mock_session = MagicMock()
    mock_session.return_value.query.return_value.all.return_value = [
        Article(
            original_title="Test Article 1",
            summary="This is a test article",
            url="https://example.com",
        ),
        Article(
            original_title="Test Article 2",
            summary="This is another test article",
            url="https://example.com",
        ),
    ]

    # Create the repository and set the mock session
    repo = ArticleRepository("username", "password", "dbname", "db_cluster_endpoint")
    repo._session = mock_session

    # Call the get_all method
    articles = repo.get_all()

    # Assert the result
    assert articles[0]._title == quote_plus("Test Article 1").lower()
    assert articles[1]._title == quote_plus("Test Article 2").lower()


def test_get_default_params(article_repo, mock_simple_order_by, mock_simple_limit):

    mock_simple_limit.return_value.all.return_value = [
        Article("the aul article", "https://example.com", "This is a test article")
    ]
    result = article_repo.get()

    assert len(result) == 1
    mock_simple_order_by.assert_called_once()
    mock_simple_limit.assert_called_once_with(20)


def test_get_with_custom_params(article_repo, mock_simple_order_by, mock_simple_limit):
    mock_simple_limit.return_value.all.return_value = [
        Article("the aul article", "https://example.com", "This is a test article")
    ]

    result = article_repo.get(limit=10, sort_by="title", descending=False)

    assert len(result) == 1
    mock_simple_order_by.assert_called_once()
    mock_simple_limit.assert_called_once_with(10)


def test_get_with_embedding_filter(article_repo, mock_where, mock_query):
    mock_where.return_value.order_by.return_value.options.return_value.limit.return_value.all.return_value = [
        Article("the aul article", "https://example.com", "This is a test article")
    ]

    result = article_repo.get(
        filter_embedding=[0.1, 0.2, 0.3], threshold=0.9, include_score_in_results=True
    )

    assert len(result) == 1
    mock_where.assert_called_once()
    mock_where.return_value.order_by.return_value.options.return_value.limit.assert_called_once_with(
        20
    )


def test_get_sort_by_browses(article_repo, mock_query):
    mock_query.join.return_value.group_by.return_value.order_by.return_value.options.return_value.limit.return_value.all.return_value = [
        Article("the aul article", "https://example.com", "This is a test article")
    ]

    result = article_repo.get(sort_by="browse")

    assert len(result) == 1
    assert (
        func.count(Browsed._browse_id)
        .desc()
        .compare(
            mock_query.join.return_value.group_by.return_value.order_by.call_args[0][0]
        )
    )


def test_get_invalid_sort_by(article_repo, mock_session):
    mock_query = mock_session.return_value.query.return_value
    mock_query.options.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value.all.return_value = [
        Article("the aul article", "https://example.com", "This is a test article")
    ]

    result = article_repo.get(sort_by="invalid_field")

    assert len(result) == 1
    mock_session.return_value.query.assert_called_once_with(Article)
    mock_query.order_by.assert_called_once()
    mock_query.limit.assert_called_once_with(20)
