import re
from backend.logger import get_logger

logger = get_logger()


class SensitiveDataDetector:
    def __init__(self):
        logger.info("SensitiveDataDetector initialized.")

        self.patterns = {
            "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
            "phone": re.compile(r"(?:\+254|0)?7\d{8}"),
            "id_number": re.compile(r"\b\d{6,8}\b"),
            "financial": re.compile(r"\b\d{12,16}\b")
        }

    def detect(self, text):
        findings = {}

        for label, pattern in self.patterns.items():
            matches = pattern.findall(text)
            findings[label] = matches

        logger.info("Detection completed.")
        return findings
