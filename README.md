<p align="center">
  <img src="./Logo/PRIVGUARD%20AI%20OFFICIAL%20LOGO.png" alt="PrivGuard AI Logo" width="720">
</p>

# PrivGuard AI

> Status: On hold. This repository is being preserved in a clean, reviewable state for future continuation.

PrivGuard AI is a local-first cybersecurity workspace for detecting, classifying, and protecting sensitive information before it is exposed.

It is designed to help a user or team drop files into a controlled intake flow, let the system inspect them offline, and then decide whether those files should be redacted, encrypted, stored in the secure vault, or tracked for retention and audit purposes.

## What PrivGuard AI Does

PrivGuard AI turns sensitive-document handling into an automated security workflow.

Core capabilities:

- Scans local files for sensitive data
- Extracts text from `.txt`, `.pdf`, `.docx`, and supported image files
- Detects entities such as national IDs, tax IDs, emails, phone numbers, passwords, financial details, and names
- Classifies risk level from the detected findings
- Applies protection actions such as redaction or encryption
- Stores originals and protected artifacts in a local secure vault
- Tracks audit events, lifecycle rules, and retention status
- Runs a watch-folder workflow so files can be processed with minimal manual input

The main operating model is simple:

1. Sign in to the PrivGuard dashboard
2. Unlock the secure vault
3. Drop files into the watch folder
4. Let PrivGuard scan, classify, and protect them locally
5. Review activity, outputs, and reports from the dashboard

## The Technology Behind PrivGuard AI

PrivGuard AI is built as a Python-based offline desktop-style web workspace.

Main technologies in the current implementation:

- `Flask` for the local web application and dashboard
- `Python` for the full application pipeline
- `watchdog` for real-time watch-folder monitoring
- `python-docx` for Word document text extraction
- `pypdf` and `PyMuPDF` for PDF handling
- `pytesseract`, `Pillow`, and `opencv-python` for OCR and image preprocessing
- `cryptography` for encryption and secure key handling
- `PyYAML` for system configuration
- `SQLite`-backed local storage through the project storage layer
- HTML, CSS, and JavaScript for the user interface

Project architecture includes:

- `app.py` for the main web application and workflow routes
- `extraction.py` for file and OCR text extraction
- `detection.py` for sensitive-data detection
- `classification.py` for risk scoring and summaries
- `protection.py` for redaction, encryption, and redaction verification
- `security/vault.py` for secure-vault layout and wrapped key handling
- `automation/` for watch-folder and lifecycle automation
- `storage/` for profiles, documents, audit logs, and database access

## The Intelligence Inside PrivGuard AI

PrivGuard AI is not just a file uploader with pattern matching. It combines multiple layers of security logic to make protection decisions more intelligently.

Its intelligence comes from four main stages:

### 1. Extraction
The system reads text directly from supported files. For scanned PDFs and images, it can use OCR to recover readable text before analysis.

### 2. Detection
PrivGuard identifies sensitive content using detection logic that combines structured matching and entity-focused analysis. This includes patterns such as:

- IDs and tax identifiers
- phone numbers and emails
- credentials and passwords
- financial information
- personal names and related sensitive attributes

### 3. Classification
After detection, the system builds a risk summary from the findings. The number, type, and severity of detected entities influence whether a document is considered low, medium, or high risk.

### 4. Protection
Based on the risk profile, PrivGuard can:

- redact content for safer sharing
- encrypt high-risk outputs
- verify redaction quality
- store artifacts in the secure vault
- record audit evidence for later review

This gives PrivGuard AI a practical form of intelligence: it understands what is risky in a document, how risky it is, and what to do next inside a local privacy-preserving workflow.

## Secure Vault and Local-First Design

PrivGuard AI is designed to run locally.

That means:

- documents are processed on the local machine
- protected outputs are stored in the local vault
- audit and lifecycle data stay in local project storage
- watch-folder automation works without depending on a cloud service

The vault workflow supports:

- locked and unlocked vault states
- wrapped per-document keys
- encrypted outputs
- redacted outputs
- local auditability

## How to Run PrivGuard AI

### 1. Create a virtual environment

```powershell
py -3.10 -m venv .venv
```

### 2. Install dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Start the app

Option A: run the starter script

```bat
start_privguard.bat
```

Option B: run the app directly

```powershell
.venv\Scripts\python.exe app.py
```

### 4. Open the local dashboard

Open:

- `http://127.0.0.1:5000/login`

### 5. Use the dashboard

Typical flow:

1. Log in
2. Unlock the secure vault
3. Enable or confirm the watch folder
4. Drop files into `WATCH FOLDER`
5. Review scans, outputs, vault items, and reports

## Demo Mode

To launch a repeatable demo flow with a rebuilt watch-folder dataset:

```bat
start_privguard_demo.bat
```

This is useful when you want to reset the workspace and run PrivGuard AI from a clean demo state.

## Running Tests

```powershell
& 'C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe' -m pytest -q tests\test_mvp_detection.py tests\test_mvp_classification.py tests\test_mvp_protection.py tests\test_vault_workflow.py tests\test_folder_watch.py tests\test_extraction_pdf.py tests\test_profile_repo.py tests\test_audit_archive.py tests\test_lifecycle_manager.py tests\test_config_and_vault_settings.py
```

## Important Files

- [C:\Users\HP\Desktop\privguard-ai\app.py](C:\Users\HP\Desktop\privguard-ai\app.py)
- [C:\Users\HP\Desktop\privguard-ai\requirements.txt](C:\Users\HP\Desktop\privguard-ai\requirements.txt)
- [C:\Users\HP\Desktop\privguard-ai\config\system_config.yaml](C:\Users\HP\Desktop\privguard-ai\config\system_config.yaml)
- [C:\Users\HP\Desktop\privguard-ai\security\vault.py](C:\Users\HP\Desktop\privguard-ai\security\vault.py)
- [C:\Users\HP\Desktop\privguard-ai\automation\folder_watch.py](C:\Users\HP\Desktop\privguard-ai\automation\folder_watch.py)
- [C:\Users\HP\Desktop\privguard-ai\templates\dashboard.html](C:\Users\HP\Desktop\privguard-ai\templates\dashboard.html)

## Summary

PrivGuard AI is a privacy-focused local security workspace that watches files, detects sensitive data, classifies risk, protects documents, and stores outputs in a secure local vault with audit and lifecycle controls built in.




