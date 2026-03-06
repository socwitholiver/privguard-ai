"""Document metadata repository for the PrivGuard secure vault."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from storage.db import get_conn, init_db

ARTIFACT_ORDER = ["original", "redacted", "masked", "encrypted", "report", "key"]
UPDATABLE_DOCUMENT_FIELDS = {
    "original_path",
    "status",
    "owner",
    "department",
    "retention_days",
    "retention_until",
    "expiry_action",
    "policy_name",
    "lifecycle_status",
    "lifecycle_next_action",
    "archive_path",
    "archived_at",
    "deleted_at",
}


def generate_document_id(year: str) -> str:
    init_db()
    like_pattern = f"PG-{year}-%"
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE document_id LIKE ?",
            (like_pattern,),
        ).fetchone()
    next_number = int(row[0] if row else 0) + 1
    return f"PG-{year}-{next_number:05d}"


def create_document_record(
    *,
    document_id: str,
    original_filename: str,
    original_path: str,
    findings: Dict[str, List[dict]],
    risk: Dict[str, Any],
    total_sensitive_items: int,
    actor: str,
    status: str = "SCANNED",
    lifecycle: Optional[Dict[str, Any]] = None,
) -> dict:
    init_db()
    lifecycle = lifecycle or {}
    payload = {
        "document_id": document_id,
        "original_filename": original_filename,
        "original_path": original_path,
        "risk_level": str(risk.get("level", "Low")),
        "risk_score": int(risk.get("score", 0)),
        "total_sensitive_items": int(total_sensitive_items),
        "counts_json": json.dumps(risk.get("counts", {})),
        "findings_json": json.dumps(findings),
        "recommendations_json": json.dumps(risk.get("recommendations", [])),
        "primary_action": str(risk.get("primary_action", "allow")),
        "status": status,
        "actor": actor,
        "owner": str(lifecycle.get("owner", "Operations")),
        "department": str(lifecycle.get("department", "Operations")),
        "retention_days": int(lifecycle.get("retention_days", 180)),
        "retention_until": str(lifecycle.get("retention_until", "")),
        "expiry_action": str(lifecycle.get("expiry_action", "review")),
        "policy_name": str(lifecycle.get("policy_name", "Default retention policy")),
        "lifecycle_status": str(lifecycle.get("lifecycle_status", "active")),
        "lifecycle_next_action": str(lifecycle.get("next_action", "Monitor lifecycle")),
        "archive_path": str(lifecycle.get("archive_path", "")),
        "archived_at": lifecycle.get("archived_at"),
        "deleted_at": lifecycle.get("deleted_at"),
    }
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO documents (
                document_id,
                original_filename,
                original_path,
                risk_level,
                risk_score,
                total_sensitive_items,
                counts_json,
                findings_json,
                recommendations_json,
                primary_action,
                status,
                actor,
                owner,
                department,
                retention_days,
                retention_until,
                expiry_action,
                policy_name,
                lifecycle_status,
                lifecycle_next_action,
                archive_path,
                archived_at,
                deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["document_id"],
                payload["original_filename"],
                payload["original_path"],
                payload["risk_level"],
                payload["risk_score"],
                payload["total_sensitive_items"],
                payload["counts_json"],
                payload["findings_json"],
                payload["recommendations_json"],
                payload["primary_action"],
                payload["status"],
                payload["actor"],
                payload["owner"],
                payload["department"],
                payload["retention_days"],
                payload["retention_until"],
                payload["expiry_action"],
                payload["policy_name"],
                payload["lifecycle_status"],
                payload["lifecycle_next_action"],
                payload["archive_path"],
                payload["archived_at"],
                payload["deleted_at"],
            ),
        )
    return get_document(document_id) or {}


def update_document_status(document_id: str, status: str) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = ? WHERE document_id = ?",
            (status, document_id),
        )


def update_document_fields(document_id: str, **fields: Any) -> None:
    init_db()
    assignments = []
    values = []
    for key, value in fields.items():
        if key not in UPDATABLE_DOCUMENT_FIELDS:
            continue
        assignments.append(f"{key} = ?")
        values.append(value)
    if not assignments:
        return
    values.append(document_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE documents SET {', '.join(assignments)} WHERE document_id = ?",
            tuple(values),
        )


def record_artifact(
    document_id: str,
    artifact_type: str,
    file_path: str,
    filename: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO document_artifacts (document_id, artifact_type, filename, file_path, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document_id,
                artifact_type,
                filename,
                file_path,
                json.dumps(metadata or {}),
            ),
        )
    return get_latest_artifact(document_id, artifact_type) or {}


def update_artifact_location(artifact_id: int, file_path: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            "UPDATE document_artifacts SET file_path = ?, filename = ?, metadata_json = ? WHERE id = ?",
            (file_path, filename, json.dumps(metadata or {}), artifact_id),
        )


def delete_artifacts_for_document(document_id: str) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM document_artifacts WHERE document_id = ?", (document_id,))


def _row_to_document(row) -> dict:
    return {
        "id": row[0],
        "document_id": row[1],
        "created_at": row[2],
        "original_filename": row[3],
        "original_path": row[4],
        "risk_level": row[5],
        "risk_score": row[6],
        "total_sensitive_items": row[7],
        "counts": json.loads(row[8] or "{}"),
        "findings": json.loads(row[9] or "{}"),
        "recommendations": json.loads(row[10] or "[]"),
        "primary_action": row[11],
        "status": row[12],
        "actor": row[13],
        "owner": row[14],
        "department": row[15],
        "retention_days": row[16],
        "retention_until": row[17],
        "expiry_action": row[18],
        "policy_name": row[19],
        "lifecycle_status": row[20],
        "lifecycle_next_action": row[21],
        "archive_path": row[22],
        "archived_at": row[23],
        "deleted_at": row[24],
    }


def _row_to_artifact(row) -> dict:
    return {
        "id": row[0],
        "document_id": row[1],
        "artifact_type": row[2],
        "filename": row[3],
        "file_path": row[4],
        "metadata": json.loads(row[5] or "{}"),
        "created_at": row[6],
    }


def get_document(document_id: str) -> dict | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        if not row:
            return None
        document = _row_to_document(row)
        artifact_rows = conn.execute(
            "SELECT * FROM document_artifacts WHERE document_id = ? ORDER BY created_at DESC, id DESC",
            (document_id,),
        ).fetchall()
    artifacts = {}
    history = []
    for artifact_row in artifact_rows:
        artifact = _row_to_artifact(artifact_row)
        history.append(artifact)
        artifacts.setdefault(artifact["artifact_type"], artifact)
    document["artifacts"] = artifacts
    document["artifact_history"] = history
    return document


def get_latest_artifact(document_id: str, artifact_type: str) -> dict | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM document_artifacts
            WHERE document_id = ? AND artifact_type = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (document_id, artifact_type),
        ).fetchone()
    return _row_to_artifact(row) if row else None


def list_documents(limit: int = 25) -> List[dict]:
    init_db()
    with get_conn() as conn:
        document_rows = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        artifact_rows = conn.execute(
            "SELECT * FROM document_artifacts ORDER BY created_at DESC, id DESC"
        ).fetchall()

    artifacts_by_doc: Dict[str, Dict[str, dict]] = {}
    for row in artifact_rows:
        artifact = _row_to_artifact(row)
        doc_artifacts = artifacts_by_doc.setdefault(artifact["document_id"], {})
        doc_artifacts.setdefault(artifact["artifact_type"], artifact)

    documents = []
    for row in document_rows:
        document = _row_to_document(row)
        document["artifacts"] = artifacts_by_doc.get(document["document_id"], {})
        document["available_artifacts"] = [
            artifact_type for artifact_type in ARTIFACT_ORDER if artifact_type in document["artifacts"]
        ]
        documents.append(document)
    return documents


def vault_summary() -> dict:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN status = 'SCANNED' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status IN ('PROTECTED', 'SECURED') THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'REVIEW_REQUIRED' THEN 1 ELSE 0 END),
                SUM(CASE WHEN lifecycle_status = 'archived' THEN 1 ELSE 0 END),
                SUM(CASE WHEN lifecycle_status = 'deleted' THEN 1 ELSE 0 END)
            FROM documents
            """
        ).fetchone()
        artifact_counts = dict(
            conn.execute(
                "SELECT artifact_type, COUNT(*) FROM document_artifacts GROUP BY artifact_type"
            ).fetchall()
        )
    total, scanned_only, protected, review_required, archived, deleted = row or (0, 0, 0, 0, 0, 0)
    return {
        "documents_total": int(total or 0),
        "pending_protection": int(scanned_only or 0),
        "protected_documents": int(protected or 0),
        "review_required": int(review_required or 0),
        "archived_documents": int(archived or 0),
        "deleted_documents": int(deleted or 0),
        "artifact_counts": {key: int(value) for key, value in artifact_counts.items()},
    }
