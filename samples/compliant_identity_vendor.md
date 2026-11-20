# HarborKey Identity — Third-Party Security Response

Vendor name: HarborKey Identity
Product: Workforce identity provider and customer SSO
Review date: 2026-10-18
Respondent: Trust office

## Data handled

HarborKey stores account identifiers, group memberships, and authentication events for this tenant. It does not store customer payment data or health information.

## Encryption

Data at rest is encrypted with AES-256 using a cloud KMS key. TLS 1.2 or newer is required on every public endpoint, and plaintext protocols are rejected.
Backups are encrypted with the same KMS key and stored in a private bucket that is not publicly readable.

## Access control

Every production login requires SSO plus a hardware-backed MFA device.
Access is role-based least privilege. Access reviews run every quarter, and unused accounts are removed within five business days.
SCIM deprovisioning disables a departed employee within 15 minutes.
No subprocessor has standing access to production. Support sessions are brokered, time-boxed to one hour, and written to the audit log.

## Logging, retention, and response

Authentication and admin logs are immutable. They are kept 30 days in hot storage and one year in cold storage.
A staffed on-call rotation follows a written incident plan. The plan was last exercised in August 2026.
Customer content for this tenant stays in us-west. Production data is not replicated outside that region.

## Compliance

HarborKey holds a current SOC 2 Type II report and an ISO 27001 certificate.
An independent penetration test runs annually. Critical findings are remediated within 14 days. The latest test had no open critical findings.

## Known gap

Customer-managed key rotation is set to 180 days. The client's standard asks for 90 days. HarborKey can switch this tenant to 90-day rotation on request, and no other exception is open.
