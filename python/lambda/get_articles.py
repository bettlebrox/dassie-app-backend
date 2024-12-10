from lambda_init_context import LambdaInitContext
from dassie_logger import logger
from aws_lambda_powertools.logging import correlation_paths

VALID_SORT_ORDERS = ["asc", "desc"]
VALID_SORT_FIELDS = [
    "title",
    "updated_at",
    "created_at",
    "logged_at",
    "count_association",
    "browse",
]
init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(
    event, context, article_repo=None, openai_client=None, useGlobal=True
):
    logger.debug("get_articles")
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            article_repo=article_repo, openai_client=openai_client
        )
    openai_client = init_context.openai_client
    article_repo = init_context.article_repo
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        sort_field = "updated_at"
        max = 10
        sort_order = "desc"
        filter = ""
        filter_embedding = None
        params = (
            event["queryStringParameters"]
            if "queryStringParameters" in event
            and event["queryStringParameters"] is not None
            else {"max": max, "sortField": sort_field}
        )
        sort_field = (
            params["sortField"].lower() if "sortField" in params else sort_field
        )
        sort_order = (
            params["sortOrder"].lower() if "sortOrder" in params else sort_order
        )
        filter = params["filter"] if "filter" in params else filter
        max = int(params["max"]) if "max" in params else max
        if sort_order not in VALID_SORT_ORDERS:
            raise ValueError("Invalid sort order")
        if sort_field not in VALID_SORT_FIELDS:
            raise ValueError("Invalid sort field")
        article_id = event["path"].split("/")[-1]
        result = []
        response["body"] = None
        if article_id != "articles":
            # get a specific article
            article = article_repo.get_by_id(article_id)
            if article is not None:
                response["body"] = article.json()
            else:
                response["statusCode"] = 404
            return response
        if filter is not None and filter != "":
            filter_embedding = openai_client.get_embedding(filter)
            logger.debug("filter by embedding", extra={"filter": filter})
        result = article_repo.get(
            limit=max,
            sort_by=sort_field,
            descending=sort_order == "desc",
            filter_embedding=filter_embedding,
            min_token_count=0,
        )
        response["body"] = "[{}]".format(
            ",".join([article.json() for article in result])
        )
    except ValueError as error:
        logger.exception("ValueError")
        response["body"] = {"message": str(error)}
        response["statusCode"] = 400
    except Exception as error:
        logger.exception("Error")
        response["body"] = {"message": str(error)}
        response["statusCode"] = 500
    return response
