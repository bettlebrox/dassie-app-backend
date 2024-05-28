import json
import os
import pytest
from moto import mock_aws
import boto3
from unittest.mock import MagicMock
from add_theme import lambda_handler
from models import Article, Theme, ThemeType
from repos import ArticleRepository, ThemeRepository
from services.openai_client import OpenAIClient
from services.themes_service import ThemesService


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["DB_SECRET_ARN"] = "DB_SECRET_ARN"
    os.environ["DB_CLUSTER_ENDPOINT"] = "DB_CLUSTER_ENDPOINT"


@mock_aws
def test_add_theme(aws_credentials):
    event = {"body": json.dumps({"title": "new theme"})}
    context = []
    theme_repo = MagicMock()
    article_repo = MagicMock()
    openai_client = MagicMock()
    openai_client.get_embedding.return_value = [1, 2, 3]
    article_repo.get_by_theme_embedding.return_value = [
        Article("some article", "http://bob.com")
    ]
    themes_service = MagicMock()
    test_theme = Theme("new theme", "some summary")
    themes_service.build_themes_from_articles.return_value = [test_theme]
    secretsmanager = boto3.client("secretsmanager")
    response = secretsmanager.create_secret(
        SecretString='{"username": "username", "password": "password", "dbname": "dbname"}',
        Name="DB_SECRET_ARN",
    )
    os.environ["DB_SECRET_ARN"] = response["ARN"]
    payload = lambda_handler(
        event, context, article_repo, theme_repo, openai_client, themes_service
    )
    assert payload["statusCode"] == 201
    assert json.loads(payload["body"])["themes"][0] == test_theme.json()
