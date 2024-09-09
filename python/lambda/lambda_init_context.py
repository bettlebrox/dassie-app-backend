from repos import BrowsedRepository
from browse_repo import BrowseRepository
from article_repo import ArticleRepository
from services.articles_service import ArticlesService
from services.navlogs_service import NavlogService
from services.openai_client import OpenAIClient
from services.themes_service import ThemesService
import boto3
import json
import os
from theme_repo import ThemeRepository
from dassie_logger import logger


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
        article_service=None,
        navlog_service=None,
        browse_repo=None,
    ):
        logger.info("init lambda context")
        self._secrets_manager = secrets_manager
        self._db_secrets = db_secrets
        self._article_repo = article_repo
        self._openai_client = openai_client
        self._theme_repo = theme_repo
        self._theme_service = theme_service
        self._article_service = article_service
        self._browse_repo = browse_repo
        self._browsed_repo = None
        self._navlog_service = navlog_service

    @property
    def browsed_repo(self):
        if self._browsed_repo is None:
            logger.info("init browsed repo")
            self._browsed_repo = BrowsedRepository(
                *self.db_secrets,
                os.getenv("DB_CLUSTER_ENDPOINT"),
            )
        logger.debug("retrieved browsed repo")
        return self._browsed_repo

    @property
    def browse_repo(self):
        if self._browse_repo is None:
            logger.info("init browse repo")
            self._browse_repo = BrowseRepository(
                *self.db_secrets,
                os.getenv("DB_CLUSTER_ENDPOINT"),
            )
        logger.debug("retrieved browse repo")
        return self._browse_repo

    @property
    def article_service(self):
        if self._article_service is None:
            logger.info("init article service")
            self._article_service = ArticlesService(
                self.article_repo,
                self.theme_repo,
                self.browse_repo,
                self.browsed_repo,
                self.openai_client,
            )
        logger.debug("retrieved article service")
        return self._article_service

    @property
    def secrets_manager(self):
        if self._secrets_manager is None:
            logger.info("init secrets manager")
            self._secrets_manager = boto3.client("secretsmanager")
        logger.debug("retrieved secrets manager")
        return self._secrets_manager

    @property
    def db_secrets(self):
        if self._db_secrets is None:
            logger.info(
                "init db secrets", extra={"db_secret_arn": os.environ["DB_SECRET_ARN"]}
            )
            get_secret_value_response = self.secrets_manager.get_secret_value(
                SecretId=os.environ["DB_SECRET_ARN"]
            )
            secret = json.loads(get_secret_value_response["SecretString"])
            self._db_secrets = secret["username"], secret["password"], "dassie"
        logger.debug("retrieved db secrets")
        return self._db_secrets

    @property
    def article_repo(self):
        if self._article_repo is None:
            logger.info("init article repo")
            self._article_repo = ArticleRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        logger.debug("retrieved article repo")
        return self._article_repo

    @property
    def openai_client(self):
        if self._openai_client is None:
            logger.info(
                "init openai client",
                extra={
                    "openai_secret_arn": os.environ["OPENAIKEY_SECRET_ARN"],
                    "langfuse_secret_arn": os.environ["LANGFUSE_SECRET_ARN"],
                },
            )
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
        logger.debug("retrieved openai client")
        return self._openai_client

    @property
    def theme_repo(self):
        if self._theme_repo is None:
            logger.info("init theme repo")
            self._theme_repo = ThemeRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        logger.debug("retrieved theme repo")
        return self._theme_repo

    @property
    def theme_service(self):
        if self._theme_service is None:
            logger.info("init theme service")
            self._theme_service = ThemesService(
                self.theme_repo, self.article_repo, self.openai_client
            )
        logger.debug("retrieved theme service")
        return self._theme_service

    @property
    def navlog_service(self):
        if self._navlog_service is None:
            logger.info("init navlog service")
            self._navlog_service = NavlogService(
                os.getenv("BUCKET_NAME"), os.getenv("DDB_TABLE")
            )
        logger.debug("retrieved navlog service")
        return self._navlog_service
