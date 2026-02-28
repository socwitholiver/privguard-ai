# PRIVGUARD AI Data Retention and Deletion Policy (MVP)

## Purpose
Define how long operational artifacts are retained and how cleanup is enforced.

## Default Retention (Configurable)

- Audit events: 90 days
- Uploaded/protected/key files in local runtime directories: 30 days

Configured in `config/system_config.yaml` under `retention`.

## Enforcement Mechanisms

- CLI: `python main.py retention-cleanup`
- Web (admin only): `POST /admin/retention-cleanup`

Cleanup includes:
- Deletion of old files in `uploads`, `outputs`, and `keys`
- Deletion of old rows in `audit_events` and `scan_events`

## Change Control

Retention periods may only be changed through reviewed pull requests and should
be documented with legal/compliance justification.
