"""Evaluate OCR quality (WER) when image samples are available."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from extraction import IMAGE_SUFFIXES, read_document_text


MANIFEST_PATH = BASE_DIR / "evaluation" / "dataset_manifest.json"
REPORT_PATH = BASE_DIR / "reports" / "eval_ocr.json"


def _tokenize(text: str) -> List[str]:
    return [token.strip().lower() for token in text.split() if token.strip()]


def _wer(reference: str, hypothesis: str) -> float:
    ref = _tokenize(reference)
    hyp = _tokenize(hypothesis)
    if not ref:
        return 0.0

    dp = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        dp[i][0] = i
    for j in range(len(hyp) + 1):
        dp[0][j] = j

    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return round(dp[-1][-1] / len(ref), 4)


def evaluate() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    image_samples = [s for s in manifest["samples"] if Path(s["path"]).suffix.lower() in IMAGE_SUFFIXES]
    sample_results = []

    for sample in image_samples:
        sample_path = BASE_DIR / sample["path"]
        gt_path = BASE_DIR / sample["ground_truth"]
        ground_truth_text = json.loads(gt_path.read_text(encoding="utf-8")).get("reference_text", "")
        try:
            extracted_text = read_document_text(sample_path)
            wer = _wer(ground_truth_text, extracted_text)
            sample_results.append({"sample_id": sample["id"], "wer": wer, "status": "ok"})
        except Exception as exc:
            sample_results.append({"sample_id": sample["id"], "status": "error", "error": str(exc)})

    available_wers = [item["wer"] for item in sample_results if "wer" in item]
    avg_wer = round(sum(available_wers) / len(available_wers), 4) if available_wers else None
    return {
        "dataset_manifest": str(MANIFEST_PATH.relative_to(BASE_DIR)),
        "image_samples_count": len(image_samples),
        "average_wer": avg_wer,
        "samples": sample_results,
        "note": "Add image samples with 'reference_text' in ground truth for full OCR KPI coverage.",
    }


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote OCR report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
