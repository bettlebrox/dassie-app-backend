from dassie_logger import logger
from aws_lambda_powertools.logging import correlation_paths
from lambda_init_context import LambdaInitContext
from models.article import ArticleType
import json

init_context = None


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(
    event,
    context,
    article_repo=None,
    theme_repo=None,
    openai_client=None,
    useGlobal=True,
):
    logger.debug("begin search lambda_handler")
    global init_context
    if init_context is None or not useGlobal:
        init_context = LambdaInitContext(
            article_repo=article_repo,
            theme_repo=theme_repo,
            openai_client=openai_client,
        )
    article_repo = init_context.article_repo
    theme_repo = init_context.theme_repo
    openai_client = init_context.openai_client
    response = {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}}
    try:
        search_query = (
            event["pathParameters"]["query"]
            if "query" in event["pathParameters"]
            else ""
        )
        embedding = openai_client.get_embedding(search_query)
        articles = article_repo.get(
            filter_embedding=embedding,
            threshold=0.5,
            type=[ArticleType.ARTICLE],
            include_score_in_results=True,
            min_token_count=0,
        )
        themes = theme_repo.get(filter_embedding=embedding, threshold=0.5)

        combined_results = {
            "articles": [
                {**article.json(dump=False), "score": score}
                for article, score in articles
            ],
            "themes": [
                {**theme.json(dump=False), "score": score} for theme, score in themes
            ],
        }
        response["body"] = json.dumps(combined_results)
    except Exception as error:
        logger.exception("Error")
        response["body"] = {"message": str(error)}
        response["statusCode"] = 500
    return response
