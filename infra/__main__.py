import pulumi
import pulumi_aws as aws
from api import make_api
from dynamo import make_table
from lambdas import make_lambda, make_worker_lambda
from roles import basic_logs_role, get_job_role, list_edits_role, presign_download_role, presign_upload_role, start_job_role, video_worker_role
from s3 import make_bucket
stack = pulumi.get_stack()



app = f"minivide"
ALLOWED_USERS = "u1,u2,u3"
URL_EXPIRY_SECONDS = "120"
MAX_UPLOAD_BYTES = "500000000"




bucket = make_bucket(f"{app}-uploads")
table  = make_table(f"{app}-edits")

worker = make_worker_lambda(
    f"{app}-video-worker",
    "video_worker",
    video_worker_role(f"{app}-video-worker", bucket, table),
    {
        "BUCKET_NAME": bucket.id,
        "TABLE_NAME": table.name,
        "ALLOWED_USERS": ALLOWED_USERS,
    },
)

presign_upload = make_lambda(
    f"{app}-presign-upload",
    "presign_upload",
    presign_upload_role(f"{app}-presign-upload", bucket),
    {
        "BUCKET_NAME": bucket.id,
        "ALLOWED_USERS": ALLOWED_USERS,
        "URL_EXPIRY_SECONDS": URL_EXPIRY_SECONDS,
        "MAX_UPLOAD_BYTES": MAX_UPLOAD_BYTES,
    },
)

start_job = make_lambda(
    f"{app}-start-job",
    "start_job",
    start_job_role(f"{app}-start-job", table, worker.arn),
    {
        "BUCKET_NAME": bucket.id, 
        "TABLE_NAME": table.name,
        "WORKER_FUNCTION_NAME": worker.name,
        "ALLOWED_USERS": ALLOWED_USERS,
    },
)

get_job = make_lambda(
    f"{app}-get-job",
    "get_job",
    get_job_role(f"{app}-get-job", table),
    {"TABLE_NAME": table.name},
)

list_edits = make_lambda(
    f"{app}-list-edits",
    "list_edits",
    list_edits_role(f"{app}-list-edits", table),
    {
        "TABLE_NAME": table.name,
        "ALLOWED_USERS": ALLOWED_USERS,
    },
)

presign_download = make_lambda(
    f"{app}-presign-download",
    "presign_download",
    presign_download_role(f"{app}-presign-download", bucket, table),
    {
        "BUCKET_NAME": bucket.id,
        "TABLE_NAME": table.name,
        "ALLOWED_USERS": ALLOWED_USERS,
        "URL_EXPIRY_SECONDS": URL_EXPIRY_SECONDS,
    },
)

dummy_lambda = make_lambda(
    "dummy-lambda", 
    "dummy",
    basic_logs_role("dummy"),
    {}
)

make_api(f"{app}-api", "dev", [
    {"method": "POST", "path": "/uploads/presign", "lambda_fn": presign_upload},
    {"method": "POST", "path": "/jobs", "lambda_fn": start_job},
    {"method": "GET", "path": "/jobs/{jobId}", "lambda_fn": get_job},
    {"method": "GET", "path": "/users/{userId}/edits", "lambda_fn": list_edits},
    {"method": "POST", "path": "/downloads/presign", "lambda_fn": presign_download},
    {"method": "GET", "path": "/dummy", "lambda_fn": dummy_lambda}
])


aws.cloudwatch.MetricAlarm(
    f"{app}-worker-errors",
    alarm_description="alarm when worker lambda errors",
    namespace="AWS/Lambda",
    metric_name="Errors",
    dimensions={"FunctionName": worker.name},
    statistic="Sum",
    period=60,
    evaluation_periods=1,
    threshold=1,
    comparison_operator="GreaterThanOrEqualToThreshold",
)

