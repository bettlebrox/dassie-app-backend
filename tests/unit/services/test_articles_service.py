import sys
import os
from unittest.mock import MagicMock


sys.path.append(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "../../../python/lambda/services",
    )
)
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "../../../python/lambda",
    )
)
from articles_service import ArticlesService
from models import Article, Association, Theme


def test_build_article():
    articles_repo = MagicMock()
    themes_repo = MagicMock()
    openai_client = MagicMock()
    articles_service = ArticlesService(articles_repo, themes_repo, openai_client)
    navlog = {
        "id": "1",
        "title": "Navlog 1",
        "body_text": "This is a test article body",
        "created_at": "2022-01-01T00:00:00.00",
    }
    article = Article(title="Test Article 1", url="https://example.com")
    article._id = 1
    mock_embedding = [0.1, 0.2, 0.3]
    mock_summary = {"summary": "This is a test article", "themes": ["testing"]}
    mock_theme = Theme(title="testing")
    mock_theme._id = 1
    openai_client.get_embedding.return_value = mock_embedding
    openai_client.get_article_summarization.return_value = mock_summary
    article.embedding = mock_embedding
    articles_repo.update.return_value = article
    themes_repo.get_by_titles.return_value = [mock_theme]
    # action
    article = articles_service.build_article(article, navlog)
    # assert
    themes_repo.add_related.assert_called_with(article, [mock_theme.title])
    assert article.embedding == mock_embedding
