from datetime import datetime, timedelta
import json
from lambda_init_context import LambdaInitContext
from aws_lambda_powertools.logging import correlation_paths
from dassie_logger import logger
from models.theme import ThemeType
from services.openai_client import LLMResponseException

init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(
    event,
    context,
    theme_service=None,
    browse_repo=None,
    useGlobal=True,
):
    logger.debug("build_themes")
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            theme_service=theme_service,
            browse_repo=browse_repo,
        )

    try:
        # Process top themes
        top_themes = init_context.theme_service.theme_repo.get_top(
            100,
            source=[
                ThemeType.TOP,
                ThemeType.ARTICLE,
                ThemeType.RECURRENT,
                ThemeType.SPORADIC,
            ],
            days=1,
            min_articles=3,
        )

        processed_top_themes = 0
        errors_top_themes = 0

        for theme in top_themes:
            most_recent_related_article = theme.most_recent_related_article
            if most_recent_related_article is None:
                logger.debug(
                    "Most recent related article is None",
                    extra={"theme_title": theme.original_title},
                )
                continue
            elif most_recent_related_article.created_at > datetime.now() - timedelta(
                hours=1
            ):
                logger.debug(
                    "Most recent related created in the last hour",
                    extra={"theme_title": theme.original_title},
                )
                try:
                    init_context.theme_service.build_theme_from_related_articles(
                        theme.related, theme.source, theme.original_title
                    )
                    processed_top_themes += 1
                except LLMResponseException as e:
                    logger.exception(
                        "Failed to build themes from related articles",
                        extra={
                            "theme_title": theme.original_title,
                            "error": str(e),
                        },
                    )
                    errors_top_themes += 1
            else:
                logger.debug(
                    "Most recent related article is too old",
                    extra={"theme_title": theme.original_title},
                )

        # Process recent browses
        recent_browses = init_context.browse_repo.get_recently_browsed(
            days=0, limit=2000, hours=1
        )

        processed_browses = 0
        errors_browses = 0

        for browse in recent_browses:
            try:
                if len(browse.articles) > 3 and browse.title is None:
                    init_context.theme_service.build_theme_from_related_articles(
                        browse.articles, ThemeType.TAB_THREAD
                    )
                elif browse.title is not None:
                    init_context.theme_service.build_theme_from_related_articles(
                        browse.articles, ThemeType.SEARCH_TERM, browse.title
                    )
                processed_browses += 1
            except Exception as e:
                logger.exception("Error processing browse", extra={"error": str(e)})
                errors_browses += 1

        logger.info(
            "Processing complete",
            extra={
                "processed_top_themes": processed_top_themes,
                "errors_top_themes": errors_top_themes,
                "processed_browses": processed_browses,
                "errors_browses": errors_browses,
            },
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "message": "Themes processed successfully",
                    "processed_top_themes": processed_top_themes,
                    "errors_top_themes": errors_top_themes,
                    "processed_browses": processed_browses,
                    "errors_browses": errors_browses,
                }
            ),
        }

    except Exception as e:
        logger.error("Error in lambda execution", extra={"error": str(e)})
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Internal server error", "error": str(e)}),
        }
