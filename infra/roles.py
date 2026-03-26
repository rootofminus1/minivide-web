import pulumi_aws as aws
import json


def lambda_logs_policy(name: str):
    return aws.iam.Policy(
        name,
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": "arn:aws:logs:*:*:*",
            }]
        })
    )

def s3_write_policy(name: str, bucket_arn):
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": f"{arn}/uploads/*",
            }]
        }))
    )

def s3_read_policy(name: str, bucket_arn):
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": f"{arn}/outputs/*",
            }]
        }))
    )

def s3_worker_policy(name: str, bucket_arn):
    """Worker needs to read from uploads/ AND write to outputs/"""
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ReadUploads",
                    "Effect": "Allow",
                    "Action": ["s3:GetObject"],
                    "Resource": f"{arn}/uploads/*",
                },
                {
                    "Sid": "WriteOutputs",
                    "Effect": "Allow",
                    "Action": ["s3:PutObject"],
                    "Resource": f"{arn}/outputs/*",
                },
            ]
        }))
    )

# def s3_write_policy(name: str, bucket_arn):
#     return aws.iam.Policy(
#         name,
#         policy=bucket_arn.apply(lambda arn: json.dumps({
#             "Version": "2012-10-17",
#             "Statement": [{
#                 "Effect": "Allow",
#                 "Action": ["s3:PutObject"],
#                 "Resource": f"{arn}/uploads/*",
#             }]
#         }))
#     )

# def s3_read_policy(name: str, bucket_arn):
#     return aws.iam.Policy(
#         name,
#         policy=bucket_arn.apply(lambda arn: json.dumps({
#             "Version": "2012-10-17",
#             "Statement": [{
#                 "Effect": "Allow",
#                 "Action": "s3:GetObject",
#                 "Resource": f"{arn}/*",
#             }]
#         }))
#     )

def dynamo_put_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:PutItem"],
                "Resource": arn,
            }]
        }))
    )

def dynamo_update_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:UpdateItem", "dynamodb:GetItem"],
                "Resource": arn,
            }]
        }))
    )

def dynamo_get_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:GetItem"],
                "Resource": arn,
            }]
        }))
    )

def dynamo_query_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:Query"],
                "Resource": [arn, f"{arn}/index/*"],
            }]
        }))
    )

def dynamo_query_policy_for_gsi(name: str, table_arn, gsi_name: str):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:Query"],
                "Resource": [
                    arn,
                    f"{arn}/index/{gsi_name}"  # because GSIs ig
                ],
            }]
        }))
    )

def lambda_invoke_policy(name: str, function_arn):
    return aws.iam.Policy(
        name,
        policy=function_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": arn,
            }]
        }))
    )


def lambda_role(name: str):
    return aws.iam.Role(
        name,
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }]
        })
    )

def attach(role, policy, name):
    aws.iam.RolePolicyAttachment(
        name,
        role=role.id,
        policy_arn=policy.arn,
    )



logs_policy = lambda_logs_policy("shared-lambda-logs")

def attach_logs(role, name: str):
    attach(role, logs_policy, f"{name}-logs")

# def write_to_bucket_role(name: str, bucket):
#     role = lambda_role(f"{name}-role")

#     policy = s3_write_policy(f"{name}-s3-write", bucket.arn)

#     attach(role, logs_policy, f"{name}-logs")
#     attach(role, policy, f"{name}-write-attach")

#     return role

# def read_from_bucket_role(name: str, bucket):
#     role = lambda_role(f"{name}-role")

#     policy = s3_read_policy(f"{name}-s3-read", bucket.arn)

#     attach(role, logs_policy, f"{name}-logs")
#     attach(role, policy, f"{name}-read-attach")

#     return role

def basic_logs_role(name: str):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    return role

def presign_upload_role(name: str, bucket):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_write_policy(f"{name}-s3-write", bucket.arn), f"{name}-s3-write-attach")
    return role

def start_job_role(name: str, table, worker_fn_arn):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_put_policy(f"{name}-dynamo-put", table.arn), f"{name}-dynamo-put-attach")
    attach(role, lambda_invoke_policy(f"{name}-invoke", worker_fn_arn), f"{name}-invoke-attach")
    return role

def video_worker_role(name: str, bucket, table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_worker_policy(f"{name}-s3", bucket.arn), f"{name}-s3-attach")
    attach(role, dynamo_update_policy(f"{name}-dynamo", table.arn), f"{name}-dynamo-attach")
    # attach(role, dynamo_query_policy(f"{name}-dynamo-query", table.arn), f"{name}-dynamo-query-attach")
    attach(role, dynamo_query_policy_for_gsi(f"{name}-dynamo-query", table.arn, "GSI1"), f"{name}-dynamo-query-attach")
    return role

def get_job_role(name: str, table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    # attach(role, dynamo_get_policy(f"{name}-dynamo-get", table.arn), f"{name}-dynamo-get-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", table.arn), f"{name}-dynamo-query-attach")
    return role

def list_edits_role(name: str, table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", table.arn), f"{name}-dynamo-query-attach")
    return role

def presign_download_role(name: str, bucket, table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_read_policy(f"{name}-s3-read", bucket.arn), f"{name}-s3-read-attach")
    # attach(role, dynamo_get_policy(f"{name}-dynamo-get", table.arn), f"{name}-dynamo-get-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", table.arn), f"{name}-dynamo-query-attach")
    return role
    