from decimal import Decimal
import json
import os
import boto3
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")
TABLE = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE)


def convert_decimals(obj):
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(x) for x in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

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
    job_id = (event.get("pathParameters") or {}).get("jobId", "").strip()

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

    return resp(200, convert_decimals(item))