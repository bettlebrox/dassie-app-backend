from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock
import pytest

from models.article import Article
from services.articles_service import ArticlesService
from services.neptune_client import NeptuneClient
from services.openai_client import OpenAIClient
from services.opencypher_translator import OpenCypherTranslator


@pytest.fixture
def llm_client():
    return MagicMock()


@pytest.fixture
def neptune_client():
    return MagicMock()


@pytest.fixture
def opencypher_translator():
    return OpenCypherTranslator()
