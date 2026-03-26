from typing import TypedDict, List
import pulumi
import pulumi_aws as aws


class RouteConfig(TypedDict):
    method: str
    path: str
    lambda_fn: aws.lambda_.Function


def make_api(name: str, environment: str, routes: List[RouteConfig]) -> aws.apigatewayv2.Api:
    api = aws.apigatewayv2.Api(
        name,
        protocol_type="HTTP",
        cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["content-type"],
            max_age=3000,
        ),
    )

    log_group =aws.cloudwatch.LogGroup(f"{name}-api-logs")

    aws.apigatewayv2.Stage(
        f"{name}-dev",
        api_id=api.id,
        name="dev",
        auto_deploy=True,
        default_route_settings=aws.apigatewayv2.StageDefaultRouteSettingsArgs(
            throttling_burst_limit=50,
            throttling_rate_limit=25,
        ),
        access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
            destination_arn=log_group.arn,
            format='{"requestId":"$context.requestId","status":"$context.status"}'
        ),
        opts=pulumi.ResourceOptions(depends_on=[apigw_account])
    )

    aws.apigatewayv2.Stage(
        f"{name}-prod",
        api_id=api.id,
        name="prod",
        auto_deploy=True,
        default_route_settings=aws.apigatewayv2.StageDefaultRouteSettingsArgs(
            throttling_burst_limit=20,
            throttling_rate_limit=10,
        ),
        access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
            destination_arn=log_group.arn,
            format='{"requestId":"$context.requestId","status":"$context.status"}'
        ),
        opts=pulumi.ResourceOptions(depends_on=[apigw_account])
    )

    for route in routes:
        method = route["method"]
        path = route["path"]
        lambda_fn = route["lambda_fn"]

        safe_path = path.replace("/", "-").replace("{", "").replace("}", "").strip("-")
        base_name = f"{name}-{method.lower()}-{safe_path}"

        integration = aws.apigatewayv2.Integration(
            f"{base_name}-integration",
            api_id=api.id,
            integration_type="AWS_PROXY",
            integration_uri=lambda_fn.invoke_arn,
            payload_format_version="2.0",
        )

        aws.apigatewayv2.Route(
            f"{base_name}-route",
            api_id=api.id,
            route_key=f"{method} {path}",
            target=integration.id.apply(lambda id: f"integrations/{id}"),
        )

        aws.lambda_.Permission(
            f"{base_name}-permission",
            action="lambda:InvokeFunction",
            function=lambda_fn.name,
            principal="apigateway.amazonaws.com",
            source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
        )

    pulumi.export(f"{name}_url", api.api_endpoint)

    

    return api


api_gw_logs_role = aws.iam.Role(
    "apigw-cloudwatch-role",
    assume_role_policy="""
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "apigateway.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }
    """
)

aws.iam.RolePolicyAttachment(
    "apigw-logs-attach",
    role=api_gw_logs_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
)

apigw_account = aws.apigateway.Account(
    "apigw-account",
    cloudwatch_role_arn=api_gw_logs_role.arn,
)