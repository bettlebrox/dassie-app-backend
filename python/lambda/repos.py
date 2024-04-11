from contextlib import closing
from typing import List
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from models import Article, Theme, Association, Recurrent, Sporadic
from sqlalchemy.orm import sessionmaker, Query


class BasePostgresRepository:
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        engine = create_engine(
            f"postgresql://{username}:{password}@{db_cluster_endpoint}/{dbname}",
            pool_timeout=30,
        )
        self.session = sessionmaker(bind=engine)

    def get_all(self):
        with closing(self.session()) as session:
            return session.query(self.model).all()

    def get_by_id(self, id):
        with closing(self.session()) as session:
            return session.query(self.model).get(id)

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
            session.merge(model)
            session.commit()


class ArticleRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Article

    def get_by_url(self, url):
        with closing(self.session()) as session:
            return session.query(self.model).filter_by(url=url).all()

    def upsert(self, model):
        if len(self.get_by_url(model._url)) > 0:
            return
        with closing(self.session()) as session:
            session.merge(model)
            session.commit()
            return model

    def enhance(self, article: Article, themes: List[Theme], embedding: List[int]):
        with closing(self.session()) as session:
            for theme in themes:
                association = Association(article._id, theme._id)
                session.add(association)
                session.commit()
            article.embedding = embedding
            session.merge(article)
            return article


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
                association = Association(article._id, theme._id)
                session.add(association)
                session.commit()
                return association
