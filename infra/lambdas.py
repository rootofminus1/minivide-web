import os
import pulumi
import pulumi_aws as aws
from pulumi import FileArchive, AssetArchive, StringAsset
from roles import basic_logs_role
from layers import ffmpeg_layer

LAMBDAS_DIR = os.path.join(os.path.dirname(__file__), "../backend/lambdas")

def make_lambda(name: str, handler_dir: str, role, env_vars: dict) -> aws.lambda_.Function:
    """for regular smaller lambdas"""
    return aws.lambda_.Function(
        name,
        runtime=aws.lambda_.Runtime.PYTHON3D14,
        role=role.arn,
        handler="handler.lambda_handler",
        code=AssetArchive({
            ".": FileArchive(os.path.join(LAMBDAS_DIR, handler_dir))
        }),
        timeout=3,
        environment=aws.lambda_.FunctionEnvironmentArgs(variables=env_vars),
    )

def make_worker_lambda(name: str, handler_dir: str, role: aws.iam.Role, env_vars: dict) -> aws.lambda_.Function:
    """for the bigger worker lambdas"""
    return aws.lambda_.Function(
        name,
        runtime=aws.lambda_.Runtime.PYTHON3D14,
        role=role.arn,
        handler="handler.lambda_handler",
        code=AssetArchive({
            ".": FileArchive(os.path.join(LAMBDAS_DIR, handler_dir))
        }),
        timeout=300,
        memory_size=2048,
        ephemeral_storage=aws.lambda_.FunctionEphemeralStorageArgs(size=512),
        environment=aws.lambda_.FunctionEnvironmentArgs(variables=env_vars),
        layers=[
            ffmpeg_layer.arn
        ]
    )