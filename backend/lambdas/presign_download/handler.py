import json
import os
import boto3
from boto3.dynamodb.conditions import Key


s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET = os.environ["BUCKET_NAME"]
TABLE = os.environ["TABLE_NAME"]
EXPIRY = int(os.environ.get("URL_EXPIRY_SECONDS", "120"))
ALLOWED_USERS = set(os.environ.get("ALLOWED_USERS", "").split(","))

table = dynamodb.Table(TABLE)

def resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return resp(400, {"error": "invalid JSON"})

    user_id = (body.get("userId") or "").strip()
    job_id  = (body.get("jobId") or "").strip()

    if user_id not in ALLOWED_USERS:
        return resp(400, {"error": "invalid userId"})
    if not job_id:
        return resp(400, {"error": "missing jobId"})


    result = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("gsi1pk").eq(f"JOB#{job_id}"),
    )

    items = result.get("Items", [])
    if not items:
        return resp(404, {"error": "job not found"})

    item = items[0]

    if item.get("userId") != user_id:
        return resp(403, {"error": "not authorised"})

    if item.get("status") != "COMPLETED":
        return resp(409, {"error": "job not complete yet", "status": item.get("status")})

    output_key = item.get("outputKey")
    if not output_key:
        return resp(500, {"error": "outputKey missing from job record"})

    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET, "Key": output_key},
        ExpiresIn=EXPIRY,
    )

    return resp(200, {"downloadUrl": url, "expiresInSeconds": EXPIRY})