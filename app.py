"""VigilCloud: multi-modal vendor risk and compliance intake.

Security and GRC reviewers upload a vendor PDF, note, or architecture diagram.
The file lands in Akamai Object Storage, the findings land in Managed PostgreSQL,
and a two-stage gate checks the model before the row is written.

    uv sync
    uv run streamlit run app.py
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

import db
import inference_verifier
import storage
from inference_verifier import IntakeError, IntakePacket
from settings import ROOT, load_settings

SAMPLES = {
    "High-Risk ETL Vendor": ROOT / "samples" / "high_risk_etl_vendor.md",
    "Compliant Identity Vendor": ROOT / "samples" / "compliant_identity_vendor.md",
}

QUESTIONS = [
    "Which vendor stores sensitive data without encryption?",
    "Compare access control at Northline DataForge and HarborKey Identity.",
    "What is the highest residual risk in the registry, and what should be fixed first?",
]


def inject_css() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
          html, body, [class*="css"] { font-family: "IBM Plex Sans", sans-serif; }
          .stApp {
            background:
              radial-gradient(900px 420px at 0% -10%, rgba(61, 220, 151, 0.08), transparent 55%),
              radial-gradient(800px 380px at 100% 0%, rgba(142, 180, 255, 0.09), transparent 50%),
              #0b1220;
          }
          .block-container { padding-top: 1.1rem; max-width: 1240px; }
          header[data-testid="stHeader"] { background: transparent; }
          [data-testid="stSidebar"] { display: none; }
          h1, h2, h3 { letter-spacing: -0.03em; }
          .vc-brand { display: flex; gap: 0.85rem; align-items: center; margin-bottom: 0.2rem; }
          .vc-mark {
            width: 2.3rem; height: 2.3rem; border-radius: 0.55rem;
            background: linear-gradient(160deg, #3ddc97, #16382c 70%);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16);
          }
          .vc-brand h1 { margin: 0; font-size: 1.7rem; line-height: 1; color: #f4f7ff; }
          .vc-brand p { margin: 0.28rem 0 0; color: #93a4c3; font-size: 0.95rem; }
          .vc-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 0.85rem 0 0.35rem;
          }
          .vc-card {
            background: rgba(18, 26, 43, 0.92);
            border: 1px solid #243049;
            border-radius: 0.75rem;
            padding: 0.7rem 0.8rem 0.75rem;
            min-height: 5.4rem;
          }
          .vc-card.tone-ok { border-top: 2px solid #3ddc97; }
          .vc-card.tone-info { border-top: 2px solid #8eb4ff; }
          .vc-card.tone-bad { border-top: 2px solid #ff5d73; }
          .vc-card.tone-warn { border-top: 2px solid #f5b942; }
          .vc-kicker {
            color: #93a4c3; font-size: 0.72rem; letter-spacing: 0.08em;
            text-transform: uppercase; font-weight: 600;
          }
          .vc-state { color: #f4f7ff; font-size: 1.02rem; font-weight: 600; margin-top: 0.2rem; }
          .vc-detail { color: #93a4c3; font-size: 0.78rem; margin-top: 0.2rem; line-height: 1.35; }
          .vc-score {
            font-family: "IBM Plex Mono", monospace;
            font-size: 3rem; font-weight: 600; line-height: 1; margin: 0.2rem 0;
          }
          .vc-score.low { color: #3ddc97; }
          .vc-score.mid { color: #f5b942; }
          .vc-score.high { color: #ff5d73; }
          .vc-badge {
            display: inline-block; border-radius: 999px; padding: 0.12rem 0.55rem;
            font-family: "IBM Plex Mono", monospace; font-size: 0.78rem; font-weight: 600;
            letter-spacing: 0.04em;
          }
          .vc-badge.PASS { background: rgba(61, 220, 151, 0.16); color: #3ddc97; }
          .vc-badge.WARN { background: rgba(245, 185, 66, 0.16); color: #f5b942; }
          .vc-badge.FAIL, .vc-badge.SKIPPED { background: rgba(255, 93, 115, 0.16); color: #ff5d73; }
          .vc-panel {
            border: 1px solid #243049; border-radius: 0.8rem; padding: 0.9rem 1rem 0.4rem;
            background: rgba(12, 18, 32, 0.65); margin: 0.4rem 0 0.8rem;
          }
          div[data-testid="stMetric"] {
            background: #121a2b; border: 1px solid #243049; border-radius: 0.7rem;
            padding: 0.55rem 0.7rem;
          }
          @media (max-width: 1100px) {
            .vc-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def lke_status() -> tuple[str, str, str]:
    """Live when this process is a pod. Otherwise show the manifest contract."""
    import os

    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        namespace = "default"
        ns_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        if ns_file.is_file():
            namespace = ns_file.read_text(encoding="utf-8").strip() or namespace
        pod = os.environ.get("HOSTNAME", "pod")
        return "ok", "Running", f"{pod} · ns {namespace}"
    return "info", "Manifest ready", "LoadBalancer :80 → :8501 · secret app-env"


@st.cache_data(ttl=30, show_spinner=False)
def service_snapshot() -> dict[str, object]:
    tone, state, detail = lke_status()
    storage_ok, storage_detail = storage.health()
    database_ok, database_detail = db.health()
    inference_ok, inference_detail = inference_verifier.health()
    return {
        "lke": {"tone": tone, "state": state, "detail": detail},
        "storage": {"tone": "ok" if storage_ok else "bad", "state": "Connected" if storage_ok else "Unavailable", "detail": storage_detail},
        "database": {"tone": "ok" if database_ok else "bad", "state": "Connected" if database_ok else "Unavailable", "detail": database_detail},
        "inference": {"tone": "ok" if inference_ok else "bad", "state": "Reachable" if inference_ok else "Unavailable", "detail": inference_detail},
        "models": inference_verifier.model_names(),
        "inference_ok": inference_ok,
    }


def render_header() -> None:
    st.markdown(
        """
        <div class="vc-brand">
          <span class="vc-mark"></span>
          <div>
            <h1>VigilCloud</h1>
            <p>Multi-modal vendor risk and compliance intake for security and GRC teams.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _card(kicker: str, state: str, detail: str, tone: str) -> str:
    return (
        f'<div class="vc-card tone-{tone}">'
        f'<div class="vc-kicker">{html.escape(kicker)}</div>'
        f'<div class="vc-state">{html.escape(state)}</div>'
        f'<div class="vc-detail">{detail}</div>'
        f"</div>"
    )


