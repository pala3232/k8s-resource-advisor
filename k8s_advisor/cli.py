import sys
import click
from kubernetes import client as k8s_client

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
@click.option("--exit-code", is_flag=True, default=False, help="Exit with code 1 if any CRITICAL findings are found.")
def main(kubeconfig: str | None, context: str | None, namespace: str | None, exit_code: bool) -> None:
    """Scan a Kubernetes cluster for best-practice violations."""
    try:
        api_client = build_client(kubeconfig=kubeconfig, context=context)
    except Exception as e:
        print(f"Failed to connect to cluster: {e}")
        sys.exit(1)

    core_v1 = k8s_client.CoreV1Api(api_client)
    apps_v1 = k8s_client.AppsV1Api(api_client)

    print("Scanning cluster...")

    findings = []
    findings.extend(check_pods(core_v1, apps_v1, namespace))
    findings.extend(check_services(core_v1, namespace))
    findings.extend(check_namespaces(core_v1, namespace))

    print_report(findings)
    notify(findings)

    if exit_code and any(f.severity == "CRITICAL" for f in findings):
        sys.exit(1)
