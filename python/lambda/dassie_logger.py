from aws_lambda_powertools import Logger
import os

log_level = "DEBUG" if os.environ.get("LOCAL_TESTING") else "INFO"
logger = Logger(
    service="dassie-app-backend", log_record_order=["message"], level=log_level
)
