from datetime import datetime, timedelta
import json
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
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            article_service=article_service,
            navlog_service=navlog_service,
        )

    try:
        navlogs = init_context.navlog_service.get_content_navlogs()
        count = 0
        skipped = 0
        errors = 0
        for navlog in navlogs:
            try:
                if (
                    len(navlog["body_text"]) < 100
                    or "url" not in navlog
                    or datetime.strptime(navlog["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                    < datetime.now() - timedelta(days=2)
                ):
                    skipped += 1
                    continue
                logger.debug("processing navlog", extra={"navlog": navlog})
                count += 1
                init_context.article_service.process_navlog(navlog)
            except Exception as error:
                logger.exception("Error processing navlog", extra={"error": str(error)})
                errors += 1

        logger.info(
            "Processing complete",
            extra={"processed": count, "skipped": skipped, "errors": errors},
        )
        statusCode = 200
        if errors > 0:
            statusCode = 207
        return {
            "statusCode": statusCode,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "message": "Articles processed successfully",
                    "processed": count,
                    "skipped": skipped,
                    "errors": errors,
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
