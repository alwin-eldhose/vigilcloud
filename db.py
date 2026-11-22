"""PostgreSQL registry for assessments, control-level findings, reviewer decisions, and search.

Akamai Managed PostgreSQL keeps the structured records. Search uses PostgreSQL full-text
search (tsvector with GIN indexes). Claude does not offer embeddings.
"""

from __future__ import annotations

import json
import re
import socket
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from settings import load_settings

_engine: Engine | None = None
_ready = False

SCHEMA = """
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
    evidence_quotes JSONB NOT NULL DEFAULT '[]'::jsonb,
    grounding_verdict TEXT NOT NULL,
    grounding_issues JSONB NOT NULL,
    quote_checks JSONB NOT NULL,
    critic_verdict TEXT NOT NULL,
    critic_reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS questionnaire_text TEXT NOT NULL DEFAULT '';
ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS draft_summary TEXT NOT NULL DEFAULT '';
ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS review_decision TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS reviewer_tier TEXT;
ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS reviewer_note TEXT NOT NULL DEFAULT '';
ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS vendor_assessments_risk_idx
    ON vendor_assessments (risk_score DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS control_findings (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT NOT NULL REFERENCES vendor_assessments(id) ON DELETE CASCADE,
    finding_order INTEGER NOT NULL,
    claim_or_control TEXT NOT NULL,
    status TEXT NOT NULL,
    model_status TEXT NOT NULL,
    evidence_quote TEXT NOT NULL DEFAULT '',
    quote_check TEXT NOT NULL DEFAULT 'n/a',
    analyst_check_needed TEXT NOT NULL,
    gate_note TEXT NOT NULL DEFAULT '',
    reviewer_status TEXT,
    reviewer_note TEXT NOT NULL DEFAULT ''
);

ALTER TABLE control_findings ADD COLUMN IF NOT EXISTS search_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(claim_or_control, '') || ' ' || replace(coalesce(status, ''), '_', ' ')
                || ' ' || coalesce(evidence_quote, ''))
) STORED;

CREATE INDEX IF NOT EXISTS control_findings_assessment_idx ON control_findings (assessment_id, finding_order);
CREATE INDEX IF NOT EXISTS control_findings_search_idx ON control_findings USING GIN (search_tsv);

CREATE TABLE IF NOT EXISTS vendor_chunks (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT NOT NULL REFERENCES vendor_assessments(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    body TEXT NOT NULL
);

ALTER TABLE vendor_chunks ADD COLUMN IF NOT EXISTS search_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('english', body)
) STORED;

ALTER TABLE vendor_assessments ADD COLUMN IF NOT EXISTS search_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(vendor_name, '') || ' ' || coalesce(profile_text, '') || ' ' ||
                coalesce(encryption_status, '') || ' ' || coalesce(access_control_summary, ''))
) STORED;

CREATE INDEX IF NOT EXISTS vendor_assessments_search_idx ON vendor_assessments USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS vendor_chunks_search_idx ON vendor_chunks USING GIN (search_tsv);
"""

CROSS_VENDOR_SQL = """
SELECT a.id, a.vendor_name, a.risk_score, a.reviewer_tier, a.review_decision,
       a.grounding_verdict, a.critic_verdict, a.source_filename, a.source_kind,
       a.object_key, a.created_at,
       (SELECT count(*) FROM control_findings f
         WHERE f.assessment_id = a.id AND f.status = 'INSUFFICIENT_EVIDENCE') AS insufficient,
       (SELECT count(*) FROM control_findings f
         WHERE f.assessment_id = a.id AND f.status = 'CONTRADICTION_RISK') AS contradictions
FROM vendor_assessments a
ORDER BY a.created_at DESC
"""

# Words that match almost every record and would only add noise to a search.
STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "any", "all", "with", "that", "this", "from",
    "have", "has", "does", "which", "what", "who", "when", "where", "how", "why", "their",
    "there", "about", "should", "first", "highest", "compare", "vendor", "vendors", "record",
    "records", "registry", "control", "controls", "company", "companies", "tell", "show",
}


