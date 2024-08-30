import json
from aws_lambda_powertools.logging import correlation_paths
from lambda_init_context import LambdaInitContext
from models.theme import ThemeType
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
    useGlobal=True,
):
    try:
        logger.info("add_theme")
        response = {"statusCode": 201, "headers": {"Access-Control-Allow-Origin": "*"}}
        global init_context
        if init_context is None or not useGlobal:
            init_context = LambdaInitContext(
                article_repo=article_repo,
                openai_client=openai_client,
                theme_service=theme_service,
            )
        article_repo = init_context.article_repo
        openai_client = init_context.openai_client
        theme_service = init_context.theme_service
        try:
            payload = json.loads(event["body"])
            title = payload["title"]
            logger.info("attempting to add theme", extra={"title": title})
        except Exception as error:
            logger.exception("error attempting to add theme")
            response["body"] = json.dumps({"message": "Bad Request"})
            response["statusCode"] = 400
            return response
        embedding = openai_client.get_embedding(title)
        related = article_repo.get(filter_embedding=embedding)
        theme = theme_service.build_theme_from_related_articles(
            related, ThemeType.CUSTOM, title, embedding
        )
        if theme is None:
            response["statusCode"] = 204
            response["body"] = json.dumps({"message": "Theme not found"})
            return response
        response["body"] = theme.json()
        return response
    except Exception as error:
        logger.exception("Error")
        response["statusCode"] = 500
        response["body"] = json.dumps({"message": str(error)})
        return response
