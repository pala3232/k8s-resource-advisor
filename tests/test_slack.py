import json
from unittest.mock import patch, MagicMock
from k8s_advisor.slack import notify
from k8s_advisor.models import Finding


def make_finding(severity="CRITICAL", resource_type="deployment", name="api", ns="default", msg="test"):
    return Finding(severity, resource_type, name, ns, msg)


def test_notify_no_webhook_url(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    with patch("urllib.request.urlopen") as mock_urlopen:
        notify([make_finding()])
        mock_urlopen.assert_not_called()


def test_notify_no_findings(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = MagicMock()
        notify([])
        mock_urlopen.assert_called_once()
        payload = json.loads(mock_urlopen.call_args[0][0].data)
        assert "no issues" in payload["text"]


def test_notify_with_criticals(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    findings = [make_finding("CRITICAL"), make_finding("WARNING")]
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = MagicMock()
        notify(findings)
        mock_urlopen.assert_called_once()
        payload = json.loads(mock_urlopen.call_args[0][0].data)
        assert "CRITICAL" in payload["text"]
