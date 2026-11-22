# Vendor Security Questionnaire Responses — NorthStar Data Pulse

- **Q1 (Encryption in Transit):** "All network traffic, including internal service-to-service traffic, is encrypted in transit."
  *(Note in packet: Only TLS 1.2/1.3 on public API/web traffic is mentioned; internal service-to-service encryption is not specified.)*

- **Q2 (Encryption at Rest):** "All customer data at rest is encrypted."
  *(Note in packet: Primary DB volumes are encrypted at rest; `nsp-nightly-staging-us` mentions lifecycle and versioning, but encryption status on that bucket is not explicitly stated.)*

- **Q3 (Privileged Access & Support):** "Access to customer environments and diagnostic data is strictly controlled and audited."
  *(Note in packet: Full-time staff use SSO/MFA, but 24-hour diagnostic tokens log to application stdout rather than a dedicated immutable audit trail, and CI/CD uses long-lived/unspecified rotation cadence.)*

- **Q4 (Independent Assurance):** "We maintain current independent security assurance."
  *(Note in packet: SOC 2 Type I is 11 months old; SOC 2 Type II is only 4 months into its observation period; pentest predates v1.8 and the multi-tenant webhook release.)*

- **Q5 (Subprocessors & Data Residency):** "All subprocessors and data residency regions are documented."
  *(Not addressed in the uploaded packet—no subprocessor list or region residency table is present.)*