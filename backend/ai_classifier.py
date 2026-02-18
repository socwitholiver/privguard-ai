class AIClassifier:
    def generate_insights(self, findings, risk_result):
        """
        Generate explanations and recommendations based on findings and risk score.
        """

        level = risk_result.get("level", "Unknown")

        reasons = []
        recommendations = []

        # Reasons
        if findings.get("financial"):
            reasons.append("Financial data detected which could lead to fraud.")

        if findings.get("id_number"):
            reasons.append("Personal identification numbers detected.")

        if findings.get("email") or findings.get("phone"):
            reasons.append("Contact information present which could expose individuals.")

        if level == "High":
            reasons.append("Overall risk level is high due to sensitive data concentration.")

        # Recommendations
        if level == "High":
            recommendations.append("Encrypt this document immediately.")
            recommendations.append("Restrict access permissions.")
        elif level == "Medium":
            recommendations.append("Review document before sharing.")
            recommendations.append("Consider masking sensitive fields.")
        else:
            recommendations.append("Monitor document usage.")

        return {
            "risk_level": level,
            "reasons": reasons,
            "recommendations": recommendations
        }
