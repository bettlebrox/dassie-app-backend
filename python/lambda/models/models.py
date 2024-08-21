from datetime import datetime
import json
import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from urllib.parse import quote_plus
from sqlalchemy.orm import relationship

Base = declarative_base()


class JsonFunctionEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "json"):
            return obj.json(dump=False)
        return super().default(obj)


class Browsed(Base):
    __tablename__ = "browsed"
    _article_id = Column(
        UUID(as_uuid=True), ForeignKey("article._id"), primary_key=True
    )
    _browse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("browse._id"),
        primary_key=True,
        default=uuid.uuid4,
    )
    _count = Column(Integer, default=1)
    _time = Column(Integer, default=0)
    _created_at = Column(DateTime, default=datetime.now())
    _logged_at = Column(DateTime, index=True)

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value

    @property
    def article_id(self):
        return self._article_id

    @article_id.setter
    def article_id(self, value):
        self._article_id = value

    @property
    def browse_id(self):
        return self._browse_id

    @browse_id.setter
    def browse_id(self, value):
        self._browse_id = value

    @property
    def created_at(self):
        return self._created_at

    @created_at.setter
    def created_at(self, value):
        self._created_at = value


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


class Browse(Base):
    __tablename__ = "browse"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _title = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    _logged_at = Column(DateTime, index=True)
    _tab_id = Column(String, index=True, unique=True)
    _articles = relationship("Article", secondary="browsed", back_populates="_browses")

    def __init__(self, tab_id, title=None, logged_at=None):
        self._tab_id = tab_id
        self._title = title
        self._logged_at = logged_at

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def created_at(self):
        return self._created_at

    @property
    def updated_at(self):
        return self._updated_at

    @property
    def logged_at(self):
        return self._logged_at

    @logged_at.setter
    def logged_at(self, value):
        self._logged_at = value

    @property
    def tab_id(self):
        return self._tab_id

    @property
    def articles(self):
        return self._articles

    def json(self, dump=True):
        json_obj = {
            "id": str(self._id),
            "title": self._title,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "logged_at": self._logged_at.isoformat(),
            "tab_id": self._tab_id,
        }
        if dump:
            return json.dumps(json_obj)
        return json_obj
