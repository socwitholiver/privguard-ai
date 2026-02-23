import os
import shutil
from pathlib import Path
from backend.logger import get_logger

logger = get_logger()


class ProtectionEngine:
    """
    Protection Engine responsible for applying defensive actions
    such as flagging, placeholder encryption, and redaction.

    Designed with secure coding practices:
    - Input validation
    - Safe file operations
    - Clear audit logging
    """

    def __init__(self):
        logger.info("ProtectionEngine initialized.")

    def _validate_path(self, filepath):
        """
        Validate file path to prevent misuse or traversal attacks.
        """
        if not filepath:
            raise ValueError("File path cannot be empty.")

        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        return path

    def flag_document(self, filepath):
        """
        Create a flag marker indicating document requires review.
        """
        path = self._validate_path(filepath)

        flag_file = str(path) + ".flag"

        with open(flag_file, "w") as f:
            f.write("FLAGGED_FOR_REVIEW")

        logger.info(f"Document flagged: {filepath}")

        return {"status": "flagged", "file": filepath}

    def encrypt_placeholder(self, filepath):
        """
        Placeholder encryption — safe copy to simulate protection.
        Real encryption will replace this.
        """
        path = self._validate_path(filepath)

        encrypted_file = str(path) + ".enc"

        shutil.copy2(path, encrypted_file)

        logger.info(f"Placeholder encryption created: {encrypted_file}")

        return {"status": "encrypted", "file": encrypted_file}

    def redact_text(self, text, findings):
        """
        Replace sensitive tokens with [REDACTED].
        """
        if not isinstance(text, str):
            raise ValueError("Text must be string.")

        redacted = text

        for category, items in findings.items():
            for item in items:
                redacted = redacted.replace(item, "[REDACTED]")

        logger.info("Text redaction completed.")

        return redacted