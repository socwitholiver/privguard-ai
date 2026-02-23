from backend.protection_engine import ProtectionEngine

engine = ProtectionEngine()


def test_flag_document(tmp_path):
    file = tmp_path / "doc.txt"
    file.write_text("hello")

    result = engine.flag_document(str(file))
    assert result["status"] == "flagged"


def test_encrypt_placeholder(tmp_path):
    file = tmp_path / "doc.txt"
    file.write_text("secret")

    result = engine.encrypt_placeholder(str(file))
    assert result["status"] == "encrypted"


def test_redaction():
    text = "Email test@example.com"
    findings = {"email": ["test@example.com"]}

    redacted = engine.redact_text(text, findings)

    assert "[REDACTED]" in redacted