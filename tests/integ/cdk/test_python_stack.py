import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest
from python_stack import PythonStack
from infra_stack import InfraStack
from python_dependencies_stack import PythonDependenciesStack
import json


@pytest.fixture
def app():
    return core.App()


@pytest.fixture
def python_dependencies_stack(app):
    stack = PythonDependenciesStack(app, "python-dependencies", testing=True)
    # simulate the hack to 'sam local start-api' hack
    stack.reqs_layer_arn = (
        "arn:aws:lambda:eu-west-1:559845934392:layer:RequirementsLayer21B3280B:45"
    )
    stack.ai_layer_arn = "arn:aws:lambda:eu-west-1:559845934392:layer:AILayerD278B124:1"
    stack.more_ai_layer_arn = (
        "arn:aws:lambda:eu-west-1:559845934392:layer:MoreAILayer75E81DE2:2"
    )
    return stack


@pytest.fixture
def dependencies_template(python_dependencies_stack):
    return assertions.Template.from_stack(python_dependencies_stack)


@pytest.fixture
def infra_stack(app):
    return InfraStack(app, "infra")


@pytest.fixture
def infra_template(infra_stack):
    return assertions.Template.from_stack(infra_stack)


@pytest.fixture
def backend_stack(app, python_dependencies_stack, infra_stack) -> PythonStack:
    return PythonStack(
        app,
        "python",
        dependencies_stack=python_dependencies_stack,
        infra_stack=infra_stack,
    )


@pytest.fixture
def backend_template(backend_stack) -> assertions.Template:
    return assertions.Template.from_stack(backend_stack)


def test_vpc_created(infra_template):
    infra_template.resource_count_is("AWS::EC2::VPC", 1)


def test_rds_instance_created(infra_template):
    infra_template.resource_count_is("AWS::RDS::DBCluster", 1)


def test_infra_resources_created(infra_template):
    infra_template.resource_count_is("AWS::DynamoDB::Table", 1)


# assertions library doesn't support this yet
# def test_secrets_created(dependencies_template):
#     dependencies_template.resource_count_is("AWS::SecretsManager::Secret", 1)


def test_s3_bucket_created(backend_template):
    backend_template.resource_count_is("AWS::S3::Bucket", 2)


def test_api_gateway_methods(backend_template):
    backend_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "ResourceId": {"Ref": assertions.Match.any_value()},
            "RestApiId": {"Ref": assertions.Match.any_value()},
            "AuthorizationType": "AWS_IAM",
        },
    )

    backend_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "POST",
            "ResourceId": {"Ref": assertions.Match.any_value()},
            "RestApiId": {"Ref": assertions.Match.any_value()},
            "AuthorizationType": "AWS_IAM",
        },
    )


def test_lambda_environment_variables(backend_template):
    backend_template.has_resource_properties(
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


def test_scheduled_event_created(backend_template):
    backend_template.resource_count_is("AWS::Events::Rule", 3)
    backend_template.has_resource_properties(
        "AWS::Events::Rule", {"ScheduleExpression": "cron(27 8-21 * * ? *)"}
    )


def test_resources_created(backend_template):
    backend_template.resource_count_is("AWS::Lambda::Function", 11)

    backend_template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_build_articles_has_ddb_read_permission(backend_template, snapshot):
    rest_api_resources = backend_template.find_resources("AWS::ApiGateway::RestApi")
    assert len(rest_api_resources) == 1
    first_resource = next(iter(rest_api_resources.values()))
    snapshot.assert_match(
        json.dumps(first_resource["Properties"], indent=2), "rest_api_properties.json"
    )
