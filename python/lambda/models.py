from datetime import datetime
import json
from typing import List
import uuid
from sqlalchemy.orm import declarative_base
import enum
from sqlalchemy import Column, Enum, ForeignKey, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from urllib.parse import quote_plus, unquote_plus
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Association(Base):
    __tablename__ = "association"
    article_id = Column(
        UUID(as_uuid=True),
        ForeignKey("article._id"),
        primary_key=True,
    )
    theme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("theme._id"),
        primary_key=True,
    )
    created_at = Column(DateTime, default=datetime.now())

    def __init__(self, article_id, theme_id):
        self.article_id = article_id
        self.theme_id = theme_id


class Recurrent(Base):
    __tablename__ = "recurrent"
    theme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("theme._id"),
        primary_key=True,
        default=uuid.uuid4,
    )
    related_id = Column(
        UUID(as_uuid=True),
        ForeignKey("theme._id"),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at = Column(DateTime, default=datetime.now())

    def __init__(self, theme_id, related_id):
        self.theme_id = theme_id
        self.related_id = related_id


class Sporadic(Base):
    __tablename__ = "sporadic"
    theme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("theme._id"),
        primary_key=True,
    )
    related_id = Column(
        UUID(as_uuid=True),
        ForeignKey("theme._id"),
        primary_key=True,
    )
    created_at = Column(DateTime, default=datetime.now())

    def __init__(self, theme_id, related_id):
        self.theme_id = theme_id
        self.related_id = related_id


class Article(Base):
    __tablename__ = "article"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _title = Column(String)
    _summary = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    _logged_at = Column(DateTime)
    _url = Column(String(2000))
    _text = Column(String)
    _themes = relationship("Theme", secondary="association", back_populates="_related")
    _embedding = Column(Vector(1536))

    def __init__(
        self,
        title: str,
        summary: str,
        url: str,
        logged_at: datetime = None,
        text: str = None,
    ):
        self._title = quote_plus(title)
        self._summary = summary
        self._url = url
        self._logged_at = logged_at
        self._text = text

    def json(self):
        return {
            "id": str(self._id),
            "title": self._title,
            "original_title": unquote_plus(self._title),
            "summary": self._summary,
            "created_at": (
                "" if self._created_at is None else self._created_at.isoformat()
            ),
            "url": self._url,
            "logged_at": (
                "" if self._logged_at is None else self._logged_at.isoformat()
            ),
            "text": "" if self._text is None else self._text[:200],
        }

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = quote_plus(value)

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value

    @property
    def created_at(self):
        return self._created_at

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def themes(self):
        return self._themes

    @property
    def embedding(self):
        return self._embedding

    @embedding.setter
    def embedding(self, value):
        self._embedding = value

    @property
    def original_title(self):
        return unquote_plus(self._title)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def logged_at(self):
        return self._logged_at

    @logged_at.setter
    def logged_at(self, value):
        self._logged_at = value


class ThemeType(enum.Enum):
    SEARCH_TERM = "search_term"
    CHAT_PROMPT = "chat_prompt"
    TAB_THREAD = "tab_thread"
    CUSTOM = "custom"
    PROPOSITION = "proposition"
    ARTICLE = "article"
    TOP = "top"


class Theme(Base):
    __tablename__ = "theme"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _source = Column(Enum(ThemeType), default=ThemeType.ARTICLE)
    _title = Column(String)
    _summary = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _logged_at = Column(DateTime)
    _updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    _related = relationship(
        "Article", secondary="association", order_by=Article._created_at
    )
    _recurrent = relationship(
        "Theme", secondary="recurrent", foreign_keys=[Recurrent.theme_id]
    )
    _sporadic = relationship(
        "Theme", secondary="sporadic", foreign_keys=[Sporadic.theme_id]
    )

    def __init__(self, title, summary=None):
        self._title = quote_plus(title)
        self._summary = summary

    @property
    def id(self):
        return self._id

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value

    @property
    def created_at(self):
        return self._created_at

    @property
    def updated_at(self):
        return self._updated_at

    @property
    def related(self):
        return self._related

    @related.setter
    def related(self, value: List[Article]):
        self._related = value

    @property
    def recurrent(self):
        return self._recurrent

    @property
    def sporadic(self):
        return self._sporadic

    @property
    def original_title(self):
        return unquote_plus(self._title)

    def json(self, related=False):
        json_obj = {
            "id": str(self.id),
            "title": self.title,
            "original_title": self.original_title,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "source": self.source.value,
        }
        if related:
            json_obj["related"] = [a.json() for a in self.related[:10]]
        return json.dumps(json_obj)

    @property
    def original_title(self):
        return unquote_plus(self._title)

    @property
    def logged_at(self):
        return self._logged_at

    @logged_at.setter
    def logged_at(self, value):
        self._logged_at = value
