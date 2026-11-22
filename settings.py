"""Resolve VigilCloud settings from the environment.

Inference runs on Claude (ANTHROPIC_API_KEY). Object Storage and PostgreSQL use the
Akamai names already stored in this repo's `.env` (`OBJ_*`, `PG*`). The spec names
(`S3_*`, `DATABASE_URL`) are accepted as aliases.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

CLAUDE_DEFAULT_MODEL = "claude-sonnet-4-6"


def pick(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def which(*names: str) -> str:
    """Return the first env var name that is set, for the telemetry strip."""
    for name in names:
        if os.environ.get(name, "").strip():
            return name
    return names[0]


def database_url() -> str:
    """SQLAlchemy URL for Akamai Managed PostgreSQL. Empty when unset."""
    raw = pick("DATABASE_URL")
    if raw:
        if raw.startswith("postgres://"):
            raw = "postgresql://" + raw[len("postgres://") :]
        if raw.startswith("postgresql://"):
            raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
        return raw
    host = pick("PGHOST")
    if not host:
        return ""
    user = quote_plus(pick("PGUSER", default="akmadmin"))
    password = quote_plus(pick("PGPASSWORD"))
    port = pick("PGPORT", default="5432")
    database = pick("PGDATABASE", default="defaultdb")
    sslmode = pick("PGSSLMODE", default="require")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"


@dataclass(frozen=True)
class Settings:
    anthropic_key: str
    anthropic_key_var: str
    chat_model: str
    vision_model: str
    summary_model: str
    s3_endpoint: str
    s3_endpoint_var: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_bucket_var: str
    database_url: str
    database_var: str
    db_host: str

    @property
    def inference_ready(self) -> bool:
        return bool(self.anthropic_key)

    @property
    def storage_ready(self) -> bool:
        return bool(self.s3_endpoint and self.s3_access_key and self.s3_secret_key and self.s3_bucket)

    @property
    def database_ready(self) -> bool:
        return bool(self.database_url)


def load_settings() -> Settings:
    return Settings(
        anthropic_key=pick("ANTHROPIC_API_KEY"),
        anthropic_key_var="ANTHROPIC_API_KEY",
        chat_model=pick("CHAT_MODEL", default=CLAUDE_DEFAULT_MODEL),
        vision_model=pick("VISION_MODEL", default=CLAUDE_DEFAULT_MODEL),
        summary_model=pick("SUMMARY_MODEL", "CHAT_MODEL", default=CLAUDE_DEFAULT_MODEL),
        s3_endpoint=pick("S3_ENDPOINT_URL", "OBJ_ENDPOINT"),
        s3_endpoint_var=which("S3_ENDPOINT_URL", "OBJ_ENDPOINT"),
        s3_region=pick("S3_REGION", default="us-east-1"),
        s3_access_key=pick("S3_ACCESS_KEY", "OBJ_ACCESS_KEY"),
        s3_secret_key=pick("S3_SECRET_KEY", "OBJ_SECRET_KEY"),
        s3_bucket=pick("S3_BUCKET_NAME", "OBJ_BUCKET"),
        s3_bucket_var=which("S3_BUCKET_NAME", "OBJ_BUCKET"),
        database_url=database_url(),
        database_var="DATABASE_URL" if pick("DATABASE_URL") else "PGHOST",
        db_host=pick("PGHOST"),
    )
