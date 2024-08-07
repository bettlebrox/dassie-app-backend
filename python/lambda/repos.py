from contextlib import closing
from typing import List
from sqlalchemy import create_engine
from models import Article, Theme, Association, Base
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
        self.session = sessionmaker(bind=engine, expire_on_commit=False)
        self._logger = logger
        # Base.metadata.create_all(engine)

    def get_all(self):
        with closing(self.session()) as session:
            return session.query(self.model).all()

    def get_by_id(self, id):
        with closing(self.session()) as session:
            return session.query(self.model).get(id)

    def get_by_title(self, title):
        with closing(self.session()) as session:
            return session.query(self.model).filter_by(_title=title).all()

    def upsert(self, model):
        existing = self.get_by_title(model._title)
        if type(existing) is list and len(existing) > 0:
            return existing[0]
        with closing(self.session()) as session:
            session.add(model)
            session.commit()
            return model

    def add(self, model):
        with closing(self.session()) as session:
            session.add(model)
            session.commit()
            return model

    def delete(self, model):
        with closing(self.session()) as session:
            session.delete(model)
            session.commit()

    def update(self, model):
        with closing(self.session()) as session:
            detached = session.merge(model)
            session.commit()
            return detached


class ArticleRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Article

    def get_by_id(self, id):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .options(
                    joinedload(self.model._themes),
                )
                .filter(self.model._id == id)
                .one()
            )

    def get_by_url(self, url):
        with closing(self.session()) as session:
            articles = (
                session.query(self.model)
                .options(joinedload(self.model._themes))
                .filter_by(_url=url)
                .all()
            )
            if len(articles) > 0:
                detached = session.merge(articles[0])
                return detached

    def upsert(self, model):
        existing = self.get_by_url(model.url)
        if existing is not None:
            return existing
        with closing(self.session()) as session:
            session.add(model)
            session.commit()
            detached = session.merge(model)
            return detached

    def enhance(self, article: Article, themes: List[Theme], embedding: List[float]):
        with closing(self.session()) as session:
            for theme in themes:
                association = Association(article.id, theme._id)
                session.add(association)
                session.commit()
            article.embedding = embedding
            detached = session.merge(article)
            session.commit()
            return detached

    """
    Retrieves articles that have an embedding vector similar to the provided `theme_embedding` vector.

    Args:
        theme_embedding (List[int]): A list of integers representing the embedding vector to search for.

    Returns:
        List[Article]: A list of Article objects that have an embedding vector similar to the provided `theme_embedding`.
    """

    def get_by_theme_embedding(
        self, theme_embedding: List[int], threshold: float = 0.8, limit: int = 20
    ):
        with closing(self.session()) as session:
            query = (
                session.query(self.model)
                .where(
                    (1 - Article._embedding.cosine_distance(theme_embedding))
                    > threshold
                )
                .order_by(Article._embedding.cosine_distance(theme_embedding).asc())
            )
            logger.debug(
                "query :{}".format(
                    query.statement.compile(compile_kwargs={"literal_binds": True})
                )
            )
            return query.limit(limit).all()

    def get(
        self,
        limit: int = 20,
        sort_by="logged_at",
        descending=True,
        filter_embedding=None,
        threshold: float = 0.8,
    ):
        try:
            sort_by_att = self.model.__dict__["_" + sort_by]
        except KeyError:
            sort_by_att = self.model.__dict__["_logged_at"]
        with closing(self.session()) as session:
            query = session.query(self.model)
            query = (
                query.where(
                    (1 - Article._embedding.cosine_distance(filter_embedding))
                    > threshold
                )
                if filter_embedding is not None
                else query
            )
            logger.info("embedding query :{}".format(query.statement.compile()))
            return (
                query.options(
                    joinedload(self.model._themes),
                )
                .order_by(sort_by_att.desc() if descending else sort_by_att.asc())
                .limit(limit)
                .all()
            )

    def get_last_7days(self):
        return self.get(days=7)
