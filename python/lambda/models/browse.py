from datetime import datetime
import json
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from models.models import Base
from models.article import Article


class Browse(Base):
    __tablename__ = "browse"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _title = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _logged_at = Column(DateTime, index=True)
    _tab_id = Column(String, index=True, unique=True)
    _articles = relationship(
        "Article",
        secondary="browsed",
        back_populates="_browses",
        order_by=Article._updated_at.desc(),
    )

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
