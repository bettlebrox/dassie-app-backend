#!/usr/bin/env python3
import os

import aws_cdk as cdk
import sys
import os

# Add ./python to the Python path
python_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "python"))
sys.path.append(python_path)
from infra_stack import InfraStack
from python_stack import PythonStack
from python_dependencies_stack import PythonDependenciesStack
from permissions_stack import PermissionsStack
import boto3

app = cdk.App()
stack_name = (
    "DassieAppBackendStack-" if "LOCAL_TESTING" not in os.environ else "LocalStack"
)
python_dependencies_stack = PythonDependenciesStack(
    app,
    "DassiePythonDependenciesStack",
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
)

# SAM needs the layer arns to be set before run local start-api
cfn_client = boto3.client("cloudformation")
response = cfn_client.describe_stacks(StackName="DassiePythonDependenciesStack")
outputs = response["Stacks"][0]["Outputs"]


def get_output_value(key, default=None):
    return next((o["OutputValue"] for o in outputs if o["OutputKey"] == key), default)


python_dependencies_stack.reqs_layer_arn = get_output_value(
    "ReqsLayerOutput",
    "arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayer21B3280B:45",
)
python_dependencies_stack.ai_layer_arn = get_output_value(
    "AILayerOutput",
    "arn:aws:lambda:eu-west-1:559845934392:layer:AILayerD278B124:1",
)
python_dependencies_stack.more_ai_layer_arn = get_output_value(
    "MoreAILayerOutput",
    "arn:aws:lambda:eu-west-1:559845934392:layer:MoreAILayer75E81DE2:2",
)

infra_stack = InfraStack(
    app,
    "DassieInfraStack",
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
)

python_stack = PythonStack(
    app,
    stack_name,
    dependencies_stack=python_dependencies_stack,
    infra_stack=infra_stack,
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
)
python_stack.add_dependency(python_dependencies_stack)
python_stack.add_dependency(infra_stack)
permissions_stack = PermissionsStack(
    app,
    "DassiePermissionsStack",
    python_stack=python_stack,
    infra_stack=infra_stack,
    dependencies_stack=python_dependencies_stack,
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
)
permissions_stack.add_dependency(python_stack)
app.synth()
