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