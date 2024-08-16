from unittest.mock import MagicMock
from models.models import Browse
from services.articles_service import ArticlesService
from models.article import Article
from models.theme import Theme


def test_build_article():
    articles_repo = MagicMock()
    themes_repo = MagicMock()
    browse_repo = MagicMock()
    browsed_repo = MagicMock()
    articles_service = ArticlesService(
        articles_repo, themes_repo, browse_repo, browsed_repo
    )
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
    browsed_repo.get.return_value = None
    # action
    article = articles_service.build_article_from_navlog(article, navlog)
    articles_service.track_browsing(article, navlog)
    # assert
    assert article.text == navlog["body_text"]
    assert article.source_navlog == navlog["id"]
    browsed_repo.add.assert_called_once()
