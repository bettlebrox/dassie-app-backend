from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock

import pytest
from models.browse import Browse
from services.articles_service import ArticlesService
from models.article import Article
from models.theme import Theme
from services.neptune_client import NeptuneClient
from services.openai_client import OpenAIClient
from services.opencypher_translator import OpenCypherTranslator


@pytest.fixture
def articles_repo():
    return MagicMock()


@pytest.fixture
def themes_repo():
    return MagicMock()


@pytest.fixture
def browse_repo():
    return MagicMock()


@pytest.fixture
def browsed_repo():
    return MagicMock()


@pytest.fixture
def llm_client():
    return MagicMock()


@pytest.fixture
def neptune_client():
    return MagicMock()


@pytest.fixture
def opencypher_translator():
    return MagicMock()


@pytest.fixture
def articles_service(
    articles_repo,
    themes_repo,
    browse_repo,
    browsed_repo,
    llm_client,
    neptune_client,
    opencypher_translator,
):
    return ArticlesService(
        articles_repo,
        themes_repo,
        browse_repo,
        browsed_repo,
        llm_client,
        neptune_client,
        opencypher_translator,
    )


def test_build_article(
    articles_service, articles_repo, themes_repo, browse_repo, browsed_repo
):
    navlog = {
        "id": "1",
        "title": "Navlog 1",
        "body_text": "This is a test article body",
        "created_at": "2022-01-01T00:00:00.00",
        "logged_at": "2022-01-01T00:00:00.00",
        "tabId": "12234",
    }
    article = Article(original_title="Test Article 1", url="https://example.com")
    article._id = 1
    mock_theme = Theme(original_title="testing")
    mock_theme._id = 1
    articles_repo.update.return_value = article
    themes_repo.get_by_titles.return_value = [mock_theme]
    browse = Browse(tab_id="12234")
    browse._id = 1
    browse_repo.upsert.return_value = browse
    browsed_repo.get_by_browse_and_article.return_value = None
    # action
    article = articles_service._build_article_from_navlog(article, navlog)
    articles_service._track_browsing(article, navlog)
    # assert
    assert article.text == navlog["body_text"]
    assert article.source_navlog == navlog["id"]
    browsed_repo.add.assert_called_once()


def test_build_article_from_navlog_without_existing_article(
    articles_service, articles_repo
):
    navlog = {
        "id": "2",
        "title": "Navlog 2",
        "body_text": "This is another test article body",
        "created_at": "2022-02-01T00:00:00.00",
        "logged_at": "2022-02-01T00:00:00.00",
        "tabId": "56789",
    }
    new_article = articles_service._build_article_from_navlog(
        Article(original_title="Test Article 2", url="https://example.org"), navlog
    )
    assert articles_repo.update.calledWith(new_article)


def test_track_browsing_with_existing_browsed(
    articles_service, browse_repo, browsed_repo
):
    article = Article(original_title="Test Article 2", url="https://example.org")
    article._id = 2
    navlog = {
        "id": "3",
        "title": "Navlog 3",
        "body_text": "This is a third test article body",
        "created_at": "2022-03-01T00:00:00.00",
        "logged_at": "2022-03-01T00:00:00.00",
        "tabId": "98765",
    }
    browse = Browse(tab_id="98765")
    browse._id = 2
    browse_repo.get_or_insert.return_value = browse
    existing_browsed = MagicMock()
    browsed_repo.get_by_browse_and_article.return_value = existing_browsed

    articles_service._track_browsing(article, navlog)

    browse_repo.get_or_insert.assert_called_once()
    browsed_repo.get_by_browse_and_article.assert_called_once()
    browsed_repo.update.assert_called_once()


def test_add_llm_summarisation(articles_service, articles_repo, themes_repo):
    article = Article(original_title="Test Article", url="https://example.com")
    article._id = 1

    article_summary = {"summary": "Test summary", "themes": ["theme1", "theme2"]}
    embedding = [0.1, 0.2, 0.3]
    token_count = 100

    # Mock theme repo get method to return empty list
    themes_repo.get.return_value = []

    articles_service._add_llm_summarisation(
        article, article_summary, embedding, token_count
    )

    # Verify article was updated with summary and metadata
    assert article.summary == "Test summary"
    assert article.embedding == embedding
    assert article.token_count == token_count
    assert isinstance(article.updated_at, datetime)

    # Verify article was updated in repo
    articles_repo.update.assert_called_once_with(article)

    # Verify themes were added
    themes_repo.add_related.assert_called_once()
    call_args = themes_repo.add_related.call_args[0]
    assert call_args[0] == article
    assert set(call_args[1]) == {"theme1", "theme2"}


