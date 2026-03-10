# Judging Evidence Snapshot

This file is generated from the current evaluation artifacts in `reports/`.

## Headline Metrics

- Detection macro F1 on covered entities: `1.0`
- Covered detection entity groups: `national_ids, phone_numbers, emails, kra_pins`
- Redaction leakage rate: `0.0`
- Redaction total leaks: `0`
- Perf average latency: `1.66` ms
- Perf p95 latency: `1.67` ms
- Round 1 average end-to-end latency: `5.82` ms
- Round 1 average throughput: `51878.52` chars/sec

## Judge-Ready Claims

- Current labeled text detection set reports macro F1 of 1.0 across the covered entity types.
- Current redaction evaluation reports zero leaks across the sampled benchmark files.
- Current local benchmark artifacts show interactive single-document latency on the tested text samples.
- OCR evidence is still incomplete because the current OCR evaluation set has zero labeled image samples.

## Highest-Priority Gaps

- Add labeled OCR samples for scanned PDFs and images.
- Add a baseline comparison against manual records review time.
- Expand the labeled evaluation set beyond the two current benchmark text samples.
- Collect workflow-owner feedback or pilot observations for sector impact evidence.

## OCR Coverage Note

- Image samples currently evaluated: `0`
- OCR note: Add image samples with 'reference_text' in ground truth for full OCR KPI coverage.
