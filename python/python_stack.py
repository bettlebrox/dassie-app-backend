from os import path
import os
from aws_cdk import Stack, CfnOutput, Duration
from constructs import Construct
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_dynamodb as dynamodb

ApiGatewayEndpointStackOutput = "ApiEndpoint"
ApiGatewayDomainStackOutput = "ApiDomain"
ApiGatewayStageStackOutput = "ApiStage"


class PythonStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ddb = dynamodb.Table(
            self,
            "navlogDB",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
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

        CfnOutput(self, ApiGatewayEndpointStackOutput, value=apiGateway.url)

        CfnOutput(self, ApiGatewayDomainStackOutput, value=apiGateway.url.split("/")[2])

        CfnOutput(
            self,
            ApiGatewayStageStackOutput,
            value=apiGateway.deployment_stage.stage_name,
        )
