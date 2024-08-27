import logging
from lambda_init_context import LambdaInitContext
from models.theme import ThemeType

logger = logging.getLogger("get_themes")
logger.setLevel(logging.DEBUG)

init_context = None


def lambda_handler(event, context, theme_repo=None, useGlobal=True):
    logger.debug("Event: {} Context: {}".format(event, context))
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(theme_repo=theme_repo)
    theme_repo = init_context.theme_repo
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        sort_field = "updated_at"
        max = 10
        params = (
            event["queryStringParameters"]
            if "queryStringParameters" in event
            and event["queryStringParameters"] is not None
            else {"max": max, "sortField": sort_field}
        )
        sort_field = params["sortField"] if "sortField" in params else sort_field
        source = ThemeType(params["source"]) if "source" in params else ThemeType.TOP
        result = []
        max = int(params["max"]) if "max" in params else "max"
        title = event["path"].split("/")[-1]
        response["body"] = None
        if title != "themes":
            theme = theme_repo.get_by_title(title.lower())
            if theme is not None:
                response["body"] = theme.json(related=True)
                return response
        # return all themes
        if sort_field == "count_association":
            result = theme_repo.get_top(max, source)
        elif sort_field == "updated_at":
            result = theme_repo.get_recent(max, source)
        elif sort_field == "recently_browsed":
            result = theme_repo.get_recently_browsed(max, source, days=7)
        else:
            raise ValueError("Invalid sort field: {}".format(sort_field))
        response["body"] = "[{}]".format(",".join([theme.json() for theme in result]))
    except ValueError as error:
        logger.error("ValueError: {}".format(error))
        response["statusCode"] = 400
        response["body"] = {"message": str(error)}
    except Exception as error:
        logger.error("Error: {}".format(error), exc_info=True)
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    return response
