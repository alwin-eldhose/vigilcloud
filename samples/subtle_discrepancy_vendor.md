# Brightpath Reconciliation — Vendor Security Packet

Vendor name: Brightpath Reconciliation Ltd.
Product: Brightpath Ledger, automated payment reconciliation for finance teams
Packet date: 2026-10-30
Prepared by: Trust and Compliance

## 1. Company and data

Brightpath processes bank transaction files and invoice records for its customers. Records include payer names, account references, and invoice amounts.
Customer data is stored and processed only in our Frankfurt (EU) region.

## 2. Encryption

All customer data is encrypted at rest with AES-256.
All public API endpoints accept TLS 1.2 or newer.
The partner SFTP endpoint still accepts TLS 1.0 for legacy bank clients. We are scheduled to retire it in Q1 2027.

Architecture note (data flow): nightly analytics extracts are written to the staging bucket `bp-staging-extracts` for up to 30 days before they are deleted. The staging bucket uses default storage settings, and server-side encryption is not enabled on it.

## 3. Access control

Multi-factor authentication is enforced for every account with production access.
Access reviews are performed quarterly. The most recent review record in this packet is dated Q2 2025.
The nightly reconciliation job authenticates to the ledger database with a static API key. Service accounts are excluded from the MFA policy because they cannot complete an interactive prompt.

## 4. Subprocessors

All subprocessors are listed and approved. See Appendix B.

Appendix B lists four subprocessors: a cloud hosting provider, an email delivery service, a payment file gateway, and a support ticketing tool.
The architecture diagram also shows an "observability vendor" component that sends application traces off-platform. It is not named in Appendix B.

Support ticket attachments are replicated to our US-East region so the support team in Boston can follow up. This replication is not listed in the data residency statement in Section 1.

## 5. Logging and retention

Audit logs are retained for at least 12 months. The log retention setting is not described in this packet.

## 6. Testing and assurance

Penetration testing is performed at least annually. The last completed test date is [to be confirmed]. The report is available on request.

The incident response plan is tested at least annually. The most recent tabletop exercise in the records we attach was held in March 2024.

A current SOC 2 Type II report is available under NDA. The report period covers 1 January to 31 March 2025. A bridge letter for the period after that date is pending.
