import pytest
from unittest.mock import Mock, patch
from services.neptune_client import NeptuneClient


@patch("boto3.Session")
def test_neptune_client_initialization(mock_session):
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client

    client = NeptuneClient("https://test-endpoint:8182")

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
    client = NeptuneClient("https://test-endpoint:8182")
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

    client = NeptuneClient("https://test-endpoint:8182")
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

    client = NeptuneClient("https://test-endpoint:8182")
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
    client = NeptuneClient("https://test-endpoint:8182")
    result = client.query(queries)

    assert mock_client.execute_open_cypher_query.call_count == 1
    assert result == [{"key1": "value1"}]


def test_query_replacement():
    query = "MATCH (n) WHERE n.date = date('2023-01-01') RETURN n"
    expected_query = "MATCH (n) WHERE n.date = '2023-01-01' RETURN n"
    client = NeptuneClient("https://test-endpoint:8182")
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = "MATCH (n) WHERE n.datetime = datetime('2023-01-01T00:00:00Z') RETURN n"
    expected_query = "MATCH (n) WHERE n.datetime = '2023-01-01T00:00:00Z' RETURN n"
    client = NeptuneClient("https://test-endpoint:8182")
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
    query = "MATCH (n) WHERE n.flightDuration = duration('PT2H9M') RETURN n"
    expected_query = "MATCH (n) WHERE n.flightDuration = 'PT2H9M' RETURN n"
    client = NeptuneClient("https://test-endpoint:8182")
    query = client._remove_unsupported_from_query(query)
    assert query == expected_query
