from functools import reduce
import logging
from urllib.parse import quote_plus

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

    def upsert_theme_from_summary(
        self,
        summary,
        theme_type=ThemeType.TOP,
        original_title=None,
        given_embedding=None,
        related_articles=None,
    ):
        original_title = summary["title"] if original_title is None else original_title
        theme = self.theme_repo.get_by_title(quote_plus(original_title.lower()))
        theme = (
            Theme(
                original_title,
                summary["summary"],
            )
            if theme is None
            else theme
        )
        theme.summary = summary["summary"]
        theme.source = theme_type
        if given_embedding is None and theme.embedding is None:
            theme.embedding = self.openai_client.get_embedding(theme.original_title)
        else:
            theme.embedding = given_embedding
        if related_articles is None and (
            theme.related is None or len(theme.related) == 0
        ):
            theme.related = self.article_repo.get_by_theme_embedding(theme.embedding)
            logger.info(f"Found {len(theme.related)} related articles")
        else:
            theme.related = related_articles
        theme = self.theme_repo.upsert(theme)
        theme = self.theme_repo.get_by_id(theme.id)
        logger.info("Added theme: {}".format(theme.id))
        theme.sporadic = self.build_related_themes(theme, summary, False)
        logger.info(f"Sporadic themes {[(t.id,t.title) for t in theme.sporadic]}")
        theme.recurrent = self.build_related_themes(theme, summary, True)
        logger.info(f"Recurrent themes {[(t.id,t.title) for t in theme.recurrent]}")
        self.theme_repo.update(theme)
        logger.info("Updated theme with relations: {}".format(theme.title))
        return theme

    def build_related_themes(self, current_theme, summary, recurrent):
        try:
            related_theme_titles = (
                summary["themes"] if recurrent else summary["disagreements"]
            )
            existing_related_themes = self.theme_repo.get_by_original_titles(
                related_theme_titles
            )
            related_theme_titles = set(related_theme_titles) - set(
                [theme.original_title for theme in existing_related_themes]
            )
            for related_theme_title in related_theme_titles:
                related_theme = Theme(
                    related_theme_title,
                    ("Similar to {}" if recurrent else "Dissimilar to {}").format(
                        current_theme.original_title
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

    def build_theme_from_related_articles(
        self, articles, theme_type, original_title=None, given_embedding=None
    ):
        total_tokens = sum([a.token_count for a in articles])
        logger.info(f"Got {len(articles)} articles with { total_tokens } total tokens")
        theme = None
        try:
            if total_tokens <= CONTEXT_WINDOW_SIZE:
                summary = self.openai_client.get_theme_summarization(
                    [a.text for a in articles]
                )
                if summary is not None:
                    theme = self.upsert_theme_from_summary(
                        summary,
                        theme_type,
                        original_title,
                        given_embedding,
                        articles,
                    )
                return theme
            logger.info("Arbitrarily cutting articles to fit context window size")
            window = []
            window_size = 0
            article_window_size = CONTEXT_WINDOW_SIZE // min(len(articles), 8)
            for i, art in enumerate(articles):
                art_text = art.text
                article_size = art.token_count
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
                        theme = self.upsert_theme_from_summary(
                            summary,
                            theme_type,
                            original_title,
                            given_embedding,
                            articles,
                        )
                    return theme
                else:
                    logger.debug(
                        f"Window not full, articles processed:{i} window size: {window_size}"
                    )
            return theme
        except LLMResponseException as error:
            raise error
        except Exception as error:
            logger.error("Error: {}".format(error), exc_info=True)
