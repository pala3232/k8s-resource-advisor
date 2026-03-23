import os
import json
import urllib.request
from k8s_advisor.models import Finding


def notify(findings: list[Finding]) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return

    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        counts[f.severity] += 1

    if not findings:
        _post(url, {"text": "k8s-advisor: scan complete — no issues found."})
        return

    lines = [
        f"*k8s-advisor scan complete*",
        f">{counts['CRITICAL']} critical  |  {counts['WARNING']} warnings  |  {counts['INFO']} info\n",
    ]

    for f in findings:
        if f.severity == "CRITICAL":
            lines.append(f":red_circle: `[{f.severity}]` *{f.resource_type}/{f.resource_name}* ({f.namespace}) — {f.message}")

    if counts["CRITICAL"] == 0:
        lines.append(f":warning: {counts['WARNING']} warnings found — run `kubectl logs` for details.")

    _post(url, {"text": "\n".join(lines)})


def _post(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Slack notification failed: {e}")
