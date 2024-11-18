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
from services.neptune_client import NeptuneClient


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
        boto_event_client=None,
        neptune_client=None,
        openai_secret=None,
        lang_fuse_secret=None,
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
        self._boto_event_client = boto_event_client
        self._neptune_client = neptune_client
        self._openai_secret = openai_secret
        self._lang_fuse_secret = lang_fuse_secret

    @property
    def neptune_client(self) -> NeptuneClient:
        if self._neptune_client is None:
            logger.info(
                "init neptune client",
                extra={"neptune_endpoint": os.getenv("NEPTUNE_ENDPOINT")},
            )
            self._neptune_client = NeptuneClient(
                os.getenv("NEPTUNE_ENDPOINT"),
                self.lang_fuse_secret,
            )
        return self._neptune_client

    @property
    def boto_event_client(self) -> boto3.client:
        if self._boto_event_client is None:
            logger.info("init boto event client")
            self._boto_event_client = boto3.client("events")
        logger.debug("retrieved boto event client")
        return self._boto_event_client

    @property
    def browsed_repo(self) -> BrowsedRepository:
        if self._browsed_repo is None:
            logger.info("init browsed repo")
            self._browsed_repo = BrowsedRepository(
                *self.db_secrets,
                os.getenv("DB_CLUSTER_ENDPOINT"),
            )
        logger.debug("retrieved browsed repo")
        return self._browsed_repo

    @property
    def browse_repo(self) -> BrowseRepository:
        if self._browse_repo is None:
            logger.info("init browse repo")
            self._browse_repo = BrowseRepository(
                *self.db_secrets,
                os.getenv("DB_CLUSTER_ENDPOINT"),
            )
        logger.debug("retrieved browse repo")
        return self._browse_repo

    @property
    def article_service(self) -> ArticlesService:
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
    def secrets_manager(self) -> boto3.client:
        if self._secrets_manager is None:
            logger.info("init secrets manager")
            self._secrets_manager = boto3.client("secretsmanager")
        logger.debug("retrieved secrets manager")
        return self._secrets_manager

    @property
    def db_secrets(self) -> tuple[str, str, str]:
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
    def article_repo(self) -> ArticleRepository:
        if self._article_repo is None:
            logger.info("init article repo")
            self._article_repo = ArticleRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        logger.debug("retrieved article repo")
        return self._article_repo

    def _get_secret_string_from_arn(self, arn, key) -> str:
        get_secret_value_response = self.secrets_manager.get_secret_value(SecretId=arn)
        return json.loads(get_secret_value_response["SecretString"])[key]

    @property
    def openai_secret(self) -> str:
        if self._openai_secret is None:
            self._openai_secret = self._get_secret_string_from_arn(
                os.environ["OPENAIKEY_SECRET_ARN"], self.OPENAI_SECRET_KEY
            )
        return self._openai_secret

    @property
    def lang_fuse_secret(self) -> str:
        if self._lang_fuse_secret is None:
            self._lang_fuse_secret = self._get_secret_string_from_arn(
                os.environ["LANGFUSE_SECRET_ARN"], self.LANGFUSE_SECRET_KEY
            )
        return self._lang_fuse_secret

    @property
    def openai_client(self) -> OpenAIClient:
        if self._openai_client is None:
            logger.info(
                "init openai client",
                extra={
                    "openai_secret_arn": os.environ["OPENAIKEY_SECRET_ARN"],
                    "langfuse_secret_arn": os.environ["LANGFUSE_SECRET_ARN"],
                },
            )
            self._openai_client = OpenAIClient(
                self.openai_secret,
                self.lang_fuse_secret,
            )
        logger.debug("retrieved openai client")
        return self._openai_client

    @property
    def theme_repo(self) -> ThemeRepository:
        if self._theme_repo is None:
            logger.info("init theme repo")
            self._theme_repo = ThemeRepository(
                *self.db_secrets,
                os.environ["DB_CLUSTER_ENDPOINT"],
            )
        logger.debug("retrieved theme repo")
        return self._theme_repo

    @property
    def theme_service(self) -> ThemesService:
        if self._theme_service is None:
            logger.info("init theme service")
            self._theme_service = ThemesService(
                self.theme_repo, self.article_repo, self.openai_client
            )
        logger.debug("retrieved theme service")
        return self._theme_service

    @property
    def navlog_service(self) -> NavlogService:
        if self._navlog_service is None:
            logger.info("init navlog service")
            self._navlog_service = NavlogService(
                os.getenv("BUCKET_NAME"), os.getenv("DDB_TABLE")
            )
        logger.debug("retrieved navlog service")
        return self._navlog_service
