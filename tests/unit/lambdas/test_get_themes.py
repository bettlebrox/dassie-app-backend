import os
from unittest.mock import MagicMock
import pytest
from get_themes import lambda_handler
import boto3
from moto import mock_aws

from models import ThemeType


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


@pytest.fixture(scope="function")
def create_secret():
    with mock_aws():
        secretsmanager = boto3.client("secretsmanager")
        response = secretsmanager.create_secret(
            SecretString='{"username": "username", "password": "password", "dbname": "dbname"}',
            Name="DB_SECRET_ARN",
        )
        os.environ["DB_SECRET_ARN"] = response["ARN"]


def test_get_themes(aws_credentials, create_secret):
    theme_repo = MagicMock()
    response = lambda_handler({"path": "/themes"}, {}, theme_repo)
    assert response["statusCode"] == 200


def test_get_theme(aws_credentials, create_secret):
    theme_repo = MagicMock()
    response = lambda_handler(
        {"path": "/themes/whats+the+best+way+to+add+google+id+with+cognito%3F"},
        {},
        theme_repo,
    )
    assert response["statusCode"] == 200


def test_get_themes_with_invalid_params(aws_credentials, create_secret):
    theme_repo = MagicMock()
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "count_asssociation", "max": 20},
        },
        {},
        theme_repo,
    )
    assert response["statusCode"] == 400
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"source": "made_up_type", "max": 20},
        },
        {},
        theme_repo,
    )
    assert response["statusCode"] == 400


def test_get_themes_with_params(aws_credentials, create_secret):
    theme_repo = MagicMock()
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "count_association", "max": 20},
        },
        {},
        theme_repo,
    )
    assert response["statusCode"] == 200
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {"sortField": "updated_at", "max": 20},
        },
        {},
        theme_repo,
    )
    assert response["statusCode"] == 200
    response = lambda_handler(
        {
            "path": "/themes",
            "queryStringParameters": {
                "sortField": "updated_at",
                "source": "custom",
                "max": 2,
            },
        },
        {},
        theme_repo,
    )
    theme_repo.get_recent.assert_called_with(2, ThemeType.CUSTOM)
    assert response["statusCode"] == 200