def test_process_article_graph(
    articles_service: ArticlesService,
    neptune_client: NeptuneClient,
    llm_client: OpenAIClient,
    opencypher_translator: OpenCypherTranslator,
):
    article = Article(
        original_title="Test Article",
        url="https://example.com",
    )
    article._updated_at = datetime.now() - timedelta(days=2)
    article._id = 1
    neptune_client.get_article_graph.return_value = []
    graph_opencypher = """
    merge (e:Entity {name: "entity1"})
    merge (a:Article {id: 1})-[:SOURCE_OF]->(e)
    """
    llm_client.get_article_entities.return_value = "entity1"
    opencypher_translator.generate_article_graph.return_value = graph_opencypher
    graph = articles_service._process_article_graph(article)
    neptune_client.upsert_article_graph.assert_called_once_with(
        article, graph_opencypher, ANY
    )
    assert graph != []


def test_process_article_graph_with_existing_graph(
    articles_service, neptune_client, llm_client
):
    article = Article(
        original_title="Test Article",
        url="https://example.com",
    )
    article._updated_at = datetime.now()
    article._id = 1

    existing_graph = """
    MERGE (e:Entity {name: "existing"})
    MERGE (a:Article {id: 1})-[:SOURCE_OF]->(e)
    """
    neptune_client.get_article_graph.return_value = existing_graph

    graph = articles_service._process_article_graph(article)

    # Should return existing graph without regenerating
    llm_client.generate_article_graph.assert_not_called()
    neptune_client.upsert_article_graph.assert_not_called()
    assert graph == existing_graph


def test_process_article_graph_with_stale_graph(
    articles_service, neptune_client, llm_client, opencypher_translator
):
    article = Article(
        original_title="Test Article",
        url="https://example.com",
    )
    # Set updated_at to over 90 days ago
    article._updated_at = datetime.now() - timedelta(days=91)
    article._id = 1

    existing_graph = """
    MERGE (e:Entity {name: "old"})
    MERGE (a:Article {id: 1})-[:SOURCE_OF]->(e)
    """
    new_graph = """
    MERGE (e:Entity {name: "new"})
    MERGE (a:Article {id: 1})-[:SOURCE_OF]->(e)
    """
    neptune_client.get_article_graph.return_value = existing_graph
    llm_client.get_article_entities.return_value = "entity1"
    opencypher_translator.generate_article_graph.return_value = new_graph
    graph = articles_service._process_article_graph(article)

    # Should regenerate graph since existing one is stale
    opencypher_translator.generate_article_graph.assert_called_once()
    neptune_client.upsert_article_graph.assert_called_once_with(article, new_graph, ANY)
    assert graph == new_graph


def test_process_article_graph_with_empty_graph(
    articles_service, neptune_client, llm_client, opencypher_translator
):
    article = Article(
        original_title="Test Article",
        url="https://example.com",
    )
    article._updated_at = datetime.now()
    article._id = 1

    neptune_client.get_article_graph.return_value = []
    new_graph = """
    MERGE (e:Entity {name: "new"})
    MERGE (a:Article {id: 1})-[:SOURCE_OF]->(e)
    """
    llm_client.get_article_entities.return_value = "entity1"
    opencypher_translator.generate_article_graph.return_value = new_graph

    graph = articles_service._process_article_graph(article)

    # Should generate new graph since none exists
    opencypher_translator.generate_article_graph.assert_called_once()
    neptune_client.upsert_article_graph.assert_called_once_with(article, new_graph, ANY)
    assert graph == new_graph


def test_add_llm_summarisation_with_existing_themes(
    articles_service, articles_repo, themes_repo
):
    article = Article(original_title="Test Article", url="https://example.com")
    article._id = 1

    article_summary = {"summary": "Test summary", "themes": ["theme1", "theme2"]}
    embedding = [0.1, 0.2, 0.3]
    token_count = 100

    # Test with existing themes from embedding
    themes_repo.get.return_value = [(Theme("theme3"), 0.9), (Theme("theme4"), 0.8)]
    articles_service._add_llm_summarisation(
        article, article_summary, embedding, token_count
    )

    # Verify themes were merged and duplicates removed
    themes_repo.add_related.assert_called_once()
    # Check if the call contains the expected themes regardless of order
    call_args = themes_repo.add_related.call_args[0][
        1
    ]  # Get the second argument from the call
    assert set(call_args) == set(["theme1", "theme2", "Theme4", "Theme3"])

    # Test with None summary
    articles_service._add_llm_summarisation(article, None, embedding, token_count)
    assert articles_repo.update.call_count == 1  # No additional updated
