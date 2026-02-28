"""Performance benchmark for scan pipeline latency and memory usage."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from classification import build_risk_summary
from detection import detect_sensitive_data
from extraction import read_document_text


MANIFEST_PATH = BASE_DIR / "evaluation" / "dataset_manifest.json"
REPORT_PATH = BASE_DIR / "reports" / "perf_benchmark.json"


def benchmark() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    samples = manifest["samples"]
    runs = []

    tracemalloc.start()
    for sample in samples:
        sample_path = BASE_DIR / sample["path"]
        start = time.perf_counter()
        text = read_document_text(sample_path)
        findings = detect_sensitive_data(text)
        _ = build_risk_summary(findings)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        runs.append({"sample_id": sample["id"], "latency_ms": elapsed_ms})

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies = sorted(run["latency_ms"] for run in runs)
    p95_index = max(0, int(round((len(latencies) - 1) * 0.95)))
    p95_latency = latencies[p95_index] if latencies else 0.0

    return {
        "dataset_manifest": str(MANIFEST_PATH.relative_to(BASE_DIR)),
        "samples_benchmarked": len(runs),
        "p95_latency_ms": p95_latency,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "sample_runs": runs,
    }


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = benchmark()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote performance report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
