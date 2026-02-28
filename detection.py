"""Offline sensitive data detection for PRIVGUARD AI.

This module combines regex pattern matching with lightweight context scoring
to improve precision without internet or heavyweight ML dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, List


EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+254|0)(?:7\d{8}|1\d{8})(?!\w)")
NATIONAL_ID_PATTERN = re.compile(r"\b\d{7,8}\b")
KRA_PIN_PATTERN = re.compile(r"\b[A-Z]\d{9}[A-Z]\b")


TYPE_KEYWORDS = {
    "email": {"email", "e-mail", "contact", "address"},
    "phone": {"phone", "mobile", "tel", "contact"},
    "national_id": {"id", "national", "identity", "citizen", "number"},
    "kra_pin": {"kra", "pin", "tax", "revenue", "identifier"},
}


@dataclass
class SensitiveMatch:
    """A single sensitive match with explainable confidence."""

    data_type: str
    value: str
    start: int
    end: int
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _context_confidence(text: str, start: int, end: int, data_type: str) -> float:
    """Assign confidence using nearby words as a lightweight NLP heuristic."""
    window_start = max(0, start - 40)
    window_end = min(len(text), end + 40)
    context = text[window_start:window_end].lower()
    keywords = TYPE_KEYWORDS.get(data_type, set())
    if not keywords:
        return 0.8

    matched = sum(1 for token in keywords if token in context)
    if matched >= 2:
        return 0.98
    if matched == 1:
        return 0.9
    return 0.78


def _build_matches(text: str, pattern: re.Pattern[str], data_type: str) -> List[SensitiveMatch]:
    matches: List[SensitiveMatch] = []
    seen_values = set()
    for hit in pattern.finditer(text):
        value = _normalize_whitespace(hit.group(0))
        if value in seen_values:
            continue
        seen_values.add(value)
        confidence = _context_confidence(text, hit.start(), hit.end(), data_type)
        reason = "regex+context"
        matches.append(
            SensitiveMatch(
                data_type=data_type,
                value=value,
                start=hit.start(),
                end=hit.end(),
                confidence=confidence,
                reason=reason,
            )
        )
    return matches


def detect_sensitive_data(text: str) -> Dict[str, List[Dict[str, object]]]:
    """Detect sensitive entities from plain text.

    Returns a mapping where each key is a sensitive type and each value is a
    list of serializable match dictionaries.
    """
    findings = {
        "national_ids": _build_matches(text, NATIONAL_ID_PATTERN, "national_id"),
        "phone_numbers": _build_matches(text, PHONE_PATTERN, "phone"),
        "emails": _build_matches(text, EMAIL_PATTERN, "email"),
        "kra_pins": _build_matches(text, KRA_PIN_PATTERN, "kra_pin"),
    }

    # Basic conflict cleanup to avoid phone numbers being interpreted as IDs.
    phone_values = {match.value for match in findings["phone_numbers"]}
    filtered_ids = [
        match for match in findings["national_ids"] if match.value not in phone_values
    ]
    findings["national_ids"] = filtered_ids

    return {key: [item.to_dict() for item in items] for key, items in findings.items()}


def count_sensitive_items(findings: Dict[str, List[Dict[str, object]]]) -> int:
    """Count total sensitive records across all categories."""
    return sum(len(items) for items in findings.values())
