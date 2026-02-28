from classification import build_risk_summary, classify_risk_level


def test_classify_risk_level_thresholds():
    assert classify_risk_level(10) == "Low"
    assert classify_risk_level(35) == "Medium"
    assert classify_risk_level(70) == "High"


def test_build_risk_summary_high_risk():
    findings = {
        "national_ids": [{"value": "12345678"}],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [{"value": "a@example.org"}],
        "kra_pins": [{"value": "A123456789B"}],
    }
    summary = build_risk_summary(findings)

    assert summary["score"] >= 70
    assert summary["level"] == "High"
    assert "insights" in summary
