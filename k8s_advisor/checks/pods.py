from kubernetes.client import CoreV1Api, AppsV1Api
from k8s_advisor.models import Finding


def check_pods(core_v1: CoreV1Api, apps_v1: AppsV1Api, namespace: str | None) -> list[Finding]:
    findings = []

    deployments = (
        apps_v1.list_namespaced_deployment(namespace).items
        if namespace
        else apps_v1.list_deployment_for_all_namespaces().items
    )

    for deploy in deployments:
        name = deploy.metadata.name
        ns = deploy.metadata.namespace
        containers = deploy.spec.template.spec.containers or []

        for container in containers:
            findings.extend(_check_resources(container, name, ns))
            findings.extend(_check_probes(container, name, ns))
            findings.extend(_check_root(container, name, ns))
            findings.extend(_check_latest_tag(container, name, ns))

        findings.extend(_check_pdb(core_v1, name, ns, deploy.spec.selector.match_labels or {}))

    return findings


def _check_resources(container, deploy_name: str, ns: str) -> list[Finding]:
    findings = []
    resources = container.resources

    if not resources or not resources.requests:
        findings.append(Finding("CRITICAL", "deployment", deploy_name, ns,
                                f"container '{container.name}' has no resource requests"))
    if not resources or not resources.limits:
        findings.append(Finding("CRITICAL", "deployment", deploy_name, ns,
                                f"container '{container.name}' has no resource limits"))
    return findings


def _check_probes(container, deploy_name: str, ns: str) -> list[Finding]:
    findings = []
    if not container.liveness_probe:
        findings.append(Finding("WARNING", "deployment", deploy_name, ns,
                                f"container '{container.name}' has no liveness probe"))
    if not container.readiness_probe:
        findings.append(Finding("WARNING", "deployment", deploy_name, ns,
                                f"container '{container.name}' has no readiness probe"))
    return findings


def _check_root(container, deploy_name: str, ns: str) -> list[Finding]:
    sc = container.security_context
    if sc and sc.run_as_user == 0:
        return [Finding("CRITICAL", "deployment", deploy_name, ns,
                        f"container '{container.name}' is configured to run as root (runAsUser=0)")]
    return []


def _check_latest_tag(container, deploy_name: str, ns: str) -> list[Finding]:
    image = container.image or ""
    tag = image.split(":")[-1] if ":" in image else "latest"
    if tag == "latest":
        return [Finding("WARNING", "deployment", deploy_name, ns,
                        f"container '{container.name}' uses image '{image}' with 'latest' tag")]
    return []


def _check_pdb(core_v1: CoreV1Api, deploy_name: str, ns: str, selector: dict) -> list[Finding]:
    try:
        from kubernetes import client as k8s_client
        policy_v1 = k8s_client.PolicyV1Api(core_v1.api_client)
        pdbs = policy_v1.list_namespaced_pod_disruption_budget(ns).items
    except Exception:
        return []

    for pdb in pdbs:
        match_labels = pdb.spec.selector.match_labels or {}
        if all(selector.get(k) == v for k, v in match_labels.items()):
            return []

    return [Finding("WARNING", "deployment", deploy_name, ns,
                    "no PodDisruptionBudget found matching this deployment")]
