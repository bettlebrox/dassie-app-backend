from contextlib import closing
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from models.models import Browse, Browsed
from sqlalchemy.orm import sessionmaker, joinedload
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class BasePostgresRepository:
    def __init__(self, username, password, dbname, db_cluster_endpoint, logger=None):
        engine = create_engine(
            f"postgresql://{username}:{password}@{db_cluster_endpoint}/{dbname}",
            pool_timeout=10,
        )
        self._session = sessionmaker(bind=engine, expire_on_commit=False)
        self._logger = logger
        # Base.metadata.create_all(engine)

    def get_all(self):
        with closing(self._session()) as session:
            return session.query(self.model).all()

    def get_by_id(self, id):
        with closing(self._session()) as session:
            return session.query(self.model).get(id)

    def get_by_title(self, title):
        with closing(self._session()) as session:
            return session.query(self.model).filter_by(_title=title).first()

    def get_or_insert(self, model):
        if self.get_by_title(model.title) is None:
            return self.add(model)
        else:
            return self.update(model)

    def add(self, model):
        with closing(self._session()) as session:
            session.add(model)
            session.commit()
            return model

    def delete(self, model):
        with closing(self._session()) as session:
            session.delete(model)
            session.commit()

    def update(self, model):
        with closing(self._session()) as session:
            detached = session.merge(model)
            session.commit()
            return detached


class BrowsedRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint, logger=None):
        super().__init__(username, password, dbname, db_cluster_endpoint, logger)
        self.model = Browsed

    def get_by_browse_and_article(self, browse_id, article_id):
        with closing(self._session()) as session:
            return (
                session.query(self.model)
                .filter_by(_browse_id=browse_id, _article_id=article_id)
                .first()
            )
