import logging

from models import Theme, ThemeType
from services.openai_client import LLMResponseException

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
CONTEXT_WINDOW_SIZE = 15000


class ThemesService:
    def __init__(self, theme_repo, article_repo, openai_client):
        self.theme_repo = theme_repo
        self.article_repo = article_repo
        self.openai_client = openai_client

    def build_related_from_title(self, theme):
        embedding = self.openai_client.get_embedding(theme.title)
        theme.related = self.article_repo.get_by_theme_embedding(embedding)
        logger.info(f"Found {len(theme.related)} related articles")

    def build_theme_from_summary(
        self,
        summary,
        theme_type=ThemeType.TOP,
        given_title=None,
        given_embedding=None,
        related_articles=None,
    ):
        title = summary["title"] if given_title is None else given_title
        theme = self.theme_repo.get_by_title(title)
        theme = (
            Theme(
                title,
                summary["summary"],
            )
            if theme is None
            else theme
        )
        theme.source = theme_type
        theme.embedding = (
            self.openai_client.get_embedding(theme.title)
            if given_embedding is None
            else given_embedding
        )
        related_articles = (
            self.article_repo.get_by_theme_embedding(theme.embedding)
            if related_articles is None
            else related_articles
        )
        logger.info(f"Found {len(related_articles)} related articles")
        theme = self.theme_repo.upsert(theme)
        theme = self.theme_repo.get_by_id(theme.id)
        logger.info("Added theme: {}".format(theme.id))
        theme.sporadic = self.build_related_themes(theme, summary, False)
        logger.info(f"Sporadic themes {[(t.id,t.title) for t in theme.sporadic]}")
        theme.recurrent = self.build_related_themes(theme, summary, True)
        logger.info(f"Recurrent themes {[(t.id,t.title) for t in theme.recurrent]}")
        theme.related = related_articles
        self.theme_repo.update(theme)
        logger.info("Updated theme with relations: {}".format(theme.title))
        return theme

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

    def build_themes_from_related_articles(
        self, articles, theme_type, given_title=None, given_embedding=None
    ):
        logger.info(f"Got {len(articles)} articles")
        themes = []
        try:
            window = []
            window_size = 0
            article_window_size = CONTEXT_WINDOW_SIZE // 8
            for i, art in enumerate(articles):
                art_text = art.text
                article_size = self.openai_client.count_tokens(art_text)
                art.token_count = article_size
                self.article_repo.update(art)
                if CONTEXT_WINDOW_SIZE - window_size < article_window_size:
                    article_window_size = CONTEXT_WINDOW_SIZE - window_size
                while article_size > article_window_size:
                    art_text = art_text[: len(art_text) // 2]
                    article_size = self.openai_client.count_tokens(art_text)
                    logger.debug(
                        f"window size: {window_size}, target article window size:{article_window_size}. Reducing article size to {len(art_text)} token size {article_size}"
                    )
                window.append(art_text)
                window_size = window_size + article_size
                if (
                    window_size >= CONTEXT_WINDOW_SIZE - CONTEXT_WINDOW_SIZE // 8
                    or len(articles) == i + 1
                ):
                    logger.debug(
                        f"Posting, articles processed:{i} window size: {window_size}"
                    )
                    summary = self.openai_client.get_theme_summarization(window)
                    if summary is not None:
                        themes.append(
                            self.build_theme_from_summary(
                                summary,
                                theme_type,
                                given_title,
                                given_embedding,
                                articles,
                            )
                        )
                    return themes
                else:
                    logger.debug(
                        f"Window not full, articles processed:{i} window size: {window_size}"
                    )
            return themes
        except LLMResponseException as error:
            raise error
        except Exception as error:
            logger.error("Error: {}".format(error), exc_info=True)
