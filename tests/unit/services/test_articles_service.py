from unittest.mock import MagicMock
from models.browse import Browse
from services.articles_service import ArticlesService
from models.article import Article
from models.theme import Theme


def test_build_article():
    articles_repo = MagicMock()
    themes_repo = MagicMock()
    browse_repo = MagicMock()
    browsed_repo = MagicMock()
    llm_client = MagicMock()
    articles_service = ArticlesService(
        articles_repo, themes_repo, browse_repo, browsed_repo, llm_client
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
    browsed_repo.get_by_browse_and_article.return_value = None
    # action
    article = articles_service._build_article_from_navlog(article, navlog)
    articles_service._track_browsing(article, navlog)
    # assert
    assert article.text == navlog["body_text"]
    assert article.source_navlog == navlog["id"]
    browsed_repo.add.assert_called_once()


def test_build_article_from_navlog_without_existing_article():
    articles_repo = MagicMock()
    themes_repo = MagicMock()
    browse_repo = MagicMock()
    browsed_repo = MagicMock()
    llm_client = MagicMock()
    articles_service = ArticlesService(
        articles_repo, themes_repo, browse_repo, browsed_repo, llm_client
    )
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


def test_track_browsing_with_existing_browsed():
    articles_repo = MagicMock()
    themes_repo = MagicMock()
    browse_repo = MagicMock()
    browsed_repo = MagicMock()
    llm_client = MagicMock()
    articles_service = ArticlesService(
        articles_repo, themes_repo, browse_repo, browsed_repo, llm_client
    )
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
