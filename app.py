"""VigilCloud: TPRM evidence and control triage workbench.

A contracting or GRC reviewer checks vendor evidence against questionnaire claims. Claude
drafts a finding per claim. The gate checks the quotes and coverage in code, and a second
Claude call critiques the statuses. The human reviewer approves or overrides each finding
before the decision is final.

    uv sync
    uv run streamlit run app.py
"""

from __future__ import annotations

import html
import re
import time
from itertools import zip_longest
from pathlib import Path

import streamlit as st

import db
import inference_verifier
import storage
from inference_verifier import (
    CONTRADICTION,
    DEFAULT_CHECKLIST,
    INSUFFICIENT,
    PARTIAL,
    STATUSES,
    SUPPORTED,
    TIERS,
    IntakeError,
    IntakePacket,
    claims_from_file,
    parse_claims,
    risk_tier,
)
from sample_catalog import SAMPLES
from settings import load_settings

QUESTIONS = [
    "Which vendors have a contradiction risk on encryption?",
    "Which vendors have insufficient evidence on data residency?",
    "What should a reviewer check first for the subtle discrepancy vendor?",
]

STATUS_CLASS = {
    SUPPORTED: "supported",
    PARTIAL: "partial",
    CONTRADICTION: "contradiction",
    INSUFFICIENT: "insufficient",
}

STATUS_HELP = {
    SUPPORTED: "A quote from the evidence proves the questionnaire response.",
    PARTIAL: "The evidence proves only part of the questionnaire response, or the wording is vague.",
    CONTRADICTION: "The vendor's own evidence conflicts with the questionnaire response.",
    INSUFFICIENT: "The evidence does not prove the questionnaire response. Absence of proof is not treated as compliance.",
}


