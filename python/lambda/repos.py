from contextlib import closing
from typing import List
from sqlalchemy import create_engine, func
from models.models import Association, Browse, Browsed
from models.article import Article
from models.theme import Theme
from sqlalchemy.orm import sessionmaker, joinedload, defer
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
            return session.query(self.model).filter_by(_title=title).first()

    def get_or_insert(self, model):
        if self.get_by_title(model.title) is None:
            return self.add(model)
        else:
            return self.update(model)

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


class BrowsedRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint, logger=None):
        super().__init__(username, password, dbname, db_cluster_endpoint, logger)
        self.model = Browsed

    def get_by_browse_and_article(self, browse_id, article_id):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .filter_by(_browse_id=browse_id, _article_id=article_id)
                .first()
            )


class BrowseRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint, logger=None):
        super().__init__(username, password, dbname, db_cluster_endpoint, logger)
        self.model = Browse

    def get_by_tab_id(self, tab_id):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .options(joinedload(Browse._articles))
                .filter_by(_tab_id=tab_id)
                .first()
            )

    def get_or_insert(self, model):
        existing = self.get_by_tab_id(model.tab_id)
        if existing is None:
            return self.add(model)
        else:
            return existing


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

    def get_or_insert(self, model):
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
            query = (
                session.query(self.model)
                .options(defer(Article._embedding))
                .options(defer(Article._text))
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
                query.order_by(sort_by_att.desc() if descending else sort_by_att.asc())
                if sort_by != "browse"
                else query.join(Browsed)
                .group_by(self.model._id)
                .order_by(
                    func.count(Browsed._browse_id).desc()
                    if descending
                    else func.count(Browsed._browse_id).asc()
                )
            )
            query = query.options(joinedload(self.model._themes))
            logger.debug("embedding query :{}".format(query.statement.compile()))
            return query.limit(limit).all()

    def get_last_7days(self):
        return self.get(days=7)
