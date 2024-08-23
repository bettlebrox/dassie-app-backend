from datetime import datetime, timedelta
import logging
import os

from lambda_init_context import LambdaInitContext
from services.articles_service import ArticlesService
from services.navlogs_service import NavlogService

logger = logging.getLogger("build_articles")
logger.setLevel(logging.DEBUG)

navlog_service = NavlogService(os.getenv("BUCKET_NAME"), os.getenv("DDB_TABLE"))
init_context = None


def lambda_handler(
    event,
    context,
    theme_repo=None,
    article_repo=None,
    browse_repo=None,
    browsed_repo=None,
    openai_client=None,
    useGlobal=True,
):
    logger.debug("Event: {} Context: {}".format(event, context))
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            theme_repo=theme_repo,
            article_repo=article_repo,
            browse_repo=browse_repo,
            browsed_repo=browsed_repo,
            openai_client=openai_client,
        )
    navlogs = navlog_service.get_content_navlogs()
    article_service = ArticlesService(
        init_context.article_repo,
        init_context.theme_repo,
        init_context.browse_repo,
        init_context.browsed_repo,
        init_context.openai_client,
    )
    count = 0
    skipped = 0
    for navlog in navlogs:
        try:
            if (
                len(navlog["body_text"]) < 100
                or "url" not in navlog
                or datetime.strptime(navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                < datetime.now() - timedelta(days=7)
            ):
                skipped += 1
                continue
            logger.debug("Processing navlog: {}".format(navlog))
            count += 1
            article_service.process_navlog(navlog)
        except Exception as error:
            logger.error("Exception: {}".format(error))
            response["statusCode"] = 400
            response["body"] = {"message": str(error)}
        logger.debug(f"Attempted to process {count} navlogs, skipped {skipped}")
    return response
