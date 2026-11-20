"""PostgreSQL registry for vendor assessments and chunk embeddings.

Akamai Managed PostgreSQL keeps the structured findings. Embeddings are
`vector(4096)` via pgvector. That dimension is above pgvector's index limit
(2,000), so similarity search is an exact `<=>` scan. The registry is small
on purpose: a GRC team reviews dozens of vendors, not millions of chunks.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from settings import EMBEDDING_DIM, load_settings

_engine: Engine | None = None
_ready = False

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS vendor_assessments (
    id BIGSERIAL PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    object_key TEXT,
    document_text TEXT NOT NULL,
    vision_summary TEXT NOT NULL DEFAULT '',
    profile_text TEXT NOT NULL,
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    encryption_status TEXT NOT NULL,
    access_control_summary TEXT NOT NULL,
    compliance_gaps JSONB NOT NULL,
    remediation_steps JSONB NOT NULL,
    evidence_quotes JSONB NOT NULL,
    grounding_verdict TEXT NOT NULL,
    grounding_issues JSONB NOT NULL,
    quote_checks JSONB NOT NULL,
    critic_verdict TEXT NOT NULL,
    critic_reason TEXT NOT NULL,
    embedding vector({EMBEDDING_DIM}),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vendor_assessments_risk_idx
    ON vendor_assessments (risk_score DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS vendor_chunks (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT NOT NULL REFERENCES vendor_assessments(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    body TEXT NOT NULL,
    embedding vector({EMBEDDING_DIM}) NOT NULL
);
"""

CROSS_VENDOR_SQL = """
SELECT id, vendor_name, risk_score, encryption_status,
       grounding_verdict, critic_verdict, source_filename, created_at
FROM vendor_assessments
WHERE risk_score >= :min_score
ORDER BY risk_score DESC, created_at DESC
"""


def _json(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def vector_literal(values: list[float]) -> str:
    return json.dumps(values)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = load_settings().database_url
        if not url:
            raise RuntimeError("PostgreSQL is not configured. Set DATABASE_URL or the PG* variables in .env.")
        _engine = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)
    return _engine


def init_db() -> None:
    """Create the extension and tables. Safe to call on every page load."""
    global _ready
    if _ready:
        return
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    statements = [statement.strip() for statement in SCHEMA.split(";") if statement.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    _ready = True


def health() -> tuple[bool, str]:
    settings = load_settings()
    if not settings.database_ready:
        return False, "DATABASE_URL / PG* not set"
    try:
        init_db()
        with get_engine().connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM vendor_assessments")).scalar_one()
        host = settings.db_host or "database"
        return True, f"{count} assessment{'s' if count != 1 else ''} · {host.split('.')[0]}"
    except Exception as exc:  # noqa: BLE001 — surface the driver error in the status strip
        return False, str(exc).split("\n")[0][:160]


def insert_assessment(record: dict[str, Any], chunks: list[dict[str, Any]]) -> int:
    """Insert one verified assessment and its chunk embeddings in a single transaction."""
    init_db()
    statement = text(
        """
        INSERT INTO vendor_assessments (
            vendor_name, source_filename, source_kind, object_key, document_text,
            vision_summary, profile_text, risk_score, encryption_status,
            access_control_summary, compliance_gaps, remediation_steps, evidence_quotes,
            grounding_verdict, grounding_issues, quote_checks, critic_verdict,
            critic_reason, embedding
        ) VALUES (
            :vendor_name, :source_filename, :source_kind, :object_key, :document_text,
            :vision_summary, :profile_text, :risk_score, :encryption_status,
            :access_control_summary, CAST(:compliance_gaps AS jsonb),
            CAST(:remediation_steps AS jsonb), CAST(:evidence_quotes AS jsonb),
            :grounding_verdict, CAST(:grounding_issues AS jsonb), CAST(:quote_checks AS jsonb),
            :critic_verdict, :critic_reason, CAST(:embedding AS vector)
        )
        RETURNING id
        """
    )
    chunk_sql = text(
        """
        INSERT INTO vendor_chunks (assessment_id, chunk_index, body, embedding)
        VALUES (:assessment_id, :chunk_index, :body, CAST(:embedding AS vector))
        """
    )
    payload = {
        **record,
        "compliance_gaps": json.dumps(record["compliance_gaps"]),
        "remediation_steps": json.dumps(record["remediation_steps"]),
        "evidence_quotes": json.dumps(record["evidence_quotes"]),
        "grounding_issues": json.dumps(record["grounding_issues"]),
        "quote_checks": json.dumps(record["quote_checks"]),
        "embedding": vector_literal(record["embedding"]),
    }
    with get_engine().begin() as conn:
        assessment_id = conn.execute(statement, payload).scalar_one()
        for chunk in chunks:
            conn.execute(
                chunk_sql,
                {
                    "assessment_id": assessment_id,
                    "chunk_index": chunk["chunk_index"],
                    "body": chunk["body"],
                    "embedding": vector_literal(chunk["embedding"]),
                },
            )
    return int(assessment_id)


def _row_summary(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "vendor_name": row.vendor_name,
        "risk_score": row.risk_score,
        "encryption_status": row.encryption_status,
        "grounding_verdict": row.grounding_verdict,
        "critic_verdict": row.critic_verdict,
        "source_filename": row.source_filename,
        "source_kind": row.source_kind,
        "object_key": row.object_key,
        "created_at": row.created_at,
    }


def list_assessments(min_score: int = 0) -> list[dict[str, Any]]:
    """Cross-vendor registry query used by the risk slider."""
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, vendor_name, risk_score, encryption_status, grounding_verdict,
                       critic_verdict, source_filename, source_kind, object_key, created_at
                FROM vendor_assessments
                WHERE risk_score >= :min_score
                ORDER BY risk_score DESC, created_at DESC
                """
            ),
            {"min_score": int(min_score)},
        ).fetchall()
    return [_row_summary(row) for row in rows]


def get_assessment(assessment_id: int) -> dict[str, Any] | None:
    init_db()
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, vendor_name, source_filename, source_kind, object_key, document_text,
                       vision_summary, profile_text, risk_score, encryption_status,
                       access_control_summary, compliance_gaps, remediation_steps, evidence_quotes,
                       grounding_verdict, grounding_issues, quote_checks, critic_verdict,
                       critic_reason, created_at
                FROM vendor_assessments
                WHERE id = :id
                """
            ),
            {"id": assessment_id},
        ).mappings().first()
    if row is None:
        return None
    record = dict(row)
    for key in ("compliance_gaps", "remediation_steps", "evidence_quotes", "grounding_issues", "quote_checks"):
        record[key] = _json(record[key])
    return record


