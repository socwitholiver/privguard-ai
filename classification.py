"""Risk classification engine for PRIVGUARD AI."""

from __future__ import annotations

from typing import Dict, List

from config_loader import load_risk_policy

RISK_POLICY = load_risk_policy()
WEIGHTS = RISK_POLICY["weights"]
THRESHOLDS = RISK_POLICY["thresholds"]
DIVERSITY_BONUS = RISK_POLICY["diversity_bonus"]

_HIGH_VALUE_TYPES = {"national_ids", "kra_pins", "passwords", "financial_info"}
_MEDIUM_VALUE_TYPES = {"phone_numbers", "emails"}
_LOW_VALUE_TYPES = {"personal_names"}


def calculate_risk_score(findings: Dict[str, List[dict]]) -> int:
    """Compute weighted risk score (0-100) from detection findings."""
    score = 0
    for data_type, items in findings.items():
        score += WEIGHTS.get(data_type, 0) * len(items)

    active_types = sum(1 for values in findings.values() if values)
    if active_types >= 3:
        score += int(DIVERSITY_BONUS["three_or_more_types"])
    if active_types >= 4:
        score += int(DIVERSITY_BONUS["four_or_more_types"])

    return min(score, 100)


def classify_risk_level(score: int) -> str:
    """Map score to a low/medium/high risk label."""
    if score >= int(THRESHOLDS["high"]):
        return "High"
    if score >= int(THRESHOLDS["medium"]):
        return "Medium"
    return "Low"


def protection_policy(findings: Dict[str, List[dict]], risk_level: str) -> Dict[str, object]:
    """Return the automatic protection action to apply without user input."""
    total_items = sum(len(items) for items in findings.values())
    has_high_value = any(findings.get(key) for key in _HIGH_VALUE_TYPES)
    has_medium_value = any(findings.get(key) for key in _MEDIUM_VALUE_TYPES)
    has_low_value = any(findings.get(key) for key in _LOW_VALUE_TYPES)

    if total_items == 0:
        return {
            "mode": "allow",
            "label": "Allow Document",
            "redact": False,
            "encrypt": False,
            "reason": "No sensitive data was detected.",
        }

    if has_high_value:
        return {
            "mode": "redact_encrypt",
            "label": "Redact and Encrypt",
            "redact": True,
            "encrypt": True,
            "reason": "High-risk identifiers, secrets, or financial data were detected.",
        }

    if has_medium_value:
        return {
            "mode": "redact",
            "label": "Redact Sensitive Data",
            "redact": True,
            "encrypt": False,
            "reason": "Contact details or other medium-risk personal data were detected.",
        }

    if has_low_value or risk_level == "Low":
        return {
            "mode": "allow",
            "label": "Allow Document",
            "redact": False,
            "encrypt": False,
            "reason": "Only low-risk personal context was detected.",
        }

    if risk_level == "High":
        return {
            "mode": "redact_encrypt",
            "label": "Redact and Encrypt",
            "redact": True,
            "encrypt": True,
            "reason": "The policy engine classified the document as high risk.",
        }

    if risk_level == "Medium":
        return {
            "mode": "redact",
            "label": "Redact Sensitive Data",
            "redact": True,
            "encrypt": False,
            "reason": "The policy engine classified the document as medium risk.",
        }

    return {
        "mode": "allow",
        "label": "Allow Document",
        "redact": False,
        "encrypt": False,
        "reason": "No automatic protection action is required.",
    }


def recommended_actions(findings: Dict[str, List[dict]], risk_level: str) -> List[str]:
    """Describe the automatic actions PrivGuard will take for the user."""
    policy = protection_policy(findings, risk_level)

    if policy["mode"] == "redact_encrypt":
        return [
            "PrivGuard will redact sensitive sections for sharing.",
            "PrivGuard will encrypt the original document for secure storage.",
            "PrivGuard will store the encryption key in the local vault automatically.",
        ]

    if policy["mode"] == "redact":
        return [
            "PrivGuard will redact sensitive sections before the document is shared.",
            "PrivGuard will store the protected copy and compliance report automatically.",
        ]

    return [
        "PrivGuard will allow this document and log the result automatically.",
    ]


def primary_action(findings: Dict[str, List[dict]], risk_level: str) -> str:
    """Return the automatic protection action selected by policy."""
    return str(protection_policy(findings, risk_level)["mode"])


def compliance_insights(findings: Dict[str, List[dict]], risk_level: str) -> List[str]:
    """Generate concise compliance guidance aligned with automated workflow."""
    policy = protection_policy(findings, risk_level)
    total = sum(len(v) for v in findings.values())
    insights: List[str] = []

    if total == 0:
        insights.append("No direct personal identifiers were detected in the provided document.")
        insights.append("The document can proceed without additional protection.")
        return insights

    insights.append("PrivGuard applies data minimization by automatically reducing exposure before storage or sharing.")
    insights.append("Protection decisions follow the local policy engine without requiring user intervention.")

    if policy["mode"] == "redact_encrypt":
        insights.append("High-risk identifiers triggered automatic redaction and encryption.")
    elif policy["mode"] == "redact":
        insights.append("Medium-risk personal data triggered automatic redaction.")
    else:
        insights.append("Only low-risk data was found, so the document is allowed with logging only.")

    return insights


def build_risk_summary(findings: Dict[str, List[dict]]) -> Dict[str, object]:
    """Create a single risk summary payload for dashboard/automation output."""
    score = calculate_risk_score(findings)
    level = classify_risk_level(score)
    policy = protection_policy(findings, level)
    return {
        "score": score,
        "level": level,
        "counts": {k: len(v) for k, v in findings.items()},
        "insights": compliance_insights(findings, level),
        "recommendations": recommended_actions(findings, level),
        "primary_action": policy["mode"],
        "policy": policy,
    }
