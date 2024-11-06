from aws_cdk import Stack, CfnOutput
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_python_alpha as lambda_python


class PythonDependenciesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.reqs_layer = lambda_python.PythonLayerVersion(
            self,
            "RequirementsLayer",
            entry="python/layer",
            compatible_architectures=[lambda_.Architecture.ARM_64],
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Requirements layer",
        )
        self.ai_layer = lambda_python.PythonLayerVersion(
            self,
            "AILayer",
            entry="python/layer_ai",
            compatible_architectures=[lambda_.Architecture.ARM_64],
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Another requirements layer - in order to split deps across zip file limits",
        )
        self.more_ai_layer = lambda_python.PythonLayerVersion(
            self,
            "MoreAILayer",
            entry="python/layer_more_ai",
            compatible_architectures=[lambda_.Architecture.ARM_64],
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
