import json
from os import path
import os
from aws_cdk import Stack, CfnOutput, Duration
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_python_alpha as lambda_python
import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_rds as rds
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_logs as logs
import aws_cdk.aws_secretsmanager as secretsmanager  # Import the secretsmanager module
import aws_cdk.aws_iam as iam
import datadog_cdk_constructs_v2 as datadog
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets

ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"

PythonLayerStackOutput = "PythonLayerStackARN"
PythonLayerStackOutput1 = "PythonLayerStackARN1"
PythonLayerStackOutput2 = "PythonLayerStackARN2"


class PythonStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.vpc = ec2.Vpc(self, "AuroraVpc1")
        self.bastion = ec2.SecurityGroup.from_security_group_id(
            self,
            "bastion",
            security_group_id="sg-0669c97cc65247ecd",
        )
        self.sql_db = self.create_postgres_database(self.vpc, self.bastion)
        self.ddb = self.create_ddb_table()
        self.openai_secret, self.langfuse_secret = self.create_secrets()
        (
            self.bucket,
            self.reqs_layers,
            self.lambdas_env,
        ) = self.create_common_lambda_dependencies(
            self.sql_db, self.openai_secret, self.langfuse_secret, self.ddb
        )
        lambda_function_props = {
            "runtime": lambda_.Runtime.PYTHON_3_9,
            "code": lambda_.AssetCode.from_asset(
                path.join(os.getcwd(), "python/lambda")
            ),
            "vpc": self.vpc,
            "layers": self.reqs_layers,
            "architecture": lambda_.Architecture.ARM_64,
            "memory_size": 1024,
            "security_groups": self.sql_db.connections.security_groups,
            "environment": self.lambdas_env,
            "tracing": lambda_.Tracing.PASS_THROUGH,
            "timeout": Duration.seconds(45),
        }

        self.functions = {
            "build_articles": self.create_lambda_function(
                "build_articles",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "get_themes": self.create_lambda_function(
                "get_themes",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "get_articles": self.create_lambda_function(
                "get_articles",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "add_theme": self.create_lambda_function(
                "add_theme",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "del_theme": self.create_lambda_function(
                "del_theme",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "del_related": self.create_lambda_function(
                "del_related",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "add_navlog": self.create_add_navlog_function(
                self.lambdas_env, self.ddb, self.bucket, self.vpc
            ),
        }
        self.instrument_with_datadog(list(self.functions.values()))
        self.modify_security_group_for_lambda_access(
            list(self.functions.values()), self.sql_db
        )

        self.create_scheduled_event_for_build_articles(self.functions["build_articles"])

        self.apiGateway = self.create_api_gateway_resources(self.functions)

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=self.apiGateway.url)

        CfnOutput(
            self, ApiGatewayDomainStackOutput, value=self.apiGateway.url.split("/")[2]
        )

        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=self.apiGateway.deployment_stage.stage_name,
        )

    def instrument_with_datadog(self, functions):
        datadog_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "datadog_api_key",
            secret_complete_arn="arn:aws:secretsmanager:eu-west-1:559845934392:secret:prod/dassie/datadog-axXB8t",
        )
        datadog_ext = datadog.Datadog(
            self,
            "datadog",
            api_key_secret=datadog_secret,
            site="datadoghq.eu",
            python_layer_version=98,
            extension_layer_version=64,
        )
        datadog_ext.add_lambda_functions(functions)
        for f in functions:
            datadog_secret.grant_read(f)

    def grant_lambda_permissions(
        self, lambda_function, sql_db, openai_secret, langfuse_secret
    ):
        sql_db.grant_data_api_access(lambda_function)
        sql_db.connections.allow_default_port_from(lambda_function)
        sql_db.secret.grant_read(lambda_function)
        openai_secret.grant_read(lambda_function)
        langfuse_secret.grant_read(lambda_function)

    def create_postgres_database(self, vpc, bastion):
        sql_db = rds.DatabaseCluster(
            self,
            "dassie1",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            serverless_v2_max_capacity=16,
            serverless_v2_min_capacity=0.5,
            vpc=vpc,
            writer=rds.ClusterInstance.serverless_v2(
                "writer", enable_performance_insights=True
            ),
            storage_encrypted=True,
            monitoring_interval=Duration.seconds(60),
            monitoring_role=iam.Role.from_role_arn(
                self,
                "monitoring-role",
                "arn:aws:iam::559845934392:role/emaccess",
            ),
            cloudwatch_logs_exports=["postgresql"],
        )
        sql_db.connections.allow_default_port_from(bastion)
        return sql_db

    def create_ddb_table(self):
        ddb = dynamodb.Table(
            self,
            "navlogDB",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
        ddb.add_global_secondary_index(
            partition_key=dynamodb.Attribute(
                name="type", type=dynamodb.AttributeType.STRING
            ),
            index_name="type-index",
        )
        return ddb

    def create_secrets(self):
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
        return openai_secret, langfuse_secret

    def create_common_lambda_dependencies(
        self, sql_db, openai_secret, langfuse_secret, ddb
    ):
        bucket = s3.Bucket(
            self,
            "navlog-images",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        reqs_layer = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayer",
            layer_version_arn="arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayer21B3280B:40",
        )
        reqs_layer_1 = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayerExtended",
            layer_version_arn="arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayerExtended6C14504C:5",
        )
        reqs_layer_2 = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayerExtended1",
            layer_version_arn="arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayerExtended2C853E8AE:6",
        )
        lambdas_env = {
            "DB_CLUSTER_ENDPOINT": sql_db.cluster_endpoint.hostname,
            "DB_SECRET_ARN": sql_db.secret.secret_arn,
            "OPENAIKEY_SECRET_ARN": openai_secret.secret_arn,
            "LANGFUSE_SECRET_ARN": langfuse_secret.secret_arn,
            "DDB_TABLE": ddb.table_name,
            "BUCKET_NAME": bucket.bucket_name,
            "DD_SERVERLESS_LOGS_ENABLED": "true",
            "DD_TRACE_ENABLED": "true",
            "DD_LOCAL_TEST": "false",
        }
        return bucket, [reqs_layer, reqs_layer_1, reqs_layer_2], lambdas_env

    def modify_security_group_for_lambda_access(self, functions, sql_db):
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            for function in functions:
                security_group.add_ingress_rule(
                    function.connections.security_groups[0], ec2.Port.tcp(5432)
                )

    def create_add_navlog_function(self, lambdas_env, ddb, bucket, vpc):
        addNavlog = lambda_.Function(
            self,
            "addNavLog",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_navlog.lambda_handler",
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(5),
            vpc=vpc,
            environment=lambdas_env,
        )
        ddb.grant_read_write_data(addNavlog)
        bucket.grant_read_write(addNavlog)
        return addNavlog

    def create_lambda_function(
        self,
        function_name,
        sql_db,
        openai_secret,
        langfuse_secret,
        lambda_function_props,
    ):
        lambda_function = lambda_.Function(
            self,
            function_name,
            handler=f"{function_name.lower()}.lambda_handler",
            **lambda_function_props,
        )
        self.grant_lambda_permissions(
            lambda_function, sql_db, openai_secret, langfuse_secret
        )
        return lambda_function

    def create_api_gateway_dependencies(self):
        log_group = logs.LogGroup(self, "ApiGatewayAccessLogs")
        api_role = iam.Role.from_role_arn(
            self,
            "google_cognito",
            role_arn="arn:aws:sts::559845934392:assumed-role/google_cognito",
        )
        policy = iam.PolicyStatement(
            sid="allow_google_cognito",
            effect=iam.Effect.ALLOW,
            actions=["execute-api:Invoke"],
            resources=[
                f"arn:aws:execute-api:eu-west-1:559845934392:p5cgnlejzk/prod/*/*/*"
            ],
            conditions={"ArnLike": {"AWS:SourceArn": api_role.role_arn}},
            principals=[iam.ServicePrincipal("apigateway.amazonaws.com")],
        )
        cors = apigateway.CorsOptions(
            allow_credentials=True,
            allow_origins=[
                "http://localhost:5174",
                "https://main.d1tgde1goqkt1z.amplifyapp.com",
            ],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return log_group, policy, cors

    def create_api_gateway_resources(self, functions):
        log_group, policy, cors = self.create_api_gateway_dependencies()
        apiGateway = apigateway.RestApi(
            self,
            "ApiGateway",
            policy=iam.PolicyDocument(statements=[policy]),
            default_cors_preflight_options=cors,
            deploy_options=apigateway.StageOptions(
                access_log_destination=apigateway.LogGroupLogDestination(log_group),
                access_log_format=apigateway.AccessLogFormat.custom(
                    json.dumps(
                        {
                            "request_id": apigateway.AccessLogField.context_request_id(),
                            "source_ip": apigateway.AccessLogField.context_identity_source_ip(),
                            "caller": apigateway.AccessLogField.context_identity_caller(),
                            "cognito_id_pool": apigateway.AccessLogField.context_identity_cognito_identity_pool_id(),
                            "method": apigateway.AccessLogField.context_http_method(),
                            "path": apigateway.AccessLogField.context_path(),
                            "status": apigateway.AccessLogField.context_status(),
                            "user_context": {
                                "sub": apigateway.AccessLogField.context_authorizer_claims(
                                    "sub"
                                ),
                                "email": apigateway.AccessLogField.context_authorizer_claims(
                                    "email"
                                ),
                            },
                        }
                    )
                ),
            ),
        )
        api = apiGateway.root.add_resource("api")
        navlogs = api.add_resource(
            "navlogs",
            default_cors_preflight_options=cors,
        )
        navlogs.add_method(
            "POST",
            apigateway.LambdaIntegration(functions["add_navlog"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        articles = api.add_resource(
            "articles",
            default_cors_preflight_options=cors,
        )
        articles.add_method(
            "GET",
            apigateway.LambdaIntegration(functions["get_articles"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes = api.add_resource(
            "themes",
            default_cors_preflight_options=cors,
        )
        themes.add_method(
            "GET",
            apigateway.LambdaIntegration(functions["get_themes"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes.add_method(
            "POST",
            apigateway.LambdaIntegration(functions["add_theme"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes_sub = themes.add_resource("{title}")
        themes_sub.add_method(
            "GET",
            apigateway.LambdaIntegration(functions["get_themes"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes_sub.add_method(
            "DELETE",
            apigateway.LambdaIntegration(functions["del_theme"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes_sub_related = themes_sub.add_resource(
            "related", default_cors_preflight_options=cors
        )
        themes_sub_related_by_id = themes_sub_related.add_resource("{article_id}")
        themes_sub_related_by_id.add_method(
            "DELETE",
            apigateway.LambdaIntegration(functions["del_related"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        return apiGateway

    def create_scheduled_event_for_build_articles(self, build_articles_function):
        # Create a rule that runs every day at 2:00 AM UTC
        rule = events.Rule(
            self,
            "BuildArticlesScheduleRule",
            schedule=events.Schedule.cron(
                minute="0", hour="2", month="*", week_day="*", year="*"
            ),
        )

        # Add the Lambda function as a target for this rule
        rule.add_target(targets.LambdaFunction(build_articles_function))


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
        CfnOutput(
            self,
            PythonLayerStackOutput,
            value=reqs_layer.layer_version_arn,
            export_name="PythonLayerStackARN",
        )
        CfnOutput(
            self,
            PythonLayerStackOutput1,
            value=reqs_layer_1.layer_version_arn,
            export_name="PythonLayerStackARN1",
        )
        CfnOutput(
            self,
            PythonLayerStackOutput2,
            value=reqs_layer_2.layer_version_arn,
            export_name="PythonLayerStackARN2",
        )
