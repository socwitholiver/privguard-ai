# Performance Benchmarks

This benchmark pack exists to answer the judging questions around reliability, speed, and evidence of impact.

## What to Measure

Use the benchmark runner to collect evidence for four claims:

- `Latency`: how quickly a single file is processed end to end.
- `Protection quality`: whether sensitive values are fully removed from the shareable output.
- `Throughput`: how many files or characters can be processed per minute on local hardware.
- `Operational gain`: how much manual review time is removed from the workflow.

## How to Run

From repository root:

```bash
python scripts/benchmark_round1.py
```

Optional custom files:

```bash
python scripts/benchmark_round1.py --files "WATCH FOLDER/sample1.txt" "WATCH FOLDER/sample2.txt" --output "reports/round1_benchmarks.json"
```

## Generated Artifact

- JSON report: `reports/round1_benchmarks.json`

This should be attached to the submission deck as primary technical evidence.

## Judge-Facing KPI Table

Fill and present this table after running the benchmark:

| KPI | What it shows | Current evidence source |
|---|---|---|
| End-to-end latency per file | Whether the workflow is practical for operators | `timings_ms.total` |
| Extraction latency | OCR and parsing burden by format | `timings_ms.extract` |
| Detection latency | Speed of the local policy engine | `timings_ms.detect` |
| Redaction quality status | Whether the protected copy leaked sensitive text | `metrics.redaction_quality_status` |
| Leak count | Residual sensitive values after redaction | `metrics.leak_count` |
| Risk level and score | Whether the file was graded consistently | `metrics.risk_level`, `metrics.risk_score` |
| Characters per second | Local throughput estimate | `metrics.characters_per_second` |

## Baseline Story for Judges

Use a realistic baseline: manual records review by an officer.

Recommended comparison points:

- Manual review requires a human to open, inspect, and decide how to handle each file.
- PrivGuard performs the first-pass triage, protection action, and audit logging automatically.
- The benchmark demonstrates machine-time latency; the value claim is reduced handling time and fewer operator mistakes.

## Suggested Claims

Only make claims you can support with the generated report.

Safe claim examples:

- `PrivGuard processes single documents locally in interactive time on commodity hardware.`
- `Detection and classification are fast relative to extraction, which is expected for OCR-heavy files.`
- `The system verifies protected output quality and reports residual leaks explicitly.`

Avoid unsupported claims such as perfect accuracy or full production readiness.

## Hardware Disclosure

Always report:

- machine specs,
- whether Tesseract OCR was installed locally,
- whether the file was text-native or OCR-derived,
- that all demo data is synthetic or consented.

## Next-Step Evidence to Add

For stronger Stage 2 scoring, add:

- false-positive and false-negative counts on a labeled sample set,
- files processed per minute on the 500-file demo batch,
- comparison against current manual handling time,
- pilot feedback from one target workflow owner.
