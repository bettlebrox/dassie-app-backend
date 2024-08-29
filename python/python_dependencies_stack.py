from aws_cdk import Stack, CfnOutput
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_python_alpha as lambda_python


class PythonDependenciesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        reqs_layer = lambda_python.PythonLayerVersion(
            self,
            "RequirementsLayer",
            entry="python/layer",
            compatible_architectures=[lambda_.Architecture.ARM_64],
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Requirements layer",
        )
        reqs_layer_1 = lambda_python.PythonLayerVersion(
            self,
            "RequirementsLayerExtended",
            entry="python/layer1",
            compatible_architectures=[lambda_.Architecture.ARM_64],
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Another requirements layer - in order to split deps across zip file limits",
        )
        reqs_layer_2 = lambda_python.PythonLayerVersion(
            self,
            "RequirementsLayerExtended2",
            entry="python/layer2",
            compatible_architectures=[lambda_.Architecture.ARM_64],
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="Another requirements layer - in order to split deps across zip file limits",
        )
        self.layer_arn = CfnOutput(
            self,
            "PythonLayerStackARN",
            value=reqs_layer.layer_version_arn,
            export_name="PythonLayerStackARN",
        ).export_name

        self.layer_arn_1 = CfnOutput(
            self,
            "PythonLayerStackARN1",
            value=reqs_layer_1.layer_version_arn,
            export_name="PythonLayerStackARN1",
        ).export_name

        self.layer_arn_2 = CfnOutput(
            self,
            "PythonLayerStackARN2",
            value=reqs_layer_2.layer_version_arn,
            export_name="PythonLayerStackARN2",
        ).export_name
