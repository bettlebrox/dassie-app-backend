import os
import sys

sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python/lambda")
)
from services.navlogs_service import NavlogService
import pytest

TABLE_NAME = "TodoAppBackendStack-nwbxl-navlogDB0A59EC5D-CJ3HCDHHL44L"
BUCKET_NAME = "todoappbackendstack-nwbxl-navlogimages0c68e55c-3ywwdtenerym"


@pytest.fixture
def navlog_service():
    return NavlogService(BUCKET_NAME, TABLE_NAME)


def test_get_content_navlogs(navlog_service):
    items = navlog_service.get_content_navlogs()
    assert len(items) >= 1
    assert items[0]["type"] == "content"
