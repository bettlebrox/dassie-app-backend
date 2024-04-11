from datetime import datetime
import json
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
    _url = Column(String(2000))
    _themes = relationship("Theme", secondary="association", back_populates="_related")
    _embedding = Column(Vector(1536))

    def __init__(self, title: str, summary: str, url: str):
        self._title = quote_plus(title)
        self._summary = summary
        self._url = url

    def set_embedding(self, embedding):
        self._embedding = embedding

    def get_original_title(self):
        return unquote_plus(self._title)


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

    def get_original_title(self):
        return unquote_plus(self._title)

    def to_json(self):
        return json.dumps(
            {
                "id": str(self.id),
                "title": self.title,
                "summary": self.summary,
                "created_at": self.created_at.isoformat() if self.created_at else "",
            }
        )
