import json
import os
import pytest
from moto import mock_aws
import boto3
from unittest.mock import MagicMock
from add_theme import lambda_handler
from models.article import Article
from models.theme import Theme, ThemeType
from services.openai_client import LLMResponseException
from services.themes_service import ThemesService


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["DB_CLUSTER_ENDPOINT"] = "DB_CLUSTER_ENDPOINT"
    os.environ["DB_SECRET_ARN"] = "DB_SECRET_ARN"
    os.environ["OPENAIKEY_SECRET_ARN"] = "OPENAIKEY_SECRET_ARN"


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.fixture
def create_secret():
    with mock_aws():
        secretsmanager = boto3.client("secretsmanager")
        response = secretsmanager.create_secret(
            SecretString='{"username": "username", "password": "password", "dbname": "dbname"}',
            Name=os.environ["DB_SECRET_ARN"],
        )
        response = secretsmanager.create_secret(
            SecretString='{"OPENAI_API_KEY": "openai_api_key"}',
            Name="OPENAIKEY_SECRET_ARN",
        )
        os.environ["OPENAIKEY_SECRET_ARN"] = response["ARN"]
        yield secretsmanager


@mock_aws
def test_add_theme(aws_credentials, create_secret, mock_context):
    event = {"body": json.dumps({"title": "new theme"})}
    theme_service = MagicMock()
    theme_service.get_theme_by_title.return_value = None
    test_theme = Theme("new theme", source=ThemeType.CUSTOM)
    theme_service.add_theme.return_value = test_theme
    payload = lambda_handler(
        event, mock_context, theme_service=theme_service, useGlobal=False
    )
    assert payload["statusCode"] == 202, f"status code is not 202"
    theme = json.loads(payload["body"])
    assert theme["original_title"] == "New Theme"
    assert theme["source"] == ThemeType.CUSTOM.value


@mock_aws
def test_add_theme_error(aws_credentials, create_secret, mock_context):
    event = {"body": json.dumps({"title": "new theme"})}
    theme_service = MagicMock()
    theme_service.get_theme_by_title.side_effect = Exception("error")
    payload = lambda_handler(
        event,
        mock_context,
        theme_service=theme_service,
        useGlobal=False,
    )
    assert payload["statusCode"] == 500
    assert json.loads(payload["body"])["message"] == "error"
