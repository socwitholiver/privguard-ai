"""Evaluate detection quality against ground truth annotations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Set

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from detection import detect_sensitive_data


MANIFEST_PATH = BASE_DIR / "evaluation" / "dataset_manifest.json"
REPORT_PATH = BASE_DIR / "reports" / "eval_detection.json"
ENTITY_TYPES = ["national_ids", "phone_numbers", "emails", "kra_pins"]


def _safe_div(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


def _extract_values(findings: Dict[str, list], entity_type: str) -> Set[str]:
    return {str(item["value"]) for item in findings.get(entity_type, [])}


def evaluate() -> Dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    totals = {
        entity: {"tp": 0, "fp": 0, "fn": 0}
        for entity in ENTITY_TYPES
    }

    for sample in manifest["samples"]:
        sample_path = BASE_DIR / sample["path"]
        gt_path = BASE_DIR / sample["ground_truth"]
        text = sample_path.read_text(encoding="utf-8")
        findings = detect_sensitive_data(text)
        ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))

        for entity in ENTITY_TYPES:
            pred = _extract_values(findings, entity)
            truth = set(ground_truth.get(entity, []))
            totals[entity]["tp"] += len(pred & truth)
            totals[entity]["fp"] += len(pred - truth)
            totals[entity]["fn"] += len(truth - pred)

    per_entity = {}
    macro_f1_sum = 0.0
    for entity in ENTITY_TYPES:
        tp = totals[entity]["tp"]
        fp = totals[entity]["fp"]
        fn = totals[entity]["fn"]
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0
        per_entity[entity] = {
            "precision": precision,
            "recall": recall,
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        macro_f1_sum += f1

    report = {
        "dataset_manifest": str(MANIFEST_PATH.relative_to(BASE_DIR)),
        "entity_metrics": per_entity,
        "macro_f1": round(macro_f1_sum / len(ENTITY_TYPES), 4),
    }
    return report


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote detection report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
