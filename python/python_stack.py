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

ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"

PythonLayerStackOutput = "PythonLayerStackARN"
PythonLayerStackOutput1 = "PythonLayerStackARN1"
PythonLayerStackOutput2 = "PythonLayerStackARN2"


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


class PythonStack(Stack):

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

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        bucket = s3.Bucket(
            self,
            "navlog-images",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        vpc = ec2.Vpc(self, "AuroraVpc1")
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
        bastion = ec2.SecurityGroup.from_security_group_id(
            self,
            "bastion",
            security_group_id="sg-0669c97cc65247ecd",
        )
        sql_db.connections.allow_default_port_from(bastion)
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
        build_articles = lambda_.Function(
            self,
            "buildArticles",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="build_articles.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(build_articles)
        sql_db.connections.allow_default_port_from(build_articles)
        sql_db.secret.grant_read(build_articles)

        getThemes = lambda_.Function(
            self,
            "getThemes",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="get_themes.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(getThemes)
        sql_db.connections.allow_default_port_from(getThemes)
        sql_db.secret.grant_read(getThemes)

        getArticles = lambda_.Function(
            self,
            "getArticles",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="get_articles.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(getArticles)
        sql_db.connections.allow_default_port_from(getArticles)
        sql_db.secret.grant_read(getArticles)
        openai_secret.grant_read(getArticles)
        langfuse_secret.grant_read(getArticles)

        addTheme = lambda_.Function(
            self,
            "addTheme",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_theme.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(addTheme)
        sql_db.connections.allow_default_port_from(addTheme)
        sql_db.secret.grant_read(addTheme)
        openai_secret.grant_read(addTheme)
        langfuse_secret.grant_read(addTheme)

        delTheme = lambda_.Function(
            self,
            "delTheme",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="del_theme.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(delTheme)
        sql_db.connections.allow_default_port_from(delTheme)
        sql_db.secret.grant_read(delTheme)

        delRelated = lambda_.Function(
            self,
            "delRelated",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="del_related.lambda_handler",
            vpc=vpc,
            layers=[reqs_layer, reqs_layer_1, reqs_layer_2],
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            security_groups=sql_db.connections.security_groups,
            environment=lambdas_env,
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(45),
        )
        sql_db.grant_data_api_access(delRelated)
        sql_db.connections.allow_default_port_from(delRelated)
        sql_db.secret.grant_read(delRelated)
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
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(5),
            environment=lambdas_env,
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
            allow_origins=[
                "http://localhost:5174",
                "https://main.d1tgde1goqkt1z.amplifyapp.com",
            ],
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
        self.instrument_with_datadog(
            [
                build_articles,
                getThemes,
                getArticles,
                addTheme,
                delTheme,
                delRelated,
                addNavlog,
            ],
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

        themes_sub_related = themes_sub.add_resource(
            "related", default_cors_preflight_options=cors
        )
        themes_sub_related_by_id = themes_sub_related.add_resource("{article_id}")
        themes_sub_related_by_id.add_method(
            "DELETE",
            apigateway.LambdaIntegration(delRelated),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=apiGateway.url)

        CfnOutput(self, ApiGatewayDomainStackOutput, value=apiGateway.url.split("/")[2])

        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=apiGateway.deployment_stage.stage_name,
        )
