import logging

from models import Theme, ThemeType

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ThemesService:
    def __init__(self, theme_repo, article_repo, openai_client):
        self.theme_repo = theme_repo
        self.article_repo = article_repo
        self.openai_client = openai_client

    def build_theme_from_summary(self, theme, summary):
        theme.summary = summary["summary"]
        theme_embedding = self.openai_client.get_embedding(theme.title)
        related_articles = self.article_repo.get_by_theme_embedding(theme_embedding)
        logger.info(f"Found {len(related_articles)} related articles")
        theme.related = related_articles
        theme = self.theme_repo.add(theme)
        logger.info("Added theme: {}".format(theme.id))
        theme.sporadic = self.build_related_themes(theme, summary, False)
        logger.info(f"Sporadic themes {[(t.id,t.title) for t in theme.sporadic]}")
        theme.recurrent = self.build_related_themes(theme, summary, True)
        logger.info(f"Recurrent themes {[(t.id,t.title) for t in theme.recurrent]}")
        self.theme_repo.update(theme)
        logger.info("Updated theme with relations: {}".format(theme.title))

    def build_related_themes(self, current_theme, summary, recurrent):
        try:
            related_theme_titles = (
                summary["themes"] if recurrent else summary["disagreements"]
            )
            existing_related_themes = self.theme_repo.get_by_titles(
                related_theme_titles
            )
            related_theme_titles = set(related_theme_titles) - set(
                [theme.title for theme in existing_related_themes]
            )
            for related_theme_title in related_theme_titles:
                related_theme = Theme(
                    related_theme_title,
                    ("Similar to {}" if recurrent else "Dissimilar to {}").format(
                        current_theme.title
                    ),
                )
                related_theme.source = (
                    ThemeType.RECURRENT if recurrent else ThemeType.SPORADIC
                )
                related_theme = self.theme_repo.upsert(related_theme)
                existing_related_themes.append(related_theme)
            return existing_related_themes
        except Exception as error:
            logger.error(f"build_related_themes Error: {error}", exc_info=True)
            return []
