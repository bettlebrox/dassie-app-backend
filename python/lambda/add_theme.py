import json
from aws_lambda_powertools.logging import correlation_paths
from lambda_init_context import LambdaInitContext
from models.theme import Theme, ThemeType
from dassie_logger import logger
import boto3

init_context = None


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
def lambda_handler(
    event,
    context,
    theme_service=None,
    boto_event_client=None,
    useGlobal=True,
):
    try:
        logger.info("add_theme")
        response = {"statusCode": 202, "headers": {"Access-Control-Allow-Origin": "*"}}
        global init_context
        if init_context is None or not useGlobal:
            init_context = LambdaInitContext(
                theme_service=theme_service,
                boto_event_client=boto_event_client,
            )
        theme_service = init_context.theme_service
        boto_event_client = init_context.boto_event_client
        try:
            payload = json.loads(event["body"])
            title = payload["title"]
            logger.info("attempting to add theme", extra={"title": title})
        except Exception as error:
            logger.exception("error attempting to add theme")
            response["body"] = json.dumps({"message": "Bad Request"})
            response["statusCode"] = 400
            return response
        theme = theme_service.get_theme_by_original_title(title)
        if theme is not None:
            response["body"] = json.dumps({"message": "Theme already exists"})
            response["statusCode"] = 302
            return response
        theme = theme_service.add_theme(Theme(title, source=ThemeType.CUSTOM))
        if theme is None:
            response["statusCode"] = 204
            response["body"] = json.dumps({"message": "Theme not added"})
            return response
        response["body"] = theme.json()
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
        logger.exception("Error")
        response["statusCode"] = 500
        response["body"] = json.dumps({"message": str(error)})
        return response
