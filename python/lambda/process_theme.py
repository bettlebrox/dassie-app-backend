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
    boto_event_client=None,
    useGlobal=True,
):
    try:
        logger.info("process_theme")
        response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
        global init_context
        if init_context is None or not useGlobal:
            init_context = LambdaInitContext(
                article_repo=article_repo,
                openai_client=openai_client,
                theme_service=theme_service,
                boto_event_client=boto_event_client,
            )
        article_repo = init_context.article_repo
        openai_client = init_context.openai_client
        theme_service = init_context.theme_service
        boto_event_client = init_context.boto_event_client
        payload = json.loads(event["body"])
        title = payload["title"]
        logger.info(f"Retrieving theme {title}")

        theme = theme_service.get_theme_by_title(title)
        if theme is None:
            response["statusCode"] = 404
            response["body"] = json.dumps({"message": "Theme not found"})
            return response

        embedding = openai_client.get_embedding(theme.original_title)
        related = article_repo.get(filter_embedding=embedding)
        processed_theme = theme_service.build_theme_from_related_articles(
            related, ThemeType.CUSTOM, theme.original_title, embedding
        )

        if processed_theme is None:
            response["statusCode"] = 500
            response["body"] = json.dumps({"message": "Failed to process theme"})
            return response

        response["body"] = processed_theme.json()
        event_detail = {
            "requestContext": {
                "functionName": context.function_name,
                "functionVersion": context.function_version,
            },
            "responsePayload": response,
        }
        boto_event_client.put_events(
            Entries=[
                {
                    "Source": "dassie.lambda",
                    "DetailType": "Lambda Function Invocation Result",
                    "Detail": json.dumps(event_detail),
                    "EventBusName": "dassie-async-events",
                }
            ]
        )
        return response

    except Exception as error:
        logger.exception("Error in process_theme")
        response["statusCode"] = 500
        response["body"] = json.dumps({"message": str(error)})
        return response
