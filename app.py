#!/usr/bin/env python3
import os

import aws_cdk as cdk

from python.python_stack import PythonStack
from python.python_stack import PythonDependenciesStack

stack_name = (
    "TodoAppBackendStack-nwbxl" if "LOCAL_TESTING" not in os.environ else "PythonStack"
)

app = cdk.App()

deps_stack = PythonDependenciesStack(app, "DassiePythonDependenciesStack")
python_stack = PythonStack(
    app,
    stack_name,
    env=cdk.Environment(account="559845934392", region="eu-west-1"),
)
python_stack.add_dependency(deps_stack)
app.synth()
