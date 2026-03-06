"""Offline sensitive data detection for PRIVGUARD AI.

This module combines regex pattern matching with lightweight context scoring
to improve precision without internet or heavyweight ML dependencies.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List

from config_loader import load_detection_config

DETECTION_CONFIG = load_detection_config()
PATTERNS = DETECTION_CONFIG["patterns"]

EMAIL_PATTERN = re.compile(PATTERNS["emails"])
PHONE_PATTERN = re.compile(PATTERNS["phone_numbers"])
NATIONAL_ID_PATTERN = re.compile(PATTERNS["national_ids"])
KRA_PIN_PATTERN = re.compile(PATTERNS["kra_pins"])
PASSWORD_PATTERN = re.compile(PATTERNS["passwords"])
FINANCIAL_PATTERN = re.compile(PATTERNS["financial_info"])
PERSONAL_NAME_PATTERN = re.compile(PATTERNS["personal_names"])

TYPE_KEYWORDS = {
    key: set(values) for key, values in DETECTION_CONFIG["type_keywords"].items()
}

_NAME_STOPWORDS = {
    "account",
    "address",
    "amount",
    "balance",
    "bank",
    "client",
    "contact",
    "customer",
    "email",
    "employee",
    "full",
    "id",
    "invoice",
    "kra",
    "name",
    "number",
    "password",
    "payee",
    "payment",
    "phone",
    "pin",
    "recipient",
    "salary",
    "secret",
    "student",
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


def _is_plausible_password(value: str) -> bool:
    return len(value.strip()) >= 4


def _is_plausible_financial(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 4 or any(currency in value.upper() for currency in {"KES", "KSH", "USD", "EUR", "GBP", "$"})


def _is_plausible_personal_name(value: str) -> bool:
    tokens = [token.strip("'-").lower() for token in value.split() if token.strip("'-")]
    if len(tokens) < 2:
        return False
    if any(token in _NAME_STOPWORDS for token in tokens):
        return False
    return all(len(token) >= 2 for token in tokens)


def _build_matches(
    text: str,
    pattern: re.Pattern[str],
    data_type: str,
    *,
    group_index: int = 0,
    validator: Callable[[str], bool] | None = None,
) -> List[SensitiveMatch]:
    matches: List[SensitiveMatch] = []
    seen_values = set()
    for hit in pattern.finditer(text):
        raw_value = hit.group(group_index)
        if raw_value is None:
            continue
        value = _normalize_whitespace(raw_value.strip(" :;,-"))
        if not value or value in seen_values:
            continue
        if validator and not validator(value):
            continue
        seen_values.add(value)
        confidence = _context_confidence(text, hit.start(), hit.end(), data_type)
        matches.append(
            SensitiveMatch(
                data_type=data_type,
                value=value,
                start=hit.start(),
                end=hit.end(),
                confidence=confidence,
                reason="regex+context",
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
        "passwords": _build_matches(
            text,
            PASSWORD_PATTERN,
            "password",
            group_index=1,
            validator=_is_plausible_password,
        ),
        "financial_info": _build_matches(
            text,
            FINANCIAL_PATTERN,
            "financial_info",
            group_index=1,
            validator=_is_plausible_financial,
        ),
        "personal_names": _build_matches(
            text,
            PERSONAL_NAME_PATTERN,
            "personal_name",
            group_index=1,
            validator=_is_plausible_personal_name,
        ),
    }

    phone_values = {match.value for match in findings["phone_numbers"]}
    id_values = {match.value for match in findings["national_ids"]}
    findings["national_ids"] = [
        match for match in findings["national_ids"] if match.value not in phone_values
    ]
    findings["financial_info"] = [
        match
        for match in findings["financial_info"]
        if match.value not in phone_values and match.value not in id_values
    ]

    return {key: [item.to_dict() for item in items] for key, items in findings.items()}


def count_sensitive_items(findings: Dict[str, List[Dict[str, object]]]) -> int:
    """Count total sensitive records across all categories."""
    return sum(len(items) for items in findings.values())