def delete_assessment(assessment_id: int) -> bool:
    init_db()
    with get_engine().begin() as conn:
        result = conn.execute(
            text("DELETE FROM vendor_assessments WHERE id = :id"),
            {"id": assessment_id},
        )
    return bool(result.rowcount)


def semantic_search(query_embedding: list[float], limit: int = 8) -> list[dict[str, Any]]:
    """Rank vendor profiles and evidence chunks by cosine distance.

    `<=>` is pgvector cosine distance. These embeddings are unit length, so
    similarity is `1 - distance`.
    """
    init_db()
    sql = text(
        """
        SELECT assessment_id, vendor_name, risk_score, encryption_status,
               critic_verdict, kind, snippet, distance
        FROM (
            SELECT id AS assessment_id, vendor_name, risk_score, encryption_status,
                   critic_verdict, 'profile' AS kind, profile_text AS snippet,
                   embedding <=> CAST(:query AS vector) AS distance
            FROM vendor_assessments
            WHERE embedding IS NOT NULL
            UNION ALL
            SELECT a.id, a.vendor_name, a.risk_score, a.encryption_status,
                   a.critic_verdict, 'evidence' AS kind, c.body AS snippet,
                   c.embedding <=> CAST(:query AS vector) AS distance
            FROM vendor_chunks c
            JOIN vendor_assessments a ON a.id = c.assessment_id
        ) hits
        ORDER BY distance
        LIMIT :limit
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(
            sql,
            {"query": vector_literal(query_embedding), "limit": int(limit)},
        ).mappings().fetchall()
    hits = []
    for row in rows:
        distance = float(row["distance"])
        hits.append(
            {
                "assessment_id": row["assessment_id"],
                "vendor_name": row["vendor_name"],
                "risk_score": row["risk_score"],
                "encryption_status": row["encryption_status"],
                "critic_verdict": row["critic_verdict"],
                "kind": row["kind"],
                "snippet": row["snippet"],
                "distance": distance,
                "similarity": max(0.0, 1.0 - distance),
            }
        )
    return hits


def vendor_spread() -> list[dict[str, Any]]:
    """One row per vendor, so repeat intakes show whether the score moved."""
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT vendor_name,
                       count(*) AS assessments,
                       min(risk_score) AS lowest,
                       max(risk_score) AS highest,
                       (array_agg(risk_score ORDER BY created_at DESC))[1] AS latest
                FROM vendor_assessments
                GROUP BY vendor_name
                ORDER BY latest DESC, vendor_name
                """
            )
        ).mappings().fetchall()
    return [dict(row) for row in rows]
