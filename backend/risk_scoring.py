from backend.logger import get_logger

logger = get_logger()


class RiskScorer:
    """
    Assigns Low, Medium, or High risk levels to a document
    based on the number and type of sensitive items detected.
    """

    def __init__(self):
        logger.info("RiskScorer initialized.")

        # Define risk weights for each type
        self.weights = {
            "email": 1,
            "phone": 1,
            "id_number": 2,
            "financial": 3
        }

    def score(self, findings: dict):
        """
        findings: dict from SensitiveDataDetector.detect()
        Example:
        {
            "email": ["test@example.com"],
            "phone": ["0712345678"],
            "id_number": ["12345678"],
            "financial": ["1234567890123456"]
        }
        Returns:
        {
            "score": int,
            "level": "Low"/"Medium"/"High"
        }
        """

        total_score = 0

        for key, items in findings.items():
            count = len(items)
            weight = self.weights.get(key, 1)
            total_score += count * weight

        # Determine risk level
        if total_score >= 6:
            level = "High"
        elif total_score >= 3:
            level = "Medium"
        else:
            level = "Low"

        logger.info(f"Document scored {total_score} -> {level}")
        return {"score": total_score, "level": level}