def inject_css() -> None:
    """Palette from the Identity Digital brand guide: teal, black, and white, with light tints.

    Colored fills always carry black text. Arial is the guide's system fallback for Nimbus Sans.
    """
    st.markdown(
        """
        <style>
          html, body, [class*="css"], .stApp { font-family: "Nimbus Sans", Arial, Helvetica, sans-serif; }
          .stApp { background: #ffffff; color: #111921; }
          .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1480px; }
          header[data-testid="stHeader"] { background: transparent; }
          [data-testid="stSidebar"] { display: none; }
          h1, h2, h3, h4 { letter-spacing: -0.01em; color: #111921; font-weight: 400; }
          h2 a, h3 a, h4 a { display: none; }
          .vc-brand { display: flex; gap: 1rem; align-items: center; margin-bottom: 0.4rem; }
          .vc-mark { width: 2.5rem; height: 2.5rem; border-radius: 0.6rem; background: #006271; }
          .vc-brand h1 { margin: 0; font-size: 2rem; line-height: 1; font-weight: 300; color: #111921; }
          .vc-brand p { margin: 0.35rem 0 0; color: #4a5560; font-size: 1rem; }
          .vc-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; padding-top: 0.2rem; }
          .vc-chip {
            display: inline-flex; align-items: center; gap: 0.45rem; border: 1px solid #c7c7c7;
            background: #ffffff; border-radius: 999px; padding: 0.3rem 0.85rem;
            color: #111921; font-size: 0.85rem;
          }
          .vc-chip i { width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; background: #939393; }
          .vc-chip.ok i { background: #006271; }
          .vc-chip.info i { background: #0055b8; }
          .vc-chip.bad i { background: #e64b38; }
          .vc-chip b { font-weight: 700; }
          .vc-kicker { color: #4a5560; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; }
          .vc-detail { color: #4a5560; font-size: 0.82rem; line-height: 1.45; }
          .vc-step { color: #006271; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; }
          .vc-howto {
            border-left: 4px solid #006271; border-radius: 0.3rem; padding: 0.85rem 1.1rem;
            background: #f0f0f0; margin: 0.4rem 0 1.1rem; color: #111921; line-height: 1.5;
          }
          .vc-draft-label {
            display: inline-block; background: #ffc8c1; color: #111921; border-radius: 0.3rem;
            padding: 0.2rem 0.6rem; font-size: 0.8rem; font-weight: 700;
          }
          .vc-tier { font-size: 2.2rem; font-weight: 700; line-height: 1; }
          .vc-tier.LOW { color: #006271; }
          .vc-tier.MEDIUM { color: #0055b8; }
          .vc-tier.HIGH, .vc-tier.CRITICAL { color: #e64b38; }
          .vc-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 0.4rem 0 0.8rem; }
          .vc-table th {
            text-align: left; color: #4a5560; font-weight: 700; font-size: 0.75rem;
            text-transform: uppercase; letter-spacing: 0.06em; padding: 0.5rem 0.7rem;
            border-bottom: 2px solid #111921;
          }
          .vc-table td { vertical-align: top; padding: 0.7rem; border-bottom: 1px solid #c7c7c7; color: #111921; text-align: left; }
          .vc-table td.gap { border-left: 4px solid #e64b38; background: #fff4f2; width: 48%; }
          .vc-table td.fix { border-left: 4px solid #006271; background: #eef8f8; width: 48%; }
          .vc-table td.arrow { color: #4a5560; text-align: center; width: 4%; }
          .vc-pill {
            display: inline-flex; align-items: center; gap: 0.4rem; border-radius: 999px; padding: 0.15rem 0.65rem 0.15rem 0.5rem;
            font-size: 0.75rem; font-weight: 700; white-space: nowrap; color: #111921;
          }
          .vc-pill::before { content: ""; width: 0.55rem; height: 0.55rem; border-radius: 50%; display: inline-block; background: #111921; }
          .vc-pill.supported, .vc-pill.PASS { background: #afe2e3; }
          .vc-pill.supported::before, .vc-pill.PASS::before { background: #006271; }
          .vc-pill.partial, .vc-pill.WARN { background: #99cef4; }
          .vc-pill.partial::before, .vc-pill.WARN::before { background: #0055b8; }
          .vc-pill.contradiction, .vc-pill.FAIL, .vc-pill.SKIPPED { background: #ffc8c1; }
          .vc-pill.contradiction::before, .vc-pill.FAIL::before, .vc-pill.SKIPPED::before { background: #e64b38; }
          .vc-pill.insufficient { background: #ffd3f8; }
          .vc-pill.insufficient::before { background: #e17fd2; }
          .vc-muted { color: #4a5560; font-size: 0.8rem; }
          .vc-quote { color: #111921; font-style: italic; }
          div[data-testid="stMetric"] { background: #f0f0f0; border-radius: 0.5rem; padding: 0.55rem 0.7rem; }
          button[data-baseweb="tab"] { font-size: 1.02rem; font-weight: 700; }
          div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #c7c7c7; border-radius: 0.5rem; }
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
    }


def render_header() -> None:
    st.markdown(
        """
        <div class="vc-brand">
          <span class="vc-mark"></span>
          <div>
            <h1>VigilCloud</h1>
            <p>Check a vendor's evidence against their questionnaire response. Claude drafts the findings, and you sign off.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_strip() -> None:
    snap = service_snapshot()
    services = (
        ("Akamai LKE", snap["lke"]),
        ("Object Storage", snap["storage"]),
        ("PostgreSQL", snap["database"]),
        ("Claude API", snap["inference"]),
    )
    chips = "".join(
        f'<span class="vc-chip {item["tone"]}"><i></i>{html.escape(name)} <b>{html.escape(item["state"])}</b></span>'
        for name, item in services
    )
    left, middle, right = st.columns([6, 1.3, 1.3], vertical_alignment="center")
    with left:
        st.markdown(f'<div class="vc-chips">{chips}</div>', unsafe_allow_html=True)
    with middle:
        show = st.toggle("Show details", key="show_details")
    with right:
        if st.button("Recheck", width="stretch", help="Run the live service checks again."):
            service_snapshot.clear()
            st.rerun()
    if show:
        settings = load_settings()
        models = snap["models"]
        columns = st.columns(4)
        for column, (name, item) in zip(columns, services):
            with column:
                st.markdown(f'<div class="vc-kicker">{html.escape(name)}</div><div class="vc-detail">{html.escape(item["detail"])}</div>', unsafe_allow_html=True)
        st.caption(
            f"Chat model `{models['chat']}` · Vision model `{models['vision']}` · "
            f"reading `{settings.anthropic_key_var}`, `{settings.s3_bucket_var}`, `{settings.database_var}` · S3 region `{settings.s3_region}`"
        )


def status_pill(status: str) -> str:
    cls = STATUS_CLASS.get(status, "insufficient")
    return f'<span class="vc-pill {cls}">{html.escape(status)}</span>'


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if part.strip()]


