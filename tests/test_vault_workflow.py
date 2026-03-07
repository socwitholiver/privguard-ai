from pathlib import Path

import pytest

from protection import generate_encryption_key
import security.vault as vault
import storage.db as db
from storage.document_repo import create_document_record, generate_document_id, get_document, record_artifact


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
            "financial_info": 0,
            "personal_names": 1,
        },
        "recommendations": ["PrivGuard will redact sensitive sections for sharing."],
        "primary_action": "redact_encrypt",
        "policy": {
            "mode": "redact_encrypt",
            "label": "Redact and Encrypt",
            "redact": True,
            "encrypt": True,
            "reason": "High-risk identifiers were detected.",
        },
    }


def sample_findings():
    return {
        "national_ids": [{"value": "12345678", "confidence": 0.99}],
        "phone_numbers": [{"value": "0712345678", "confidence": 0.98}],
        "emails": [],
        "kra_pins": [],
        "passwords": [{"value": "TempPass!9", "confidence": 0.91}],
        "financial_info": [],
        "personal_names": [{"value": "Jane Doe", "confidence": 0.74}],
    }


def test_master_password_vault_wrap_and_unwrap(tmp_path, monkeypatch):
    monkeypatch.setattr(vault, "VAULT_ROOT", tmp_path / "vault")
    monkeypatch.setattr(vault, "VAULT_STATE_PATH", tmp_path / "instance" / "vault_state.json")
    vault.lock_vault()

    info = vault.unlock_vault("MasterPass123!", "tester")
    assert info["unlocked"] is True
    key = generate_encryption_key()
    key_path = vault.wrap_document_key("PG-2026-00001", key)

    assert key_path.exists()
    assert vault.unwrap_document_key("PG-2026-00001") == key


def test_document_repo_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "instance" / "audit.db")
    db.init_db()

    document_id = generate_document_id("2026")
    document = create_document_record(
        document_id=document_id,
        original_filename="payroll.docx",
        original_path=str(tmp_path / "vault" / "Originals" / "payroll.docx"),
        findings=sample_findings(),
        risk=sample_risk(),
        total_sensitive_items=4,
        actor="tester",
        status="SCANNED",
    )
    record_artifact(document_id, "original", str(tmp_path / "vault" / "Originals" / "payroll.docx"), "payroll.docx", {"kind": "original"})
    record_artifact(document_id, "report", str(tmp_path / "vault" / "Reports" / "payroll.report.json"), "payroll.report.json", {"kind": "report"})

    loaded = get_document(document_id)
    assert document["document_id"] == document_id
    assert loaded is not None
    assert loaded["document_id"] == document_id
    assert loaded["primary_action"] == "redact_encrypt"
    assert loaded["artifacts"]["original"]["filename"] == "payroll.docx"
    assert loaded["artifacts"]["report"]["filename"] == "payroll.report.json"
