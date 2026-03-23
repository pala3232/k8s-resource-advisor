from rich.console import Console
from rich.table import Table
from rich import box
from k8s_advisor.models import Finding

console = Console(width=200)

SEVERITY_STYLES = {
    "CRITICAL": "bold red",
    "WARNING": "bold yellow",
    "INFO": "bold cyan",
}


def print_report(findings: list[Finding]) -> None:
    if not findings:
        console.print("\n[bold green]No issues found. Your cluster looks healthy![/bold green]\n")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Resource", width=35)
    table.add_column("Namespace", width=20)
    table.add_column("Message")

    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    sorted_findings = sorted(findings, key=lambda f: order[f.severity])

    for f in sorted_findings:
        style = SEVERITY_STYLES[f.severity]
        table.add_row(
            f"[{style}]{f.severity}[/{style}]",
            f"{f.resource_type}/{f.resource_name}",
            f.namespace,
            f.message,
        )

    console.print()
    console.print(table)
    _print_summary(sorted_findings)


def _print_summary(findings: list[Finding]) -> None:
    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        counts[f.severity] += 1

    parts = []
    if counts["CRITICAL"]:
        parts.append(f"[bold red]{counts['CRITICAL']} critical[/bold red]")
    if counts["WARNING"]:
        parts.append(f"[bold yellow]{counts['WARNING']} warning(s)[/bold yellow]")
    if counts["INFO"]:
        parts.append(f"[bold cyan]{counts['INFO']} info[/bold cyan]")

    console.print(f"\nFound {', '.join(parts)} across {len(findings)} finding(s).\n")
