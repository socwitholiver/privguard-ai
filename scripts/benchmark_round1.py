"""Round 1 benchmark runner for PRIVGUARD AI.

Runs local benchmarks for extraction, detection, classification,
redaction, and redaction-quality verification on provided files.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from classification import build_risk_summary
from detection import count_sensitive_items, detect_sensitive_data
from extraction import read_document_text
from protection import redact_text, verify_redaction_quality


DEFAULT_FILES = [
    Path("demo_docs/school_admission_sample.txt"),
    Path("demo_docs/sme_payroll_sample.txt"),
]


def _ms(start: float, end: float) -> float:
    return round((end - start) * 1000, 2)


def benchmark_file(path: Path) -> dict:
    if not path.exists():
        return {
            "file": str(path),
            "status": "missing",
            "error": "file not found",
        }

    try:
        t0 = time.perf_counter()
        extracted_text = read_document_text(path)
        t1 = time.perf_counter()

        findings = detect_sensitive_data(extracted_text)
        t2 = time.perf_counter()

        risk = build_risk_summary(findings)
        t3 = time.perf_counter()

        redacted = redact_text(extracted_text, findings)
        t4 = time.perf_counter()

        quality = verify_redaction_quality(findings, redacted)
        t5 = time.perf_counter()

        total_items = count_sensitive_items(findings)
        total_ms = _ms(t0, t5)
        chars = max(len(extracted_text), 1)
        chars_per_sec = round(chars / max((t5 - t0), 0.001), 2)

        return {
            "file": str(path),
            "status": "ok",
            "timings_ms": {
                "extract": _ms(t0, t1),
                "detect": _ms(t1, t2),
                "classify": _ms(t2, t3),
                "redact": _ms(t3, t4),
                "verify_quality": _ms(t4, t5),
                "total": total_ms,
            },
            "metrics": {
                "characters": chars,
                "characters_per_second": chars_per_sec,
                "sensitive_item_count": total_items,
                "risk_level": risk.get("level"),
                "risk_score": risk.get("score"),
                "redaction_quality_status": quality.get("quality_status"),
                "redaction_coverage_percent": quality.get("coverage_percent"),
                "leak_count": quality.get("leak_count"),
            },
        }
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        return {
            "file": str(path),
            "status": "error",
            "error": str(exc),
        }


def summarize(results: list[dict]) -> dict:
    ok_runs = [r for r in results if r.get("status") == "ok"]
    if not ok_runs:
        return {"ok_runs": 0}

    avg_total = round(
        sum(r["timings_ms"]["total"] for r in ok_runs) / len(ok_runs), 2
    )
    avg_extract = round(
        sum(r["timings_ms"]["extract"] for r in ok_runs) / len(ok_runs), 2
    )
    avg_detect = round(
        sum(r["timings_ms"]["detect"] for r in ok_runs) / len(ok_runs), 2
    )
    avg_chars_per_sec = round(
        sum(r["metrics"]["characters_per_second"] for r in ok_runs) / len(ok_runs), 2
    )

    return {
        "ok_runs": len(ok_runs),
        "avg_total_ms": avg_total,
        "avg_extract_ms": avg_extract,
        "avg_detect_ms": avg_detect,
        "avg_characters_per_second": avg_chars_per_sec,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round 1 MVP benchmarks.")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Optional file paths. If omitted, demo_docs defaults are used.",
    )
    parser.add_argument(
        "--output",
        default="reports/round1_benchmarks.json",
        help="Output JSON path for benchmark report.",
    )
    args = parser.parse_args()

    files = [Path(p) for p in args.files] if args.files else DEFAULT_FILES
    results = [benchmark_file(path) for path in files]
    summary = summarize(results)

    payload = {
        "generated_at_epoch": int(time.time()),
        "files_tested": [str(p) for p in files],
        "summary": summary,
        "results": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Saved benchmark report to: {out_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
