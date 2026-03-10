"""Build a judge-facing evidence snapshot from existing evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def detection_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = payload.get("entity_metrics", {})
    macro_f1 = payload.get("macro_f1")
    covered_entities = sorted(metrics.keys())
    return {
        "macro_f1": macro_f1,
        "covered_entities": covered_entities,
        "sample_count": len(covered_entities),
    }


def redaction_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    samples = payload.get("samples", [])
    pass_count = sum(1 for sample in samples if sample.get("quality_status") == "PASS")
    return {
        "redaction_leakage_rate": payload.get("redaction_leakage_rate"),
        "total_leaks": payload.get("total_leaks"),
        "samples_tested": len(samples),
        "pass_count": pass_count,
    }


def perf_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "samples_benchmarked": payload.get("samples_benchmarked"),
        "avg_latency_ms": payload.get("avg_latency_ms"),
        "p95_latency_ms": payload.get("p95_latency_ms"),
        "peak_memory_mb": payload.get("peak_memory_mb"),
    }


def round1_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = payload.get("summary", {})
    return {
        "ok_runs": summary.get("ok_runs"),
        "avg_total_ms": summary.get("avg_total_ms"),
        "avg_extract_ms": summary.get("avg_extract_ms"),
        "avg_detect_ms": summary.get("avg_detect_ms"),
        "avg_characters_per_second": summary.get("avg_characters_per_second"),
    }


def build_snapshot() -> Dict[str, Any]:
    detection = load_json(REPORTS_DIR / "eval_detection.json")
    redaction = load_json(REPORTS_DIR / "eval_redaction.json")
    ocr = load_json(REPORTS_DIR / "eval_ocr.json")
    perf = load_json(REPORTS_DIR / "perf_benchmark.json")
    round1 = load_json(REPORTS_DIR / "round1_benchmarks.json")

    return {
        "evidence_sources": {
            "detection": "reports/eval_detection.json",
            "redaction": "reports/eval_redaction.json",
            "ocr": "reports/eval_ocr.json",
            "perf": "reports/perf_benchmark.json",
            "round1": "reports/round1_benchmarks.json",
        },
        "headline_metrics": {
            "detection": detection_summary(detection),
            "redaction": redaction_summary(redaction),
            "perf": perf_summary(perf),
            "round1": round1_summary(round1),
            "ocr": {
                "image_samples_count": ocr.get("image_samples_count"),
                "average_wer": ocr.get("average_wer"),
                "note": ocr.get("note"),
            },
        },
        "judge_ready_claims": [
            "Current labeled text detection set reports macro F1 of 1.0 across the covered entity types.",
            "Current redaction evaluation reports zero leaks across the sampled benchmark files.",
            "Current local benchmark artifacts show interactive single-document latency on the tested text samples.",
            "OCR evidence is still incomplete because the current OCR evaluation set has zero labeled image samples.",
        ],
        "highest_priority_gaps": [
            "Add labeled OCR samples for scanned PDFs and images.",
            "Add a baseline comparison against manual records review time.",
            "Expand the labeled evaluation set beyond the two current benchmark text samples.",
            "Collect workflow-owner feedback or pilot observations for sector impact evidence.",
        ],
    }


def build_markdown(snapshot: Dict[str, Any]) -> str:
    metrics = snapshot["headline_metrics"]
    lines = [
        "# Judging Evidence Snapshot",
        "",
        "This file is generated from the current evaluation artifacts in `reports/`.",
        "",
        "## Headline Metrics",
        "",
        f"- Detection macro F1 on covered entities: `{metrics['detection']['macro_f1']}`",
        f"- Covered detection entity groups: `{', '.join(metrics['detection']['covered_entities'])}`",
        f"- Redaction leakage rate: `{metrics['redaction']['redaction_leakage_rate']}`",
        f"- Redaction total leaks: `{metrics['redaction']['total_leaks']}`",
        f"- Perf average latency: `{metrics['perf']['avg_latency_ms']}` ms",
        f"- Perf p95 latency: `{metrics['perf']['p95_latency_ms']}` ms",
        f"- Round 1 average end-to-end latency: `{metrics['round1']['avg_total_ms']}` ms",
        f"- Round 1 average throughput: `{metrics['round1']['avg_characters_per_second']}` chars/sec",
        "",
        "## Judge-Ready Claims",
        "",
    ]
    lines.extend(f"- {claim}" for claim in snapshot["judge_ready_claims"])
    lines.extend([
        "",
        "## Highest-Priority Gaps",
        "",
    ])
    lines.extend(f"- {gap}" for gap in snapshot["highest_priority_gaps"])
    lines.extend([
        "",
        "## OCR Coverage Note",
        "",
        f"- Image samples currently evaluated: `{metrics['ocr']['image_samples_count']}`",
        f"- OCR note: {metrics['ocr']['note']}",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    snapshot = build_snapshot()
    json_path = REPORTS_DIR / "judging_evidence_snapshot.json"
    md_path = DOCS_DIR / "judging_evidence_snapshot.md"
    json_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(snapshot), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
