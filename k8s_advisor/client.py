from __future__ import annotations

from kubernetes import client, config
from kubernetes.client import ApiClient


def build_client(kubeconfig: str | None = None, context: str | None = None) -> ApiClient:
    if kubeconfig:
        config.load_kube_config(config_file=kubeconfig, context=context)
    else:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config(context=context)

    return ApiClient()
