import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from botocore.client import Config

s3 = boto3.client("s3", region_name="eu-west-1", config=Config(
    signature_version="s3v4",
    s3={"addressing_style": "virtual"}
))

BUCKET = os.environ["BUCKET_NAME"]
EXPIRY = int(os.environ.get("URL_EXPIRY_SECONDS", "120"))
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "100000000"))
ALLOWED_USERS = set(os.environ.get("ALLOWED_USERS", "").split(","))


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
    filename = (body.get("filename") or "untitled.mp4").strip().replace("/", "_")[:120]
    # TODO: try to break the above

    if user_id not in ALLOWED_USERS:
        return resp(400, {"error": "invalid userId", "allowed": sorted(ALLOWED_USERS)})

    object_key = f"uploads/{user_id}/{uuid.uuid4()}_{filename}"

    presigned = s3.generate_presigned_post(
        Bucket=BUCKET,
        Key=object_key,
        Fields={
            "key": object_key,
            "success_action_status": "201",
        },
        Conditions=[
            ["starts-with", "$key", f"uploads/{user_id}/"],
            ["content-length-range", 1, MAX_BYTES],
            {"success_action_status": "201"},
        ],
        ExpiresIn=EXPIRY,
    )

    print(presigned["url"])

    return resp(200, {
        "objectKey": object_key,
        "upload": presigned,
        "expiresInSeconds": EXPIRY,
    })