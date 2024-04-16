from contextlib import closing
import copy
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus
from sqlalchemy import create_engine, func, select
from models import Article, Theme, Association, Base
from sqlalchemy.orm import sessionmaker


class BasePostgresRepository:
    def __init__(self, username, password, dbname, db_cluster_endpoint, logger=None):
        engine = create_engine(
            f"postgresql://{username}:{password}@{db_cluster_endpoint}/{dbname}",
            pool_timeout=30,
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
        if len(existing) > 0:
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

    def get_by_url(self, url):
        with closing(self.session()) as session:
            articles = session.query(self.model).filter_by(_url=url).all()
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

    def get_by_theme_embedding(self, theme_embedding: List[int]):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .order_by(Article._embedding.cosine_distance(theme_embedding))
                .limit(10)
                .all()
            )

    def get_last_days(self, days=7):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .filter(self.model._logged_at > datetime.now() - timedelta(days=days))
                .all()
            )

    def get_last_7days(self):
        return self.get_last_days(days=7)


class ThemeRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Theme

    def get_by_title(self, title: str):
        titles = self.get_by_titles([title])
        if len(titles) > 0:
            return titles[0]
        return None

    def get_by_titles(self, titles: List[str]):
        with closing(self.session()) as session:
            titles = [quote_plus(title) for title in titles]
            return session.query(self.model).filter(self.model._title.in_(titles)).all()

    def add_realted(self, article: Article, theme_titles: List[str]):
        with closing(self.session()) as session:
            for theme_title in theme_titles:
                theme = self.get_by_title(theme_title)
                if theme is None:
                    theme = Theme(theme_title)
                    session.add(theme)
                    session.commit()
                association = Association(article.id, theme._id)
                session.add(association)
                session.commit()
                return association
