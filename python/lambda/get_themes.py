from lambda_init_context import LambdaInitContext
from dassie_logger import logger
from aws_lambda_powertools.logging import correlation_paths
from models.theme import ThemeType

VALID_SORT_FIELDS = [
    "title",
    "updated_at",
    "created_at",
    "logged_at",
    "count_association",
    "browse",
    "recently_browsed",
]
init_context = None


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event, context, theme_repo=None, openai_client=None, useGlobal=True):
    logger.debug("begin lambda_handler")
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            theme_repo=theme_repo, openai_client=openai_client
        )
    theme_repo = init_context.theme_repo
    openai_client = init_context.openai_client
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        sort_field = "updated_at"
        max = 10
        filter = ""
        filter_embedding = None
        recent_browsed_days = 0

        params = (
            event["queryStringParameters"]
            if "queryStringParameters" in event
            and event["queryStringParameters"] is not None
            else {"max": max, "sortField": sort_field}
        )
        filter = params["filter"] if "filter" in params else filter
        sort_field = params["sortField"] if "sortField" in params else sort_field
        source = (
            [ThemeType(source) for source in params["source"].split(",")]
            if "source" in params
            else [ThemeType.TOP]
        )
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
        if sort_field not in VALID_SORT_FIELDS:
            raise ValueError("Invalid sort field")
        logger.info(
            f"get_themes: sort_field: {sort_field}, source: {source}, max: {max}",
            extra={"sort_field": sort_field, "source": source, "max": max},
        )
        if sort_field == "recently_browsed":
            recent_browsed_days = 14
        if filter != "":
            filter_embedding = openai_client.get_embedding(filter)
        result = theme_repo.get(
            max,
            source,
            filter_embedding=filter_embedding,
            sort_by=sort_field,
            recent_browsed_days=recent_browsed_days,
        )
        response["body"] = "[{}]".format(",".join([theme.json() for theme in result]))
    except ValueError as error:
        logger.error("ValueError: {}".format(error), extra={"error": error})
        response["statusCode"] = 400
        response["body"] = {"message": str(error)}
    except Exception as error:
        logger.exception("Error")
        response["statusCode"] = 500
        response["body"] = {"message": str(error)}
    logger.debug("end lambda_handler")
    return response
