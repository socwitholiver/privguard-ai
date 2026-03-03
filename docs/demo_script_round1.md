# Round 1 Demo Script (Judge-Facing)

## 2-Minute Version

1. **Open context (15s)**
   - "PRIVGUARD AI protects sensitive citizen/business data offline for schools, SMEs, and public-facing workflows."

2. **Scan demo (35s)**
   - Upload `demo_docs/school_admission_sample.txt`.
   - Click **Scan**.
   - Point to detected entities + risk score + recommended action.

3. **Protect + verify (40s)**
   - Choose **Redact** and run protection.
   - Open **Verify Redaction Quality** with original + protected file.
   - Highlight coverage and leak metrics.

4. **Admin operations (20s)**
   - Click **Export Signed Audit**.
   - Click **OCR Diagnostics**.
   - Mention retention cleanup as policy enforcement.

5. **Close (10s)**
   - "This is an offline-capable, test-backed MVP with practical controls and auditability."

## 6-8 Minute Version

### Part A: Problem and national relevance (1 min)
- Data exposure risk in digitizing sectors.
- Low-connectivity environments need local/offline privacy tooling.

### Part B: Live workflow (3-4 min)
- Scan `school_admission_sample.txt`.
- Scan `sme_payroll_sample.txt`.
- If available, scan real `.jpg` and `.pdf` (including scanned PDF fallback).
- Show risk trend and recent scans update.

### Part C: Protection and trust (1-2 min)
- Redact one file.
- Verify redaction quality and explain PASS/FAIL interpretation.

### Part D: Admin control plane (1 min)
- Export signed audit.
- Run retention cleanup.
- Run OCR diagnostics.

### Part E: Reliability evidence (30-60s)
- Mention full test pass.
- Mention benchmark report artifact from `scripts/benchmark_round1.py`.
- Mention fairness/limits and mitigation roadmap.

## Demo safety notes

- Use synthetic or consented data only.
- Avoid exposing real personal identifiers in public demos.
- Keep one fallback file per format (txt/jpg/pdf) in case OCR is slow.
