from models.models import Association, Browsed, Recurrent, Sporadic
from models.article import Article
from models.theme import Theme, ThemeType
from repos import BasePostgresRepository
from dassie_logger import logger


from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from contextlib import closing
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus


class ThemeRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Theme

    def get_all(self):
        return super().get_all()

    def get(
        self,
        limit: int = 10,
        source: List[ThemeType] = None,
        recent_days: int = 0,
        association_days: int = 0,
        min_associations: int = 2,
        filter_embedding: List[float] = None,
        threshold: float = 0.8,
        sort_by: str = "count_association",
    ):
        logger.debug(
            "get",
            extra={
                "limit": limit,
                "source": source,
                "association_days": association_days,
                "min_associations": min_associations,
                "filter_embedding": filter_embedding,
                "threshold": threshold,
                "sort_by": sort_by,
            },
        )
        with closing(self._session()) as session:
            if recent_days > 0:
                articles_ids = (
                    session.query(Article._id)
                    .join(Browsed)
                    .filter(
                        Browsed._logged_at
                        > datetime.now() - timedelta(days=recent_days)
                    )
                    .group_by(Article.id)
                    .all()
                )
                articles_ids = [article_id for (article_id,) in articles_ids]
                query = (
                    session.query(self.model)
                    .join(Association)
                    .filter(Association.article_id.in_(articles_ids))
                    .group_by(self.model._id)
                )
            else:
                query = (
                    session.query(self.model).join(Association).group_by(self.model._id)
                )

            if source is not None:
                query = query.filter(self.model._source.in_(source))

            if association_days > 0:
                query = query.filter(
                    Association.created_at
                    > datetime.now() - timedelta(days=association_days)
                )

            if filter_embedding is not None:
                query = query.where(
                    (1 - Theme._embedding.cosine_distance(filter_embedding)) > threshold
                )
            if min_associations > 0:
                query = query.having(
                    func.count(Association.article_id) > min_associations
                )
            if sort_by == "count_association":
                query = query.order_by(func.count(Association.article_id).desc())
            elif sort_by == "updated_at":
                query = query.order_by(self.model._updated_at.desc())
            elif sort_by == "recently_browsed":
                query = query.order_by(self.model._updated_at.desc())

            logger.debug(
                "get_query",
                extra={
                    "query": query.statement.compile(
                        compile_kwargs={"literal_binds": True}
                    )
                },
            )

            return query.limit(limit).with_entities(self.model)

    def add(self, model):
        logger.debug(f"Adding theme {model.title}")
        return super().add(model)

    def get_by_id(self, id):
        with closing(self._session()) as session:
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
        with closing(self._session()) as session:
            logger.debug(f"Retrieving theme {title}")
            theme = (
                session.query(self.model)
                .options(
                    joinedload(self.model._related).selectinload(Article._themes),
                    joinedload(self.model._recurrent),
                    joinedload(self.model._sporadic),
                )
                .filter(self.model._title == title)
                .first()
            )
            logger.debug(f"Retrieved theme {theme}")
            return theme

    def get_by_original_titles(self, original_titles: List[str]):
        with closing(self._session()) as session:
            titles = [quote_plus(title) for title in original_titles]
            return session.query(self.model).filter(self.model._title.in_(titles)).all()

    """
        Adds a new association between an article and a list of themes.

        Args:
            article (Article): The article to associate with the themes.
            theme_titles (List[str]): A list of theme titles to associate with the article.

        Returns:
            Association: The newly created association.
    """

    def add_related(self, article: Article, theme_original_titles: List[str]):
        with closing(self._session()) as session:
            associations = []
            for theme_title in theme_original_titles:
                theme = self.get_by_title(quote_plus(theme_title.lower()))
                if theme is None:
                    theme = Theme(theme_title)
                    theme = self.add(theme)
                    logger.debug(
                        "Adding new theme",
                        extra={"theme": theme.title},
                    )
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
                    associations.append(duplicate_association)
                    break
                session.add(association)
                session.commit()
                associations.append(association)
                logger.debug(
                    "Added association between article and theme",
                    extra={
                        "article": article.title,
                        "theme": theme.title,
                    },
                )
            return associations

    def del_related(self, article_id, theme):
        with closing(self._session()) as session:
            session.query(Association).filter(
                Association.article_id == article_id,
                Association.theme_id == theme.id,
            ).delete()
            session.commit()

    def delete(self, model):
        with closing(self._session()) as session:
            model = session.merge(model)
            model.recurrent = []
            model.sporadic = []
            model.related = []
            session.merge(model)
            session.query(Recurrent).filter(Recurrent.related_id == model.id).delete()
            session.query(Sporadic).filter(Sporadic.related_id == model.id).delete()
            session.delete(model)
            session.commit()
            session.flush()

    def upsert(self, model):
        try:
            if self.get_by_title(model.title) is not None:
                logger.debug(
                    "Updating existing theme",
                    extra={"theme": model.title},
                )
                return self.update(model)
            else:
                logger.debug(
                    "Adding new theme",
                    extra={"theme": model.title},
                )
                return self.add(model)
        except NoResultFound as e:
            logger.debug(
                "Adding new theme",
                extra={"theme": model.title},
            )
            return self.add(model)
