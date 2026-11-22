"""Built-in demo packets used by the one-click sample buttons."""

from __future__ import annotations

from settings import ROOT

SUBTLE_CLAIMS = """All customer data is encrypted at rest.
All public endpoints enforce TLS 1.2 or newer.
Multi-factor authentication is enforced for every account with production access.
Customer data is stored and processed only in the EU.
All subprocessors are listed and approved.
Penetration testing is performed at least annually.
Access reviews are performed quarterly.
Audit logs are retained for at least 12 months.
The incident response plan is tested at least annually.
A current SOC 2 Type II report is available."""

SAMPLES = {
    "high_risk": {
        "label": "High-risk vendor",
        "blurb": "Northline DataForge. Plain failures: no encryption, a shared admin password. Reviewed against the standard checklist.",
        "path": ROOT / "samples" / "high_risk_etl_vendor.pdf",
        "claims": "",
    },
    "clean": {
        "label": "Clean vendor",
        "blurb": "HarborKey Identity. Controls are proven, with one small gap. Reviewed against the standard checklist.",
        "path": ROOT / "samples" / "compliant_identity_vendor.pdf",
        "claims": "",
    },
    "subtle": {
        "label": "Subtle discrepancies",
        "blurb": "Brightpath Reconciliation. Ten questionnaire responses, several contradicted by the vendor's own packet.",
        "path": ROOT / "samples" / "subtle_discrepancy_vendor.pdf",
        "claims": SUBTLE_CLAIMS,
    },
}
