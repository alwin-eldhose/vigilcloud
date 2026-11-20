"""Akamai Object Storage for vendor evidence files.

The bucket stays private. Reviewers open a file through a pre-signed URL that
expires after one hour. boto3 1.36+ sends checksum headers this endpoint
rejects, so checksums are computed only when the operation requires them.
"""

from __future__ import annotations

import mimetypes
import re
from datetime import datetime, timezone

import boto3
from botocore.config import Config

from settings import load_settings

_client = None


def client():
    global _client
    if _client is None:
        settings = load_settings()
        if not settings.storage_ready:
            raise RuntimeError("Object Storage is not configured. Set S3_* or OBJ_* in .env.")
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", request_checksum_calculation="when_required"),
        )
    return _client


def _bucket() -> str:
    return load_settings().s3_bucket


def health() -> tuple[bool, str]:
    settings = load_settings()
    if not settings.storage_ready:
        return False, "S3_* / OBJ_* not set"
    try:
        listed = client().list_objects_v2(Bucket=settings.s3_bucket, Prefix="vigilcloud/", MaxKeys=20)
        count = listed.get("KeyCount", 0)
        shown = f"{count}+" if listed.get("IsTruncated") else str(count)
        noun = "object" if shown == "1" else "objects"
        return True, f"{settings.s3_bucket} · {shown} vigilcloud {noun}"
    except Exception as exc:  # noqa: BLE001 — show the storage error in the status strip
        return False, str(exc).split("\n")[0][:160]


def _safe_name(filename: str) -> str:
    base = filename.strip().replace("\\", "/").split("/")[-1] or "evidence"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-.")
    return (cleaned or "evidence")[:80]


def upload(filename: str, data: bytes, content_type: str | None = None) -> dict[str, object]:
    """Store one evidence file and return a one-hour inspection link."""
    kind = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"vigilcloud/{stamp}-{_safe_name(filename)}"
    client().put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=kind)
    return {
        "bucket": _bucket(),
        "key": key,
        "bytes": len(data),
        "content_type": kind,
        "url": presign(key),
    }


def presign(key: str, expires: int = 3600) -> str:
    return client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=expires,
    )


def list_recent(limit: int = 8) -> list[dict[str, object]]:
    response = client().list_objects_v2(Bucket=_bucket(), Prefix="vigilcloud/", MaxKeys=50)
    items = response.get("Contents", [])
    items.sort(key=lambda item: item["LastModified"], reverse=True)
    recent = []
    for item in items[:limit]:
        recent.append(
            {
                "key": item["Key"],
                "size": item["Size"],
                "modified": item["LastModified"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
        )
    return recent
