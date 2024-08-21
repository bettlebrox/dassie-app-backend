from repos import ArticleRepository
from services.openai_client import OpenAIClient
from services.themes_service import ThemesService


import boto3
import logging

import json
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


from theme_repo import ThemeRepository


class LambdaInitContext:
    OPENAI_SECRET_KEY = "OPENAI_API_KEY"
    LANGFUSE_SECRET_KEY = "langfuse_secret_key"
    DB_NAME = "dassie"

    def __init__(
        self,
        secrets_manager=None,
        db_secrets=None,
        article_repo=None,
        openai_client=None,
        theme_repo=None,
        theme_service=None,
    ):
        self._secrets_manager = secrets_manager
        self._db_secrets = db_secrets
        self._article_repo = article_repo
        self._openai_client = openai_client
        self._theme_repo = theme_repo
        self._theme_service = theme_service

    @property
    def secrets_manager(self):
        if self._secrets_manager is None:
            self._secrets_manager = boto3.client("secretsmanager")
        return self._secrets_manager

    @property
    def db_secrets(self):
        if self._db_secrets is None:
            logger.info(f"Fetching db secret: {os.environ['DB_SECRET_ARN']}")
            get_secret_value_response = self.secrets_manager.get_secret_value(
                SecretId=os.environ["DB_SECRET_ARN"]
            )
            secret = json.loads(get_secret_value_response["SecretString"])
            self._db_secrets = secret["username"], secret["password"], "dassie"
        return self._db_secrets

    @property
    def article_repo(self):
        if self._article_repo is None:
            self._article_repo = ArticleRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        return self._article_repo

    @property
    def openai_client(self):
        if self._openai_client is None:
            get_secret_value_response = self.secrets_manager.get_secret_value(
                SecretId=os.environ["OPENAIKEY_SECRET_ARN"]
            )
            secret = json.loads(get_secret_value_response["SecretString"])
            get_secret_value_response = self.secrets_manager.get_secret_value(
                SecretId=os.environ["LANGFUSE_SECRET_ARN"]
            )
            lang_fuse_secret = json.loads(get_secret_value_response["SecretString"])
            self._openai_client = OpenAIClient(
                secret[self.OPENAI_SECRET_KEY],
                lang_fuse_secret[self.LANGFUSE_SECRET_KEY],
            )
        return self._openai_client

    @property
    def theme_repo(self):
        if self._theme_repo is None:
            self._theme_repo = ThemeRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        return self._theme_repo

    @property
    def theme_service(self):
        if self._theme_service is None:
            self._theme_service = ThemesService(
                self.theme_repo, self.article_repo, self.openai_client
            )
        return self._theme_service
