@app.route("/api/dashboard-data")
def dashboard_data():
    scans = Scan.query.all()

    total_scans = len(scans)
    critical = sum(1 for s in scans if s.risk_level == "Critical")
    high = sum(1 for s in scans if s.risk_level == "High")
    medium = sum(1 for s in scans if s.risk_level == "Medium")
    low = sum(1 for s in scans if s.risk_level == "Low")

    recent_scans = sorted(
        scans, key=lambda x: x.timestamp, reverse=True
    )[:5]

    return jsonify({
        "total_scans": total_scans,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "recent_scans": [
            {
                "id": s.id,
                "filename": s.filename,
                "risk_level": s.risk_level,
                "risk_score": s.risk_score,
                "timestamp": s.timestamp
            } for s in recent_scans
        ]
    })