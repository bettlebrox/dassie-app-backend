import unittest
from unittest.mock import MagicMock, patch
from lambda_init_context import LambdaInitContext


class TestLambdaInitContext(unittest.TestCase):

    def test_lambda_init_context_instantiation(self):
        context = LambdaInitContext()
        self.assertIsInstance(context, LambdaInitContext)

    def test_lambda_init_context_attributes(self):
        context = LambdaInitContext()
        self.assertTrue(hasattr(context, "__dict__"))

    def test_secrets_manager_property(self):
        context = LambdaInitContext()
        self.assertIsNotNone(context.secrets_manager)
        self.assertEqual(
            context.secrets_manager, context.secrets_manager
        )  # Test caching

    @patch.dict("os.environ", {"DB_SECRET_ARN": "test_db_secret_arn"})
    def test_db_secrets_with_mocked_env_variable(self):
        secrets_manager_mock = MagicMock()
        secrets_manager_mock.get_secret_value.return_value = {
            "SecretString": '{"username": "test_user", "password": "test_pass"}'
        }
        context = LambdaInitContext(secrets_manager=secrets_manager_mock)

        self.assertIsNotNone(context.db_secrets)
        self.assertEqual(len(context.db_secrets), 3)
        self.assertEqual(context.db_secrets[0], "test_user")
        self.assertEqual(context.db_secrets[1], "test_pass")
        self.assertEqual(context.db_secrets[2], "dassie")

        # Verify that the mocked environment variable was used
        secrets_manager_mock.get_secret_value.assert_called_once_with(
            SecretId="test_db_secret_arn"
        )

    @patch.dict("os.environ", {"DB_SECRET_ARN": "test_db_secret_arn"})
    @patch.dict("os.environ", {"DB_CLUSTER_ENDPOINT": "test_cluster_endpoint"})
    def test_article_repo_property(self):
        context = LambdaInitContext(db_secrets=("user", "pass", "db"))
        self.assertIsNotNone(context.article_repo)
        self.assertEqual(context.article_repo, context.article_repo)  # Test caching

    @patch.dict("os.environ", {"OPENAIKEY_SECRET_ARN": "test_openai_secret_arn"})
    @patch.dict("os.environ", {"LANGFUSE_SECRET_ARN": "test_langfuse_secret_key"})
    def test_openai_client_property(self):
        mock_secrets_manager = MagicMock()
        mock_secrets_manager.get_secret_value.side_effect = [
            {"SecretString": '{"OPENAI_API_KEY": "test_openai_key"}'},
            {"SecretString": '{"langfuse_secret_key": "test_langfuse_key"}'},
        ]
        context = LambdaInitContext(secrets_manager=mock_secrets_manager)
        self.assertIsNotNone(context.openai_client)
        self.assertEqual(context.openai_client, context.openai_client)  # Test caching

    @patch.dict("os.environ", {"DB_SECRET_ARN": "test_db_secret_arn"})
    @patch.dict("os.environ", {"DB_CLUSTER_ENDPOINT": "test_cluster_endpoint"})
    def test_article_repo_property(self):
        context = LambdaInitContext(db_secrets=("user", "pass", "db"))
        self.assertIsNotNone(context.article_repo)
        self.assertEqual(context.article_repo, context.article_repo)  # Test caching

    @patch.dict("os.environ", {"DB_SECRET_ARN": "test_db_secret_arn"})
    def test_theme_service_property(self):
        context = LambdaInitContext(
            theme_repo=MagicMock(), article_repo=MagicMock(), openai_client=MagicMock()
        )
        self.assertIsNotNone(context.theme_service)
        self.assertEqual(context.theme_service, context.theme_service)  # Test caching

    def test_navlog_service_property(self):
        context = LambdaInitContext()
        self.assertIsNotNone(context.navlog_service)
        self.assertEqual(context.navlog_service, context.navlog_service)  # Test caching

    def test_lambda_init_context_add_attribute(self):
        context = LambdaInitContext()
        context.test_attr = "test_value"
        self.assertEqual(context.test_attr, "test_value")

    def test_lambda_init_context_multiple_attributes(self):
        context = LambdaInitContext()
        context.attr1 = 1
        context.attr2 = "two"
        context.attr3 = [3]
        self.assertEqual(context.attr1, 1)
        self.assertEqual(context.attr2, "two")
        self.assertEqual(context.attr3, [3])

    def test_lambda_init_context_attribute_modification(self):
        context = LambdaInitContext()
        context.mutable_attr = [1, 2, 3]
        context.mutable_attr.append(4)
        self.assertEqual(context.mutable_attr, [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
