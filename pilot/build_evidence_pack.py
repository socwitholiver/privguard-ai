"""Build pilot evidence pack from KPI reports, docs, and audit export."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from ops.audit_export import export_signed_audit


BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
DOCS_DIR = BASE_DIR / "docs"
PILOT_DIR = BASE_DIR / "pilot"


def build_pack() -> dict:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pack_dir = PILOT_DIR / f"evidence_pack_{timestamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    copied_reports = []
    for report in REPORTS_DIR.glob("*.json"):
        target = pack_dir / report.name
        shutil.copy2(report, target)
        copied_reports.append(report.name)

    compliance_doc = DOCS_DIR / "compliance_dpa2019.md"
    copied_docs = []
    if compliance_doc.exists():
        target = pack_dir / compliance_doc.name
        shutil.copy2(compliance_doc, target)
        copied_docs.append(compliance_doc.name)

    export_result = export_signed_audit(limit=5000)
    audit_export = Path(export_result["export_file"])
    audit_sig = Path(export_result["signature_file"])
    shutil.copy2(audit_export, pack_dir / audit_export.name)
    shutil.copy2(audit_sig, pack_dir / audit_sig.name)

    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "reports": copied_reports,
        "docs": copied_docs,
        "audit_export": audit_export.name,
        "audit_signature": audit_sig.name,
    }
    manifest_path = pack_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive_base = PILOT_DIR / f"evidence_pack_{timestamp}"
    zip_path = shutil.make_archive(str(archive_base), "zip", root_dir=pack_dir)
    return {"pack_dir": str(pack_dir), "zip_file": str(zip_path)}


def main() -> None:
    result = build_pack()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
