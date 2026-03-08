"""Rebuild the repeatable PrivGuard AI demo workflow."""

from __future__ import annotations

import argparse

from automation.demo_workflow import get_demo_target_count, rebuild_demo_workspace
from automation.folder_watch import configure_watch_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset PrivGuard demo data and reseed the default watch folder.")
    parser.add_argument(
        "--target",
        type=int,
        default=get_demo_target_count(),
        help="Number of synthetic sensitive files to recreate in WATCH FOLDER.",
    )
    args = parser.parse_args()

    summary = rebuild_demo_workspace(target_count=args.target)
    state = configure_watch_folder(summary["watch_folder"], "demo-reset", reset_progress=True)

    print(f"Demo watch folder: {summary['watch_folder']}")
    print(f"Synthetic files recreated: {summary['seeded_file_count']}")
    print(f"Removed prior watch-folder files: {summary['removed_watch_files']}")
    print(f"Database rows cleared: {summary['reset_database_rows']}")
    print(f"Vault files cleared: {summary['removed_vault_files']}")
    print(f"Audit archive entries cleared: {summary['removed_audit_archive_entries']}")
    print(f"Watch folder enabled: {state['enabled']}")
    print(f"Watch folder path: {state['path']}")


if __name__ == "__main__":
    main()
