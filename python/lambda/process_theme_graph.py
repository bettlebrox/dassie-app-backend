import json
from aws_lambda_powertools.logging import correlation_paths
from lambda_init_context import LambdaInitContext
from dassie_logger import logger

init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(
    event,
    context,
    article_repo=None,
    openai_client=None,
    theme_service=None,
    neptune_client=None,
    openai_secret=None,
    useGlobal=True,
):
    try:
        logger.info("process_theme_graph")
        response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
        global init_context
        if init_context is None or not useGlobal:
            init_context = LambdaInitContext(
                article_repo=article_repo,
                openai_client=openai_client,
                theme_service=theme_service,
                neptune_client=neptune_client,
                openai_secret=openai_secret,
            )
        article_repo = init_context.article_repo
        openai_client = init_context.openai_client
        theme_service = init_context.theme_service
        neptune_client = init_context.neptune_client
        openai_secret = init_context.openai_secret
        logger.info(f"openai_secret", extra={"openai_secret": openai_secret})
        payload = json.loads(event["body"])
        title = payload["title"]
        logger.info(f"Retrieving theme {title}")
        errors = 0
        processed_articles = 0
        theme = theme_service.get_theme_by_title(title)
        if theme is None:
            response["statusCode"] = 404
            response["body"] = json.dumps({"message": "Theme not found"})
            return response
        try:
            embedding = openai_client.get_embedding(theme.original_title)
            related = article_repo.get(filter_embedding=embedding)
            logger.debug(
                "processing theme",
                extra={
                    "theme": theme.original_title,
                    "related_count": len(related),
                },
            )
            for article in related:
                logger.debug(
                    "processing theme article", extra={"article": article.title}
                )
                neptune_client.upsert_theme_graph(theme)
        except Exception as error:
            logger.exception("Error processing article graphs for theme")
            errors += 1

        response["body"] = json.dumps(
            {
                "processed_articles": processed_articles,
                "errors": errors,
            }
        )
        return response

    except Exception as error:
        logger.exception("Error in process_theme")
        response["statusCode"] = 500
        response["body"] = json.dumps({"message": str(error)})
        return response
