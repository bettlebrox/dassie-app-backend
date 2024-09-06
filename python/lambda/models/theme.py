from datetime import datetime
import enum
import json
from typing import List
from urllib.parse import quote_plus, unquote_plus
import uuid
import numpy as np
from sqlalchemy import UUID, Column, DateTime, Enum, Float, String
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from models.article import Article
from models.models import JsonFunctionEncoder, Recurrent, Sporadic
from models.models import Base


class ThemeType(enum.Enum):
    SEARCH_TERM = "search_term"
    CHAT_PROMPT = "chat_prompt"
    TAB_THREAD = "tab_thread"
    CUSTOM = "custom"
    PROPOSITION = "proposition"
    ARTICLE = "article"
    TOP = "top"
    RECURRENT = "recurrent"
    SPORADIC = "sporadic"


class Theme(Base):
    __tablename__ = "theme"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _source = Column(Enum(ThemeType), default=ThemeType.ARTICLE)
    _title = Column(String)
    _summary = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _embedding = Column(Vector(1536))
    _avg_article_distance = Column(Float, default=0.0)
    _related = relationship(
        "Article", secondary="association", order_by=Article._updated_at.desc()
    )
    _recurrent = relationship(
        "Theme",
        secondary="recurrent",
        foreign_keys=[Recurrent.theme_id, Recurrent.related_id],
        remote_side=[_id],
        primaryjoin=Recurrent.theme_id == _id,
        secondaryjoin=Recurrent.related_id == _id,
    )

    _sporadic = relationship(
        "Theme",
        secondary="sporadic",
        foreign_keys=[Sporadic.theme_id, Sporadic.related_id],
        remote_side=[_id],
        primaryjoin=Sporadic.theme_id == _id,
        secondaryjoin=Sporadic.related_id == _id,
    )

    def __init__(self, original_title="", summary=None):
        self._title = quote_plus(original_title.lower())
        self._summary = summary

    def calculate_avg_cos_distance_per_article(self):
        if self._embedding is None or len(self._related) == 0:
            return 0
        return float(
            sum(
                1 - self.cosine_similarity(self._embedding, article.embedding)
                for article in self._related
                if article._embedding is not None
            )
            / len(self._related)
        )

    def cosine_similarity(self, embedding1, embedding2):
        np_embedding1 = np.array(embedding1)
        np_embedding2 = np.array(embedding2)
        return np.dot(np_embedding1, np_embedding2) / (
            np.linalg.norm(np_embedding1) * np.linalg.norm(np_embedding2)
        )

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
        self._avg_article_distance = self.calculate_avg_cos_distance_per_article()

    @property
    def avg_article_distance(self):
        return self._avg_article_distance

    @property
    def recurrent(self):
        return self._recurrent

    @recurrent.setter
    def recurrent(self, value):
        self._recurrent = value

    @property
    def sporadic(self):
        return self._sporadic

    @sporadic.setter
    def sporadic(self, value):
        self._sporadic = value

    @property
    def original_title(self):
        return unquote_plus(self._title).title()

    def json(self, related=False, dump=True):
        json_obj = {
            "id": str(self.id),
            "title": self.title,
            "original_title": self.original_title,
            "summary": self.summary,
            "avg_cosine_distance_per_article": self.avg_article_distance,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else ""
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else ""
            ),
            "source": str(self.source.value) if self.source is not None else "",
        }
        if related:
            json_obj["related"] = self.related
            json_obj["recurrent"] = self.recurrent
            json_obj["sporadic"] = self.sporadic
        return json.dumps(json_obj, cls=JsonFunctionEncoder) if dump else json_obj

    @property
    def embedding(self):
        return self._embedding

    @embedding.setter
    def embedding(self, value):
        self._embedding = value
