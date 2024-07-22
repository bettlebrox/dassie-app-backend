import logging

from lambda_init_context import LambdaInitContext

logger = logging.getLogger()
logger.setLevel(logging.INFO)

init_context = None


def lambda_handler(event, context, theme_repo=None, useGlobal=False):
    logger.info("Event: {} Context: {}".format(event, context))
    response = {"statusCode": 204, "headers": {"Access-Control-Allow-Origin": "*"}}
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(theme_repo=theme_repo)
    theme_repo = init_context.theme_repo
    try:
        title = event["pathParameters"]["title"]
        article_id = event["pathParameters"]["article_id"]
        theme = theme_repo.get_by_title(title.lower())
        if theme is None:
            response["statusCode"] = 404
            response["body"] = {"message": "Theme not found"}
            return response
        theme_repo.del_related(theme=theme, article_id=article_id)
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    return response
