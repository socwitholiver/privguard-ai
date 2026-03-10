# PrivGuard AI

PrivGuard AI is an offline-first records-protection MVP for Kenyan public-sector and critical-service document workflows.

The current MVP is optimized for one operational job: protect sensitive inbound records before they are shared, mishandled, or leaked. The strongest fit today is public-sector HR, payroll, admissions, and citizen-service document handling where agencies must process personally identifiable and operationally sensitive records on local infrastructure.

## Core Workflow

1. An operator signs in and unlocks the local vault.
2. A monitored intake folder receives new files.
3. PrivGuard extracts text, detects sensitive entities, scores risk, and applies a policy outcome.
4. The system stores originals, redacted outputs, encrypted artifacts, reports, and audit trails locally.
5. Lifecycle controls track retention, archive eligibility, and secure deletion actions.

## Why This Matters

PrivGuard is designed for environments where agencies cannot rely on foreign cloud tooling for sensitive citizen or operational records. The MVP reduces manual handling risk by turning privacy controls into an automated operational workflow.

Current public-sector use cases include:

- HR and payroll records containing IDs, salaries, contacts, and passwords.
- Admissions and citizen-service forms containing names, IDs, and contact details.
- Legal and contract records requiring controlled retention and auditability.

## MVP Capabilities

- Offline-first detection and classification.
- Automated redaction for shareable outputs.
- Encryption of high-risk originals with wrapped per-document keys.
- Local secure vault storage for originals, protected files, reports, keys, and logs.
- Audit logging and lifecycle management for retention, archive, and deletion decisions.
- Dashboard-driven watch-folder operations for non-technical users.

## Demo Workflow

- Default demo intake: `WATCH FOLDER`
- Default dataset size: `500` synthetic sensitive files
- Automatic pipeline per file:
  - text extraction
  - sensitive-data detection
  - risk classification
  - policy-based redaction or encryption
  - compliance report generation
  - secure local vault storage
  - lifecycle tracking

## Security Configuration

Tracked configuration no longer stores the live demo vault PIN.

- Repository defaults live in [config/system_config.yaml](/C:/Users/HP/Desktop/privguard-ai/config/system_config.yaml)
- Local secret overrides live in `instance/local_system_config.yaml`
- `instance/` is ignored by git and is the correct place for demo-only secrets or local overrides

## Judge-Facing Docs

- Benchmarks: [performance_benchmarks.md](/C:/Users/HP/Desktop/privguard-ai/docs/performance_benchmarks.md)
- Safety and fairness: [fairness_and_limits.md](/C:/Users/HP/Desktop/privguard-ai/docs/fairness_and_limits.md)
- Demo script: [demo_script_round1.md](/C:/Users/HP/Desktop/privguard-ai/docs/demo_script_round1.md)
- Sector impact and integration: [sector_impact_and_integration.md](/C:/Users/HP/Desktop/privguard-ai/docs/sector_impact_and_integration.md)
- Judging evidence matrix: [judging_evidence_matrix.md](/C:/Users/HP/Desktop/privguard-ai/docs/judging_evidence_matrix.md)
- Operational KPI model: [operational_kpis.md](/C:/Users/HP/Desktop/privguard-ai/docs/operational_kpis.md)
- Generated evidence snapshot: [judging_evidence_snapshot.md](/C:/Users/HP/Desktop/privguard-ai/docs/judging_evidence_snapshot.md)

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

4. Open the local dashboard, sign in, unlock the vault once, and either:
   - click `Use WATCH FOLDER`, or
   - click `Rebuild Demo` for a clean rerun from the UI.

## Test

```bash
pytest -q tests/test_demo_workflow.py tests/test_folder_watch.py tests/test_folder_watch_reconfigure.py tests/test_workspace_flow.py tests/test_config_and_vault_settings.py
```

