from unittest.mock import MagicMock
from models.article import Article
from lambda_init_context import LambdaInitContext
from process_theme_graph import lambda_handler
from dotenv import load_dotenv


def test_process_theme_graph_success():
    assert load_dotenv("tests/integ/lambda/local.env")
    init_context = LambdaInitContext()
    context = MagicMock()
    response = lambda_handler(
        {"body": '{"title": "history+prediction+markets"}'},
        context,
        article_repo=init_context.article_repo,
        openai_client=init_context.openai_client,
        neptune_client=init_context.neptune_client,
        useGlobal=False,
    )
    assert response["statusCode"] == 201
