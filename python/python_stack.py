import json
from os import path
import os
from aws_cdk import Stack, CfnOutput, Duration, TimeZone
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_applicationautoscaling as appscaling
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
from python_dependencies_stack import PythonDependenciesStack

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
        python_dependencies_stack: PythonDependenciesStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.python_dependencies_stack = python_dependencies_stack

        # Create the VPC with both public and private subnets
        self.vpc = ec2.Vpc(
            self,
            "AuroraVpc1",
            max_azs=2,  # Maximum Availability Zones
            nat_gateways=0,  # Disable NAT gateways
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=18,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=18,
                ),
            ],
        )

        # Create a VPC endpoint for S3
        s3_endpoint = ec2.GatewayVpcEndpoint(
            self,
            "S3VpcEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )
        dynamodb_endpoint = ec2.GatewayVpcEndpoint(
            self,
            "DynamoDBVpcEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )

        # Create a NAT instance using Amazon Linux 2
        nat_instance = ec2.Instance(
            self,
            "NatInstance",
            instance_type=ec2.InstanceType(
                "t3.micro"
            ),  # Choose an appropriate instance type
            machine_image=ec2.MachineImage.latest_amazon_linux2(),  # Use Amazon Linux 2 AMI
            source_dest_check=False,
            vpc=self.vpc,
            vpc_subnets={
                "subnet_type": ec2.SubnetType.PUBLIC
            },  # Place in a public subnet
            key_name="nat_instances",  # Specify your key pair for SSH access
            user_data=ec2.UserData.custom(
                """#!/bin/bash
                # Update the system
                yum update -y

                # Enable IP forwarding
                echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
                sysctl -p

                # Install iptables if not already installed
                yum install -y iptables

                # Set up iptables rules for NAT
                iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
                iptables -F FORWARD
                # Save iptables rules to persist across reboots
                service iptables save

                # Optionally, restart the iptables service
                service iptables restart
                """
            ),
        )

        # Allow the NAT instance to access the internet
        nat_instance.add_security_group(
            ec2.SecurityGroup(
                self,
                "NatInstanceSG",
                vpc=self.vpc,
                allow_all_outbound=True,
            )
        )

        # Update route tables to use the NAT instance
        for subnet in self.vpc.private_subnets:
            subnet.add_route(
                "NatRoute",
                router_id=nat_instance.instance_id,
                router_type=ec2.RouterType.INSTANCE,
                destination_cidr_block="0.0.0.0/0",
            )

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
        self.archive_bucket, self.archive_navlog = (
            self.create_archive_related_resources(self.reqs_layers[2], self.ddb)
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
                {**lambda_function_props, "timeout": Duration.seconds(240)},
            ),
            "build_themes": self.create_lambda_function(
                "build_themes",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                {**lambda_function_props, "timeout": Duration.seconds(120)},
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
            "process_theme": self.create_lambda_function(
                "process_theme",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                {**lambda_function_props, "timeout": Duration.minutes(5)},
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
            "search": self.create_lambda_function(
                "search",
                self.sql_db,
                self.openai_secret,
                self.langfuse_secret,
                lambda_function_props,
            ),
            "add_navlog": self.create_add_navlog_function(
                self.lambdas_env, self.ddb, self.bucket, self.vpc, self.reqs_layers[2]
            ),
        }
        self.ddb.grant_read_write_data(self.functions["build_articles"])
        functions_to_dd_instrument = list(self.functions.values())
        functions_to_dd_instrument.append(self.archive_navlog)
        self.instrument_with_datadog(functions_to_dd_instrument)
        self.modify_security_group_for_lambda_access(
            list(self.functions.values()), self.sql_db
        )

        self.create_scheduled_event_for_function(
            "build_articles", self.functions["build_articles"], "27"
        )
        self.create_scheduled_event_for_function(
            "build_themes", self.functions["build_themes"], "47"
        )

        # Create the EventBus
        self.event_bus = events.EventBus(
            self,
            "DassieAsyncEvents",
            event_bus_name="dassie-async-events",
        )

        # Grant permission to add_theme function to put events to the EventBus
        self.event_bus.grant_put_events_to(self.functions["add_theme"])

        self.add_theme_completion_rule = events.Rule(
            self,
            "AddThemeCompletionRule",
            event_bus=self.event_bus,
            event_pattern=events.EventPattern(
                source=["dassie.lambda"],
                detail_type=["Lambda Function Invocation Result"],
                detail={
                    "requestContext": {
                        "functionName": [self.functions["add_theme"].function_name]
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

        if construct_id != "LocalStack":
            self.functions["get_themes"] = self.create_auto_scaling_for_lambda(
                self.functions["get_themes"]
            )
            self.functions["search"] = self.create_auto_scaling_for_lambda(
                self.functions["search"]
            )
            self.functions["add_theme"] = self.create_auto_scaling_for_lambda(
                self.functions["add_theme"]
            )

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
            enable_profiling=True,
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

    def create_archive_related_resources(self, deps_layer, ddb):
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
        archive_function = lambda_.Function(
            self,
            "ArchiveFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="archive_navlog.lambda_handler",
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            architecture=lambda_.Architecture.ARM_64,
            environment={
                "BUCKET_NAME": archive_bucket.bucket_name,
            },
            layers=[deps_layer],
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

        return archive_bucket, archive_function

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
        postgres_layer = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayer",
            layer_version_arn=self.python_dependencies_stack.layer_arn,
        )
        ai_layer = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayerExtended",
            layer_version_arn=self.python_dependencies_stack.layer_arn_1,
        )
        utils_layer = lambda_python.PythonLayerVersion.from_layer_version_arn(
            self,
            "RequirementsLayerExtended1",
            layer_version_arn=self.python_dependencies_stack.layer_arn_2,
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
            "DD_ENV": "prod",
            "DD_SERVICE": "dassie-app-backend",
            "DD_VERSION": "1.0.0",
        }
        return bucket, [postgres_layer, ai_layer, utils_layer], lambdas_env

    def modify_security_group_for_lambda_access(
        self, functions, sql_db: rds.DatabaseCluster
    ):
        # Modify the security group of the Aurora Serverless cluster to allow inbound connections from the Lambda function
        for security_group in sql_db.connections.security_groups:
            for function in functions:
                security_group.add_ingress_rule(
                    function.connections.security_groups[0], ec2.Port.tcp(5432)
                )

    def create_add_navlog_function(self, lambdas_env, ddb, bucket, vpc, layer):
        addNavlog = lambda_.Function(
            self,
            "add_navlog",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.AssetCode.from_asset(path.join(os.getcwd(), "python/lambda")),
            handler="add_navlog.lambda_handler",
            tracing=lambda_.Tracing.PASS_THROUGH,
            timeout=Duration.seconds(10),
            layers=[layer],
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

    def create_auto_scaling_for_lambda(self, lambda_function: lambda_.Function):
        alias = lambda_function.add_alias("provisioned")
        auto_scaling_target = alias.add_auto_scaling(min_capacity=1, max_capacity=3)
        auto_scaling_target.scale_on_utilization(utilization_target=0.5)
        auto_scaling_target.scale_on_schedule(
            "scale-up-in-the-morning",
            schedule=appscaling.Schedule.cron(
                minute="0",
                hour="8",
                day="*",
                month="*",
                year="*",
            ),
            time_zone=TimeZone.EUROPE_DUBLIN,
            min_capacity=1,
            max_capacity=3,
        )
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
        return alias

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

        search = api.add_resource(
            "search",
            default_cors_preflight_options=cors,
        )
        search.add_method(
            "GET",
            apigateway.LambdaIntegration(functions["search"]),
            authorization_type=apigateway.AuthorizationType.IAM,
        )
        search_sub = search.add_resource("{query}")
        search_sub.add_method(
            "GET",
            apigateway.LambdaIntegration(functions["search"]),
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

    def create_scheduled_event_for_function(self, name, function, minute):
        rule = events.Rule(
            self,
            name + "ScheduleRule",
            schedule=events.Schedule.cron(
                minute=minute, hour="8-21", month="*", day="*", year="*"
            ),
        )

        # Add the Lambda function as a target for this rule
        rule.add_target(targets.LambdaFunction(function))
