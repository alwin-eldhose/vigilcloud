# NorthStar Data Pulse — Security & Architecture Evidence Packet (v2.1)

## 1. System Overview & Data Scope
NorthStar Data Pulse ingests customer support tickets, product telemetry, and webhook events from client systems and publishes aggregated analytics dashboards via a REST API and web portal.
- Supported customer data fields may include support ticket text, user IDs, email addresses, and account metadata.
- Ingestion workers run on containerized compute nodes; batch reporting jobs run nightly.

## 2. Encryption & Key Management
- Public API endpoints and customer web traffic terminate TLS 1.2 or TLS 1.3.
- Primary transactional database volumes use storage-level encryption at rest.
- Nightly analytics staging exports are written to an internal bucket (`nsp-nightly-staging-us`) for transformation before warehouse loading. Lifecycle policy is set to 14 days; bucket versioning is enabled.
- Cryptographic key rotation policy is documented as "annual or upon security incident."

## 3. Identity, Access & Secrets
- Production cloud console access requires SSO and MFA for full-time engineering staff.
- CI/CD pipelines deploy containers using service credentials stored in GitHub Actions secrets.
- For rapid customer onboarding and tier-1 support debugging, on-call engineers can generate temporary read-only diagnostic tokens valid for 24 hours; token issuance is logged to application stdout.

## 4. Logging, Monitoring & Assurance
- Application logs and API access logs are shipped to a central log aggregator with a 90-day hot search window.
- NorthStar completed a SOC 2 Type I attestation 11 months ago covering the core web and ingestion platform. A SOC 2 Type II observation window began 4 months ago; no Type II report has been issued yet.
- Penetration testing was last performed on the v1.8 web portal prior to the multi-tenant webhook ingestion release.