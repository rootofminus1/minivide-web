from decimal import Decimal
import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from dataclasses import dataclass

dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

TABLE = os.environ["TABLE_NAME"]
WORKER_FN = os.environ["WORKER_FUNCTION_NAME"]
ALLOWED_USERS = set(os.environ.get("ALLOWED_USERS", "").split(","))

table = dynamodb.Table(TABLE)


def json_safe(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(v) for v in obj]
    return obj

def now_iso():
    return datetime.now(timezone.utc).isoformat()

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
    object_key = (body.get("objectKey") or "").strip()
    edit_params = convert_floats(body.get("editParams") or {})

    # uploads/{user}/{uuid}_filename.mp4
    # PS: there's prob a better way to do it
    raw_name = object_key.split("/")[-1]
    filename = raw_name.split("_", 1)[-1] if "_" in raw_name else raw_name

    if user_id not in ALLOWED_USERS:
        return resp(400, {"error": "invalid userId"})

    if not object_key.startswith(f"uploads/{user_id}/"):
        return resp(403, {"error": "objectKey not in user prefix"})
    
    job_id = str(uuid.uuid4())
    now = now_iso()

    table.put_item(Item={
        "pk": f"USER#{user_id}",
        "sk": f"JOB#{now}#{job_id}",
        "gsi1pk": f"JOB#{job_id}",
        "gsi1sk": "meta",
        "jobId": job_id,
        "userId": user_id,
        "status": "QUEUED",
        "objectKey": object_key,
        "filename": filename,
        "editParams": edit_params,
        "createdAt": now,
        "updatedAt": now,
        "processingStartedAt": None,
        "completedAt": None,
        "failedAt": None,
    })
    

    lambda_client.invoke(
        FunctionName=WORKER_FN,
        InvocationType="Event",
        Payload=json.dumps({
            "jobId": job_id,
            "userId": user_id,
            "objectKey": object_key,
            "editParams": edit_params,
        }, 
            default=json_safe,
        ).encode(),
    )

    return resp(202, {
        "jobId": job_id,
        "status": "QUEUED",
        "message": "job accepted",
    })