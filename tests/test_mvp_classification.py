from classification import build_risk_summary, classify_risk_level


def test_classify_risk_level_thresholds():
    assert classify_risk_level(11) == "Low"
    assert classify_risk_level(12) == "Medium"
    assert classify_risk_level(30) == "High"


def test_build_risk_summary_high_risk_for_sensitive_secrets():
    findings = {
        "national_ids": [],
        "phone_numbers": [],
        "emails": [],
        "kra_pins": [],
        "passwords": [{"value": "P@ss1234"}],
        "financial_info": [{"value": "KES 120,000"}],
        "personal_names": [],
    }
    summary = build_risk_summary(findings)

    assert summary["score"] >= 30
    assert summary["level"] == "High"
    assert summary["primary_action"] == "redact_encrypt"
    assert summary["policy"]["encrypt"] is True
    assert summary["recommendations"]


def test_build_risk_summary_medium_risk_for_contacts():
    findings = {
        "national_ids": [],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [{"value": "a@example.org"}],
        "kra_pins": [],
        "passwords": [],
        "financial_info": [],
        "personal_names": [],
    }
    summary = build_risk_summary(findings)

    assert summary["level"] in {"Medium", "High"}
    assert summary["primary_action"] == "redact"
    assert summary["policy"]["redact"] is True
    assert summary["policy"]["encrypt"] is False


def test_build_risk_summary_low_risk_names_are_allowed():
    findings = {
        "national_ids": [],
        "phone_numbers": [],
        "emails": [],
        "kra_pins": [],
        "passwords": [],
        "financial_info": [],
        "personal_names": [{"value": "Jane Doe"}],
    }
    summary = build_risk_summary(findings)

    assert summary["level"] == "Low"
    assert summary["primary_action"] == "allow"
    assert summary["policy"]["redact"] is False
    assert summary["policy"]["encrypt"] is False
