from datetime import datetime, timedelta
from sqlalchemy.orm.strategy_options import joinedload
from sqlalchemy import func
from contextlib import closing
from typing import List
from models.models import Association, Browsed
from models.theme import Theme
from models.article import Article, ArticleType
from repos import BasePostgresRepository
from dassie_logger import logger
from uuid import UUID as PyUUID


class ArticleRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Article

    def get_by_id(self, id: str):
        with closing(self._session()) as session:
            return (
                session.query(self.model)
                .options(
                    joinedload(self.model._themes),
                )
                .filter(self.model._id == PyUUID(id))
                .one()
            )

    def get_by_url(self, url):
        with closing(self._session()) as session:
            articles = (
                session.query(self.model)
                .options(joinedload(self.model._themes))
                .filter_by(_url=url)
                .all()
            )
            if len(articles) > 0:
                detached = session.merge(articles[0])
                return detached

    def get_or_insert(self, model):
        existing = self.get_by_url(model.url)
        if existing is not None:
            return existing
        with closing(self._session()) as session:
            session.add(model)
            session.commit()
            detached = session.merge(model)
            return detached

    def enhance(self, article: Article, themes: List[Theme], embedding: List[float]):
        with closing(self._session()) as session:
            for theme in themes:
                association = Association(article.id, theme._id)
                session.add(association)
                session.commit()
            article.embedding = embedding
            detached = session.merge(article)
            session.commit()
            return detached

    def get(
        self,
        limit: int = 20,
        type: List[ArticleType] = None,
        sort_by=None,
        descending=True,
        filter_embedding=None,
        include_score_in_results=False,
        threshold: float = 0.8,
        days: int = None,
    ):
        with closing(self._session()) as session:
            query = session.query(self.model)
            query = (
                session.query(
                    self.model, 1 - Article._embedding.cosine_distance(filter_embedding)
                )
                if include_score_in_results
                else query
            )
            query = (
                query.where(
                    (1 - Article._embedding.cosine_distance(filter_embedding))
                    > threshold
                )
                if filter_embedding is not None
                else query
            )
            query = (
                query.where(Article._created_at > datetime.now() - timedelta(days=days))
                if days is not None
                else query
            )
            if type is not None:
                query = query.where(Article._type.in_(type))
            if sort_by is None:
                sort_by = "logged_at"
                if filter_embedding is not None:
                    sort_by = "embedding"
            query = self._append_sort_by(query, sort_by, descending, filter_embedding)
            query = query.options(joinedload(self.model._themes))
            logger.debug("embedding query", extra={"query": query})
            return query.limit(limit).all()

    def _append_sort_by(self, query, sort_by, descending, filter_embedding=None):
        if sort_by == "browse":
            query = query.join(Browsed).group_by(self.model._id)
            order_by_func = func.count(Browsed._browse_id)
        elif sort_by == "embedding":
            order_by_func = 1 - Article._embedding.cosine_distance(filter_embedding)
        else:
            try:
                order_by_func = self.model.__dict__["_" + sort_by]
            except KeyError:
                order_by_func = self.model.__dict__["_logged_at"]
        query = query.order_by(
            order_by_func.desc() if descending else order_by_func.asc()
        )
        return query

    def get_last_7days(self):
        return self.get(days=7)
