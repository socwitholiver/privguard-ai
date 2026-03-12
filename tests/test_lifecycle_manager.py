from datetime import datetime, timedelta, timezone

import storage.db as db
from lifecycle_manager import build_lifecycle_policy, evaluate_lifecycle
from storage.document_repo import create_document_record, get_document


def sample_risk(level="High", score=44):
    return {
        "level": level,
        "score": score,
        "counts": {
            "national_ids": 1,
            "phone_numbers": 1,
            "emails": 0,
            "kra_pins": 0,
            "passwords": 1,
            "financial_info": 1,
            "personal_names": 1,
        },
        "recommendations": ["Encrypt and restrict retention."],
        "primary_action": "redact_encrypt",
        "policy": {"mode": "redact_encrypt"},
    }


def sample_findings():
    return {
        "national_ids": [{"value": "12345678"}],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [],
        "kra_pins": [],
        "passwords": [{"value": "TempPass!9"}],
        "financial_info": [{"value": "KES 350000"}],
        "personal_names": [{"value": "Jane Doe"}],
    }


def test_build_lifecycle_policy_assigns_payroll_retention():
    policy = build_lifecycle_policy("payroll_march.pdf", sample_risk("High"))
    assert policy["owner"] == "HR"
    assert policy["retention_days"] == 90
    assert policy["expiry_action"] == "archive_or_delete"


def test_evaluate_lifecycle_flags_expired_record():
    now = datetime.now(timezone.utc)
    document = {
        "risk_level": "High",
        "owner": "HR",
        "department": "Human Resources",
        "retention_days": 90,
        "retention_until": (now - timedelta(days=1)).isoformat(),
        "expiry_action": "archive_or_delete",
        "policy_name": "Payroll retention policy",
    }
    lifecycle = evaluate_lifecycle(document, now=now)
    assert lifecycle["lifecycle_status"] == "Expired"
    assert lifecycle["next_action"] == "Archive or secure delete"


def test_evaluate_lifecycle_flags_expiring_soon_record():
    now = datetime.now(timezone.utc)
    document = {
        "risk_level": "Medium",
        "owner": "Admissions",
        "department": "Student Records",
        "retention_days": 365,
        "retention_until": (now + timedelta(days=3)).isoformat(),
        "expiry_action": "archive",
        "policy_name": "Admissions retention policy",
    }
    lifecycle = evaluate_lifecycle(document, now=now)
    assert lifecycle["lifecycle_status"] == "Expiring Soon"
    assert lifecycle["retention_label"] == "3 days left"


def test_document_record_persists_lifecycle_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "instance" / "audit.db")
    db.init_db()

    lifecycle = build_lifecycle_policy("admission_form.docx", sample_risk("Medium"))
    document = create_document_record(
        document_id="PG-2026-99999",
        original_filename="admission_form.docx",
        original_path=str(tmp_path / "vault" / "Originals" / "admission_form.docx"),
        findings=sample_findings(),
        risk=sample_risk("Medium"),
        total_sensitive_items=5,
        actor="tester",
        status="SCANNED",
        lifecycle=lifecycle,
    )

    loaded = get_document(document["document_id"])
    assert loaded is not None
    assert loaded["owner"] == "Admissions"
    assert loaded["department"] == "Student Records"
    assert int(loaded["retention_days"]) == 365
    assert loaded["policy_name"] == "Admissions retention policy"
