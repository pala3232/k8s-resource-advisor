import json
from k8s_advisor.models import Finding


def print_report(findings: list[Finding], output: str = "text") -> None:
    if output == "json":
        _print_json(findings)
    else:
        _print_text(findings)


def _print_text(findings: list[Finding]) -> None:
    if not findings:
        print("No issues found. Your cluster looks healthy!")
        return

    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    sorted_findings = sorted(findings, key=lambda f: order[f.severity])

    for f in sorted_findings:
        print(f"[{f.severity}] {f.resource_type}/{f.resource_name} ({f.namespace}) - {f.message}")

    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for f in sorted_findings:
        counts[f.severity] += 1

    parts = []
    if counts["CRITICAL"]:
        parts.append(f"{counts['CRITICAL']} critical")
    if counts["WARNING"]:
        parts.append(f"{counts['WARNING']} warning(s)")
    if counts["INFO"]:
        parts.append(f"{counts['INFO']} info")

    print(f"\nFound {', '.join(parts)} across {len(findings)} finding(s).")


def _print_json(findings: list[Finding]) -> None:
    output = {
        "summary": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
            "warning": sum(1 for f in findings if f.severity == "WARNING"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
        },
        "findings": [
            {
                "severity": f.severity,
                "resource_type": f.resource_type,
                "resource_name": f.resource_name,
                "namespace": f.namespace,
                "message": f.message,
            }
            for f in findings
        ],
    }
    print(json.dumps(output, indent=2))
