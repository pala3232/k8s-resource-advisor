from kubernetes.client import CoreV1Api
from k8s_advisor.models import Finding

SYSTEM_NAMESPACES = {"kube-system", "kube-public", "kube-node-lease"}


def check_namespaces(core_v1: CoreV1Api, namespace: str | None) -> list[Finding]:
    findings = []

    if namespace:
        namespaces = [core_v1.read_namespace(namespace)]
    else:
        namespaces = core_v1.list_namespace().items

    for ns_obj in namespaces:
        ns = ns_obj.metadata.name

        if ns in SYSTEM_NAMESPACES:
            continue

        findings.extend(_check_resource_quota(core_v1, ns))
        findings.extend(_check_secret_env_vars(core_v1, ns))

    return findings


def _check_resource_quota(core_v1: CoreV1Api, ns: str) -> list[Finding]:
    quotas = core_v1.list_namespaced_resource_quota(ns).items
    if not quotas:
        return [Finding("INFO", "namespace", ns, ns,
                        "no ResourceQuota defined — workloads can consume unlimited cluster resources")]
    return []


def _check_secret_env_vars(core_v1: CoreV1Api, ns: str) -> list[Finding]:
    findings = []
    pods = core_v1.list_namespaced_pod(ns).items

    for pod in pods:
        for container in pod.spec.containers or []:
            for env in container.env or []:
                if env.value_from and env.value_from.secret_key_ref:
                    findings.append(Finding(
                        "WARNING",
                        "pod",
                        pod.metadata.name,
                        ns,
                        f"container '{container.name}' mounts secret '{env.value_from.secret_key_ref.name}' "
                        f"as env var '{env.name}' — prefer mounting secrets as volumes",
                    ))

    return findings
