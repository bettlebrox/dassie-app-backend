import pytest
from unittest.mock import Mock, patch
from get_theme_graph import lambda_handler


@pytest.fixture
def neptune_client_mock():
    return Mock()


@pytest.fixture
def event():
    return {"pathParameters": {"title": "test%20theme"}}


@pytest.fixture
def context():
    return Mock()


def test_get_theme_graph_success(neptune_client_mock, event, context):
    # Arrange
    expected_graph = {
        "nodes": [
            {
                "id": "1",
                "type": "entity",
                "position": {"x": 0, "y": 0},
                "data": {"name": "test"},
            }
        ],
        "edges": [{"id": "e1", "source": "1", "target": "2"}],
    }
    neptune_client_mock.get_theme_graph.return_value = expected_graph

    # Act
    response = lambda_handler(event, context, neptune_client_mock, useGlobal=False)

    # Assert
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert (
        response["body"]
        == '{"nodes": [{"id": "1", "type": "entity", "position": {"x": 0, "y": 0}, "data": {"name": "test"}}], "edges": [{"id": "e1", "source": "1", "target": "2"}]}'
    )
    neptune_client_mock.get_theme_graph.assert_called_once_with("Test Theme")


def test_get_theme_graph_error(neptune_client_mock, event, context):
    # Arrange
    neptune_client_mock.get_theme_graph.side_effect = Exception("Test error")

    # Act
    response = lambda_handler(event, context, neptune_client_mock, useGlobal=False)

    # Assert
    assert response["statusCode"] == 500
    neptune_client_mock.get_theme_graph.assert_called_once_with("Test Theme")
