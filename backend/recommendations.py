def generate_recommendations(findings, level):
    recommendations = []

    if "credit_card" in findings:
        recommendations.append("Immediately redact or encrypt exposed credit card numbers.")

    if "api_key" in findings:
        recommendations.append("Rotate exposed API keys immediately and restrict permissions.")

    if "national_id" in findings:
        recommendations.append("Apply masking to national ID numbers in stored documents.")

    if level in ["High", "Critical"]:
        recommendations.append("Restrict document access and enforce encryption at rest.")

    if not recommendations:
        recommendations.append("No major exposure detected.")

    return recommendations