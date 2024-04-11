import json
import os
import sys

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "../../../python/services"
    )
)
from navlogs_service import NavlogService


def test_get_navlogs():
    navlog_service = NavlogService()

    # Call the get_navlogs method
    result = navlog_service.get_navlogs()

    assert len(result) > 0


def test_get_content_navlogs():
    navlog_service = NavlogService()

    # Call the get_content_navlogs method
    result = navlog_service.get_content_navlogs()

    assert len(result) > 0


def test_put_navlog():
    navlog_service = NavlogService()
    navlog = {"id": "1", "title": "Navlog 1"}

    # Call the put_navlog method
    result = navlog_service.put_navlog(navlog)

    assert result == json.dumps(navlog)
