from unittest.mock import MagicMock
import pytest
from models import Article, Theme
from repos import ArticleRepository


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
