from protection import (
    decrypt_text,
    encrypt_text,
    generate_encryption_key,
    mask_text,
    redact_text,
    verify_redaction_quality,
)


def test_redact_and_mask():
    text = "Contact 0712345678 and email user@example.org"
    findings = {
        "national_ids": [],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [{"value": "user@example.org"}],
        "kra_pins": [],
    }
    redacted = redact_text(text, findings)
    masked = mask_text(text, findings)

    assert "[REDACTED]" in redacted
    assert "0712345678" not in masked
    assert "user@example.org" not in masked


def test_encrypt_then_decrypt_roundtrip():
    key = generate_encryption_key()
    plain = "Synthetic private content"
    encrypted = encrypt_text(plain, key)
    decrypted = decrypt_text(encrypted, key)
    assert plain == decrypted


def test_verify_redaction_quality_pass_and_fail():
    original_findings = {
        "national_ids": [{"value": "87654321"}],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [],
        "kra_pins": [],
    }
    protected_ok = "ID [REDACTED], phone [REDACTED]"
    protected_bad = "ID [REDACTED], phone 0712345678"

    ok_report = verify_redaction_quality(original_findings, protected_ok)
    bad_report = verify_redaction_quality(original_findings, protected_bad)

    assert ok_report["quality_status"] == "PASS"
    assert ok_report["leak_count"] == 0
    assert bad_report["quality_status"] == "FAIL"
    assert bad_report["leak_count"] == 1


def test_verify_redaction_quality_ignores_numeric_substring_overlap():
    original_findings = {
        "national_ids": [{"value": "12345678"}],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [],
        "kra_pins": [],
    }
    protected_text = "Phone remains exposed: 0712345678, ID already redacted."

    report = verify_redaction_quality(original_findings, protected_text)
    assert report["quality_status"] == "FAIL"
    assert report["leak_count"] == 1
    assert report["leaked_items"][0]["data_type"] == "phone_numbers"
