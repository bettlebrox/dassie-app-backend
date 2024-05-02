from unittest.mock import MagicMock
import os
import sys

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "../../../python/lambda/services"
    )
)
from navlogs_service import NavlogService

TABLE_NAME = "TodoAppBackendStack-nwbxl-navlogDB0A59EC5D-CJ3HCDHHL44L"
BUCKET_NAME = "todoappbackendstack-nwbxl-navlogimages0c68e55c-3ywwdtenerym"


def test_get_navlogs():
    # Create a mock DynamoDB resource and table
    dynamodb_mock = MagicMock()
    table_mock = MagicMock()
    dynamodb_mock.Table.return_value = table_mock

    # Create a mock response from the DynamoDB table
    items = [{"id": "1", "title": "Navlog 1"}, {"id": "2", "title": "Navlog 2"}]
    table_mock.scan.return_value = {"Items": items}

    # Create an instance of NavlogService with the mock DynamoDB resource
    navlog_service = NavlogService(TABLE_NAME, BUCKET_NAME)
    navlog_service._dynamodb = dynamodb_mock

    # Call the get_navlogs method
    result = navlog_service.get_navlogs()

    # Assert that the result matches the expected items
    expected_result = (
        '[{"id": "1", "title": "Navlog 1"}, {"id": "2", "title": "Navlog 2"}]'
    )
    assert result == expected_result
