"""Resolve VigilCloud settings from the environment.

The portal reads the names in the build spec. When those are empty, it falls
back to the Akamai workshop lab names already stored in this repo's `.env`
(`AKAMAI_API_KEY`, `OBJ_*`, `PG*`), so a local demo works without renaming keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

EMBEDDING_DIM = 4096
INFERENCE_DEFAULT_URL = "https://api.akamai-inference.com/v1"


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
    inference_key: str
    inference_key_var: str
    inference_base_url: str
    inference_url_var: str
    chat_model: str
    vision_model: str
    embedding_model: str
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
        return bool(self.inference_key and self.inference_base_url)

    @property
    def storage_ready(self) -> bool:
        return bool(self.s3_endpoint and self.s3_access_key and self.s3_secret_key and self.s3_bucket)

    @property
    def database_ready(self) -> bool:
        return bool(self.database_url)


def load_settings() -> Settings:
    return Settings(
        inference_key=pick("AKAMAI_INFERENCE_API_KEY", "AKAMAI_API_KEY", "OPENAI_API_KEY"),
        inference_key_var=which("AKAMAI_INFERENCE_API_KEY", "AKAMAI_API_KEY", "OPENAI_API_KEY"),
        inference_base_url=pick(
            "AKAMAI_INFERENCE_BASE_URL", "AKAMAI_BASE_URL", "OPENAI_BASE_URL", default=INFERENCE_DEFAULT_URL
        ),
        inference_url_var=which("AKAMAI_INFERENCE_BASE_URL", "AKAMAI_BASE_URL", "OPENAI_BASE_URL"),
        chat_model=pick("CHAT_MODEL", default="qwen3-8-27b"),
        vision_model=pick("VISION_MODEL", default="gemma-4-26b-a4b-it"),
        embedding_model=pick("EMBEDDING_MODEL", default="qwen3-embedding-8b"),
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
