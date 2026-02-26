"""
PrivGuard AI Intelligence Engine

Provides:
- Context-aware sensitive data analysis
- Risk reasoning
- Smart recommendations

Designed for offline processing.
"""

import re
from typing import Dict, List


class AIEngine:
    """
    Hybrid AI analysis engine combining pattern detection
    with contextual reasoning.
    """

    def __init__(self):
        # Keywords for contextual understanding
        self.financial_keywords = [
            "card", "account", "bank", "visa", "mastercard", "cvv", "expiry"
        ]

        self.identity_keywords = [
            "id", "national", "passport", "kra", "pin", "identity"
        ]

    def analyze_context(self, text: str) -> Dict:
        """
        Determine document context.
        """

        text_lower = text.lower()

        financial_hits = sum(word in text_lower for word in self.financial_keywords)
        identity_hits = sum(word in text_lower for word in self.identity_keywords)

        return {
            "financial_context": financial_hits > 0,
            "identity_context": identity_hits > 0,
        }

    def generate_recommendations(self, findings: Dict) -> List[str]:
        """
        Provide security recommendations.
        """

        recommendations = []

        if findings.get("financial"):
            recommendations.append("Encrypt or mask financial information.")

        if findings.get("id_number"):
            recommendations.append("Redact national ID numbers.")

        if findings.get("email"):
            recommendations.append("Restrict access to personal emails.")

        if findings.get("phone"):
            recommendations.append("Apply privacy controls to phone numbers.")

        if not recommendations:
            recommendations.append("No critical risks detected.")

        return recommendations

    def confidence_score(self, findings: Dict) -> float:
        """
        Estimate confidence level.
        """

        total_items = sum(len(v) for v in findings.values())

        if total_items >= 5:
            return 0.95
        elif total_items >= 3:
            return 0.85
        elif total_items >= 1:
            return 0.70
        else:
            return 0.50