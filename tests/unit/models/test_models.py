from urllib.parse import quote_plus
import pytest
from datetime import datetime
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import create_engine, desc, func
from sqlalchemy.exc import IntegrityError
import uuid
import sys
import os


@pytest.fixture(scope="module")
def setup_database_engine():
    # Create an in-memory SQLite database for testing
    return create_engine("sqlite:///:memory:")


sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python/lambda")
)
from models.models import (
    Association,
    Recurrent,
    Sporadic,
    Base,
    Browsed,
    Browse,
)
from models.article import Article
from models.theme import Theme


@pytest.fixture
def setup_tables(setup_database_engine):
    # Create the tables in the database
    Base.metadata.create_all(setup_database_engine)
    yield
    # Drop the tables after testing
    Base.metadata.drop_all(setup_database_engine)


@pytest.fixture
def session(setup_tables, setup_database_engine):
    # Create a session for testing
    Session = sessionmaker(bind=setup_database_engine)
    session = Session()
    yield session


def test_create_article(session):
    # Create a new article
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    session.add(article)
    session.commit()

    # Retrieve the article from the database
    retrieved_article = (
        session.query(Article).filter_by(_title=quote_plus("Test Article")).first()
    )

    # Check if the retrieved article matches the original article
    assert retrieved_article._title == quote_plus("Test Article")
    assert retrieved_article._summary == "This is a test article"
    assert retrieved_article._url == "https://example.com"
    assert isinstance(retrieved_article._created_at, datetime)


def test_create_theme(session):
    # Create a new theme
    theme = Theme(original_title="Test Theme", summary="This is a test theme")
    session.add(theme)
    session.commit()

    # Retrieve the theme from the database
    retrieved_theme = (
        session.query(Theme).filter_by(_title=quote_plus("Test Theme".lower())).first()
    )

    # Check if the retrieved theme matches the original theme
    assert retrieved_theme._title == quote_plus("Test Theme").lower()
    assert retrieved_theme._summary == "This is a test theme"
    assert isinstance(retrieved_theme._created_at, datetime)