def render_telemetry() -> None:
    snap = service_snapshot()
    models = snap["models"]
    model_detail = "<br>".join(
        html.escape(f"{label} · {models[key]}")
        for label, key in (("Chat", "chat"), ("Vision", "vision"), ("Embed", "embedding"))
    )
    cards = [
        _card("Akamai LKE", snap["lke"]["state"], html.escape(snap["lke"]["detail"]), snap["lke"]["tone"]),
        _card("Object Storage", snap["storage"]["state"], html.escape(snap["storage"]["detail"]), snap["storage"]["tone"]),
        _card("PostgreSQL", snap["database"]["state"], html.escape(snap["database"]["detail"]), snap["database"]["tone"]),
        _card("Inference API", snap["inference"]["state"], html.escape(snap["inference"]["detail"]), snap["inference"]["tone"]),
        _card("Active models", "Bound", model_detail, "ok" if snap["inference_ok"] else "bad"),
    ]
    st.markdown(f'<div class="vc-strip">{"".join(cards)}</div>', unsafe_allow_html=True)
    settings = load_settings()
    left, right = st.columns([4, 1])
    with left:
        st.caption(
            f"Reading `{settings.inference_key_var}`, `{settings.inference_url_var}`, "
            f"`{settings.s3_bucket_var}`, `{settings.database_var}` · S3 region `{settings.s3_region}`"
        )
    with right:
        if st.button("Recheck services", width="stretch"):
            service_snapshot.clear()
            st.rerun()


def score_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "mid"
    return "low"


def badge(verdict: str) -> str:
    label = verdict if verdict in {"PASS", "WARN", "FAIL", "SKIPPED"} else "FAIL"
    return f'<span class="vc-badge {label}">{html.escape(label)}</span>'


