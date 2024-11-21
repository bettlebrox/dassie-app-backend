import json
from dassie_logger import logger
from aws_lambda_powertools.logging import correlation_paths
from urllib.parse import unquote_plus
from lambda_init_context import LambdaInitContext

init_context = None


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event, context, neptune_client=None, useGlobal=True):
    logger.debug("begin lambda_handler")
    response = {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": "",
    }
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(neptune_client=neptune_client)
    neptune_client = init_context.neptune_client
    title = unquote_plus(event["pathParameters"]["title"]).title()
    try:
        graph = neptune_client.get_theme_graph(title)
        response["body"] = json.dumps(graph)
    except Exception as e:
        logger.error(f"Error getting theme graph for {title}: {e}")
        response["statusCode"] = 500
    return response
