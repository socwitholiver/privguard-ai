"""
PrivGuard AI Classifier
-----------------------

Classifies documents based on detected sensitive data.

This is a rule-based AI simulation for MVP purposes.
Designed to be easily replaceable with a real ML/NLP model later.

Author: PrivGuard Team
"""

from typing import Dict


class AIClassifier:
    """
    AI-powered document classifier.

    Determines document sensitivity level based on findings
    from SensitiveDataDetector.
    """

    def __init__(self):
        # Placeholder for future model loading
        # e.g. load NLP model, embeddings, etc.
        pass

    def classify(self, findings: Dict) -> Dict:
        """
        Classify document sensitivity.

        Parameters:
        ----------
        findings : dict
            Dictionary of detected sensitive data.

        Returns:
        -------
        dict
            Classification result with label and confidence.
        """

        score = 0

        # Assign weights based on sensitivity
        if findings.get("id_number"):
            score += 3

        if findings.get("financial"):
            score += 3

        if findings.get("email"):
            score += 1

        if findings.get("phone"):
            score += 1

        # Determine classification
        if score >= 5:
            label = "Highly Confidential"
            confidence = 0.95

        elif score >= 3:
            label = "Confidential"
            confidence = 0.85

        elif score >= 1:
            label = "Internal"
            confidence = 0.70

        else:
            label = "Public"
            confidence = 0.99

        return {
            "label": label,
            "confidence": confidence,
            "score": score
        }

    def generate_insights(self, findings: Dict, risk_result: Dict) -> Dict:
        """
        Legacy compatibility API expected by older tests.

        Returns lightweight reasons/recommendations aligned to detected
        sensitive types and the provided risk level.
        """
        risk_level = str(risk_result.get("level", "Low"))
        reasons = []
        recommendations = []

        if findings.get("financial"):
            reasons.append("Financial identifiers detected.")
            recommendations.append("Mask or encrypt financial fields before sharing.")
        if findings.get("id_number"):
            reasons.append("National ID values detected.")
            recommendations.append("Redact ID values from outbound documents.")
        if findings.get("email"):
            reasons.append("Email addresses detected.")
            recommendations.append("Limit exposure of contact data to authorized users.")
        if findings.get("phone"):
            reasons.append("Phone numbers detected.")
            recommendations.append("Apply masking for phone values in reports.")

        if risk_level in {"High", "Critical"}:
            recommendations.append("Restrict access and enforce strong encryption controls.")

        if not reasons:
            reasons.append("No sensitive data patterns were detected.")
        if not recommendations:
            recommendations.append("Maintain current controls and continue monitoring.")

        return {
            "risk_level": risk_level,
            "reasons": reasons,
            "recommendations": recommendations,
        }