import re

class IntelligentDataDetector:
    """
    Detects sensitive fields from OCR text.
    Adds document understanding and fuzzy corrections.
    """

    def normalize_text(self, text):
        """
        Clean OCR text for better detection.
        """
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text)

        # Fuzzy corrections for OCR mistakes
        text = text.replace("O", "0")
        text = text.replace("I", "1")
        text = text.replace("l", "1")
        text = text.replace("S", "5")

        # Remove spaces inside numeric sequences
        text = re.sub(r"(\d)\s+(?=\d)", r"\1", text)

        return text

    def detect_fields(self, text):
        """
        Detect sensitive fields in text.
        """
        text = self.normalize_text(text)

        email_pattern = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
        phone_pattern = r"\b07\d{8}\b"
        id_pattern = r"\b\d{8}\b"
        card_pattern = r"\b\d{13,16}\b"
        expiry_pattern = r"(0[1-9]|1[0-2])\/?([0-9]{2}|[0-9]{4})"
        name_pattern = r"[A-Z]{2,}(?:\s[A-Z]{2,})+"

        findings = {
            "email": re.findall(email_pattern, text),
            "phone": re.findall(phone_pattern, text),
            "id_number": re.findall(id_pattern, text),
            "financial": re.findall(card_pattern, text),
            "expiry_date": re.findall(expiry_pattern, text),
            "holder_name": re.findall(name_pattern, text),
        }

        # Document type detection
        doc_type = "Generic Image"
        if "BANK" in text or "MasterCard" in text or "VISA" in text:
            doc_type = "ATM Card"
        elif "NATIONAL ID" in text or "ID" in text:
            doc_type = "National ID"

        return findings, doc_type

    def classify_document(self, findings, doc_type):
        """
        Classify document risk & confidentiality
        """
        risk_score = 0
        if findings["financial"] or findings["id_number"]:
            risk_score = 8
            level = "High"
            label = "Highly Confidential"
        else:
            risk_score = 0
            level = "Low"
            label = "Public"

        classification = {
            "document_type": doc_type,
            "risk": {"score": risk_score, "level": level},
            "classification": {"label": label, "score": risk_score, "confidence": 0.95},
            "findings": findings,
            "recommendations": ["Redact or encrypt sensitive fields."] if risk_score >= 8 else ["No critical risks detected."]
        }

        return classification