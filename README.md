# PrivGuard AI

PrivGuard AI is an offline-first privacy protection pipeline for sensitive documents.

The product flow is intentionally minimal:

1. Log in.
2. Choose any folder on the local machine and enable it as the watch folder.
3. PrivGuard scans, classifies risk, redacts what should be shared, encrypts high-risk originals, stores outputs in the local vault, and generates a compliance report automatically.

## Current Workflow

- Silent vault unlock after login
- Automatic text extraction for `.txt`, `.pdf`, `.docx`, and supported images
- Sensitive data detection for:
  - Kenyan National IDs
  - KRA PINs
  - phone numbers
  - emails
  - passwords
  - financial information
  - personal names
- Automatic protection policy:
  - low risk -> allow
  - medium risk -> redact
  - high-value identifiers or secrets -> redact and encrypt
- Secure local vault structure:
  - `vault/Originals`
  - `vault/Redacted`
  - `vault/Encrypted`
  - `vault/Reports`
  - `vault/Keys`
  - `vault/Logs`
- Watch folder automation for hands-free protection
- Local audit trail and compliance reports aligned to the Kenya Data Protection Act (2019)

## Run PrivGuard

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

3. Open the local PrivGuard dashboard and sign in.

Default demo users are configured in [config/system_config.yaml](/C:/Users/HP/Desktop/privguard-ai/config/system_config.yaml).

## Test

```bash
pytest -q tests/test_mvp_detection.py tests/test_mvp_classification.py tests/test_mvp_protection.py tests/test_vault_workflow.py
```

## Product Direction

PrivGuard is no longer centered on manual CLI protection flows. The active product is the dashboard-driven, automation-first vault workflow in [app.py](/C:/Users/HP/Desktop/privguard-ai/app.py) and [templates/dashboard.html](/C:/Users/HP/Desktop/privguard-ai/templates/dashboard.html).
