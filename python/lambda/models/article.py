from datetime import datetime
import json
from urllib.parse import quote_plus, unquote_plus
import uuid
from sqlalchemy import UUID, Column, DateTime, Integer, String
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from models.models import Base


class Article(Base):
    __tablename__ = "article"
    _id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    _title = Column(String)
    _summary = Column(String)
    _created_at = Column(DateTime, default=datetime.now())
    _updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    _logged_at = Column(DateTime, index=True)
    _url = Column(String(2000))
    _token_count = Column(Integer)
    _text = Column(String)
    _themes = relationship("Theme", secondary="association", back_populates="_related")
    _embedding = Column(Vector(1536))
    _image = Column(String)
    _source_navlog = Column(String)

    def __init__(
        self,
        original_title: str,
        url: str,
        summary: str = None,
        logged_at: datetime = None,
        text: str = None,
    ):
        self._title = quote_plus(original_title)
        self._summary = summary
        self._url = url
        self._logged_at = logged_at
        self._text = text
        self._token_count = 0

    def json(self, dump=True) -> str:
        json_obj = {
            "id": str(self._id),
            "title": self._title,
            "original_title": self.original_title,
            "summary": self._summary,
            "created_at": (
                "" if self._created_at is None else self._created_at.isoformat()
            ),
            "url": self._url,
            "logged_at": (
                "" if self._logged_at is None else self._logged_at.isoformat()
            ),
            "updated_at": (
                "" if self._updated_at is None else self._updated_at.isoformat()
            ),
            "text": "" if self._text is None else self._text,
            "source": self._source_navlog,
            "image": self._image,
            "themes": [theme.json(dump=False) for theme in self._themes],
        }
        return json.dumps(json_obj) if dump else json_obj

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def original_title(self):
        return unquote_plus(self._title)

    @original_title.setter
    def original_title(self, value):
        self._title = quote_plus(value)

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

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    @property
    def source_navlog(self):
        return self._source_navlog

    @source_navlog.setter
    def source_navlog(self, value):
        self._source_navlog = value

    @property
    def tab_id(self):
        return self._tab_id

    @tab_id.setter
    def tab_id(self, value):
        self._tab_id = value

    @property
    def token_count(self):
        return self._token_count

    @token_count.setter
    def token_count(self, value):
        self._token_count = value

    @property
    def parent_document_id(self):
        return self._parent_document_id

    @parent_document_id.setter
    def parent_document_id(self, value):
        self._parent_document_id = value

    @property
    def document_id(self):
        return self._document_id

    @document_id.setter
    def document_id(self, value):
        self._document_id = value

    @property
    def updated_at(self):
        return self._updated_at

    @updated_at.setter
    def updated_at(self, value):
        self._updated_at = value
