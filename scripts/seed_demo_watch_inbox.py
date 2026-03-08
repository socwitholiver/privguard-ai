"""Seed the demo watch inbox with synthetic local demo files.

This keeps the existing demo-watch-inbox files and adds enough new files
to reach the requested total for watch-folder demonstrations.
"""

from __future__ import annotations

import argparse
from pathlib import Path


TARGET_DIR = Path("demo-watch-inbox")

PEOPLE = [
    ("Amina Njeri", "0712345678", "records@uhuru.co.ke", "23456789", "A123456789B"),
    ("Kevin Mutua", "0723456789", "ops@baraka.co.ke", "24567890", "A234567890C"),
    ("Faith Wanjiku", "0734567890", "admin@tumaini.org", "25678901", "A345678901D"),
    ("Brian Otieno", "0745678901", "finance@harvest.co.ke", "26789012", "A456789012E"),
    ("Mercy Chebet", "0756789012", "hr@jambo.co.ke", "27890123", "A567890123F"),
    ("John Mwangi", "0767890123", "contact@pendo.co.ke", "28901234", "A678901234G"),
    ("Linet Achieng", "0778901234", "support@afya.or.ke", "29012345", "A789012345H"),
    ("Peter Kiptoo", "0789012345", "service@elimu.co.ke", "30123456", "A890123456J"),
]


def _person(index: int) -> tuple[str, str, str, str, str]:
    return PEOPLE[(index - 1) % len(PEOPLE)]


def _account(index: int) -> str:
    return f"01{index:02d}22334455{(index % 90) + 10:02d}"


def _admission_content(index: int) -> str:
    name, phone, email, national_id, _kra_pin = _person(index)
    return "\n".join(
        [
            f"Student Admission Form {index}",
            f"Applicant Name: {name}",
            f"Guardian Phone: {phone}",
            f"Guardian Email: {email}",
            f"National ID: {national_id}",
            f"Fee Wallet Account: {_account(index)}",
            f"Medical Notes Password: school{index}!pass",
        ]
    )


def _bank_content(index: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    amount = 180000 + (index * 3700)
    return "\n".join(
        [
            "field,value",
            f"customer,{name}",
            f"national_id,{national_id}",
            f"kra_pin,{kra_pin}",
            f"phone,{phone}",
            f"email,{email}",
            f"account,{_account(index)}",
            f"transaction_amount,KES {amount}",
            f"pin_reset,bank{index}-reset",
        ]
    )


def _contract_content(index: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"# Vendor Contract {index}",
            f"Vendor Representative: {name}",
            f"Contact Phone: {phone}",
            f"Contact Email: {email}",
            f"KRA PIN: {kra_pin}",
            f"National ID: {national_id}",
            f"Settlement Account: {_account(index)}",
            f"Confidential Clause Password: Contract{index}#Vault",
        ]
    )


def _county_content(index: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    return "\n".join(
        [
            f"[2026-03-06] Record {index} intake started",
            f"Subject: {name}",
            f"Phone: {phone}",
            f"Email: {email}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Payment Reference Account: {_account(index)}",
            f"Temporary Password issued: county-{index}-access",
            f"[2026-03-06] Record {index} intake completed",
        ]
    )


def _payroll_content(index: int) -> str:
    name, phone, email, national_id, kra_pin = _person(index)
    net_pay = 42000 + (index * 475)
    return "\n".join(
        [
            f"Payroll Report Batch {index}",
            f"Employee: {name}",
            f"National ID: {national_id}",
            f"KRA PIN: {kra_pin}",
            f"Phone: {phone}",
            f"Email: {email}",
            f"Salary Account: {_account(index)}",
            f"Monthly Net Pay: KES {net_pay}",
            f"Payroll Password Reset Token: PAY{index}-SECURE-2026",
        ]
    )


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _file_count() -> int:
    if not TARGET_DIR.exists():
        return 0
    return sum(1 for path in TARGET_DIR.iterdir() if path.is_file())


def seed_demo_watch_inbox(target: int) -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    created = 0
    plans = [
        ("admission", "txt", range(21, 71), _admission_content),
        ("bank", "csv", range(41, 91), _bank_content),
        ("contract", "md", range(31, 81), _contract_content),
        ("county", "log", range(51, 101), _county_content),
        ("payroll", "txt", range(11, 61), _payroll_content),
    ]

    for prefix, suffix, numbers, builder in plans:
        for number in numbers:
            if _file_count() >= target:
                return created
            filename = f"{prefix}_{number:02d}.{suffix}"
            created += int(_write_if_missing(TARGET_DIR / filename, builder(number)))

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo-watch-inbox to a target size.")
    parser.add_argument(
        "--target",
        type=int,
        default=300,
        help="Total file count to reach in demo-watch-inbox.",
    )
    args = parser.parse_args()

    before = _file_count()
    created = seed_demo_watch_inbox(args.target)
    after = _file_count()

    print(f"demo-watch-inbox files before: {before}")
    print(f"files created: {created}")
    print(f"demo-watch-inbox files after: {after}")


if __name__ == "__main__":
    main()
