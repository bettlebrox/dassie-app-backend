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
import aws_cdk.aws_logs as logs
import aws_cdk.aws_logs_destinations as destinations
import aws_cdk.aws_secretsmanager as secretsmanager  # Import the secretsmanager module

ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"


class PythonStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = ec2.Vpc(self, "AuroraVpc")
        # Create a new secret to store the master username and password for the Aurora Serverless cluster
        sql_db = rds.ServerlessCluster(
            self,
            "dassie",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_13_12
            ),
            vpc=vpc,
            enable_data_api=True,
            default_database_name="dassie",
        )
        ddb = dynamodb.Table(
            self,
            "navlogDB",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
        )
        ddb.add_global_secondary_index(
            partition_key=dynamodb.Attribute(
                name="type", type=dynamodb.AttributeType.STRING
            ),
            index_name="type-index",
        )
        reqs_layer = lambda_python.PythonLayerVersion(
            self,
            "RequirementsLayer",
            entry="python/lambda",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_8],
            description="Requirements layer",
        )
        nr_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "nr_license_key",
            secret_complete_arn="arn:aws:secretsmanager:eu-west-1:559845934392:secret:NEW_RELIC_LICENSE_KEY-vZyhkl",
        )
        getThemes = lambda_.Function(
            self,
            "getThemes",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="get_themes.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer],
            security_groups=sql_db.connections.security_groups,
            environment={
                "DB_CLUSTER_ENDPOINT": sql_db.cluster_endpoint.hostname,
                "DB_SECRET_ARN": sql_db.secret.secret_arn,
            },
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(getThemes)
        sql_db.connections.allow_default_port_from(getThemes)
        sql_db.secret.grant_read(getThemes)
        nr_secret.grant_read(getThemes)

        addTheme = lambda_.Function(
            self,
            "addTheme",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_theme.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer],
            security_groups=sql_db.connections.security_groups,
            environment={
                "DB_CLUSTER_ENDPOINT": sql_db.cluster_endpoint.hostname,
                "DB_SECRET_ARN": sql_db.secret.secret_arn,
            },
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(25),
        )
        sql_db.grant_data_api_access(addTheme)
        sql_db.connections.allow_default_port_from(addTheme)
        sql_db.secret.grant_read(addTheme)
        nr_secret.grant_read(addTheme)
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            security_group.add_ingress_rule(
                addTheme.connections.security_groups[0], ec2.Port.tcp(5432)
            )
            security_group.add_ingress_rule(
                getThemes.connections.security_groups[0], ec2.Port.tcp(5432)
            )

        getNavlogs = lambda_.Function(
            self,
            "getNavlogs",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="get_navlogs.lambda_handler",
            environment={"DDB_TABLE": ddb.table_name},
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(15),
        )
        ddb.grant_read_data(getNavlogs)

        addNavlog = lambda_.Function(
            self,
            "addNavLog",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_navlog.lambda_handler",
            environment={"DDB_TABLE": ddb.table_name},
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(5),
        )
        ddb.grant_read_write_data(addNavlog)

        log_group = logs.LogGroup(self, "ApiGatewayAccessLogs")
        apiGateway = apigateway.RestApi(
            self,
            "ApiGateway",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_credentials=True,
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "PUT", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "Content-Length",
                    "X-Requested-With",
                ],
            ),
            deploy_options=apigateway.StageOptions(
                access_log_destination=apigateway.LogGroupLogDestination(log_group),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
        )
        nr_logger = lambda_.Function.from_function_arn(
            self,
            "NRLogger",
            "arn:aws:lambda:eu-west-1:559845934392:function:newrelic-log-ingestion-06a0f5fff877",
        )
        logs.SubscriptionFilter(
            self,
            "ApiGatewayAccessLogsSubscription",
            log_group=log_group,
            destination=destinations.LambdaDestination(nr_logger),
            filter_pattern=logs.FilterPattern.any_term(
                "Method=OPTIONS", "Method=GET", "Method=PUT", "Method=POST"
            ),
        )

        api = apiGateway.root.add_resource("api")
        todos = api.add_resource(
            "navlogs",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_credentials=True,
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "Content-Length",
                    "X-Requested-With",
                ],
            ),
        )
        todos.add_method("GET", apigateway.LambdaIntegration(getNavlogs))
        todos.add_method("POST", apigateway.LambdaIntegration(addNavlog))

        todos = api.add_resource(
            "themes",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_credentials=True,
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "Content-Length",
                    "X-Requested-With",
                ],
            ),
        )
        todos.add_method("GET", apigateway.LambdaIntegration(getThemes))
        todos.add_method("POST", apigateway.LambdaIntegration(addTheme))

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=apiGateway.url)

        CfnOutput(self, ApiGatewayDomainStackOutput, value=apiGateway.url.split("/")[2])

        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=apiGateway.deployment_stage.stage_name,
        )
