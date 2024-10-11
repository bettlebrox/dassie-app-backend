import pytest
from unittest.mock import Mock, patch
from services.openai_client import OpenAIClient, LLMResponseException
import json


@pytest.fixture
def openai_client():
    return OpenAIClient(
        api_key="test_api_key", langfuse_key="test_langfuse_key", langfuse_enabled=False
    )


def test_get_embedding(openai_client):
    with patch.object(openai_client.openai_client.embeddings, "create") as mock_create:
        mock_create.return_value.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        result = openai_client.get_embedding("Test article")
        assert result == [0.1, 0.2, 0.3]
        mock_create.assert_called_once_with(
            input=["Test article"], model="text-embedding-ada-002"
        )


def test_get_completion_json_response(openai_client):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"key": "value"}'))]

    with patch.object(
        openai_client.openai_client.chat.completions,
        "create",
        return_value=mock_response,
    ):
        result = openai_client.get_completion(
            "Test prompt", "Test query" * 100, json_response=True
        )
        assert result == {"key": "value"}


def test_get_completion_text_response(openai_client):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]

    with patch.object(
        openai_client.openai_client.chat.completions,
        "create",
        return_value=mock_response,
    ):
        result = openai_client.get_completion(
            "Test prompt", "Test query" * 100, json_response=False
        )
        assert result == "Test response"


def test_get_completion_json_decode_error(openai_client):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Invalid JSON"))]

    with patch.object(
        openai_client.openai_client.chat.completions,
        "create",
        return_value=mock_response,
    ):
        with pytest.raises(LLMResponseException):
            openai_client.get_completion(
                "Test prompt", "Test query" * 100, json_response=True
            )


def test_get_article_graph(openai_client):
    with patch.object(openai_client, "get_completion") as mock_get_completion:
        mock_get_completion.side_effect = [
            "Turtle RDF content",
            "```opencypher\nCREATE (a:Article {id: 'test_id'})\n```",
        ]
        result = openai_client.get_article_graph("Test article" * 100, "test_id")
        assert result == "\nCREATE (a:Article {id: 'test_id'})\n"
    with patch.object(openai_client, "get_completion") as mock_get_completion:
        mock_get_completion.side_effect = [
            "Turtle RDF content",
            "some preamble text that I don't really care about ```cypher\nCREATE (a:Article {id: 'test_id'})\n```",
        ]
        result = openai_client.get_article_graph("Test article" * 100, "test_id")
        assert result == "\nCREATE (a:Article {id: 'test_id'})\n"


def test_get_cypher_code_block_unterminated_block(openai_client):
    example_text = """ provided text, the following entities and relations are grounded:

1. **Entity: RDFLib**
   - Title: "RDFLib"
   - Description: "RDFLib is a pure Python package for working with RDF."
   - Release Date: "2023"
   - Version: "7.0.0"
   - Homepage: "https://github.com/RDFLib/rdflib"
   - Programming Language: Python
   - License: MIT License
   - Developer: RDFLib Team

2. **Entity: RDFLib Team**
   - Name: "RDFLib Team"
   - Homepage: "https://github.com/RDFLib"


Here is the corresponding Cypher query:

```cypher
MERGE (a:Article {id: '6417f3da-51be-4328-99a5-66df16901ebd'})
MERGE (a)-[:SOURCE_OF]->(d)"""
    result = openai_client._get_opencypher_code_block(example_text)
    assert (
        result
        == """
MERGE (a:Article {id: '6417f3da-51be-4328-99a5-66df16901ebd'})
MERGE (a)-[:SOURCE_OF]->(d)"""
    )


def test_get_article_summarization(openai_client):
    mock_summary = {"summary": "Test summary", "themes": ["Theme1", "Theme2"]}
    with patch.object(openai_client, "get_completion", return_value=mock_summary):
        result = openai_client.get_article_summarization("Test article" * 100)
        assert result == mock_summary


def test_get_theme_summarization(openai_client):
    mock_theme_summary = {
        "title": "Test title",
        "summary": "Test summary",
        "themes": ["Theme1", "Theme2"],
    }
    with patch.object(openai_client, "get_completion", return_value=mock_theme_summary):
        result = openai_client.get_theme_summarization(["Text1", "Text2"])
        assert result == mock_theme_summary


def test_count_tokens(openai_client):
    result = openai_client.count_tokens("This is a test sentence.")
    assert isinstance(result, int)
    assert result > 0
