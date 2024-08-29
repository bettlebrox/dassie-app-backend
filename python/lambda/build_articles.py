import logging
from datetime import datetime, timedelta
from lambda_init_context import LambdaInitContext

logger = logging.getLogger()
logger.setLevel(logging.INFO)

init_context = None


def lambda_handler(
    event,
    context,
    article_service=None,
    navlog_service=None,
    useGlobal=True,
):
    logger.debug(event=event, context=context)
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            article_service=article_service,
            navlog_service=navlog_service,
        )
    navlogs = init_context.navlog_service.get_content_navlogs()
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
            logger.debug(navlog=navlog)
            count += 1
            init_context.article_service.process_navlog(navlog)
        except Exception as error:
            logger.exception("Error processing navlog", error=error, navlog=navlog)
            response["statusCode"] = 400
            response["body"] = {"message": str(error)}
        logger.debug(count=count, skipped=skipped)
    return response