def _ipv4_for(host: str) -> str:
    """The database host also publishes an IPv6 address. Networks without IPv6 wait
    about a minute on it before falling back, so connect over IPv4 directly."""
    try:
        for _family, _type, _proto, _canon, sockaddr in socket.getaddrinfo(host, None, socket.AF_INET):
            return sockaddr[0]
    except OSError:
        pass
    return ""


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = load_settings().database_url
        if not url:
            raise RuntimeError("PostgreSQL is not configured. Set DATABASE_URL or the PG* variables in .env.")
        connect_args: dict[str, str] = {}
        host = make_url(url).host
        address = _ipv4_for(host) if host else ""
        if address:
            connect_args["hostaddr"] = address
        _engine = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2, connect_args=connect_args)
    return _engine


def init_db() -> None:
    """Create or migrate the tables. Safe to call on every page load."""
    global _ready
    if _ready:
        return
    engine = get_engine()
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


def insert_assessment(record: dict[str, Any], findings: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> int:
    """Insert one assessment, its findings, and its evidence chunks in a single transaction."""
    init_db()
    statement = text(
        """
        INSERT INTO vendor_assessments (
            vendor_name, source_filename, source_kind, object_key, document_text,
            vision_summary, profile_text, risk_score, encryption_status,
            access_control_summary, compliance_gaps, remediation_steps, evidence_quotes,
            grounding_verdict, grounding_issues, quote_checks, critic_verdict, critic_reason,
            questionnaire_text, draft_summary
        ) VALUES (
            :vendor_name, :source_filename, :source_kind, :object_key, :document_text,
            :vision_summary, :profile_text, :risk_score, :encryption_status,
            :access_control_summary, CAST(:compliance_gaps AS jsonb),
            CAST(:remediation_steps AS jsonb), CAST(:evidence_quotes AS jsonb),
            :grounding_verdict, CAST(:grounding_issues AS jsonb), CAST(:quote_checks AS jsonb),
            :critic_verdict, :critic_reason, :questionnaire_text, :draft_summary
        )
        RETURNING id
        """
    )
    finding_sql = text(
        """
        INSERT INTO control_findings (
            assessment_id, finding_order, claim_or_control, status, model_status,
            evidence_quote, quote_check, analyst_check_needed, gate_note
        ) VALUES (
            :assessment_id, :finding_order, :claim_or_control, :status, :model_status,
            :evidence_quote, :quote_check, :analyst_check_needed, :gate_note
        )
        """
    )
    chunk_sql = text("INSERT INTO vendor_chunks (assessment_id, chunk_index, body) VALUES (:assessment_id, :chunk_index, :body)")
    payload = {
        **record,
        "compliance_gaps": json.dumps(record["compliance_gaps"]),
        "remediation_steps": json.dumps(record["remediation_steps"]),
        "evidence_quotes": json.dumps(record.get("evidence_quotes", [])),
        "grounding_issues": json.dumps(record["grounding_issues"]),
        "quote_checks": json.dumps(record["quote_checks"]),
    }
    with get_engine().begin() as conn:
        assessment_id = conn.execute(statement, payload).scalar_one()
        for finding in findings:
            conn.execute(finding_sql, {"assessment_id": assessment_id, **finding})
        for chunk in chunks:
            conn.execute(chunk_sql, {"assessment_id": assessment_id, **chunk})
    return int(assessment_id)


def get_findings(assessment_id: int) -> list[dict[str, Any]]:
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, finding_order, claim_or_control, status, model_status, evidence_quote,
                       quote_check, analyst_check_needed, gate_note, reviewer_status, reviewer_note
                FROM control_findings
                WHERE assessment_id = :id
                ORDER BY finding_order
                """
            ),
            {"id": assessment_id},
        ).mappings().fetchall()
    return [dict(row) for row in rows]


def save_review(assessment_id: int, decision: str, tier: str | None, note: str, overrides: dict[int, str | None]) -> None:
    """Save the reviewer's decision, tier, note, and any per-finding status overrides."""
    init_db()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE vendor_assessments
                SET review_decision = :decision, reviewer_tier = :tier,
                    reviewer_note = :note, reviewed_at = now()
                WHERE id = :id
                """
            ),
            {"id": assessment_id, "decision": decision, "tier": tier, "note": note},
        )
        for finding_id, status in overrides.items():
            conn.execute(
                text("UPDATE control_findings SET reviewer_status = :status WHERE id = :fid AND assessment_id = :aid"),
                {"status": status, "fid": finding_id, "aid": assessment_id},
            )


def _row_summary(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "vendor_name": row.vendor_name,
        "risk_score": row.risk_score,
        "reviewer_tier": row.reviewer_tier,
        "review_decision": row.review_decision,
        "insufficient": row.insufficient,
        "contradictions": row.contradictions,
        "grounding_verdict": row.grounding_verdict,
        "critic_verdict": row.critic_verdict,
        "source_filename": row.source_filename,
        "source_kind": row.source_kind,
        "object_key": row.object_key,
        "created_at": row.created_at,
    }


def list_assessments() -> list[dict[str, Any]]:
    """Every saved assessment, newest first, with its finding counts."""
    init_db()
    with get_engine().connect() as conn:
        rows = conn.execute(text(CROSS_VENDOR_SQL)).fetchall()
    return [_row_summary(row) for row in rows]


def get_assessment(assessment_id: int) -> dict[str, Any] | None:
    init_db()
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, vendor_name, source_filename, source_kind, object_key, document_text,
                       vision_summary, profile_text, risk_score, encryption_status,
                       access_control_summary, compliance_gaps, remediation_steps,
                       grounding_verdict, grounding_issues, quote_checks, critic_verdict,
                       critic_reason, created_at, questionnaire_text, draft_summary,
                       review_decision, reviewer_tier, reviewer_note, reviewed_at
                FROM vendor_assessments
                WHERE id = :id
                """
            ),
            {"id": assessment_id},
        ).mappings().first()
    if row is None:
        return None
    record = dict(row)
    for key in ("compliance_gaps", "remediation_steps", "grounding_issues", "quote_checks"):
        if isinstance(record[key], str):
            record[key] = json.loads(record[key])
    return record


