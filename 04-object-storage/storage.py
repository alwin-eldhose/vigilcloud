# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3>=1.44", "python-dotenv>=1.2.4"]
# ///
"""Upload a file, list the bucket, read the file back, and print a link that works for one hour.

    uv run 04-object-storage/storage.py
    uv run 04-object-storage/storage.py path/to/your/file
"""
import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("OBJ_ENDPOINT", "OBJ_BUCKET", "OBJ_ACCESS_KEY", "OBJ_SECRET_KEY"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env.")

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["OBJ_ENDPOINT"],
    aws_access_key_id=os.environ["OBJ_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJ_SECRET_KEY"],
    # s3v4 signs requests and links with Signature Version 4, the current method.
    # boto3 1.36 and later send checksums that Object Storage does not support. when_required turns them off.
    config=Config(signature_version="s3v4", request_checksum_calculation="when_required"),
)
bucket = os.environ["OBJ_BUCKET"]

path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
key = path.name if path else "hello.txt"
# The type comes from the file name, so a browser shows hello.txt instead of downloading it.
kind = mimetypes.guess_type(key)[0] or "application/octet-stream"
s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes() if path else b"Hello from Seattle\n", ContentType=kind)
print(f"uploaded  {key}")

for item in s3.list_objects_v2(Bucket=bucket).get("Contents", []):
    print(f"listed    {item['Key']}  {item['Size']} bytes")

data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
print(f"read      {len(data)} bytes back from {key}")

# The bucket stays private. A presigned link lets anyone with the link read this one file until it expires.
url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
print(f"\nThis link works for one hour:\n{url}")
