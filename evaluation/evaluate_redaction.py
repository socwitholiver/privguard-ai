"""Evaluate redaction quality leakage rate over benchmark samples."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from detection import detect_sensitive_data
from protection import redact_text, verify_redaction_quality


MANIFEST_PATH = BASE_DIR / "evaluation" / "dataset_manifest.json"
REPORT_PATH = BASE_DIR / "reports" / "eval_redaction.json"


def evaluate() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    total_items = 0
    total_leaks = 0
    sample_results = []

    for sample in manifest["samples"]:
        sample_path = BASE_DIR / sample["path"]
        text = sample_path.read_text(encoding="utf-8")
        findings = detect_sensitive_data(text)
        redacted = redact_text(text, findings)
        quality = verify_redaction_quality(findings, redacted)
        total_items += int(quality["total_sensitive_items"])
        total_leaks += int(quality["leak_count"])
        sample_results.append(
            {
                "sample_id": sample["id"],
                "quality_status": quality["quality_status"],
                "coverage_percent": quality["coverage_percent"],
                "leak_count": quality["leak_count"],
                "total_sensitive_items": quality["total_sensitive_items"],
            }
        )

    leakage_rate = 0.0 if total_items == 0 else round(total_leaks / total_items, 6)
    return {
        "dataset_manifest": str(MANIFEST_PATH.relative_to(BASE_DIR)),
        "redaction_leakage_rate": leakage_rate,
        "total_leaks": total_leaks,
        "total_sensitive_items": total_items,
        "samples": sample_results,
    }


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote redaction report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
