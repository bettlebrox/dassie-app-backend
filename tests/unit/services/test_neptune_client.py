import pytest
from unittest.mock import MagicMock, Mock, patch
from models.article import Article
from models.theme import Theme
from models.browse import Browse
from services.neptune_client import NeptuneClient


@patch("boto3.Session")
def test_neptune_client_initialization(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client

    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)

    assert client._endpoint == "https://test-endpoint:8182"
    mock_session.return_value.client.assert_called_once_with(
        "neptunedata", endpoint_url="https://test-endpoint:8182", verify=False
    )


@patch("boto3.Session")
def test_neptune_client_query_success(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "results": [{"key": "value"}],
    }
    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    query = "MATCH (n) RETURN n LIMIT 1"
    result = client.query(query)

    mock_client.execute_open_cypher_query.assert_called_once_with(openCypherQuery=query)
    assert result == [{"key": "value"}]


@patch("boto3.Session")
def test_neptune_client_query_failure(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 400},
    }

    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    query = "INVALID QUERY"
    with pytest.raises(Exception) as exc_info:
        client.query(query)

    assert str(exc_info.value) == "Neptune query failed with status code: 400"


@patch("boto3.Session")
def test_neptune_client_query_date_replacement(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "results": [{"key": "value"}],
    }

    query = "MATCH (n) WHERE n.date = date('2023-01-01') RETURN n"
    expected_query = "MATCH (n) WHERE n.date = '2023-01-01' RETURN n"

    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    client.query(query)

    mock_client.execute_open_cypher_query.assert_called_once_with(
        openCypherQuery=expected_query
    )


@patch("boto3.Session")
def test_neptune_client_multiple_queries(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.execute_open_cypher_query.side_effect = [
        {"ResponseMetadata": {"HTTPStatusCode": 200}, "results": [{"key1": "value1"}]},
    ]

    queries = "MATCH (n) RETURN n LIMIT 1\n\nMATCH (m) RETURN m LIMIT 1"
    client = NeptuneClient("https://test-endpoint:8182", "test")
    result = client.query(queries)

    assert mock_client.execute_open_cypher_query.call_count == 1
    assert result == [{"key1": "value1"}]


def test_query_replacement():
    query = "MATCH (n) WHERE n.date = date('2023-01-01') RETURN n"
    expected_query = "MATCH (n) WHERE n.date = '2023-01-01' RETURN n"
    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = "MATCH (n) WHERE n.datetime = datetime('2023-01-01T00:00:00Z') RETURN n"
    expected_query = "MATCH (n) WHERE n.datetime = '2023-01-01T00:00:00Z' RETURN n"
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = "MATCH (n) WHERE n.flightDuration = duration('PT2H9M') RETURN n"
    expected_query = "MATCH (n) WHERE n.flightDuration = 'PT2H9M' RETURN n"
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = """MERGE (cypherManual:SoftwareDocumentation {name: 'Cypher Manual'})
    SET cypherManual.version = ['5', '4.4', '4.3', '4.2', '4.1', '4.0', '3.5']"""
    expected_query = """MERGE (cypherManual:SoftwareDocumentation {name: 'Cypher Manual'})
    SET cypherManual.version = '5,4.4,4.3,4.2,4.1,4.0,3.5'"""
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = """MERGE (product)-[:MANUFACTURER]->(company)"""
    expected_query = """MERGE (product)-[:MANUFACTURER]->(company)"""
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = """MERGE (stackOverflow)-[:ARTICLE {title: 'Remove quotes from String in Python', date: '22 Oct 2020'}]->(python)"""
    expected_query = """MERGE (stackOverflow)-[:ARTICLE {title: 'Remove quotes from String in Python', date: '22 Oct 2020'}]->(python)"""
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = """MERGE (openaiDeveloperForum)-[:DISCUSSION {title: 'How to train OpenAI with my own data', date: date('2023-07-21')}]->(:Discussion)"""
    expected_query = """MERGE (openaiDeveloperForum)-[:DISCUSSION {title: 'How to train OpenAI with my own data', date: '2023-07-21'}]->(:Discussion)"""
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = """MERGE (e:Company {name: 'Elite Tree Services'})
SET e.location = 'Dublin',
    e.services = ['Tree care'],
    e.website = 'http://etree.ie'"""
    expected_query = """MERGE (e:Company {name: 'Elite Tree Services'})
SET e.location = 'Dublin',
    e.services = 'Tree care',
    e.website = 'http://etree.ie'"""
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query


def test_scope_updated_graph():
    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    client.client = MagicMock()
    client.client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "results": [{"count": 1}],
    }
    result = client._scope_updated_graph(article_id="123", trace_id="456")
    assert result == [{"count": 1}]


def test_scope_updated_graph_failure():
    client = NeptuneClient("https://test-endpoint:8182", "test")
    client.client = MagicMock()
    client.client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 400},
    }
    with pytest.raises(Exception) as exc_info:
        client._scope_updated_graph()


def test_upsert_article():
    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    client.client = MagicMock()
    client.client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "results": [],
    }
    res = client._upsert_article(
        Article(
            "test",
            url="https://test.com",
            text="Test",
        ),
        trace_id="456",
    )
    assert res == []


def test_upsert_theme():
    client = NeptuneClient("https://test-endpoint:8182", "test", langfuse_enabled=False)
    client.client = MagicMock()
    client.client.execute_open_cypher_query.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "results": [],
    }
    mock_article = Article(
        "test",
        url="https://test.com",
        text="Test",
    )
    mock_theme = Theme("test")
    mock_theme._id = "test"
    mock_theme._source = "article"
    mock_theme._created_at = "2024-02-29T16:25:00+00:00"
    mock_theme._related = [mock_article]
    mock_article._id = "test"
    res = client._upsert_theme(mock_theme, trace_id="456")
    assert client.client.execute_open_cypher_query.call_count == 1
    client.client.execute_open_cypher_query.assert_called_once_with(
        openCypherQuery='\n        merge (t:Theme {id: "test"})\n        on create set t.domain = "dassie_browse", t.source = "article", t.created_at = "2024-02-29T16:25:00+00:00", t.name = "Test", t.title = "test", t.trace_id = "456"\n        on match set t.domain = "dassie_browse", t.source = "article", t.created_at = "2024-02-29T16:25:00+00:00", t.name = "Test", t.title = "test", t.trace_id = t.trace_id + ",456"\n        \n        merge (a0:Article {id: "test"})\n        on create set a0.domain = "dassie_browse", a0.title = "test", a0.url = "https://test.com", a0.created_at = "None", a0.updated_at = "None", a0.trace_id = "456"\n        on match set a0.domain = "dassie_browse", a0.title = "test", a0.url = "https://test.com", a0.created_at = "None", a0.updated_at = "None", a0.trace_id = a0.trace_id + ",456"\n        merge (t)-[:RELATED_TO]->(a0:Article {id: "test"})\n'
    )
    assert res == []
