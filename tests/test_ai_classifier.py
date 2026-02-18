from backend.ai_classifier import AIClassifier

classifier = AIClassifier()

def test_ai_insights():
    findings = {
        "email": ["test@example.com"],
        "phone": ["0712345678"],
        "id_number": [],
        "financial": ["1234567890123456"]
    }

    risk_result = {"level": "High"}

    result = classifier.generate_insights(findings, risk_result)

    assert result["risk_level"] == "High"
    assert len(result["reasons"]) > 0
    assert len(result["recommendations"]) > 0
