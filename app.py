#!/usr/bin/env python3
import os

import aws_cdk as cdk
import sys
import os

# Add ./python to the Python path
python_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "python"))
sys.path.append(python_path)
from python_stack import PythonStack
from python_dependencies_stack import PythonDependenciesStack


app = cdk.App()
stack_name = (
    "TodoAppBackendStack-nwbxl" if "LOCAL_TESTING" not in os.environ else "LocalStack"
)
python_dependencies_stack = PythonDependenciesStack(
    app, "DassiePythonDependenciesStack"
)
import boto3

# Initialize a boto3 CloudFormation client
cfn_client = boto3.client("cloudformation")

# Get the stack outputs
response = cfn_client.describe_stacks(StackName="DassiePythonDependenciesStack")
outputs = response["Stacks"][0]["Outputs"]


# Function to get output value by key
def get_output_value(key):
    return next((o["OutputValue"] for o in outputs if o["OutputKey"] == key), None)


# Query the outputs from python_dependencies_stack
python_dependencies_stack.layer_arn = get_output_value("PythonLayerStackARN")
python_dependencies_stack.layer_arn_1 = get_output_value("PythonLayerStackARN1")
python_dependencies_stack.layer_arn_2 = get_output_value("PythonLayerStackARN2")


python_stack = PythonStack(
    app,
    stack_name,
    python_dependencies_stack=python_dependencies_stack,
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
)
python_stack.add_dependency(python_dependencies_stack)

app.synth()
