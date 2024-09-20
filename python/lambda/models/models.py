from datetime import datetime
import json
import uuid
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, ForeignKey, Integer, DateTime, event
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID


class CustomBase:
    _updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def before_update(mapper, connection, target):
        target._updated_at = datetime.now()


Base = declarative_base(cls=CustomBase)


@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, Base):
            instance.before_update(None, None, instance)


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

    def __init__(self, article_id, browse_id, logged_at):
        self.article_id = article_id
        self.browse_id = browse_id
        self.logged_at = logged_at

    @property
    def logged_at(self):
        return self._logged_at

    @logged_at.setter
    def logged_at(self, value):
        self._logged_at = value

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
