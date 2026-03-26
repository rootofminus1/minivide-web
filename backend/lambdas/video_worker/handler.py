import json
import subprocess
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

TABLE = os.environ["TABLE_NAME"]
BUCKET = os.environ["BUCKET_NAME"]
table = dynamodb.Table(TABLE)

FFMPEG_BIN = "/opt/bin/ffmpeg"


def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_job(job_id: str):
    result = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("gsi1pk").eq(f"JOB#{job_id}"),
    )

    items = result.get("Items", [])
    return items[0] if items else None  # additional protection

# def update_status(job_id: str, status: str, extra: dict[str, Any] | None = None):
#     result = table.query(
#         IndexName="GSI1",
#         KeyConditionExpression=Key("gsi1pk").eq(f"JOB#{job_id}"),
#     )

#     items = result.get("Items", [])
#     if not items:
#         print(f"[worker] WARNING: job {job_id} not found in GSI1")
#         return

#     item = items[0]
#     pk = item["pk"]
#     sk = item["sk"]

#     update_expr  = "SET #s = :status, updatedAt = :now"
#     expr_values  = {":status": status, ":now": now_iso()}
#     expr_names   = {"#s": "status"}

#     if extra:
#         for k, v in extra.items():
#             update_expr += f", {k} = :{k}"
#             expr_values[f":{k}"] = v

#     table.update_item(
#         Key={"pk": pk, "sk": sk},
#         UpdateExpression=update_expr,
#         ExpressionAttributeNames=expr_names,
#         ExpressionAttributeValues=expr_values,
#     )
#     print(f"[worker] job {job_id}: {status}")


# NEW FIXED IDEMPOTENCY GATE
def claim_job(job_id: str) -> dict | None:
    item = get_job(job_id)
    if not item:
        print(f"[worker] job {job_id} not found")
        return None

    pk = item["pk"]
    sk = item["sk"]

    try:
        table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="""
                SET #s = :processing,
                    processingStartedAt = :now,
                    updatedAt = :now
            """,
            ConditionExpression="#s = :queued",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":queued": "QUEUED",
                ":processing": "PROCESSING",
                ":now": now_iso(),
            },
        )
        print(f"[worker] claimed job {job_id}")
        return item

    except ClientError as e:
        print("[worker] this might error anyway check this later")
        if e.response.get("Error", {}).get("Code", {}) == "ConditionalCheckFailedException":
            print(f"[worker] job {job_id} already claimed or finished")
            return None
        raise

def update_status(job_id: str, from_status: str, to_status: str, extra: dict[str, Any] | None = None):
    item = get_job(job_id)
    if not item:
        print(f"[worker] job {job_id} not found during update")
        return

    pk = item["pk"]
    sk = item["sk"]

    update_expr = "SET #s = :new, updatedAt = :now"
    expr_names = {"#s": "status"}
    expr_values = {
        ":old": from_status,
        ":new": to_status,
        ":now": now_iso(),
    }

    if extra:
        for k, v in extra.items():
            update_expr += f", {k} = :{k}"
            expr_values[f":{k}"] = v

    table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression=update_expr,
        ConditionExpression="#s = :old",
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )

    print(f"[worker] job {job_id}: {from_status} -> {to_status}")


def process_video(input_path: str, output_path: str, trim_start: float, trim_end: float, target_size_mb: float):
    duration = trim_end - trim_start
    if duration <= 0:
        raise ValueError("trim_end must be greater than trim_start")

    SAFETY_MARGIN = 0.92
    AUDIO_KBPS = 128

    total_kbps = int((target_size_mb * 8 * 1024) / duration)
    video_kbps = int(total_kbps * SAFETY_MARGIN) - AUDIO_KBPS
    video_kbps = max(100, video_kbps)

    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(trim_start),
        "-to", str(trim_end),
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", f"{video_kbps}k",
        "-c:a", "aac",
        "-b:a", f"{AUDIO_KBPS}k",
        output_path,
    ]

    print(f"[worker] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[worker] ffmpeg stderr: {result.stderr[-1000:]}")
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    actual_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[worker] output size: {actual_mb:.2f} MB (target was {target_size_mb} MB)")
    return actual_mb


def lambda_handler(event, context):
    job_id = event["jobId"]
    user_id = event["userId"]
    object_key = event["objectKey"]
    edit_params = event.get("editParams", {})

    trim_start = float(edit_params.get("trimStart", 0))
    trim_end = float(edit_params.get("trimEnd", 0))
    target_size_mb = float(edit_params.get("targetSizeMB", 10))

    print(f"[worker] job={job_id} user={user_id}")
    print(f"[worker] objectKey={object_key}")
    print(f"[worker] trimStart={trim_start} trimEnd={trim_end} targetSizeMB={target_size_mb}")

    # idempotency gate
    job = claim_job(job_id)
    if not job:
        return {"ok": True, "skipped": True}

    input_path = f"/tmp/{job_id}_input.mp4"
    output_path = f"/tmp/{job_id}_output.mp4"
    output_key = object_key.replace("uploads/", "outputs/", 1)

    try:
        # state transition to processing done in claim_job now
        print(f"[worker] downloading s3://{BUCKET}/{object_key}")
        s3.download_file(BUCKET, object_key, input_path)
        print(f"[worker] download complete ({os.path.getsize(input_path) / (1024*1024):.1f} MB)")

        actual_mb = process_video(input_path, output_path, trim_start, trim_end, target_size_mb)

        print(f"[worker] uploading to s3://{BUCKET}/{output_key}")
        s3.upload_file(output_path, BUCKET, output_key)
        print(f"[worker] upload complete")

        update_status(job_id, "PROCESSING", "COMPLETED", {
            "outputKey": output_key,
            "completedAt": now_iso(),
            "outputSizeMB": str(round(actual_mb, 2)),
        })

        return {"ok": True, "jobId": job_id}

    except Exception as e:
        print(f"[worker] ERROR job {job_id}: {e}")
        update_status(job_id, "PROCESSING", "FAILED", {
            "errorMessage": str(e),
            "failedAt": now_iso(),
        })
        raise

    finally:
        for path in (input_path, output_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass