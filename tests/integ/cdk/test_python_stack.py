import os
import sys
import aws_cdk as core
import aws_cdk.assertions as assertions

sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python")
)
from python_stack import PythonStack


def test_vpc_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::VPC", 1)


def test_rds_instance_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::RDS::DBCluster", 1)


def test_s3_bucket_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::S3::Bucket", 1)


def test_secrets_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)
    template.resource_count_is(
        "AWS::SecretsManager::Secret", 1
    )  # this is the DB secret


def test_api_gateway_methods():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "ResourceId": {"Ref": assertions.Match.any_value()},
            "RestApiId": {"Ref": assertions.Match.any_value()},
            "AuthorizationType": "AWS_IAM",
        },
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "POST",
            "ResourceId": {"Ref": assertions.Match.any_value()},
            "RestApiId": {"Ref": assertions.Match.any_value()},
            "AuthorizationType": "AWS_IAM",
        },
    )


def test_lambda_environment_variables():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": assertions.Match.object_like(
                    {
                        "DB_SECRET_ARN": assertions.Match.any_value(),
                        "OPENAIKEY_SECRET_ARN": assertions.Match.any_value(),
                        "LANGFUSE_SECRET_ARN": assertions.Match.any_value(),
                    }
                )
            }
        },
    )


def test_scheduled_event_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Events::Rule", 1)
    template.has_resource_properties(
        "AWS::Events::Rule", {"ScheduleExpression": "cron(0 2 ? * * *)"}
    )


def test_resources_created():
    app = core.App()
    stack = PythonStack(app, "python")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Lambda::Function", 7)

    template.resource_count_is("AWS::DynamoDB::Table", 1)

    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
