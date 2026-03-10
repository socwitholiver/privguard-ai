# Operational KPIs and Baseline Model

This document gives you a conservative way to talk about impact without overstating what has been pilot-validated.

## KPI Set

Use these five KPIs in the pitch and deck:

1. `Sensitive-entity detection quality`
   - Source: `reports/eval_detection.json`
   - Meaning: how accurately PrivGuard detects covered entity types on the labeled set.

2. `Protected-output leakage rate`
   - Source: `reports/eval_redaction.json`
   - Meaning: how often sensitive values remain visible after redaction.

3. `Single-file processing latency`
   - Source: `reports/round1_benchmarks.json`
   - Meaning: whether first-pass protection feels operationally immediate.

4. `High-risk file escalation rate`
   - Source: dashboard/workspace metrics from the app.
   - Meaning: how many files triggered the strictest protection policy.

5. `Manual review time avoided`
   - Source: projected baseline model below.
   - Meaning: estimated workload reduction from automated first-pass triage.

## Baseline Model

This is a projected operational model, not a pilot claim.

Assume a records officer spends:

- `60 to 120 seconds` opening, scanning, and deciding how to handle one sensitive inbound document,
- plus additional time to redact or route high-risk files.

PrivGuard automates the first-pass tasks:

- intake,
- text extraction,
- sensitive-data detection,
- risk grading,
- policy action selection,
- audit logging,
- protected-output generation.

## Conservative Talking Point

Use this line:

`Even with a conservative manual baseline of one minute per sensitive record, automating first-pass triage on hundreds of records yields material time savings while reducing exposure risk from inconsistent manual handling.`

## What Not To Claim

Do not claim:

- exact officer hours saved unless you measured them,
- production-wide throughput on OCR-heavy files unless benchmarked,
- perfect real-world accuracy outside the current labeled set.

## Suggested Next Measurements

For a stronger Stage 2 score, measure:

- average manual handling time on 20 to 50 files,
- watch-folder batch throughput on the 500-file demo set,
- false positives and false negatives on a larger labeled sample,
- OCR word error rate on scanned PDFs and photographed pages,
- user feedback from one real operator workflow.

## Current Numeric Evidence Available

From current repo artifacts:

- Detection macro F1 on covered entity groups: `1.0`
- Redaction total leaks on sampled benchmark files: `0`
- Round 1 average end-to-end latency on tested text files: `5.82 ms`
- Round 1 average throughput on tested text files: `51878.52 chars/sec`

These should be presented as current benchmark values on the existing evaluation set, not universal production guarantees.
