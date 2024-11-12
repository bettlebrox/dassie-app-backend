from aws_cdk import CfnOutput, Stack
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_python_alpha as lambda_python
import aws_cdk.aws_secretsmanager as secretsmanager  # Import the secretsmanager module


class PythonDependenciesStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, testing: bool = False, **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)
        if testing:
            # TODO: this is a hack speed up testing, pip won't actually run in this case
            self.reqs_layer = lambda_.LayerVersion.from_layer_version_arn(
                self,
                "RequirementsLayer",
                "arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayer21B3280B:45",
            )
            self.ai_layer = lambda_.LayerVersion.from_layer_version_arn(
                self,
                "AILayer",
                "arn:aws:lambda:eu-west-1:559845934392:layer:AILayerD278B124:1",
            )
            self.more_ai_layer = lambda_.LayerVersion.from_layer_version_arn(
                self,
                "MoreAILayer",
                "arn:aws:lambda:eu-west-1:559845934392:layer:MoreAILayer75E81DE2:2",
            )
        else:
            self.reqs_layer = lambda_python.PythonLayerVersion(
                self,
                "RequirementsLayer",
                entry="python/layer",
                compatible_architectures=[lambda_.Architecture.X86_64],
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
                description="Requirements layer",
            )
            self.ai_layer = lambda_python.PythonLayerVersion(
                self,
                "AILayer",
                entry="python/layer_ai",
                compatible_architectures=[lambda_.Architecture.X86_64],
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
                description="Another requirements layer - in order to split deps across zip file limits",
            )
            self.more_ai_layer = lambda_python.PythonLayerVersion(
                self,
                "MoreAILayer",
                entry="python/layer_more_ai",
                compatible_architectures=[lambda_.Architecture.X86_64],
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
                description="Requirements layer for layer2 - more ai",
                bundling=lambda_python.BundlingOptions(
                    asset_excludes=[
                        "*.pyc",
                        "*.pyo",
                        "tests/*",
                        "docs/*",
                        "pyarrow/*",
                        "pandas/*",
                        "openai/*",
                    ],
                    environment={
                        "PYTHONUNBUFFERED": "1",
                    },
                ),
            )
        self.openai_secret, self.langfuse_secret, self.datadog_secret = (
            self._create_secrets()
        )
        CfnOutput(
            self,
            "ReqsLayerOutput",
            value=self.reqs_layer.layer_version_arn,
            export_name="ReqsLayer",
        )
        CfnOutput(
            self,
            "AILayerOutput",
            value=self.ai_layer.layer_version_arn,
            export_name="AILayer",
        )
        CfnOutput(
            self,
            "MoreAILayerOutput",
            value=self.more_ai_layer.layer_version_arn,
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
