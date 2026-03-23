from __future__ import annotations

import logging
from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException
from k8s_advisor.models import Finding

logger = logging.getLogger("k8s_advisor")


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
    except ApiException as e:
        if e.status == 404:
            return []
        if e.status == 403:
            logger.error("Permission denied: cannot read endpoints in %s — add endpoints to ClusterRole", ns)
        return []

    subsets = endpoints.subsets or []
    has_ready_addresses = any(
        subset.addresses for subset in subsets if subset.addresses
    )

    if not has_ready_addresses:
        return [Finding("WARNING", "service", svc_name, ns,
                        "service has no matching ready endpoints (no pods selected or all pods unready)")]
    return []
