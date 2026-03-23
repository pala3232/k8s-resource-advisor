from kubernetes import client as k8s_client
from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException
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

        for check in (_check_resource_quota, _check_secret_env_vars, _check_network_policy):
            try:
                findings.extend(check(core_v1, ns))
            except ApiException as e:
                if e.status == 403:
                    print(f"[PERMISSION ERROR] {check.__name__} in {ns}: insufficient RBAC permissions")
                else:
                    print(f"[API ERROR] {check.__name__} in {ns}: {e.status} {e.reason}")

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


def _check_network_policy(core_v1: CoreV1Api, ns: str) -> list[Finding]:
    networking_v1 = k8s_client.NetworkingV1Api(core_v1.api_client)
    policies = networking_v1.list_namespaced_network_policy(ns).items
    if not policies:
        return [Finding("WARNING", "namespace", ns, ns,
                        "no NetworkPolicy defined — all pod-to-pod traffic is allowed")]
    return []
