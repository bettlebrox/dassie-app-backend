from urllib.parse import quote_plus, unquote_plus

from aws_lambda_powertools.logging import correlation_paths
from lambda_init_context import LambdaInitContext
from dassie_logger import logger

init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(event, context, theme_repo=None):
    logger.debug("gel_theme")
    global init_context
    if init_context is None:
        init_context = LambdaInitContext(theme_repo=theme_repo)
    theme_repo = init_context.theme_repo
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        title = quote_plus(unquote_plus(event["pathParameters"]["title"].lower()))
        logger.debug(f"Attempting to delete theme title", extra={"title": title})
        if title != "themes":
            theme = theme_repo.get_by_title(title)
            if theme is None:
                response["statusCode"] = 404
                response["body"] = {"message": "Theme not found"}
                return response
            theme_repo.delete(theme)
    except Exception as error:
        logger.exception("Error")
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    return response
