from aws_lambda_powertools import Logger

logger = Logger(service="dassie", log_record_order=["message"], level="INFO")
