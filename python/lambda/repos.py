from contextlib import closing
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus
from sqlalchemy import create_engine, func
from models import Article, Theme, Association, Base, ThemeType
from sqlalchemy.orm import sessionmaker, joinedload
import logging

logger = logging.getLogger()


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

    def get_by_theme_embedding(self, theme_embedding: List[int]):
        with closing(self.session()) as session:
            query = (
                session.query(self.model)
                .where((1 - Article._embedding.cosine_distance(theme_embedding)) > 0.8)
                .order_by(Article._embedding.cosine_distance(theme_embedding).asc())
            )
            logger.info(
                "query :{}".format(
                    query.statement.compile(compile_kwargs={"literal_binds": True})
                )
            )
            return query.limit(20).all()

    def get_last_days(self, days=7):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .options(
                    joinedload(self.model._themes),
                )
                .filter(self.model._logged_at > datetime.now() - timedelta(days=days))
                .order_by(self.model._logged_at.desc())
                .all()
            )

    def get_last_7days(self):
        return self.get_last_days(days=7)


class ThemeRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Theme

    def get_all(self):
        return super().get_all()

    def get_recent(self, limit: int = 10):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .filter(self.model._source == ThemeType.TOP)
                .order_by(self.model._updated_at.desc())
                .limit(limit)
            )

    def get_top(self, limit: int = 10):
        with closing(self.session()) as session:
            join_query = session.query(
                self.model, func.count(Association.article_id)
            ).join(Association)
            query = join_query.group_by(self.model._id).order_by(
                func.count(Association.article_id).desc()
            )
            query = query.limit(limit).with_entities(self.model)
            logger.info(
                "query :{}".format(
                    query.statement.compile(compile_kwargs={"literal_binds": True})
                )
            )
            return query

    def add(self, model):
        model = super().add(model)
        return self.get_by_id(model.id)

    def get_by_id(self, id):
        with closing(self.session()) as session:
            return (
                session.query(self.model)
                .options(
                    joinedload(self.model._related),
                    joinedload(self.model._recurrent),
                    joinedload(self.model._sporadic),
                )
                .filter(self.model._id == id)
                .one()
            )

    def get_by_title(self, title: str):
        with closing(self.session()) as session:
            themes = (
                session.query(self.model)
                .options(
                    joinedload(self.model._related).selectinload(Article._themes),
                    joinedload(self.model._recurrent),
                    joinedload(self.model._sporadic),
                )
                .filter(self.model._title == quote_plus(title))
                .first()
            )
            return themes[0] if themes is not None and type(themes) is list else themes

    def get_by_titles(self, titles: List[str]):
        with closing(self.session()) as session:
            titles = [quote_plus(title) for title in titles]
            return session.query(self.model).filter(self.model._title.in_(titles)).all()

    """
        Adds a new association between an article and a list of themes.

        Args:
            article (Article): The article to associate with the themes.
            theme_titles (List[str]): A list of theme titles to associate with the article.

        Returns:
            Association: The newly created association.
    """

    def add_related(self, article: Article, theme_titles: List[str]):
        with closing(self.session()) as session:
            associations = []
            for theme_title in theme_titles:
                theme = self.get_by_title(theme_title)
                if theme is None:
                    theme = Theme(theme_title)
                    session.add(theme)
                    session.commit()
                    association = Association(article.id, theme._id)
                    duplicate_association = (
                        session.query(Association)
                        .filter(
                            Association.article_id == article.id,
                            Association.theme_id == theme._id,
                        )
                        .first()
                    )
                    if duplicate_association is not None:
                        return duplicate_association
                    session.add(association)
                    session.commit()
                    associations.append(association)
                    logger.info(
                        "Added association between article {} and theme {}".format(
                            article.id, theme._id
                        )
                    )
            return associations
