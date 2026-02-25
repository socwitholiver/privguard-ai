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