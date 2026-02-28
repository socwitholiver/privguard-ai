"""Protection actions for PRIVGUARD AI (redact, mask, encrypt)."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Dict, List, Set

from cryptography.fernet import Fernet, InvalidToken


def generate_encryption_key() -> bytes:
    """Generate a secure symmetric key."""
    return Fernet.generate_key()


def save_encryption_key(key: bytes, key_path: Path) -> None:
    """Persist encryption key with strict file permissions where possible."""
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    try:
        # Works on Unix-like systems; no-op on Windows if unsupported.
        key_path.chmod(0o600)
    except OSError:
        pass


def load_encryption_key(key_path: Path) -> bytes:
    """Load an encryption key from file."""
    return key_path.read_bytes()


def encrypt_text(text: str, key: bytes) -> str:
    """Encrypt plain text and return a URL-safe token."""
    fernet = Fernet(key)
    encrypted = fernet.encrypt(text.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_text(token: str, key: bytes) -> str:
    """Decrypt token to plain text."""
    fernet = Fernet(key)
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Decryption failed. Invalid key or token.") from exc


def _collect_unique_values(findings: Dict[str, List[dict]]) -> Set[str]:
    values: Set[str] = set()
    for entries in findings.values():
        for entry in entries:
            values.add(str(entry["value"]))
    return values


def redact_text(text: str, findings: Dict[str, List[dict]]) -> str:
    """Replace detected sensitive values with a fixed redaction token."""
    output = text
    for value in sorted(_collect_unique_values(findings), key=len, reverse=True):
        output = output.replace(value, "[REDACTED]")
    return output


def mask_value(value: str) -> str:
    """Mask a value while keeping short prefix/suffix for readability."""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


def mask_text(text: str, findings: Dict[str, List[dict]]) -> str:
    """Mask sensitive values in text while preserving some structure."""
    output = text
    for value in sorted(_collect_unique_values(findings), key=len, reverse=True):
        output = output.replace(value, mask_value(value))
    return output


def validate_encrypted_token(token: str) -> bool:
    """Shallow check for Fernet token shape before decryption."""
    try:
        base64.urlsafe_b64decode(token.encode("utf-8"))
        return True
    except Exception:
        return False


def verify_redaction_quality(
    original_findings: Dict[str, List[dict]], protected_text: str
) -> Dict[str, object]:
    """Verify whether protected output still contains original sensitive values."""
    leaked = []
    for data_type, entries in original_findings.items():
        for entry in entries:
            value = str(entry.get("value", ""))
            # Use token-aware matching to avoid false positives from substrings.
            pattern = re.compile(rf"(?<!\w){re.escape(value)}(?!\w)")
            if value and pattern.search(protected_text):
                leaked.append({"data_type": data_type, "value": value})

    total_items = sum(len(items) for items in original_findings.values())
    leak_count = len(leaked)
    coverage = 100.0 if total_items == 0 else round(((total_items - leak_count) / total_items) * 100, 2)
    return {
        "total_sensitive_items": total_items,
        "leak_count": leak_count,
        "leaked_items": leaked,
        "coverage_percent": coverage,
        "quality_status": "PASS" if leak_count == 0 else "FAIL",
    }