def test_associate_article_with_theme(session):
    # Create an article and a theme
    article = Article(
        original_title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    theme = Theme(original_title="Test Theme", summary="This is a test theme")
    session.add(article)
    session.add(theme)
    session.commit()

    # Associate the article with the theme
    association = Association(article_id=article._id, theme_id=theme._id)
    session.add(association)
    session.commit()

    # Retrieve the associated theme from the article
    retrieved_article = (
        session.query(Article).filter_by(_title=quote_plus("Test Article")).first()
    )

    # Check if the retrieved theme matches the original theme
    assert retrieved_article._themes[0]._title == quote_plus("Test Theme").lower()
    assert retrieved_article._themes[0]._summary == "This is a test theme"
    assert isinstance(retrieved_article._themes[0]._created_at, datetime)


def test_create_recurrent_theme(session):
    # Create a new recurrent theme
    theme1 = Theme(original_title="Theme 1", summary="This is theme 1")
    theme2 = Theme(original_title="Theme 2", summary="This is theme 2")
    session.add(theme1)
    session.add(theme2)
    session.commit()
    recurrent = Recurrent(theme_id=theme1._id, related_id=theme2._id)
    session.add(recurrent)
    session.commit()

    # Retrieve the recurrent theme from the database
    retrieved_recurrent = (
        session.query(Recurrent).filter_by(theme_id=theme1._id).first()
    )

    # Check if the retrieved recurrent theme matches the original recurrent theme
    assert retrieved_recurrent.theme_id == theme1._id
    assert retrieved_recurrent.related_id == theme2._id
    assert isinstance(retrieved_recurrent.created_at, datetime)


def test_create_sporadic_theme(session):
    # Create a new sporadic theme
    theme1 = Theme(original_title="Theme 1", summary="This is theme 1")
    theme2 = Theme(original_title="Theme 2", summary="This is theme 2")
    session.add(theme1)
    session.add(theme2)
    session.commit()
    sporadic = Sporadic(theme_id=theme1._id, related_id=theme2._id)
    session.add(sporadic)
    session.commit()

    # Retrieve the sporadic theme from the database
    retrieved_sporadic = session.query(Sporadic).filter_by(theme_id=theme1._id).first()

    # Check if the retrieved sporadic theme matches the original sporadic theme
    assert retrieved_sporadic.theme_id == theme1._id
    assert retrieved_sporadic.related_id == theme2._id
    assert isinstance(retrieved_sporadic.created_at, datetime)


def test_article_title_encoding(session):
    # Test article title with special characters
    article = Article(
        original_title="Test & Article",
        summary="This is a test article with special characters",
        url="https://example.com/special",
    )
    session.add(article)
    session.commit()

    retrieved_article = (
        session.query(Article).filter_by(_title=quote_plus("Test & Article")).first()
    )

    assert retrieved_article._title == quote_plus("Test & Article")
    assert retrieved_article.title == "Test+%26+Article"
    assert retrieved_article.original_title == "Test & Article"


def test_theme_title_case_insensitivity(session):
    # Test theme title case insensitivity
    theme1 = Theme(original_title="Test Theme", summary="This is a test theme")
    theme2 = Theme(original_title="TEST THEME", summary="This is another test theme")
    session.add(theme1)
    session.add(theme2)
    session.commit()

    retrieved_themes = (
        session.query(Theme).filter_by(_title=quote_plus("test theme")).all()
    )

    assert len(retrieved_themes) == 2
    assert retrieved_themes[0]._title == quote_plus("test theme")
    assert retrieved_themes[1]._title == quote_plus("test theme")


def test_article_without_summary(session):
    # Test creating an article without a summary
    article = Article(
        original_title="No Summary Article",
        url="https://example.com/no-summary",
    )
    session.add(article)
    session.commit()

    retrieved_article = (
        session.query(Article)
        .filter_by(_title=quote_plus("No Summary Article"))
        .first()
    )

    assert retrieved_article._title == quote_plus("No Summary Article")
    assert retrieved_article._summary is None
    assert retrieved_article._url == "https://example.com/no-summary"


def test_theme_without_summary(session):
    # Test creating a theme without a summary
    theme = Theme(original_title="No Summary Theme")
    session.add(theme)
    session.commit()

    retrieved_theme = (
        session.query(Theme).filter_by(_title=quote_plus("no summary theme")).first()
    )

    assert retrieved_theme._title == quote_plus("no summary theme")
    assert retrieved_theme._summary is None


def test_multiple_articles_same_theme(session):
    # Test associating multiple articles with the same theme
    theme = Theme(original_title="Common Theme", summary="This is a common theme")
    article1 = Article(original_title="Article 1", url="https://example.com/1")
    article2 = Article(original_title="Article 2", url="https://example.com/2")
    session.add_all([theme, article1, article2])
    session.commit()

    association1 = Association(article_id=article1._id, theme_id=theme._id)
    association2 = Association(article_id=article2._id, theme_id=theme._id)
    session.add_all([association1, association2])
    session.commit()

    retrieved_theme = (
        session.query(Theme).filter_by(_title=quote_plus("common theme")).first()
    )

    assert len(retrieved_theme.related) == 2
    retrieved_original_title = retrieved_theme.related[0].original_title
    assert (
        retrieved_original_title == "Article 1"
        or retrieved_original_title == "Article 2"
    )
    retrieved_original_title = retrieved_theme.related[1].original_title
    assert (
        retrieved_original_title == "Article 1"
        or retrieved_original_title == "Article 2"
    )


def test_recurrent_theme_self_reference(session):
    # Test creating a recurrent theme that references itself
    theme = Theme(
        original_title="Self Referencing Theme", summary="This theme references itself"
    )
    session.add(theme)
    session.commit()

    recurrent = Recurrent(theme_id=theme._id, related_id=theme._id)
    session.add(recurrent)
    session.commit()

    retrieved_recurrent = session.query(Recurrent).filter_by(theme_id=theme._id).first()

    assert retrieved_recurrent.theme_id == theme._id
    assert retrieved_recurrent.related_id == theme._id


def test_sporadic_theme_bidirectional(session):
    # Test creating bidirectional sporadic themes
    theme1 = Theme(original_title="Theme 1", summary="This is theme 1")
    theme2 = Theme(original_title="Theme 2", summary="This is theme 2")
    session.add_all([theme1, theme2])
    session.commit()

    sporadic1 = Sporadic(theme_id=theme1._id, related_id=theme2._id)
    sporadic2 = Sporadic(theme_id=theme2._id, related_id=theme1._id)
    session.add_all([sporadic1, sporadic2])
    session.commit()

    retrieved_sporadic1 = session.query(Sporadic).filter_by(theme_id=theme1._id).first()
    retrieved_sporadic2 = session.query(Sporadic).filter_by(theme_id=theme2._id).first()

    assert retrieved_sporadic1.theme_id == theme1._id
    assert retrieved_sporadic1.related_id == theme2._id
    assert retrieved_sporadic2.theme_id == theme2._id
    assert retrieved_sporadic2.related_id == theme1._id


def test_create_browsed(session):
    # Create a new browsed entry
    article = Article(
        original_title="Browsed Article",
        summary="This is a browsed article",
        url="https://example.com/browsed",
    )
    session.add(article)
    session.commit()
    browse = Browse(
        "some title",
        logged_at=datetime.now(),
    )
    session.add(browse)
    session.commit()
    browsed = Browsed(article_id=article._id, browse_id=browse._id)
    session.add(browsed)
    session.commit()

    # Retrieve the browsed entry from the database
    retrieved_browsed = (
        session.query(Browsed).filter_by(_article_id=article._id).first()
    )
    article = session.get(Article, article._id)
    # Check if the retrieved browsed entry matches the original
    assert retrieved_browsed.article_id == article._id
    assert isinstance(retrieved_browsed.created_at, datetime)
    assert len(article.browses) == 1


def test_browsed_unique_constraint(session):
    # Create an article
    article = Article(
        original_title="Unique Browsed Article",
        summary="This is a unique browsed article",
        url="https://example.com/unique-browsed",
    )
    session.add(article)
    session.commit()
    browse = Browse(
        "some title",
        logged_at=datetime.now(),
    )
    session.add(browse)
    session.commit()
    # Create first browsed entry
    browsed1 = Browsed(article_id=article._id, browse_id=browse._id)
    session.add(browsed1)
    session.commit()

    # Attempt to create a second browsed entry for the same article
    browsed2 = Browsed(article_id=article._id, browse_id=browse._id)
    session.add(browsed2)

    # Check if an IntegrityError is raised due to unique constraint
    with pytest.raises(IntegrityError):
        session.commit()


def test_order_articles_by_browsed_count(session):
    # Create articles with browsed counts
    article1 = Article(
        original_title="Article 1",
        summary="This is article 1",
        url="https://example.com/article1",
    )
    article2 = Article(
        original_title="Article 2",
        summary="This is article 2",
        url="https://example.com/article2",
    )
    article3 = Article(
        original_title="Article 3",
        summary="This is article 3",
        url="https://example.com/article3",
    )
    session.add_all([article1, article2, article3])
    session.commit()
    # Create browsed entries for the articles
    browse1 = Browse(
        "some title",
        logged_at=datetime.now(),
    )
    session.add(browse1)
    session.commit
    browsed1 = Browsed(article_id=article3._id, browse_id=browse1._id)
    session.add(browsed1)
    session.commit()
    browse2 = Browse(
        "some title1",
        logged_at=datetime.now(),
    )
    session.add(browse2)
    session.commit()
    browsed2 = Browsed(article_id=article3._id, browse_id=browse2._id)
    session.add(browsed2)
    session.commit()
    browsed3 = Browsed(article_id=article2._id, browse_id=browse2._id)
    browsed4 = Browsed(article_id=article1._id, browse_id=browse2._id)
    session.add_all([browsed3, browsed4])
    results = (
        session.query(Article)
        .join(Browsed)
        .options(joinedload(Article._themes))
        .group_by(Article._id)
        .order_by(func.count(Browsed._browse_id).desc())
        .all()
    )
    assert results[0] == article3
    assert len(results) == 3


def test_browsed_cascade_delete(session):
    # Create an article
    article = Article(
        original_title="Cascade Delete Article",
        summary="This article will be deleted",
        url="https://example.com/cascade-delete",
    )
    session.add(article)
    session.commit()

    browse = Browse(
        "some title",
        logged_at=datetime.now(),
    )
    session.add(browse)
    session.commit()
    # Create browsed entry
    browsed = Browsed(article_id=article._id, browse_id=browse._id)
    session.add(browsed)
    session.commit()

    # Delete the article
    session.delete(article)
    session.commit()

    # Check if the browsed entry is also deleted
    retrieved_browsed = session.query(Browsed).filter_by(article_id=article._id).first()
    assert retrieved_browsed is None
