import json
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")
TABLE = os.environ["TABLE_NAME"]
ALLOWED_USERS = set(os.environ.get("ALLOWED_USERS", "").split(","))

table = dynamodb.Table(TABLE)

def json_safe(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj

def resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body, default=json_safe),
    }

def lambda_handler(event, context):
    qs = event.get("queryStringParameters") or {}
    user_id = (qs.get("userId") or "").strip()


    if not user_id:
        user_id = ((event.get("pathParameters") or {}).get("userId") or "").strip()

    if user_id not in ALLOWED_USERS:
        return resp(400, {"error": "invalid userId"})

    result = table.query(
        KeyConditionExpression=Key("pk").eq(f"USER#{user_id}") & Key("sk").begins_with("JOB#"),
        ScanIndexForward=False,
    )

    edits = []
    for item in result.get("Items", []):
        raw_filename = item.get("filename")

        if isinstance(raw_filename, str) and raw_filename:
            display_name = raw_filename.rsplit(".", 1)[0]
        else:
            display_name = "untitled"

        edits.append({
            "jobId": item.get("jobId"),
            "status": item.get("status"),
            "filename": display_name,
            "objectKey": item.get("objectKey"),
            "outputKey": item.get("outputKey"),
            "editParams": item.get("editParams"),
            "createdAt": item.get("createdAt"),
            "completedAt": item.get("completedAt"),
        })

    return resp(200, {"userId": user_id, "edits": edits})