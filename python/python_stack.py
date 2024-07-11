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
import aws_cdk.aws_logs_destinations as destinations
import aws_cdk.aws_secretsmanager as secretsmanager  # Import the secretsmanager module
import aws_cdk.aws_cognito as cognito
import aws_cdk.aws_iam as iam


ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"


class PythonStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        bucket = s3.Bucket(
            self,
            "navlog-images",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        vpc = ec2.Vpc(self, "AuroraVpc1")
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
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
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
            entry="python/layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
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
            runtime=lambda_.Runtime.PYTHON_3_9,
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

        getArticles = lambda_.Function(
            self,
            "getArticles",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="get_articles.lambda_handler",
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
        sql_db.grant_data_api_access(getArticles)
        sql_db.connections.allow_default_port_from(getArticles)
        sql_db.secret.grant_read(getArticles)
        nr_secret.grant_read(getArticles)

        addTheme = lambda_.Function(
            self,
            "addTheme",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_theme.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer],
            security_groups=sql_db.connections.security_groups,
            environment={
                "DB_CLUSTER_ENDPOINT": sql_db.cluster_endpoint.hostname,
                "DB_SECRET_ARN": sql_db.secret.secret_arn,
                "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
            },
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(addTheme)
        sql_db.connections.allow_default_port_from(addTheme)
        sql_db.secret.grant_read(addTheme)
        nr_secret.grant_read(addTheme)

        delTheme = lambda_.Function(
            self,
            "delTheme",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="del_theme.lambda_handler",
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
        sql_db.grant_data_api_access(delTheme)
        sql_db.connections.allow_default_port_from(delTheme)
        sql_db.secret.grant_read(delTheme)
        nr_secret.grant_read(delTheme)
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            security_group.add_ingress_rule(
                addTheme.connections.security_groups[0], ec2.Port.tcp(5432)
            )
            security_group.add_ingress_rule(
                getThemes.connections.security_groups[0], ec2.Port.tcp(5432)
            )
            security_group.add_ingress_rule(
                getArticles.connections.security_groups[0], ec2.Port.tcp(5432)
            )

        addNavlog = lambda_.Function(
            self,
            "addNavLog",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_navlog.lambda_handler",
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.seconds(5),
            environment={
                "DDB_TABLE": ddb.table_name,
                "BUCKET_NAME": bucket.bucket_name,
            },
        )
        ddb.grant_read_write_data(addNavlog)
        bucket.grant_read_write(addNavlog)

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
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
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
            default_cors_preflight_options=cors,
        )
        todos.add_method(
            "POST",
            apigateway.LambdaIntegration(addNavlog),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        articles = api.add_resource(
            "articles",
            default_cors_preflight_options=cors,
        )
        articles.add_method(
            "GET",
            apigateway.LambdaIntegration(getArticles),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes = api.add_resource(
            "themes",
            default_cors_preflight_options=cors,
        )
        themes.add_method(
            "GET",
            apigateway.LambdaIntegration(getThemes),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes.add_method(
            "POST",
            apigateway.LambdaIntegration(addTheme),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes_sub = themes.add_resource("{title}")
        themes_sub.add_method(
            "GET",
            apigateway.LambdaIntegration(getThemes),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes_sub.add_method(
            "DELETE",
            apigateway.LambdaIntegration(delTheme),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=apiGateway.url)

        CfnOutput(self, ApiGatewayDomainStackOutput, value=apiGateway.url.split("/")[2])

        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=apiGateway.deployment_stage.stage_name,
        )