def delete_assessment(assessment_id: int) -> bool:
    init_db()
    with get_engine().begin() as conn:
        result = conn.execute(text("DELETE FROM vendor_assessments WHERE id = :id"), {"id": assessment_id})
    return bool(result.rowcount)


def search_terms(question: str) -> str:
    """Turn a question into an OR query of content words, e.g. 'encryption | backup'."""
    words = re.findall(r"[a-z0-9]{3,}", question.lower())
    terms = [word for word in dict.fromkeys(words) if word not in STOPWORDS]
    return " | ".join(terms)


def fulltext_search(question: str, limit: int = 8) -> list[dict[str, Any]]:
    """Rank vendor profiles, control findings, and evidence passages by full-text relevance."""
    init_db()
    query = search_terms(question)
    if not query:
        return []
    sql = text(
        """
        SELECT assessment_id, vendor_name, risk_score, critic_verdict, kind, snippet, score
        FROM (
            SELECT a.id AS assessment_id, a.vendor_name, a.risk_score, a.critic_verdict,
                   'profile' AS kind, a.profile_text AS snippet,
                   ts_rank(a.search_tsv, to_tsquery('english', :q)) AS score
            FROM vendor_assessments a
            WHERE a.search_tsv @@ to_tsquery('english', :q)
            UNION ALL
            SELECT a.id, a.vendor_name, a.risk_score, a.critic_verdict,
                   'finding', f.claim_or_control || ' [' || f.status || '] ' || f.evidence_quote,
                   ts_rank(f.search_tsv, to_tsquery('english', :q))
            FROM control_findings f
            JOIN vendor_assessments a ON a.id = f.assessment_id
            WHERE f.search_tsv @@ to_tsquery('english', :q)
            UNION ALL
            SELECT a.id, a.vendor_name, a.risk_score, a.critic_verdict,
                   'evidence', c.body,
                   ts_rank(c.search_tsv, to_tsquery('english', :q))
            FROM vendor_chunks c
            JOIN vendor_assessments a ON a.id = c.assessment_id
            WHERE c.search_tsv @@ to_tsquery('english', :q)
        ) hits
        ORDER BY score DESC, risk_score DESC
        LIMIT :limit
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"q": query, "limit": int(limit)}).mappings().fetchall()
    return [
        {
            "assessment_id": row["assessment_id"],
            "vendor_name": row["vendor_name"],
            "risk_score": row["risk_score"],
            "critic_verdict": row["critic_verdict"],
            "kind": row["kind"],
            "snippet": row["snippet"],
            "score": float(row["score"]),
        }
        for row in rows
    ]


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
