from aws_cdk import Stack
from aws_cdk import aws_iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from infra_stack import InfraStack
from python_dependencies_stack import PythonDependenciesStack
from python_stack import PythonStack


class PermissionsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        python_stack: PythonStack,
        infra_stack: InfraStack,
        dependencies_stack: PythonDependenciesStack,
        dev_env_instance_role_arn: str = "arn:aws:iam::559845934392:role/Gitpod-gitpodec2runnerinstancerole559EF735-5LajPS4Qj7cP",
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        self.build_article = python_stack.functions["build_articles"]
        self.ddb = infra_stack.ddb
        self.ddb.grant_read_write_data(self.build_article)
        if dev_env_instance_role_arn is not None:
            self.dev_env_instance_role = aws_iam.Role.from_role_arn(
                self,
                "dev_env_instance_role",
                dev_env_instance_role_arn,
            )
            self.grant_lambda_permissions(
                self.dev_env_instance_role,
                infra_stack.sql_db,
                dependencies_stack.openai_secret,
                dependencies_stack.langfuse_secret,
                dependencies_stack.datadog_secret,
            )
        for function in python_stack.functions.values():
            if function.is_bound_to_vpc:
                self.grant_lambda_permissions(
                    function,
                    infra_stack.sql_db,
                    dependencies_stack.openai_secret,
                    dependencies_stack.langfuse_secret,
                    dependencies_stack.datadog_secret,
                )
            else:
                raise ValueError(
                    f"Lambda function {function.function_name} is not bound to a VPC"
                )

    def grant_lambda_permissions(
        self,
        principle,
        sql_db,
        openai_secret,
        langfuse_secret,
        datadog_secret,
    ):
        sql_db.grant_data_api_access(principle)
        sql_db.secret.grant_read(principle)
        openai_secret.grant_read(principle)
        langfuse_secret.grant_read(principle)
        datadog_secret.grant_read(principle)
