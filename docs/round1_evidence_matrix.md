# PRIVGUARD AI Round 1 Evidence Matrix

This page maps Stage 1 criteria to concrete proof from the MVP.

## A. National Security Alignment

- **A1. Sectoral Resilience**
  - **What we show:** Sensitive data detection + protection for school/SME/public documents.
  - **Evidence:** Dashboard scan results, protected output preview, redaction verification output.
  - **Where:** `templates/dashboard.html`, demo walkthrough, sample docs in `demo_docs/`.

- **A2. National Self-Reliance**
  - **What we show:** Offline-capable processing with local OCR and local storage.
  - **Evidence:** No cloud API dependency in core scan/protect/verify flow.
  - **Where:** `extraction.py`, `app.py`, local SQLite/audit modules.

- **A3. Crisis & Emergency Utility**
  - **What we show:** Works in low-connectivity/offline settings for urgent document screening.
  - **Evidence:** End-to-end local workflow + admin diagnostics.
  - **Where:** Dashboard flow + `/admin/ocr-diagnostics`.

## B. Technical Innovation and Implementation

- **B1. Originality & Sophistication**
  - **What we show:** Hybrid practical stack (OCR + pattern detection + risk scoring + quality verification + audit ops).
  - **Evidence:** Guided workflow from scan to protection and verification.
  - **Where:** `app.py`, `extraction.py`, `detection.py`, `classification.py`, `protection.py`.

- **B2. System Performance & Reliability**
  - **What we show:** Stable test-backed build and benchmark script.
  - **Evidence:** `python -m pytest` pass output + benchmark report artifact.
  - **Where:** `tests/`, `scripts/benchmark_round1.py`, `docs/performance_benchmarks.md`.

## C. Problem-Solution Fit

- **C1. Effectiveness of Solution**
  - **What we show:** Detect -> classify risk -> protect -> verify leaks.
  - **Evidence:** Demo run on sample school/payroll documents with actionable outputs.
  - **Where:** `demo_docs/`, dashboard panels and APIs.

- **C2. National Scalability**
  - **What we show:** Modular Python service and role-based workflow.
  - **Evidence:** Separated modules for detection/classification/protection/admin operations.
  - **Where:** Root modules + `ops/` + `security/` + `storage/`.

## D. Ethics, Safety, and Responsibility

- **D1. Data Privacy & Security**
  - **What we show:** Redaction, encryption, verification, audit export signing, RBAC.
  - **Evidence:** Protection endpoints + signed audit export + role permissions.
  - **Where:** `protection.py`, `ops/audit_export.py`, `security/auth.py`.

- **D2. Transparency & Explainability**
  - **What we show:** Visible findings, risk score/level, insights, timeline, and logs.
  - **Evidence:** Dashboard output and recent scans summary.
  - **Where:** `templates/dashboard.html`, `app.py`.

- **D3. Bias/Fairness**
  - **What we show now:** Pattern-driven approach reduces model-opinion bias but still needs monitoring.
  - **Evidence:** Fairness and limits documentation + planned controls.
  - **Where:** `docs/fairness_and_limits.md`.

## E. User Experience and Operational Utility

- **E1. Operational UX**
  - **What we show:** Guided flow, clear risk visualization, one-click actions.
  - **Evidence:** Dashboard workflow, role-specific capabilities, profile/theme controls.
  - **Where:** `templates/dashboard.html`, `static/css/privguard-dashboard.css`.

- **E2. Actionable Insights**
  - **What we show:** Recommended action banner + verification metrics + admin operations outputs.
  - **Evidence:** Scan risk insights, recommendation text, redaction PASS/FAIL, admin JSON outputs.
  - **Where:** Dashboard UI and admin endpoints in `app.py`.

## Submission Checklist (Round 1)

- Capture screenshots for each criterion group (A-E).
- Export one signed audit sample and include in evidence folder.
- Run benchmark script and attach output JSON/summary.
- Include one short demo video or scripted live demo using `demo_docs/` files.
