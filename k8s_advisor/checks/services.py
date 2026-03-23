from kubernetes.client import CoreV1Api
from k8s_advisor.models import Finding


def check_services(core_v1: CoreV1Api, namespace: str | None) -> list[Finding]:
    findings = []

    services = (
        core_v1.list_namespaced_service(namespace).items
        if namespace
        else core_v1.list_service_for_all_namespaces().items
    )

    for svc in services:
        name = svc.metadata.name
        ns = svc.metadata.namespace

        if svc.spec.type == "NodePort":
            findings.append(Finding("WARNING", "service", name, ns,
                                    "service is of type NodePort, which exposes a port on every node"))

        findings.extend(_check_endpoints(core_v1, name, ns))

    return findings


def _check_endpoints(core_v1: CoreV1Api, svc_name: str, ns: str) -> list[Finding]:
    try:
        endpoints = core_v1.read_namespaced_endpoints(svc_name, ns)
    except Exception:
        return []

    subsets = endpoints.subsets or []
    has_ready_addresses = any(
        subset.addresses for subset in subsets if subset.addresses
    )

    if not has_ready_addresses:
        return [Finding("WARNING", "service", svc_name, ns,
                        "service has no matching ready endpoints (no pods selected or all pods unready)")]
    return []
