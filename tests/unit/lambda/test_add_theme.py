import json
import os
import pytest
from unittest.mock import MagicMock
from add_theme import lambda_handler
from models.theme import Theme, ThemeType


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


def test_add_theme(mock_context):
    event = {"body": json.dumps({"title": "new theme"})}
    theme_service = MagicMock()
    boto_event_client = MagicMock()
    theme_service.get_theme_by_original_title.return_value = None
    test_theme = Theme("new theme", source=ThemeType.CUSTOM)
    theme_service.add_theme.return_value = test_theme
    mock_context.function_name = "add_theme"
    mock_context.function_version = "1"
    payload = lambda_handler(
        event,
        mock_context,
        theme_service=theme_service,
        useGlobal=False,
        boto_event_client=boto_event_client,
    )
    assert payload["statusCode"] == 202, f"status code is not 202"
    theme = json.loads(payload["body"])
    assert theme["original_title"] == "New Theme"
    assert theme["source"] == ThemeType.CUSTOM.value
    assert boto_event_client.put_events.call_count == 1


def test_add_theme_error(mock_context):
    event = {"body": json.dumps({"title": "new theme"})}
    theme_service = MagicMock()
    theme_service.get_theme_by_original_title.side_effect = Exception("error")
    payload = lambda_handler(
        event,
        mock_context,
        theme_service=theme_service,
        useGlobal=False,
    )
    assert payload["statusCode"] == 500
    assert json.loads(payload["body"])["message"] == "error"
