# PRIVGUARD AI (Offline MVP)

PRIVGUARD AI is a secure, offline-capable MVP for detecting and protecting
sensitive personal data in documents used by schools, SMEs, and local
organizations in Kenya.

It is designed to support practical privacy workflows under low-connectivity
conditions while aligning to key principles in Kenya's Data Protection Act
(DPA 2019), such as data minimization, purpose limitation, and secure storage.

## Problem Statement

As institutions in Kenya digitize records, personally identifiable information
(PII) such as National ID numbers, phone numbers, email addresses, and KRA PINs
is often exposed in shared or archived documents. Many organizations need an
affordable, lightweight privacy tool that:

- Works fully offline
- Detects sensitive data intelligently
- Classifies risk quickly
- Applies one-click protections (redact/mask/encrypt)
- Gives clear compliance guidance

## MVP Features

- **Offline AI processing**
  - Detection and protection run locally with no internet dependency.
  - Supports image OCR locally through Tesseract (no cloud APIs).
- **Smart data detection**
  - Detects National IDs, phone numbers, emails, and KRA PINs.
  - Uses regex + lightweight context scoring (NLP-style heuristic).
- **Risk classification engine**
  - Assigns Low, Medium, High risk from weighted detection outputs.
- **One-click protection actions**
  - `redact`: irreversible token replacement (`[REDACTED]`)
  - `mask`: partially hide values for operational use
  - `encrypt`: reversible encryption using secure Fernet keys
- **Compliance dashboard**
  - CLI dashboard summary (supports rich output if installed).
- **Student and SME friendly**
  - Minimal dependencies and runs on modest hardware.

## Project Structure

```text
privguard-ai/
├── main.py                  # CLI entrypoint
├── detection.py             # Regex + context-based sensitive data detection
├── classification.py        # Risk scoring and DPA-aligned insights
├── protection.py            # Redact, mask, encrypt/decrypt actions
├── dashboard.py             # CLI dashboard rendering
├── requirements.txt
├── demo_docs/
│   ├── school_admission_sample.txt
│   └── sme_payroll_sample.txt
└── tests/
    ├── test_mvp_detection.py
    ├── test_mvp_classification.py
    └── test_mvp_protection.py
```

## Installation

1. Use Python 3.10+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage Examples

### 1) Scan a document (text or image)

```bash
python main.py scan --input demo_docs/school_admission_sample.txt
```

Optional JSON report:

```bash
python main.py scan --input demo_docs/school_admission_sample.txt --json-output outputs/report.json
```

Extract OCR text to file:

```bash
python main.py scan --input "path/to/document.png" --extracted-output outputs/extracted.txt --json-output outputs/scan_report.json
```

### 2) Protect a document (one-click actions)

**Redact**

```bash
python main.py protect --input demo_docs/sme_payroll_sample.txt --action redact --output-dir outputs
```

**Mask**

```bash
python main.py protect --input demo_docs/sme_payroll_sample.txt --action mask --output-dir outputs
```

**Encrypt (reversible)**

```bash
python main.py protect --input demo_docs/sme_payroll_sample.txt --action encrypt --output-dir outputs
```

This creates:
- encrypted file: `outputs/<name>.encrypted.txt`
- key file: `outputs/<name>.key`

### 3) Decrypt a protected file

```bash
python main.py decrypt --input outputs/sme_payroll_sample.encrypted.txt --key-path outputs/sme_payroll_sample.key --output-dir outputs
```

### 4) Verify redaction quality

```bash
python main.py verify-redaction --original demo_docs/sme_payroll_sample.txt --protected outputs/sme_payroll_sample.redacted.txt --json-output outputs/redaction_quality.json
```

This checks whether any originally detected sensitive values are still present in
the protected output and returns:
- `PASS` if no leaks remain
- `FAIL` with leaked values if any were missed

## Test Cases

Run unit tests:

```bash
pytest -q tests/test_mvp_detection.py tests/test_mvp_classification.py tests/test_mvp_protection.py
```

Tests cover:
- Detection of all required sensitive types
- Risk level classification behavior
- Redaction/masking and encryption roundtrip

## Compliance Notes (Kenya DPA 2019)

This MVP supports practical controls aligned with core DPA principles:

- **Data minimization:** flag and reduce unnecessary exposure of personal data.
- **Purpose limitation:** encourage processing only for legitimate documented use.
- **Security safeguards:** provide local encryption and controlled output handling.
- **Accountability support:** produce a clear risk and findings summary for reviews.

> Note: This tool provides technical safeguards and guidance but is not legal advice.
> Organizations should pair this with internal policies, role-based access, and
> proper consent/lawful-basis documentation.

## Safety Considerations

- Demo documents use synthetic placeholder values only.
- Encryption keys are generated securely using `cryptography.fernet`.
- File input is sanitized and restricted to known text/image formats in the CLI.
- Avoid storing key files in publicly accessible/shared locations.

## OCR Setup (Offline)

For image text extraction, install Tesseract locally:

- **Windows:** install Tesseract OCR and add it to your system `PATH`
- **Linux:** `sudo apt install tesseract-ocr`
- **macOS:** `brew install tesseract`

PRIVGUARD AI uses local OCR only; no image data is sent to external services.