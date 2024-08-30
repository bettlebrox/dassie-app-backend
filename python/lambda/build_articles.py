from datetime import datetime, timedelta
from lambda_init_context import LambdaInitContext
from aws_lambda_powertools.logging import correlation_paths
from dassie_logger import logger

init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(
    event,
    context,
    article_service=None,
    navlog_service=None,
    useGlobal=True,
):
    logger.debug("build_articles")
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
            logger.debug("processing navlog", extra={"navlog": navlog})
            count += 1
            init_context.article_service.process_navlog(navlog)
        except Exception as error:
            logger.exception("Error processing navlog")
            response["statusCode"] = 400
            response["body"] = {"message": str(error)}
    logger.debug("processed", extra={"count": count, "skipped": skipped})
    return response