def gap_table(gaps: list[str], steps: list[str]) -> str:
    if not gaps and not steps:
        return '<div class="vc-muted">No gaps were recorded.</div>'
    rows = "".join(
        f'<tr><td class="gap">{html.escape(gap or "")}</td><td class="arrow">→</td><td class="fix">{html.escape(step or "")}</td></tr>'
        for gap, step in zip_longest(gaps, steps, fillvalue="")
    )
    return (
        '<table class="vc-table"><thead><tr><th>Key gap or contradiction</th><th></th><th>Draft remediation</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )


def render_draft_triage(view: dict[str, object]) -> None:
    tier = str(view.get("risk_tier") or risk_tier(int(view.get("risk_score") or 0)))
    st.markdown('<span class="vc-draft-label">Draft Triage Assistance — Requires Human TPRM Sign-Off</span>', unsafe_allow_html=True)
    left, right = st.columns([1, 5])
    with left:
        st.markdown(f'<div class="vc-tier {tier}">{tier}</div>', unsafe_allow_html=True)
        st.caption(f"Suggested tier · draft score {view.get('risk_score')} / 100")
    with right:
        points = sentences(str(view.get("draft_summary") or ""))
        if points:
            st.markdown("\n".join(f"- {point}" for point in points))
        else:
            st.write("No summary returned.")
    st.markdown(gap_table(list(view.get("compliance_gaps") or []), list(view.get("remediation_steps") or [])), unsafe_allow_html=True)


def findings_table(findings: list[dict[str, object]]) -> str:
    rows = []
    for item in findings:
        effective = str(item.get("reviewer_status") or item.get("status"))
        gate_note = ""
        if item.get("gate_note"):
            gate_note = f'<div class="vc-muted">{html.escape(str(item["gate_note"]))}</div>'
        if item.get("reviewer_status") and item.get("reviewer_status") != item.get("status"):
            gate_note += f'<div class="vc-muted">Reviewer override from {html.escape(str(item["status"]))}</div>'
        quote = item.get("evidence_quote") or ""
        quote_cell = (
            f'<div class="vc-quote">“{html.escape(str(quote))}”</div>'
            f'<div class="vc-muted">match: {html.escape(str(item.get("quote_check") or "n/a"))}</div>'
            if quote else '<div class="vc-muted">No quote. Not proven by the evidence.</div>'
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('finding_order')))}</td>"
            f"<td>{html.escape(str(item.get('claim_or_control')))}</td>"
            f"<td>{status_pill(effective)}{gate_note}</td>"
            f"<td>{quote_cell}</td>"
            f"<td>{html.escape(str(item.get('analyst_check_needed')))}</td>"
            "</tr>"
        )
    return (
        '<table class="vc-table"><thead><tr>'
        "<th>#</th><th>Questionnaire response or control</th><th>Status</th><th>Evidence quote</th><th>Analyst check needed</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_audit(view: dict[str, object]) -> None:
    settings = load_settings()
    st.markdown('<div class="vc-kicker">Output verification audit</div>', unsafe_allow_html=True)
    with st.container(border=True):
        left, right = st.columns(2)
        with left:
            st.markdown(
                f"**1 · Quote and coverage check** <span class='vc-pill {view['grounding_verdict']}'>{view['grounding_verdict']}</span>",
                unsafe_allow_html=True,
            )
            st.caption("Done in code, not by the model. A quote that is not in the source downgrades the finding to INSUFFICIENT_EVIDENCE. A questionnaire response with no finding is marked insufficient.")
            for issue in view.get("grounding_issues", []):
                st.caption(issue)
            downgraded = [item for item in view.get("findings", []) if str(item.get("gate_note", "")).startswith("Downgraded")]
            for item in downgraded:
                st.write(f"• {item['claim_or_control']}: {item['gate_note']}")
        with right:
            critic = str(view.get("critic_verdict"))
            st.markdown(
                f"**2 · Second-pass critic** <span class='vc-pill {critic}'>{critic}</span>",
                unsafe_allow_html=True,
            )
            if view.get("critic_ran"):
                st.caption(f"A separate `{settings.chat_model}` call checks that each status matches its quote and does not overstate certainty.")
            else:
                st.caption("The critic did not return a verdict, so only the code checks apply.")
            st.write(view.get("critic_reason") or "")
        if view.get("saved"):
            st.success(f"Saved as PostgreSQL assessment {view['assessment_id']}. The findings are ready for reviewer sign-off below.")
        elif view.get("grounding_blocking"):
            st.error("Not saved. The output did not match the findings schema.")


def render_review(scope: str, assessment_id: int, draft_tier: str, record: dict[str, object] | None, findings: list[dict[str, object]]) -> None:
    st.markdown("#### Human reviewer sign-off")
    st.caption("You make the final call. Change a status if you disagree, set the final tier, then save. Your change is stored next to the draft status, which is kept.")
    if not findings:
        st.caption("No findings are stored for this record.")
        return
    current_tier = str((record or {}).get("reviewer_tier") or draft_tier)
    # One row per response, laid out with columns so long text wraps and nothing is cut off.
    widths = [0.4, 3.2, 2.2, 2.4, 3.6]
    header = st.columns(widths, vertical_alignment="bottom")
    for cell, label in zip(header, ["#", "Questionnaire response or control", "Draft status", "Your status", "Analyst check needed"]):
        cell.markdown(f'<div class="vc-kicker">{label}</div>', unsafe_allow_html=True)
    chosen_status: dict[int, str] = {}
    for item in findings:
        number, response, draft, yours, check = st.columns(widths, vertical_alignment="center")
        number.write(str(item["finding_order"]))
        response.write(str(item["claim_or_control"]))
        draft.markdown(status_pill(str(item["status"])), unsafe_allow_html=True)
        start = str(item["reviewer_status"] or item["status"])
        chosen_status[int(item["id"])] = yours.selectbox(
            f"Your status for response {item['finding_order']}",
            list(STATUSES),
            index=list(STATUSES).index(start) if start in STATUSES else 0,
            key=f"status-{scope}-{assessment_id}-{item['id']}",
            label_visibility="collapsed",
        )
        check.write(str(item["analyst_check_needed"]))
        st.markdown('<hr style="margin:0.15rem 0; border:0; border-top:1px solid #C7C7C7">', unsafe_allow_html=True)
    left, right = st.columns([1, 3])
    with left:
        tier = st.selectbox("Final risk tier", TIERS, index=TIERS.index(current_tier), key=f"tier-{scope}-{assessment_id}")
        approve = st.checkbox("I approve this draft", key=f"approve-{scope}-{assessment_id}", help="Tick this when you agree with the findings and tier as drafted.")
    with right:
        note = st.text_area("Reviewer note", value=str((record or {}).get("reviewer_note") or ""), key=f"note-{scope}-{assessment_id}", height=100)
    if st.button("Save review decision", key=f"save-{scope}-{assessment_id}", type="primary"):
        overrides: dict[int, str | None] = {}
        changed_from_draft = False
        for item in findings:
            chosen = str(chosen_status.get(int(item["id"])) or item["status"])
            previous = str(item["reviewer_status"] or item["status"])
            if chosen != item["status"]:
                changed_from_draft = True
            if chosen != previous:
                overrides[int(item["id"])] = None if chosen == item["status"] else chosen
        if changed_from_draft or tier != draft_tier:
            decision = "OVERRIDDEN"
        elif approve:
            decision = "APPROVED"
        else:
            decision = "PENDING"
        db.save_review(assessment_id, decision, tier, note, overrides)
        service_snapshot.clear()
        st.rerun()
    if record and record.get("review_decision"):
        when = f" · {record['reviewed_at']:%Y-%m-%d %H:%M}" if record.get("reviewed_at") else ""
        st.caption(f"Saved decision: **{record['review_decision']}**{when}")


def remember(view: dict[str, object]) -> None:
    st.session_state["intake"] = view


def run_pipeline(filename: str, data: bytes, claims: list[str]) -> None:
    finished = False
    started = time.monotonic()

    def say(status, message: str) -> None:
        status.write(f"`{time.monotonic() - started:4.0f}s`  {message}")

    with st.status(f"Reviewing {filename}", expanded=True) as status:
        try:
            say(status, "Uploading the evidence to Akamai Object Storage")
            stored = storage.upload(filename, data)
            say(status, f"Stored privately as `{stored['key']}` ({stored['bytes']} bytes)")
            packet: IntakePacket = inference_verifier.run_intake(
                filename, data, claims or None, progress=lambda message: say(status, message)
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
                status.update(label="Output rejected before the write", state="error")
                remember(public)
                service_snapshot.clear()
                finished = True
            else:
                say(status, "Saving the findings and draft to Akamai Managed PostgreSQL")
                extraction = packet.extraction
                record = {
                    "vendor_name": extraction.vendor_name,
                    "source_filename": filename,
                    "source_kind": packet.source_kind,
                    "object_key": stored["key"],
                    "document_text": packet.document_text,
                    "vision_summary": packet.vision_summary,
                    "profile_text": packet.profile_text,
                    "risk_score": extraction.risk_score,
                    "encryption_status": extraction.encryption_status,
                    "access_control_summary": extraction.access_control_summary,
                    "compliance_gaps": list(extraction.compliance_gaps),
                    "remediation_steps": list(extraction.remediation_steps),
                    "evidence_quotes": [item.evidence_quote for item in packet.findings if item.evidence_quote],
                    "grounding_verdict": packet.schema_report.verdict,
                    "grounding_issues": packet.schema_report.issues,
                    "quote_checks": public["quote_checks"],
                    "critic_verdict": packet.critic_verdict,
                    "critic_reason": packet.critic_reason,
                    "questionnaire_text": "" if packet.checklist_used else "\n".join(packet.claims),
                    "draft_summary": extraction.draft_summary,
                }
                findings_rows = [
                    {
                        "finding_order": item.finding_order,
                        "claim_or_control": item.claim_or_control,
                        "status": item.status,
                        "model_status": item.model_status,
                        "evidence_quote": item.evidence_quote,
                        "quote_check": item.quote_check,
                        "analyst_check_needed": item.analyst_check_needed,
                        "gate_note": item.gate_note,
                    }
                    for item in packet.findings
                ]
                assessment_id = db.insert_assessment(record, findings_rows, packet.chunks)
                public["saved"] = True
                public["assessment_id"] = assessment_id
                remember(public)
                service_snapshot.clear()
                status.update(label=f"Saved assessment {assessment_id} in {time.monotonic() - started:.0f}s", state="complete")
                finished = True
        except IntakeError as exc:
            status.update(label="Review stopped before the write", state="error")
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — keep the page up and name the failing stage
            status.update(label="Review stopped before the write", state="error")
            st.error(f"Review failed before the PostgreSQL write: {exc}")
    if finished:
        st.rerun()


def resolve_claims(claims_file, pasted: str) -> tuple[list[str], str, str | None]:
    """Questionnaire file first, then pasted claims, then the default checklist."""
    if claims_file is not None:
        try:
            claims = claims_from_file(claims_file.name, claims_file.getvalue())
        except IntakeError as exc:
            return [], "", str(exc)
        return claims, f"{len(claims)} answers from {claims_file.name}", None
    claims = parse_claims(pasted)
    if claims:
        return claims, f"{len(claims)} pasted answers", None
    return [], f"the standard {len(DEFAULT_CHECKLIST)}-control checklist", None


def render_review_tab() -> None:
    st.markdown(
        '<div class="vc-howto"><b>How this works.</b> Give the app the vendor\'s evidence and their questionnaire response. '
        "Claude checks each answer against the evidence and drafts a verdict with a quote. "
        "Code then confirms every quote is really in the document. <b>Nothing is final until you sign off.</b></div>",
        unsafe_allow_html=True,
    )
    one, two, three = st.columns(3, gap="large")
    with one:
        with st.container(border=True):
            st.markdown('<span class="vc-step">STEP 1 · REQUIRED</span>', unsafe_allow_html=True)
            st.markdown("**Add the vendor's evidence**")
            st.caption("The vendor's own document that should prove the questionnaire response: a security packet, policy, or an architecture diagram.")
            evidence = st.file_uploader(
                "Vendor evidence",
                type=["pdf", "docx", "txt", "md", "png", "jpg", "jpeg", "webp"],
                label_visibility="collapsed",
                key="evidence_file",
            )
            st.caption("PDF, Word, text, or image")
    with two:
        with st.container(border=True):
            st.markdown('<span class="vc-step">STEP 2 · OPTIONAL</span>', unsafe_allow_html=True)
            st.markdown("**Add the questionnaire response**")
            st.caption("The answers the vendor sent back. Skip this to use our standard control checklist instead.")
            claims_file = st.file_uploader(
                "Questionnaire file",
                type=["docx", "pdf", "txt", "md"],
                label_visibility="collapsed",
                key="claims_file",
            )
            with st.expander("Or paste the questionnaire response, one answer per line"):
                pasted = st.text_area(
                    "Pasted questionnaire response",
                    key="questionnaire",
                    height=130,
                    label_visibility="collapsed",
                    placeholder="All customer data is encrypted at rest.\nMulti-factor authentication is enforced for production access.",
                )
    claims, source_label, claims_error = resolve_claims(claims_file, pasted)
    with three:
        with st.container(border=True):
            st.markdown('<span class="vc-step">STEP 3</span>', unsafe_allow_html=True)
            st.markdown("**Run the review**")
            if claims_error:
                st.error(claims_error)
            else:
                st.caption(f"Checking: **{source_label}**.")
            clicked = st.button(
                "Review this evidence",
                type="primary",
                disabled=evidence is None or bool(claims_error),
                width="stretch",
            )
            if evidence is None:
                st.caption("Add evidence in step 1 to enable this button.")
            else:
                st.caption("Takes about 10 to 20 seconds.")
            with st.expander("See the questionnaire responses that will be checked"):
                for number, claim in enumerate(claims or DEFAULT_CHECKLIST, start=1):
                    st.write(f"{number}. {claim}")
    if clicked and evidence is not None:
        run_pipeline(evidence.name, evidence.getvalue(), claims)

    st.markdown('<div class="vc-kicker" style="margin-top:0.6rem">No files handy? Try a ready-made packet</div>', unsafe_allow_html=True)
    sample_columns = st.columns(len(SAMPLES), gap="large")
    for column, (key, sample) in zip(sample_columns, SAMPLES.items()):
        with column:
            if st.button(sample["label"], key=f"sample-{key}", width="stretch"):
                path: Path = sample["path"]
                run_pipeline(path.name, path.read_bytes(), parse_claims(sample["claims"]))
            st.caption(sample["blurb"])

    view = st.session_state.get("intake")
    if not view:
        return
    st.divider()
    if view.get("saved") and view.get("assessment_id"):
        assessment_id = int(view["assessment_id"])
        record = db.get_assessment(assessment_id)
        findings = db.get_findings(assessment_id)
        view = {**view, "findings": findings}
        st.subheader(f"{view.get('vendor_name') or 'Vendor'} · draft triage")
        render_draft_triage(view)
        st.subheader("Here is each questionnaire response, checked against the evidence.")
        st.caption("  ·  ".join(f"{name}: {STATUS_HELP[name]}" for name in STATUSES))
        st.markdown(findings_table(findings), unsafe_allow_html=True)
        st.write("")
        render_audit(view)
        link_col, text_col = st.columns([1, 3], vertical_alignment="center")
        with link_col:
            if view.get("presigned_url"):
                st.link_button("Open the stored evidence", str(view["presigned_url"]), width="stretch")
        with text_col:
            st.caption(f"Stored privately in Akamai Object Storage as s3://{view.get('bucket', '')}/{view.get('object_key', '')} · the link works for one hour.")
        with st.expander("Text Claude read from the evidence"):
            if view.get("vision_summary"):
                st.write(view["vision_summary"])
            st.text(str(view.get("document_text") or "")[:6000])
        render_review("intake", assessment_id, str(view.get("risk_tier") or "LOW"), record, findings)
    else:
        st.subheader("The review did not finish.")
        render_audit(view)


def render_registry_tab() -> None:
    st.write("Every review is saved in Akamai Managed PostgreSQL with its findings, the reviewer's decision, and a link to the original file.")
    try:
        rows = db.list_assessments()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not read PostgreSQL: {exc}")
        return
    with st.expander("Show the query behind this table"):
        st.code(db.CROSS_VENDOR_SQL.strip(), language="sql")
    if not rows:
        st.info("Nothing is saved yet. Run a review in the Evidence review tab.")
        return
    table = [
        {
            "id": row["id"],
            "Vendor": row["vendor_name"],
            "Tier": row["reviewer_tier"] or risk_tier(row["risk_score"]),
            "Draft score": row["risk_score"],
            "Review": row["review_decision"],
            "Contradictions": row["contradictions"],
            "Insufficient evidence": row["insufficient"],
            "File": row["source_filename"],
            "Saved": row["created_at"].strftime("%m-%d %H:%M"),
        }
        for row in rows
    ]
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={"Draft score": st.column_config.ProgressColumn("Draft score", min_value=0, max_value=100, format="%d")},
    )
    labels = {f"{row['id']} · {row['vendor_name']} · {row['source_filename']}": row["id"] for row in rows}
    selected = st.selectbox("Open a saved review", list(labels))
    record = db.get_assessment(labels[selected])
    if record is None:
        return
    findings = db.get_findings(record["id"])
    draft_tier = risk_tier(record["risk_score"])
    st.subheader(f"{record['vendor_name']} · draft score {record['risk_score']} ({draft_tier})")
    points = sentences(record["draft_summary"] or record["profile_text"])
    st.markdown("\n".join(f"- {point}" for point in points))
    st.markdown(gap_table(list(record["compliance_gaps"]), list(record["remediation_steps"])), unsafe_allow_html=True)
    if findings:
        st.markdown(findings_table(findings), unsafe_allow_html=True)
    else:
        st.caption("This record was saved before findings existed, so it has no response-level view.")
    if record.get("object_key"):
        try:
            st.link_button("Open the stored evidence", storage.presign(record["object_key"]))
        except Exception as exc:  # noqa: BLE001
            st.caption(f"Object key `{record['object_key']}` · link unavailable ({exc})")
    render_review("registry", record["id"], draft_tier, record, findings)
    if st.button("Delete this saved review", key=f"delete-{record['id']}"):
        db.delete_assessment(record["id"])
        service_snapshot.clear()
        st.rerun()


def render_qa_tab() -> None:
    st.write("Ask a question across every saved review. Full-text search finds the matching findings and evidence passages, and Claude answers only from those. If the records do not contain the answer, it says so.")
    for question in QUESTIONS:
        if st.button(question, key=f"q-{question}"):
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
        with st.spinner("Searching the saved reviews"):
            hits = inference_verifier.diversify(db.fulltext_search(question, limit=8), limit=5)
            answer = inference_verifier.answer_question(question, hits)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return
    st.markdown("#### Answer")
    st.write(answer)
    if hits:
        st.markdown("#### Records the answer came from")
        st.dataframe(
            [
                {
                    "Vendor": hit["vendor_name"],
                    "Draft score": hit["risk_score"],
                    "Matched": hit["kind"],
                    "Match strength": round(hit["score"], 3),
                    "Text": str(hit["snippet"])[:220],
                }
                for hit in hits
            ],
            hide_index=True,
            width="stretch",
        )


def render_about() -> None:
    with st.expander("About this workbench"):
        st.markdown(
            """
            **Who it is for.** A contracting or GRC reviewer who has to decide whether a vendor can be trusted with customer data.

            **What Claude does.** Reads the evidence, drafts one finding per questionnaire response with a word-for-word quote and the next check a human should run, and writes the draft summary, gaps, and remediation. Images such as architecture diagrams are read by Claude's vision model.

            **What the code checks.** Every quote must appear in the source, or the finding is downgraded to INSUFFICIENT_EVIDENCE. Any response Claude skipped is marked insufficient. A second Claude call critiques the statuses.

            **What the human decides.** The reviewer can change any status, set the final tier, and approve. Decisions are saved in PostgreSQL with a note, next to the draft.

            **Services.** Akamai Object Storage keeps the evidence private, with one-hour links. Akamai Managed PostgreSQL keeps reviews, findings, and decisions, and powers the search. The container runs on Akamai LKE (`k8s/deployment.yaml`).

            **Known limits.** Search matches words, not meaning. Scanned PDFs without a text layer need an image upload. The draft tier is a suggestion until a reviewer signs off.
            """
        )


def main() -> None:
    st.set_page_config(page_title="VigilCloud", page_icon="◈", layout="wide")
    inject_css()
    render_header()
    render_status_strip()
    review_tab, registry_tab, qa_tab = st.tabs(["Evidence review", "PostgreSQL registry", "Cross-vendor Q&A"])
    with review_tab:
        render_review_tab()
    with registry_tab:
        render_registry_tab()
    with qa_tab:
        render_qa_tab()
    render_about()


if __name__ == "__main__":
    main()
