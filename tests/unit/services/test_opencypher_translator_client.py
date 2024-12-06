import pytest
from services.opencypher_translator import OpenCypherTranslatorClient


@pytest.fixture
def opencypher_translator_client():
    return OpenCypherTranslatorClient()


def test_get_article_graph(opencypher_translator_client):
    assert (
        opencypher_translator_client._get_opencypher_code_block(
            "```opencypher\nCREATE (a:Article {id: 'test_id'})\n```"
        )
        == "CREATE (a:Article {id: 'test_id'})"
    )
    assert (
        opencypher_translator_client._get_opencypher_code_block(
            "some preamble text that I don't really care about ```cypher\nCREATE (a:Article {id: 'test_id'})\n```"
        )
        == "CREATE (a:Article {id: 'test_id'})"
    )


def test_get_cypher_code_block_unterminated_block(opencypher_translator_client):
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
    result = opencypher_translator_client._get_opencypher_code_block(example_text)
    assert (
        result
        == """MERGE (a:Article {id: '6417f3da-51be-4328-99a5-66df16901ebd'})
MERGE (a)-[:SOURCE_OF]->(d)"""
    )
