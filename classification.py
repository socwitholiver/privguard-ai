"""Risk classification engine for PRIVGUARD AI."""

from __future__ import annotations

from typing import Dict, List


WEIGHTS = {
    "national_ids": 30,
    "phone_numbers": 15,
    "emails": 10,
    "kra_pins": 35,
}


def calculate_risk_score(findings: Dict[str, List[dict]]) -> int:
    """Compute weighted risk score (0-100) from detection findings."""
    score = 0
    for data_type, items in findings.items():
        score += WEIGHTS.get(data_type, 0) * len(items)

    # A diversity bonus reflects compounding risk from multiple data types.
    active_types = sum(1 for values in findings.values() if values)
    if active_types >= 3:
        score += 10
    if active_types >= 4:
        score += 10

    return min(score, 100)


def classify_risk_level(score: int) -> str:
    """Map score to a low/medium/high risk label."""
    if score >= 70:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def compliance_insights(findings: Dict[str, List[dict]], risk_level: str) -> List[str]:
    """Generate concise recommendations aligned with Kenya DPA 2019 principles."""
    insights: List[str] = []
    total = sum(len(v) for v in findings.values())

    if total == 0:
        insights.append("No direct personal identifiers detected in the provided text.")
        insights.append("Maintain secure storage and role-based access controls.")
        return insights

    insights.append(
        "Apply data minimization: retain only personal data required for your process."
    )
    insights.append(
        "Use purpose limitation: process personal data only for clearly defined lawful use."
    )

    if findings.get("national_ids") or findings.get("kra_pins"):
        insights.append(
            "High-value identifiers found: enforce strict access controls and audit logs."
        )

    if risk_level == "High":
        insights.append(
            "Immediate action advised: redact/mask before sharing and encrypt at rest."
        )
    elif risk_level == "Medium":
        insights.append(
            "Apply masking for routine use and encryption for storage or transmission."
        )
    else:
        insights.append("Continue regular monitoring and periodic privacy reviews.")

    return insights


def build_risk_summary(findings: Dict[str, List[dict]]) -> Dict[str, object]:
    """Create a single risk summary payload for dashboard/CLI output."""
    score = calculate_risk_score(findings)
    level = classify_risk_level(score)
    return {
        "score": score,
        "level": level,
        "counts": {k: len(v) for k, v in findings.items()},
        "insights": compliance_insights(findings, level),
    }