def render_audit(view: dict[str, object]) -> None:
    settings = load_settings()
    st.markdown('<div class="vc-kicker">Output Verification Audit Panel</div>', unsafe_allow_html=True)
    with st.container(border=True):
        _render_audit_body(view, settings)


def _render_audit_body(view: dict[str, object], settings) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown(f"**1 · Schema and grounding** {badge(str(view['grounding_verdict']))}", unsafe_allow_html=True)
        st.caption("Deterministic. Pydantic checks the JSON, then each evidence quote is searched in the extracted text or vision summary.")
        if view["quote_checks"]:
            st.dataframe(
                [
                    {
                        "in_source": "yes" if item["grounded"] else "no",
                        "match": item["method"],
                        "quote": item["quote"],
                    }
                    for item in view["quote_checks"]
                ],
                hide_index=True,
                width="stretch",
            )
        for issue in view["grounding_issues"]:
            st.caption(issue)
        if view.get("raw_model_output") and view["grounding_blocking"]:
            with st.expander("Rejected model output"):
                st.code(str(view["raw_model_output"])[:4000])
    with right:
        critic_label = str(view["critic_verdict"])
        st.markdown(f"**2 · Second-pass critic** {badge(critic_label)}", unsafe_allow_html=True)
        if view.get("critic_ran"):
            st.caption(f"A separate `{settings.chat_model}` call. It checks the score against the gaps and looks for a critical omission.")
        else:
            st.caption("Skipped. The schema check did not produce an assessment the critic could judge.")
        st.write(view["critic_reason"])
    if view.get("saved"):
        st.success(
            f"Gate complete (grounding {view['grounding_verdict']}, critic {view['critic_verdict']}) "
            f"before PostgreSQL assessment {view['assessment_id']} was written."
        )
    elif view.get("grounding_blocking"):
        st.error("PostgreSQL write blocked. The schema check failed, so this assessment was not stored.")
    else:
        st.warning("Verification finished, but the row was not stored.")


