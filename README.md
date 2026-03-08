# PrivGuard AI

PrivGuard AI is an offline-first privacy protection pipeline for sensitive documents.

The demo workflow now centers on one repeatable intake path:

1. Log in.
2. Use the default `WATCH FOLDER` inside the project.
3. PrivGuard scans the synthetic files, extracts sensitive data, redacts shareable output, encrypts high-risk originals, stores everything in the local vault, and generates compliance reports automatically.
4. When you need a fresh demo, rebuild the workflow and rerun the same 500-file batch.

## Demo Workflow

- Default demo intake: `WATCH FOLDER`
- Default dataset size: 500 synthetic sensitive files
- Automatic pipeline per file:
  - scan and text extraction
  - sensitive-data detection
  - redaction of exposed values
  - encryption of the original high-risk record
  - compliance report generation
  - secure vault storage
- Repeatable reset options:
  - dashboard button: `Rebuild Demo`
  - launcher: `start_privguard_demo.bat`
  - script: `scripts/rebuild_demo_workflow.py`

## Run PrivGuard

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the standard app:

```bat
start_privguard.bat
```

3. Start a fresh repeatable demo run with a rebuilt 500-file dataset:

```bat
start_privguard_demo.bat
```

Alternative reset-only command:

```bat
.venv\Scripts\python.exe scripts\rebuild_demo_workflow.py --target 500
```

4. Open the local dashboard, sign in, unlock the vault once, and either:
   - click `Use WATCH FOLDER`, or
   - click `Rebuild Demo` for a clean rerun from the UI.

Default demo users are configured in [config/system_config.yaml](/C:/Users/HP/Desktop/privguard-ai/config/system_config.yaml).

## Test

```bash
pytest -q tests/test_demo_workflow.py tests/test_folder_watch.py tests/test_folder_watch_reconfigure.py tests/test_workspace_flow.py
```

## Product Direction

PrivGuard is centered on the dashboard-driven, automation-first vault workflow in [app.py](/C:/Users/HP/Desktop/privguard-ai/app.py). The repeatable demo tooling now lives in [automation/demo_workflow.py](/C:/Users/HP/Desktop/privguard-ai/automation/demo_workflow.py) and [scripts/rebuild_demo_workflow.py](/C:/Users/HP/Desktop/privguard-ai/scripts/rebuild_demo_workflow.py).
