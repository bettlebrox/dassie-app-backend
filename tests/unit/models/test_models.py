from urllib.parse import quote_plus
import pytest
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import sys
import os

# Create an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")
Session = sessionmaker(bind=engine)
session = Session()

sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python/lambda")
)
from models import Article, Theme, Association, Recurrent, Sporadic, Base


@pytest.fixture
def setup_database():
    # Create the tables in the database
    Base.metadata.create_all(engine)
    yield
    # Drop the tables after testing
    Base.metadata.drop_all(engine)


def test_create_article(setup_database):
    # Create a new article
    article = Article(
        title="Test Article",
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


def test_create_theme(setup_database):
    # Create a new theme
    theme = Theme(title="Test Theme", summary="This is a test theme")
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


def test_associate_article_with_theme(setup_database):
    # Create an article and a theme
    article = Article(
        title="Test Article",
        summary="This is a test article",
        url="https://example.com",
    )
    theme = Theme(title="Test Theme", summary="This is a test theme")
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


def test_create_recurrent_theme(setup_database):
    # Create a new recurrent theme
    theme1 = Theme(title="Theme 1", summary="This is theme 1")
    theme2 = Theme(title="Theme 2", summary="This is theme 2")
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


def test_create_sporadic_theme(setup_database):
    # Create a new sporadic theme
    theme1 = Theme(title="Theme 1", summary="This is theme 1")
    theme2 = Theme(title="Theme 2", summary="This is theme 2")
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
