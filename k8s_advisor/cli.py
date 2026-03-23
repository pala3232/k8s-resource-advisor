import sys
import click
from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from k8s_advisor.client import build_client
from k8s_advisor.report import print_report
from k8s_advisor.slack import notify
from k8s_advisor.checks.pods import check_pods
from k8s_advisor.checks.services import check_services
from k8s_advisor.checks.namespaces import check_namespaces


@click.command()
@click.option("--kubeconfig", default=None, help="Path to kubeconfig file. Defaults to in-cluster config, then ~/.kube/config.")
@click.option("--context", default=None, help="Kubeconfig context to use.")
@click.option("--namespace", "-n", default=None, help="Limit scan to a single namespace. Scans all namespaces by default.")
@click.option("--exclude-namespace", "-e", default=None, help="Comma-separated list of namespaces to exclude (e.g. kube-system,argocd).")
@click.option("--output", "-o", default="text", type=click.Choice(["text", "json"]), help="Output format (default: text).")
@click.option("--severity", "-s", default=None, type=click.Choice(["CRITICAL", "WARNING", "INFO"]), help="Only show findings at or above this severity.")
@click.option("--exit-code", is_flag=True, default=False, help="Exit with code 1 if any CRITICAL findings are found.")
def main(kubeconfig: str | None, context: str | None, namespace: str | None, exclude_namespace: str | None, output: str, severity: str | None, exit_code: bool) -> None:
    """Scan a Kubernetes cluster for best-practice violations."""
    try:
        api_client = build_client(kubeconfig=kubeconfig, context=context)
    except Exception as e:
        print(f"Failed to connect to cluster: {e}")
        sys.exit(1)

    core_v1 = k8s_client.CoreV1Api(api_client)
    apps_v1 = k8s_client.AppsV1Api(api_client)

    excluded = set(exclude_namespace.split(",")) if exclude_namespace else set()
    if output != "json":
        print("Scanning cluster...")

    findings = []
    for check, args in [
        (check_pods, (core_v1, apps_v1, namespace)),
        (check_services, (core_v1, namespace)),
        (check_namespaces, (core_v1, namespace)),
    ]:
        try:
            findings.extend(check(*args))
        except ApiException as e:
            if e.status == 403:
                print(f"[PERMISSION ERROR] {check.__name__}: insufficient RBAC permissions — {e.reason}")
            else:
                print(f"[API ERROR] {check.__name__}: {e.status} {e.reason}")
        except Exception as e:
            print(f"[ERROR] {check.__name__} failed unexpectedly: {e}")

    if excluded:
        findings = [f for f in findings if f.namespace not in excluded]

    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    if severity:
        findings = [f for f in findings if severity_order[f.severity] <= severity_order[severity]]

    print_report(findings, output=output)
    notify(findings)

    if exit_code and any(f.severity == "CRITICAL" for f in findings):
        sys.exit(1)
