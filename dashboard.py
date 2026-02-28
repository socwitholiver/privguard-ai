"""Lightweight CLI dashboard rendering for PRIVGUARD AI."""

from __future__ import annotations

from typing import Dict, List

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def _render_plain(findings: Dict[str, List[dict]], risk_summary: Dict[str, object]) -> None:
    print("=" * 72)
    print("PRIVGUARD AI - Compliance Dashboard")
    print("=" * 72)
    print(f"Risk Level : {risk_summary['level']}")
    print(f"Risk Score : {risk_summary['score']}/100")
    print("-" * 72)
    print("Detected Sensitive Items:")
    for data_type, count in risk_summary["counts"].items():
        print(f"  - {data_type}: {count}")
    print("-" * 72)
    print("DPA 2019 Compliance Insights:")
    for insight in risk_summary["insights"]:
        print(f"  * {insight}")
    print("=" * 72)


def _render_rich(findings: Dict[str, List[dict]], risk_summary: Dict[str, object]) -> None:
    console = Console()
    table = Table(title="PRIVGUARD AI - Detected Sensitive Items")
    table.add_column("Data Type", style="cyan", justify="left")
    table.add_column("Count", style="magenta", justify="right")

    for data_type, count in risk_summary["counts"].items():
        table.add_row(data_type, str(count))

    insights = "\n".join(f"- {item}" for item in risk_summary["insights"])
    panel = Panel(
        f"[bold]Risk Level:[/bold] {risk_summary['level']}\n"
        f"[bold]Risk Score:[/bold] {risk_summary['score']}/100\n\n"
        f"[bold]DPA 2019 Insights[/bold]\n{insights}",
        title="Compliance Summary",
        border_style="green",
    )

    console.print(table)
    console.print(panel)


def render_dashboard(findings: Dict[str, List[dict]], risk_summary: Dict[str, object]) -> None:
    """Render a dashboard in rich format if available, plain text otherwise."""
    if RICH_AVAILABLE:
        _render_rich(findings, risk_summary)
        return
    _render_plain(findings, risk_summary)
