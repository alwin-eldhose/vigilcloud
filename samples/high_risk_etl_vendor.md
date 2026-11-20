# Northline DataForge — Third-Party Security Response

Vendor name: Northline DataForge
Product: DataForge ETL for customer analytics
Review date: 2026-11-01
Respondent: Platform operations

## Data handled

DataForge copies customer emails, payment account tokens, and health-intake notes from the client's warehouse into Northline's processing account. Those fields are used to build a marketing extract.

## Encryption

Encryption at rest is not enabled. Production disks are standard SSD volumes, and the database files sit in plaintext.
Backups are written weekly to an object bucket named nl-prod-dumps. That bucket is public-read, and the backup files are not encrypted.
Several file transfers still use plain FTP. TLS is optional on the ingestion endpoint, and two nightly jobs authenticate with a long-lived password.

## Access control

Production database administration uses one shared admin password. The password is stored in a team Slack canvas.
MFA is not turned on for the production database or the cloud console.
Unnamed offshore contractors have standing access to the production database. Access reviews are not performed, and individual accounts are not issued.

## Logging, retention, and response

Audit logging was disabled to save cost. There is no record of who exported the marketing extract.
Customer data is kept indefinitely. There is no deletion workflow and no documented retention period.
There is no on-call rotation, and the incident response plan has never been tested.

## Compliance

Northline DataForge has no SOC 2 report and no ISO 27001 certificate. A penetration test has not been run.
Subprocessors are not listed in the contract. Contractors can query production tables directly.

## Data flow

The client warehouse sends files over plain FTP into a staging PostgreSQL database that stores records in plaintext. A nightly job then copies the extract to the public-read bucket nl-prod-dumps, where downstream tools download it without authentication.
