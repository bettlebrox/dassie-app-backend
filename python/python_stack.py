import json
from os import path
import os
import subprocess
from aws_cdk import Stack, CfnOutput, Duration, TimeZone
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_applicationautoscaling as appscaling
import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_rds as rds
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_logs as logs

import aws_cdk.aws_iam as iam
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
from infra_stack import InfraStack
from python_dependencies_stack import PythonDependenciesStack

ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"


class PythonStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        dependencies_stack: PythonDependenciesStack,
        infra_stack: InfraStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        (
            self.bucket,
            self.lambdas_env,
        ) = self.create_common_lambda_dependencies(
            infra_stack.sql_db,
            "https://dassie.cluster-c9w86oa4s60z.eu-west-1.neptune.amazonaws.com:8182",
            dependencies_stack.openai_secret,
            dependencies_stack.langfuse_secret,
            dependencies_stack.datadog_secret,
            infra_stack.ddb,
        )
        lambda_function_props = self._get_default_lambda_props(
            infra_stack.lambda_db_access_sg,
            infra_stack.lambda_neptune_access_sg,
            self.lambdas_env,
            infra_stack.vpc,
        )
        self.aliases = {}
        self.functions = self._get_lambdas(
            lambda_function_props,
            infra_stack.ddb,
            self.bucket,
            infra_stack.vpc,
            self.lambdas_env,
        )

        self.archive_navlog = self.create_archive_function(
            infra_stack.ddb, self.lambdas_env
        )

        self.create_scheduled_event_for_function("build_articles", self.functions, "27")
        self.create_scheduled_event_for_function("build_themes", self.functions, "47")

        self._connect_add_theme_event_bus(self.functions)

        # Hack to deal with lack of support for aliases on sam local start-api
        if construct_id != "LocalStack":
            self._create_auto_scaling_for_lambda(
                "get_themes", self.aliases, self.functions
            )
            self._create_auto_scaling_for_lambda("search", self.aliases, self.functions)
            self._create_auto_scaling_for_lambda(
                "add_theme", self.aliases, self.functions
            )

        self.apiGateway = self.create_api_gateway_resources(
            self.functions, self.aliases
        )

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=self.apiGateway.url)
        CfnOutput(
            self, ApiGatewayDomainStackOutput, value=self.apiGateway.url.split("/")[2]
        )
        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=self.apiGateway.deployment_stage.stage_name,
        )

    def _connect_add_theme_event_bus(self, functions):
        # Create the EventBus
        event_bus = events.EventBus(
            self,
            "DassieAsyncEvents",
            event_bus_name="dassie-async-events",
        )
        # Grant permission to add_theme function to put events to the EventBus
        event_bus.grant_put_events_to(functions["add_theme"])
        event_bus.grant_put_events_to(functions["process_theme"])
        events.Rule(
            self,
            "AddThemeCompletionRule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["dassie.lambda"],
                detail_type=["Lambda Function Invocation Result"],
                detail={
                    "requestContext": {
                        "functionName": [functions["add_theme"].function_name]
                    },
                    "responsePayload": {"statusCode": [202]},
                },
            ),
            targets=[
                targets.LambdaFunction(
                    self.functions["process_theme"],
                    event=events.RuleTargetInput.from_event_path(
                        "$.detail.responsePayload"
                    ),
                )
            ],
        )

        events.Rule(
            self,
            "AddThemeGraphCompletionRule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["dassie.lambda"],
                detail_type=["Lambda Function Invocation Result"],
                detail={
                    "requestContext": {
                        "functionName": [functions["process_theme"].function_name]
                    },
                    "responsePayload": {"statusCode": [200]},
                },
            ),
            targets=[
                targets.LambdaFunction(
                    self.functions["process_theme_graph"],
                    event=events.RuleTargetInput.from_event_path(
                        "$.detail.responsePayload"
                    ),
                )
            ],
        )

    def _get_lambdas(
        self,
        lambda_function_props,
        ddb,
        bucket,
        vpc,
        lambdas_env,
    ):
        return {
            "build_articles": self.create_lambda_function(
                "build_articles",
                {**lambda_function_props, "timeout": Duration.minutes(5)},
            ),
            "build_themes": self.create_lambda_function(
                "build_themes",
                {**lambda_function_props, "timeout": Duration.seconds(120)},
            ),
            "get_themes": self.create_lambda_function(
                "get_themes",
                lambda_function_props,
            ),
            "get_theme_graph": self.create_lambda_function(
                "get_theme_graph",
                lambda_function_props,
            ),
            "get_articles": self.create_lambda_function(
                "get_articles",
                lambda_function_props,
            ),
            "add_theme": self.create_lambda_function(
                "add_theme",
                lambda_function_props,
            ),
            "process_theme": self.create_lambda_function(
                "process_theme",
                {**lambda_function_props, "timeout": Duration.minutes(5)},
            ),
            "process_theme_graph": self.create_lambda_function(
                "process_theme_graph",
                {**lambda_function_props, "timeout": Duration.minutes(15)},
            ),
            "del_theme": self.create_lambda_function(
                "del_theme",
                lambda_function_props,
            ),
            "del_related": self.create_lambda_function(
                "del_related",
                lambda_function_props,
            ),
            "search": self.create_lambda_function(
                "search",
                lambda_function_props,
            ),
            "add_navlog": self.create_add_navlog_function(
                lambdas_env,
                ddb,
                bucket,
                vpc,
            ),
        }

    def create_lambda_function(
        self,
        function_name,
        lambda_function_props,
    ):
        lambda_function_props["environment"][
            "DD_LAMBDA_HANDLER"
        ] = f"{function_name.lower()}.lambda_handler"
        lambda_function = lambda_.DockerImageFunction(
            self,
            function_name,
            code=lambda_.DockerImageCode.from_image_asset(
                path.join(os.getcwd(), "python"),
                cmd=["datadog_lambda.handler.handler"],
            ),
            **lambda_function_props,
        )
        return lambda_function

    def _get_default_lambda_props(
        self,
        lambda_db_access_sg,
        lambda_neptune_access_sg,
        lambdas_env,
        vpc,
    ):
        return {
            "vpc": vpc,
            "security_groups": [lambda_db_access_sg, lambda_neptune_access_sg],
            "architecture": lambda_.Architecture.X86_64,
            "memory_size": 1024,
            "environment": lambdas_env,
            "tracing": lambda_.Tracing.PASS_THROUGH,
            "timeout": Duration.seconds(45),
        }

    def create_common_lambda_dependencies(
        self,
        sql_db,
        neptune_endpoint,
        openai_secret,
        langfuse_secret,
        datadog_secret,
        ddb,
    ):
        bucket = s3.Bucket(
            self,
            "navlog-images",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        lambdas_env = {
            "DB_CLUSTER_ENDPOINT": sql_db.cluster_endpoint.hostname,
            "NEPTUNE_ENDPOINT": neptune_endpoint,
            "DB_SECRET_ARN": sql_db.secret.secret_arn,
            "OPENAIKEY_SECRET_ARN": openai_secret.secret_arn,
            "LANGFUSE_SECRET_ARN": langfuse_secret.secret_arn,
            "DD_API_KEY_SECRET_ARN": datadog_secret.secret_arn,
            "DDB_TABLE": ddb.table_name,
            "BUCKET_NAME": bucket.bucket_name,
            "DD_SERVERLESS_LOGS_ENABLED": "true",
            "DD_TRACE_ENABLED": "true",
            "DD_LOCAL_TEST": "false",
            "DD_ENV": "prod",
            "DD_VERSION": f"1.0.{subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode('ascii').strip()}",
            "DD_LOG_LEVEL": "ERROR",
            "DSP_CACHEDIR": "/tmp",
            "DSPY_CACHEDIR": "/tmp",
            "JOBLIB_MULTIPROCESSING": "0",
            "DD_SITE": "datadoghq.eu",
            "DD_SERVICE": "dassie-app-backend",
            "DD_GIT_COMMIT_SHA": subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip(),
            "DD_GIT_REPOSITORY_URL": "github.com/bettlebrox/dassie-app-backend.git",
        }
        return (
            bucket,
            lambdas_env,
        )

    def create_postgres_database(self, vpc, bastion, snapshot_id=None):
        common_params = {
            "engine": rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            "serverless_v2_max_capacity": 16,
            "serverless_v2_min_capacity": 0.5,
            "vpc": vpc,
            "writer": rds.ClusterInstance.serverless_v2(
                "writer", enable_performance_insights=True
            ),
            "storage_encrypted": True,
            "monitoring_interval": Duration.seconds(60),
            "monitoring_role": iam.Role.from_role_arn(
                self,
                "monitoring-role",
                "arn:aws:iam::559845934392:role/emaccess",
            ),
            "cloudwatch_logs_exports": ["postgresql"],
        }

        if snapshot_id is not None:
            sql_db = rds.DatabaseClusterFromSnapshot(
                self, "dassie1", snapshot_identifier=snapshot_id, **common_params
            )
        else:
            sql_db = rds.DatabaseCluster(self, "dassie1", **common_params)
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
            time_to_live_attribute="ttl",
            stream=dynamodb.StreamViewType.OLD_IMAGE,  # Enable DynamoDB Streams
        )
        ddb.add_global_secondary_index(
            partition_key=dynamodb.Attribute(
                name="type", type=dynamodb.AttributeType.STRING
            ),
            index_name="type-index",
        )
        return ddb

    def create_archive_function(self, ddb, lambdas_env):
        # Create an S3 bucket for archiving old DynamoDB items
        archive_bucket = s3.Bucket(
            self,
            "ArchiveBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(365),
                        )
                    ]
                )
            ],
        )

        # Create a Lambda function to archive deleted items
        lambdas_env["BUCKET_NAME"] = archive_bucket.bucket_name
        lambdas_env["DD_LAMBDA_HANDLER"] = "archive_navlog.lambda_handler"
        archive_function = lambda_.DockerImageFunction(
            self,
            "ArchiveFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                path.join(os.getcwd(), "python"),
                cmd=["datadog_lambda.handler.handler"],
            ),
            environment=lambdas_env,
            timeout=Duration.minutes(1),
        )

        # Grant the Lambda function read permissions to DynamoDB Stream and write permissions to S3
        ddb.grant_stream_read(archive_function)
        archive_bucket.grant_write(archive_function)

        # Create an event source mapping to trigger the Lambda function from the DynamoDB stream
        lambda_.EventSourceMapping(
            self,
            "ArchiveFunctionEventSourceMapping",
            target=archive_function,
            event_source_arn=ddb.table_stream_arn,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=100,
            max_batching_window=Duration.minutes(5),
        )

        return archive_function

    def modify_security_group_for_lambda_access(
        self, functions, sql_db: rds.DatabaseCluster
    ):
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            for function in functions:
                security_group.add_ingress_rule(
                    function.connections.security_groups[0], ec2.Port.tcp(5432)
                )

    def create_add_navlog_function(self, lambdas_env, ddb, bucket, vpc):
        lambdas_env["DD_LAMBDA_HANDLER"] = "add_navlog.lambda_handler"
        addNavlog = lambda_.DockerImageFunction(
            self,
            "add_navlog",
            code=lambda_.DockerImageCode.from_image_asset(
                path.join(os.getcwd(), "python"),
                cmd=["datadog_lambda.handler.handler"],
            ),
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(10),
            vpc=vpc,
            environment=lambdas_env,
        )
        ddb.grant_read_write_data(addNavlog)
        bucket.grant_read_write(addNavlog)
        return addNavlog

    def _create_auto_scaling_for_lambda(self, name, aliases, functions):
        aliases[name] = functions[name].add_alias("provisioned")
        auto_scaling_target = aliases[name].add_auto_scaling(
            min_capacity=1, max_capacity=3
        )
        auto_scaling_target.scale_on_utilization(utilization_target=0.5)
        # auto_scaling_target.scale_on_schedule(
        #     "scale-up-in-the-morning",
        #     schedule=appscaling.Schedule.cron(
        #         minute="0",
        #         hour="8",
        #         day="*",
        #         month="*",
        #         year="*",
        #     ),
        #     time_zone=TimeZone.EUROPE_DUBLIN,
        #     min_capacity=1,
        #     max_capacity=3,
        # )
        auto_scaling_target.scale_on_schedule(
            "scale-down-in-the-evening",
            schedule=appscaling.Schedule.cron(
                minute="0",
                hour="20",
                day="*",
                month="*",
                year="*",
            ),
            time_zone=TimeZone.EUROPE_DUBLIN,
            min_capacity=0,
            max_capacity=0,
        )
        return aliases[name]

    def create_api_gateway_dependencies(self):
        log_group = logs.LogGroup(self, "ApiGatewayAccessLogs")
        api_role = iam.Role.from_role_arn(
            self,
            "frontend_role",
            role_arn="arn:aws:iam::559845934392:role/amplify-d1tgde1goqkt1z-ma-amplifyAuthauthenticatedU-y3rmjhCgkLMl",
        )
        api_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="allow_google_cognito",
                    effect=iam.Effect.ALLOW,
                    actions=["execute-api:Invoke"],
                    resources=[
                        f"arn:aws:execute-api:eu-west-1:559845934392:2eh5dqfti6/prod/*/*/*"  # apiID needs to be manually updated if API recreated
                    ],
                    conditions={"ArnLike": {"AWS:SourceArn": api_role.role_arn}},
                    principals=[iam.ServicePrincipal("apigateway.amazonaws.com")],
                ),
                iam.PolicyStatement(
                    sid="allow_unauthenticated_options",
                    effect=iam.Effect.ALLOW,
                    actions=["execute-api:Invoke"],
                    resources=[
                        f"arn:aws:execute-api:eu-west-1:559845934392:2eh5dqfti6/prod/OPTIONS/*"  # apiID needs to be manually updated if API recreated
                    ],
                    principals=[iam.AnyPrincipal()],
                ),
            ]
        )

        cors = apigateway.CorsOptions(
            allow_origins=apigateway.Cors.ALL_ORIGINS,
            allow_methods=apigateway.Cors.ALL_METHODS,
        )
        return log_group, api_policy, cors

    def _get_alias_or_function(self, aliases, functions, function_name):
        return (
            aliases[function_name]
            if function_name in aliases
            else functions[function_name]
        )

    def create_api_gateway_resources(self, functions, aliases):
        log_group, api_policy, cors = self.create_api_gateway_dependencies()
        apiGateway = apigateway.RestApi(
            self,
            "ApiGateway",
            policy=api_policy,
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
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "add_navlog")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        articles = api.add_resource(
            "articles",
            default_cors_preflight_options=cors,
        )
        articles.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "get_articles")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        search = api.add_resource(
            "search",
            default_cors_preflight_options=cors,
        )
        search.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "search")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        search_sub = search.add_resource("{query}")
        search_sub.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "search")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes = api.add_resource("themes", default_cors_preflight_options=cors)
        themes.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "get_themes")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "add_theme")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        themes_sub = themes.add_resource("{title}")
        themes_sub.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "get_themes")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes_sub.add_method(
            "DELETE",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "del_theme")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        theme_sub_graph = themes_sub.add_resource(
            "graph", default_cors_preflight_options=cors
        )
        theme_sub_graph.add_method(
            "GET",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "get_theme_graph")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        themes_sub_related = themes_sub.add_resource(
            "related", default_cors_preflight_options=cors
        )
        themes_sub_related_by_id = themes_sub_related.add_resource("{article_id}")
        themes_sub_related_by_id.add_method(
            "DELETE",
            apigateway.LambdaIntegration(
                self._get_alias_or_function(aliases, functions, "del_related")
            ),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        return apiGateway

    def create_scheduled_event_for_function(self, name, functions, minute):
        rule = events.Rule(
            self,
            name + "ScheduleRule",
            schedule=events.Schedule.cron(
                minute=minute, hour="8-21", month="*", day="*", year="*"
            ),
        )

        # Add the Lambda function as a target for this rule
        rule.add_target(targets.LambdaFunction(functions[name]))
