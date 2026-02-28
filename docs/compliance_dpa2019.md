# PRIVGUARD AI - DPA 2019 Control Mapping (Sprint 1)

This document maps MVP controls to Kenya's Data Protection Act (2019) principles
for evidence-driven compliance reviews.

## Control Matrix

| DPA Principle | MVP Control | Evidence Artifact | Status |
|---|---|---|---|
| Data Minimization | Detection and redaction/masking of direct identifiers | `main.py`, `protection.py`, `reports/eval_redaction.json` | In progress |
| Purpose Limitation | Risk insights emphasize lawful and defined processing purpose | `classification.py` | In progress |
| Security Safeguards | Local encryption with Fernet keys, offline-only processing | `protection.py`, `README.md` | In progress |
| Accountability | Audit event logging for scan/protect/verify actions | `storage/audit_repo.py`, SQLite DB at `instance/privguard_audit.db` | Implemented |
| Accuracy | Detection KPI evaluation against ground truth | `evaluation/evaluate_detection.py`, `reports/eval_detection.json` | Implemented |
| Integrity/Confidentiality | Branch protection + CI checks + PR review workflow | `.github/workflows/ci.yml`, branch protection settings | Implemented |

## Required Evidence for Advancement

1. KPI reports generated from benchmark scripts:
   - `reports/eval_detection.json`
   - `reports/eval_redaction.json`
   - `reports/eval_ocr.json`
   - `reports/perf_benchmark.json`
2. Security and governance evidence:
   - CI passing on PR
   - Code review approvals
   - Issue-linked changes
3. Operational evidence:
   - Audit DB populated with real workflow events
   - Pilot runbook and incident drill records (next sprint)

## Known Gaps (to complete in next sprint)

- Add authentication/RBAC for web routes
- Add retention/deletion policy implementation
- Add signed audit export for regulator review
- Expand OCR benchmark set with validated image ground truth
