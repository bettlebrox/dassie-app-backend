import os
import sys
import aws_cdk as core
import aws_cdk.assertions as assertions
from unittest.mock import MagicMock
import pytest

sys.path.append(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../python")
)
from python_stack import PythonStack


@pytest.fixture
def python_dependencies_stack():
    mock_stack = MagicMock()
    mock_stack.layer_arn = "layer_arn"
    mock_stack.layer_arn_1 = "layer_arn_1"
    mock_stack.layer_arn_2 = "layer_arn_2"
    return mock_stack


def test_vpc_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::VPC", 1)


def test_rds_instance_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::RDS::DBCluster", 1)


def test_s3_bucket_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::S3::Bucket", 2)


def test_secrets_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)
    template.resource_count_is(
        "AWS::SecretsManager::Secret", 1
    )  # this is the DB secret


def test_api_gateway_methods(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
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


def test_lambda_environment_variables(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
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


def test_scheduled_event_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Events::Rule", 1)
    template.has_resource_properties(
        "AWS::Events::Rule", {"ScheduleExpression": "cron(27 8-21 ? * * *)"}
    )


def test_resources_created(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Lambda::Function", 8)

    template.resource_count_is("AWS::DynamoDB::Table", 1)

    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_build_articles_has_ddb_read_permission(python_dependencies_stack):
    app = core.App()
    stack = PythonStack(
        app, "python", python_dependencies_stack=python_dependencies_stack
    )
    template = assertions.Template.from_stack(stack)

    # with open("template_output.json", "w") as f:
    #    json.dump(template.to_json(), f, indent=2)

    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.any_value(),
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.any_value(),
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.any_value(),
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.any_value(),
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.any_value(),
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                        assertions.Match.object_like(
                            {
                                "Action": [
                                    "dynamodb:BatchGetItem",
                                    "dynamodb:GetRecords",
                                    "dynamodb:GetShardIterator",
                                    "dynamodb:Query",
                                    "dynamodb:GetItem",
                                    "dynamodb:Scan",
                                    "dynamodb:ConditionCheckItem",
                                    "dynamodb:DescribeTable",
                                ],
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        ),
                    ]
                )
            },
            "Roles": assertions.Match.array_with(
                [
                    {
                        "Ref": assertions.Match.string_like_regexp(
                            "buildarticlesServiceRole*"
                        )
                    }
                ]
            ),
        },
    )
