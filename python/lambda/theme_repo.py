from models.models import Association, Recurrent, Sporadic
from models.article import Article
from models.theme import Theme, ThemeType
from repos import BasePostgresRepository, logger


from sqlalchemy import func
from sqlalchemy.orm import joinedload


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

    def get_recent(self, limit: int = 10, source: ThemeType = ThemeType.TOP):
        with closing(self.session()) as session:
            query = session.query(self.model)
            query = (
                query.filter(self.model._source == source)
                if source is not None
                else query
            )
            return query.order_by(self.model._updated_at.desc()).limit(limit)

    def get_top(self, limit: int = 10, source: ThemeType = None, days: int = 0):
        with closing(self.session()) as session:
            join_query = session.query(
                self.model, func.count(Association.article_id)
            ).join(Association)
            join_query = (
                join_query
                if source is None
                else join_query.filter(self.model._source == source)
            )
            join_query = (
                join_query
                if days == 0
                else join_query.filter(
                    Association.created_at > datetime.now() - timedelta(days=days)
                )
            )
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
                .filter(self.model._title == title)
                .first()
            )
            return themes[0] if themes is not None and type(themes) is list else themes

    def get_by_original_titles(self, original_titles: List[str]):
        with closing(self.session()) as session:
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
        with closing(self.session()) as session:
            associations = []
            for theme_title in theme_original_titles:
                theme = self.get_by_title(quote_plus(theme_title.lower()))
                if theme is None:
                    theme = Theme(theme_title)
                    session.add(theme)
                    logger.debug(f"Adding new theme: {theme.title}")
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
                    associations.append(duplicate_association)
                    break
                session.add(association)
                session.commit()
                associations.append(association)
                logger.debug(
                    "Added association between article {} and theme {}".format(
                        article.title, theme.title
                    )
                )
            return associations

    def del_related(self, article_id, theme):
        with closing(self.session()) as session:
            session.query(Association).filter(
                Association.article_id == article_id,
                Association.theme_id == theme.id,
            ).delete()
            session.commit()

    def delete(self, model):
        with closing(self.session()) as session:
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
