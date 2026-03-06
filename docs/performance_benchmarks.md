# Performance Benchmarks (Round 1)

Use this page to produce and present objective reliability numbers for judging.

## 1) Run benchmark script

From repository root:

```bash
python scripts/benchmark_round1.py
```

Optional custom files:

```bash
python scripts/benchmark_round1.py --files "demo_docs/school_admission_sample.txt" "demo_docs/sme_payroll_sample.txt" --output "reports/round1_benchmarks.json"
```

## 2) What is measured

- Extraction time (text/image/pdf)
- Detection time
- Classification time
- Redaction time
- Redaction verification time
- End-to-end total latency
- Throughput estimate (characters/second)
- Risk and redaction quality outputs

## 3) Evidence artifact for judges

Attach generated file:

- `reports/round1_benchmarks.json`

And include a short table in your submission/deck.

## 4) Summary table template

| File | File Type | Total ms | Extract ms | Detect ms | Risk Level | Quality Status | Leak Count |
|---|---:|---:|---:|---:|---|---|---:|
| school_admission_sample.txt | txt | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ |
| sme_payroll_sample.txt | txt | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ |
| sample_real_photo.jpg | jpg | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ |
| sample_real_text.pdf | pdf-text | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ |
| sample_real_scanned.pdf | pdf-ocr | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ | _fill_ |

## 5) Minimum target guidance (MVP)

- End-to-end processing should feel interactive for single documents.
- OCR-based files (jpg/scanned-pdf) will naturally be slower than text pdf/txt.
- Detection/classification steps should remain fast relative to extraction.

## 6) Reporting note

When presenting, always state:

- local hardware used,
- OCR installed locally (Tesseract),
- offline mode (no cloud inference),
- that all sample data shown is synthetic or consented demo data.
