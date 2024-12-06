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
import aws_cdk.aws_lambda as lambda_

RUNTIME = lambda_.Runtime.PYTHON_3_12

app = cdk.App()
stack_name = (
    "DassieAppBackendStack-" if "LOCAL_TESTING" not in os.environ else "LocalStack"
)
python_dependencies_stack = PythonDependenciesStack(
    app,
    "DassiePythonDependenciesStack",
    env=cdk.Environment(account=os.environ["AWS_ACCOUNT_ID"], region="eu-west-1"),
    runtime=RUNTIME,
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
    runtime=RUNTIME,
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
