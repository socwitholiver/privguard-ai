import re

PATTERNS = {
    "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    "phone": r"\+?\d{1,3}?[\s-]?\(?\d{2,3}\)?[\s-]?\d{3,4}[\s-]?\d{4}",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "api_key": r"(?i)(api[_-]?key|secret|token)[\s:=]+[a-zA-Z0-9_\-]{16,}",
    "national_id": r"\b\d{6,14}\b"
}

def detect_sensitive_data(text):
    findings = {}

    for label, pattern in PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            findings[label] = list(set(matches))

    return findings


def _to_legacy_findings(raw_findings):
    """Map current detector labels to the legacy test contract."""
    return {
        "email": raw_findings.get("email", []),
        "phone": raw_findings.get("phone", []),
        "id_number": raw_findings.get("national_id", []),
        "financial": raw_findings.get("credit_card", []),
    }


class SensitiveDataDetector:
    """Backward-compatible detector API used by older tests/modules."""

    def detect(self, text):
        return _to_legacy_findings(detect_sensitive_data(text))


class IntelligentDataDetector:
    """
    Compatibility shim for the historical pipeline API.

    This keeps older integration tests working while the new
    lightweight detector remains the primary implementation.
    """

    def detect_fields(self, text):
        findings = _to_legacy_findings(detect_sensitive_data(text))
        doc_type = "sensitive_document" if any(findings.values()) else "general_document"
        return findings, doc_type

    def classify_document(self, findings, doc_type):
        score = (
            len(findings.get("financial", [])) * 3
            + len(findings.get("id_number", [])) * 2
            + len(findings.get("email", []))
            + len(findings.get("phone", []))
        )
        if score >= 6:
            risk = "High"
        elif score >= 3:
            risk = "Medium"
        else:
            risk = "Low"
        return {"findings": findings, "risk": {"score": score, "level": risk}, "doc_type": doc_type}