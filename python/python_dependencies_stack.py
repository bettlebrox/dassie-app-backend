from aws_cdk import CfnOutput, Stack
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_python_alpha as lambda_python
import aws_cdk.aws_secretsmanager as secretsmanager  # Import the secretsmanager module

from aws_cdk import RemovalPolicy


class PythonDependenciesStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, testing: bool = False, **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)

        self.openai_secret, self.langfuse_secret, self.datadog_secret = (
            self._create_secrets()
        )
        CfnOutput(
            self,
            "ReqsLayerOutput",
            value="1",
            export_name="ReqsLayer",
        )
        CfnOutput(
            self,
            "AILayerOutput",
            value="2",
            export_name="AILayer",
        )
        CfnOutput(
            self,
            "MoreAILayerOutput",
            value="3",
            export_name="MoreAILayer",
        )

    def _create_secrets(self):
        openai_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "openai_api_key",
            secret_complete_arn="arn:aws:secretsmanager:eu-west-1:559845934392:secret:dassie/prod/openaikey-8BLvR2",
        )
        langfuse_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "langfuse_secret_key",
            secret_complete_arn="arn:aws:secretsmanager:eu-west-1:559845934392:secret:dassie/prod/langfusekey-f9UsZW",
        )
        datadog_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "datadog_api_key",
            secret_complete_arn="arn:aws:secretsmanager:eu-west-1:559845934392:secret:prod/dassie/datadog-axXB8t",
        )
        return openai_secret, langfuse_secret, datadog_secret
