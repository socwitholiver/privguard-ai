def calculate_risk(findings):
    score = 0

    weights = {
        "email": 1,
        "phone": 2,
        "national_id": 5,
        "credit_card": 10,
        "api_key": 8
    }

    for category, items in findings.items():
        score += weights.get(category, 1) * len(items)

    if score == 0:
        level = "Low"
    elif score < 10:
        level = "Medium"
    elif score < 25:
        level = "High"
    else:
        level = "Critical"

    return score, level