def render_findings(view: dict[str, object]) -> None:
    score = view.get("risk_score")
    if not isinstance(score, int):
        return
    st.markdown(
        f'<div class="vc-score {score_band(score)}">{score}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Residual risk for {view['vendor_name']} · 0 is clean, 100 is critical")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grounding", str(view["grounding_verdict"]))
    c2.metric("Critic", str(view["critic_verdict"]))
    c3.metric("Evidence", view["source_kind"])
    st.markdown("**Encryption**")
    st.write(view["encryption_status"])
    st.markdown("**Access control**")
    st.write(view["access_control_summary"])
    gaps = view["compliance_gaps"] or ["None recorded"]
    steps = view["remediation_steps"] or ["None recorded"]
    gcol, scol = st.columns(2)
    with gcol:
        st.markdown("**Compliance gaps**")
        for gap in gaps:
            st.write(f"• {gap}")
    with scol:
        st.markdown("**Remediation**")
        for step in steps:
            st.write(f"• {step}")


def render_evidence(view: dict[str, object]) -> None:
    if view.get("presigned_url"):
        st.link_button("Open evidence in Object Storage", str(view["presigned_url"]))
    st.caption(
        f"s3://{view.get('bucket', '')}/{view.get('object_key', '')} · {view.get('object_bytes', 0)} bytes"
    )
    if view.get("vision_summary"):
        with st.expander("Vision summary", expanded=view.get("source_kind") == "image"):
            st.write(view["vision_summary"])
    excerpt = str(view.get("document_text") or "")
    if excerpt:
        with st.expander("Extracted text", expanded=False):
            st.text(excerpt[:6000])


def remember(view: dict[str, object]) -> None:
    st.session_state["intake"] = view


def run_pipeline(filename: str, data: bytes) -> None:
    finished = False
    with st.status(f"Assessing {filename}", expanded=True) as status:
        try:
            status.write("Uploading evidence to Object Storage")
            stored = storage.upload(filename, data)
            status.write(f"Stored `{stored['key']}` ({stored['bytes']} bytes)")
            packet: IntakePacket = inference_verifier.run_intake(
                filename, data, progress=lambda message: status.write(message)
            )
            public = packet.public()
            public.update(
                {
                    "bucket": stored["bucket"],
                    "object_key": stored["key"],
                    "object_bytes": stored["bytes"],
                    "presigned_url": stored["url"],
                    "source_filename": filename,
                    "saved": False,
                    "assessment_id": None,
                    "raw_model_output": packet.raw_model_output,
                }
            )
            if packet.schema_report.blocking or packet.extraction is None:
                status.update(label="Verification gate blocked the write", state="error")
                remember(public)
                service_snapshot.clear()
                finished = True
            else:
                status.write("Writing the verified assessment to PostgreSQL")
                assert packet.extraction is not None
                assessment_id = db.insert_assessment(
                    {
                        "vendor_name": packet.extraction.vendor_name,
                        "source_filename": filename,
                        "source_kind": packet.source_kind,
                        "object_key": stored["key"],
                        "document_text": packet.document_text,
                        "vision_summary": packet.vision_summary,
                        "profile_text": packet.profile_text,
                        "risk_score": packet.extraction.risk_score,
                        "encryption_status": packet.extraction.encryption_status,
                        "access_control_summary": packet.extraction.access_control_summary,
                        "compliance_gaps": list(packet.extraction.compliance_gaps),
                        "remediation_steps": list(packet.extraction.remediation_steps),
                        "evidence_quotes": list(packet.extraction.evidence_quotes),
                        "grounding_verdict": packet.schema_report.verdict,
                        "grounding_issues": packet.schema_report.issues,
                        "quote_checks": [item.__dict__ for item in packet.schema_report.quotes],
                        "critic_verdict": packet.critic_verdict,
                        "critic_reason": packet.critic_reason,
                        "embedding": packet.embedding,
                    },
                    packet.chunks,
                )
                public["saved"] = True
                public["assessment_id"] = assessment_id
                remember(public)
                service_snapshot.clear()
                status.update(label=f"Saved assessment {assessment_id}", state="complete")
                finished = True
        except IntakeError as exc:
            status.update(label="Intake stopped before the write", state="error")
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — keep the demo page up and name the failing stage
            status.update(label="Intake stopped before the write", state="error")
            st.error(f"Intake failed before the PostgreSQL write: {exc}")
    if finished:
        st.rerun()


def render_intake() -> None:
    st.subheader("Intake and verification")
    st.write("Upload a vendor PDF, note, or architecture diagram. Sample packets run the same path, including the Object Storage upload.")
    uploaded = st.file_uploader(
        "Vendor evidence",
        type=["pdf", "txt", "md", "png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )
    if st.button("Assess uploaded file", type="primary", disabled=uploaded is None, width="stretch"):
        run_pipeline(uploaded.name, uploaded.getvalue())
    st.caption("One-click samples")
    first, second = st.columns(2)
    for column, name in zip((first, second), SAMPLES):
        with column:
            if st.button(name, width="stretch"):
                path = SAMPLES[name]
                run_pipeline(path.name, path.read_bytes())
    view = st.session_state.get("intake")
    if not view:
        return
    st.divider()
    render_evidence(view)
    render_audit(view)
    render_findings(view)


def render_registry() -> None:
    st.subheader("PostgreSQL registry")
    st.write("Structured findings stay here after a restart. The slider is a cross-vendor query, not a filter in the browser.")
    try:
        min_score = st.slider("Minimum risk score", 0, 100, 0)
        rows = db.list_assessments(min_score)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not read PostgreSQL: {exc}")
        return
    with st.expander("Query running now"):
        st.code(db.CROSS_VENDOR_SQL.strip(), language="sql")
        st.caption("Embeddings are vector(4096). pgvector indexes stop at 2,000 dimensions, so semantic search is an exact cosine scan.")
    if not rows:
        st.info("No assessments at this threshold yet. Run a sample on the left.")
        return
    table = [
        {
            "id": row["id"],
            "vendor": row["vendor_name"],
            "risk_score": row["risk_score"],
            "grounding": row["grounding_verdict"],
            "critic": row["critic_verdict"],
            "encryption": row["encryption_status"][:72],
            "file": row["source_filename"],
            "stored": row["created_at"].strftime("%m-%d %H:%M"),
        }
        for row in rows
    ]
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={"risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%d")},
    )
    spread = db.vendor_spread()
    if spread:
        st.caption("Latest score by vendor")
        st.dataframe(
            [
                {
                    "vendor": item["vendor_name"],
                    "assessments": item["assessments"],
                    "lowest": item["lowest"],
                    "highest": item["highest"],
                    "latest": item["latest"],
                }
                for item in spread
            ],
            hide_index=True,
            width="stretch",
        )
    labels = {f"{row['id']} · {row['vendor_name']} · {row['risk_score']}": row["id"] for row in rows}
    selected = st.selectbox("Inspect a record", list(labels))
    record = db.get_assessment(labels[selected])
    if record is None:
        return
    st.write(record["profile_text"])
    if record.get("object_key"):
        try:
            st.link_button("Pre-signed evidence link", storage.presign(record["object_key"]))
        except Exception as exc:  # noqa: BLE001
            st.caption(f"Object key `{record['object_key']}` · link unavailable ({exc})")
    with st.expander("Stored gaps, remediation, and critic"):
        st.write({"gaps": record["compliance_gaps"], "remediation": record["remediation_steps"], "critic": record["critic_reason"]})
    remove, refresh = st.columns(2)
    with remove:
        if st.button("Delete selected", width="stretch"):
            db.delete_assessment(record["id"])
            service_snapshot.clear()
            st.rerun()
    with refresh:
        if st.button("Refresh registry", width="stretch"):
            service_snapshot.clear()
            st.rerun()


def render_qa() -> None:
    st.subheader("Cross-vendor Q&A")
    st.write("The question is embedded, nearest vendor profiles and evidence chunks are retrieved, and the chat model answers only from those rows.")
    if "question" not in st.session_state:
        st.session_state["question"] = QUESTIONS[0]
    for question in QUESTIONS:
        if st.button(question, key=f"q-{question}", width="stretch"):
            st.session_state["question"] = question
            st.session_state["ask_now"] = True
    question = st.text_input("Ask the registry", key="question")
    ask = st.button("Ask", type="primary") or st.session_state.pop("ask_now", False)
    if not ask:
        return
    if not question.strip():
        st.warning("Enter a question.")
        return
    try:
        with st.spinner("Retrieving similar assessments"):
            vector = inference_verifier.embed_query(question)
            hits = inference_verifier.diversify(db.semantic_search(vector, limit=8), limit=5)
            answer = inference_verifier.answer_question(question, hits)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return
    st.write(answer)
    if hits:
        st.dataframe(
            [
                {
                    "vendor": hit["vendor_name"],
                    "risk": hit["risk_score"],
                    "kind": hit["kind"],
                    "similarity": f"{hit['similarity']:.0%}",
                    "snippet": str(hit["snippet"])[:180],
                }
                for hit in hits
            ],
            hide_index=True,
            width="stretch",
        )


def render_about() -> None:
    with st.expander("Demo notes for reviewers"):
        st.markdown(
            """
            **User and task.** A security or GRC reviewer qualifies a third-party vendor from a questionnaire, PDF, or architecture diagram.

            **Services.** LKE runs this container behind a LoadBalancer (`k8s/deployment.yaml`, port 80 to 8501, `envFrom` secret `app-env`). Object Storage keeps the original evidence private and hands out a one-hour link. Managed PostgreSQL keeps the score, gaps, verification verdicts, and 4,096-dimension chunk embeddings.

            **Inference.** `CHAT_MODEL` extracts the risk JSON and later answers cross-vendor questions. `VISION_MODEL` reads diagrams. `EMBEDDING_MODEL` retrieves similar vendors. The audit panel shows a deterministic grounding check and a second critic call before the row is inserted.

            **Known limit.** Scanned PDFs with no text layer need an image upload. Semantic search scans every embedding because a 4,096-dimension vector cannot use a pgvector index.
            """
        )


def main() -> None:
    st.set_page_config(page_title="VigilCloud", page_icon="◈", layout="wide")
    inject_css()
    render_header()
    render_telemetry()
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        render_intake()
    with right:
        render_registry()
        st.divider()
        render_qa()
    render_about()


if __name__ == "__main__":
    main()
