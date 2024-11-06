from aws_cdk import Stack
from aws_cdk import aws_iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from infra_stack import InfraStack
from python_stack import PythonStack


class PermissionsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        python_stack: PythonStack,
        infra_stack: InfraStack,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        self.build_article = python_stack.functions["build_articles"]
        self.ddb = infra_stack.ddb
        self.lambda_db_access_sg = infra_stack.lambda_db_access_sg
        self.ddb.grant_read_write_data(self.build_article)
        for function in python_stack.functions.values():
            if function.is_bound_to_vpc:
                self.grant_lambda_permissions(
                    function,
                    infra_stack.sql_db,
                    python_stack.openai_secret,
                    python_stack.langfuse_secret,
                    self.lambda_db_access_sg,
                )
            else:
                raise ValueError(
                    f"Lambda function {function.function_name} is not bound to a VPC"
                )
        # self.modify_security_group_for_lambda_access(
        #     python_stack.functions.values(), infra_stack.sql_db
        # )

    def grant_lambda_permissions(
        self,
        lambda_function,
        sql_db,
        openai_secret,
        langfuse_secret,
        lambda_db_access_sg,
    ):
        sql_db.grant_data_api_access(lambda_function)
        sql_db.secret.grant_read(lambda_function)
        openai_secret.grant_read(lambda_function)
        langfuse_secret.grant_read(lambda_function)

    def modify_security_group_for_lambda_access(
        self, functions, sql_db: rds.DatabaseCluster
    ):
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            for function in functions:
                if function.is_bound_to_vpc:
                    security_group.add_ingress_rule(
                        function.connections.security_groups[0], ec2.Port.tcp(5432)
                    )
