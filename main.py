"""PRIVGUARD AI MVP entrypoint.

Offline-first CLI for detecting, classifying, and protecting sensitive data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from classification import build_risk_summary
from dashboard import render_dashboard
from detection import detect_sensitive_data
from extraction import read_document_text
from protection import (
    decrypt_text,
    encrypt_text,
    generate_encryption_key,
    load_encryption_key,
    mask_text,
    redact_text,
    save_encryption_key,
    validate_encrypted_token,
    verify_redaction_quality,
)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_scan(input_path: Path, show_dashboard: bool = True) -> Dict[str, object]:
    text = read_document_text(input_path)
    findings = detect_sensitive_data(text)
    risk_summary = build_risk_summary(findings)
    report = {
        "input_file": str(input_path),
        "extracted_text": text,
        "findings": findings,
        "risk": risk_summary,
    }

    if show_dashboard:
        render_dashboard(findings, risk_summary)
    return report


def run_protection(
    input_path: Path, action: str, output_dir: Path, key_path: Path | None = None
) -> Dict[str, object]:
    text = read_document_text(input_path)
    findings = detect_sensitive_data(text)

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = input_path.stem

    if action == "redact":
        protected = redact_text(text, findings)
        output_file = output_dir / f"{base_name}.redacted.txt"
        write_output(output_file, protected)
        quality = verify_redaction_quality(findings, protected)
        return {"action": action, "output_file": str(output_file), "quality": quality}

    if action == "mask":
        protected = mask_text(text, findings)
        output_file = output_dir / f"{base_name}.masked.txt"
        write_output(output_file, protected)
        quality = verify_redaction_quality(findings, protected)
        return {"action": action, "output_file": str(output_file), "quality": quality}

    if action == "encrypt":
        if key_path is None:
            key_path = output_dir / f"{base_name}.key"
        key = generate_encryption_key()
        save_encryption_key(key, key_path)
        encrypted = encrypt_text(text, key)
        output_file = output_dir / f"{base_name}.encrypted.txt"
        write_output(output_file, encrypted)
        return {
            "action": action,
            "output_file": str(output_file),
            "key_file": str(key_path),
        }

    raise ValueError(f"Unsupported protection action: {action}")


def run_decrypt(input_path: Path, key_path: Path, output_dir: Path) -> Dict[str, str]:
    token = read_document_text(input_path).strip()
    if not validate_encrypted_token(token):
        raise ValueError("Input does not look like a valid encrypted token.")

    key = load_encryption_key(key_path)
    plain_text = decrypt_text(token, key)
    output_file = output_dir / f"{input_path.stem}.decrypted.txt"
    write_output(output_file, plain_text)
    return {"output_file": str(output_file)}


def parser_builder() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PRIVGUARD AI - Offline Sensitive Data Protection MVP"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Detect sensitive data and show risk dashboard.")
    scan.add_argument(
        "--input",
        required=True,
        help="Path to supported file (.txt/.md/.csv/.log or image: .png/.jpg/.jpeg/.bmp/.tiff/.webp).",
    )
    scan.add_argument(
        "--json-output",
        required=False,
        help="Optional path to save JSON scan report.",
    )
    scan.add_argument(
        "--extracted-output",
        required=False,
        help="Optional path to save extracted text from the input file.",
    )

    protect = sub.add_parser(
        "protect",
        help="Apply one-click protection action: redact, mask, or encrypt.",
    )
    protect.add_argument(
        "--input",
        required=True,
        help="Path to supported file (.txt/.md/.csv/.log or image formats).",
    )
    protect.add_argument(
        "--action",
        required=True,
        choices=["redact", "mask", "encrypt"],
        help="Protection action to apply.",
    )
    protect.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where protected output will be written.",
    )
    protect.add_argument(
        "--key-path",
        required=False,
        help="Optional key file location for encrypt action.",
    )

    decrypt = sub.add_parser("decrypt", help="Decrypt a previously encrypted output file.")
    decrypt.add_argument("--input", required=True, help="Path to encrypted text file.")
    decrypt.add_argument("--key-path", required=True, help="Path to key file.")
    decrypt.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where decrypted output will be written.",
    )

    verify = sub.add_parser(
        "verify-redaction",
        help="Check whether protected output still leaks original sensitive values.",
    )
    verify.add_argument("--original", required=True, help="Path to original document.")
    verify.add_argument("--protected", required=True, help="Path to redacted/masked text file.")
    verify.add_argument(
        "--json-output",
        required=False,
        help="Optional path to save verification report JSON.",
    )
    return parser


def main() -> int:
    parser = parser_builder()
    args = parser.parse_args()

    try:
        if args.command == "scan":
            report = run_scan(Path(args.input))
            if args.extracted_output:
                extracted_path = Path(args.extracted_output)
                extracted_path.parent.mkdir(parents=True, exist_ok=True)
                extracted_path.write_text(report["extracted_text"], encoding="utf-8")
                print(f"Extracted text saved to {extracted_path}")
            if args.json_output:
                output_path = Path(args.json_output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"Scan report saved to {output_path}")
            return 0

        if args.command == "protect":
            result = run_protection(
                input_path=Path(args.input),
                action=args.action,
                output_dir=Path(args.output_dir),
                key_path=Path(args.key_path) if args.key_path else None,
            )
            print(json.dumps(result, indent=2))
            return 0

        if args.command == "verify-redaction":
            original_text = read_document_text(Path(args.original))
            protected_text = read_document_text(Path(args.protected))
            original_findings = detect_sensitive_data(original_text)
            quality = verify_redaction_quality(original_findings, protected_text)
            print(json.dumps(quality, indent=2))
            if args.json_output:
                quality_path = Path(args.json_output)
                quality_path.parent.mkdir(parents=True, exist_ok=True)
                quality_path.write_text(json.dumps(quality, indent=2), encoding="utf-8")
                print(f"Verification report saved to {quality_path}")
            return 0

        if args.command == "decrypt":
            result = run_decrypt(
                input_path=Path(args.input),
                key_path=Path(args.key_path),
                output_dir=Path(args.output_dir),
            )
            print(json.dumps(result, indent=2))
            return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
