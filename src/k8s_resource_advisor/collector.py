"""Collect pod resource requests/limits and live usage from the Kubernetes API."""

import urllib3
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from .models import ContainerMetrics, PodMetrics
from .units import parse_cpu, parse_memory

_TIMEOUT = (10, 30)        # (connect_seconds, read_seconds) for pod list — slow EKS endpoints
_METRICS_TIMEOUT = (5, 8)  # shorter — metrics are best-effort; fail fast if unavailable


def load_k8s_config() -> None:
    try:
        config.load_incluster_config()          # running inside a pod
    except config.ConfigException:
        config.load_kube_config()               # running locally with kubeconfig


def _fetch_metrics(custom: client.CustomObjectsApi, namespace: str | None) -> dict[str, dict]:
    """Return {namespace/pod-name: {container-name: usage-dict}} or {} if unavailable."""
    try:
        if namespace:
            resp = custom.list_namespaced_custom_object(
                "metrics.k8s.io", "v1beta1", namespace, "pods",
                _request_timeout=_METRICS_TIMEOUT,
            )
        else:
            resp = custom.list_cluster_custom_object(
                "metrics.k8s.io", "v1beta1", "pods",
                _request_timeout=_METRICS_TIMEOUT,
            )
    except ApiException as e:
        if e.status in (404, 503):
            return {}
        raise
    except (
        urllib3.exceptions.ReadTimeoutError,
        urllib3.exceptions.ConnectTimeoutError,
        urllib3.exceptions.MaxRetryError,
        Exception,                              # any other network failure
    ):
        return {}                               # metrics unavailable — continue without them

    result: dict[str, dict] = {}
    for pm in resp.get("items", []):
        key = f"{pm['metadata']['namespace']}/{pm['metadata']['name']}"
        result[key] = {c["name"]: c["usage"] for c in pm.get("containers", [])}
    return result


def collect(namespace: str | None = None) -> tuple[list[PodMetrics], bool]:
    """
    Returns (pod_metrics_list, metrics_available).
    metrics_available=False when metrics-server is not installed.
    """
    load_k8s_config()
    v1 = client.CoreV1Api()
    custom = client.CustomObjectsApi()

    # Running pods only — no point reporting requests for Pending/Succeeded/Failed
    field_selector = "status.phase=Running"
    if namespace:
        pods = v1.list_namespaced_pod(
            namespace, field_selector=field_selector, _request_timeout=_TIMEOUT
        )
    else:
        pods = v1.list_pod_for_all_namespaces(
            field_selector=field_selector, _request_timeout=_TIMEOUT
        )

    metrics_map = _fetch_metrics(custom, namespace)
    metrics_available = bool(metrics_map)

    results: list[PodMetrics] = []
    for pod in pods.items:
        ns = pod.metadata.namespace
        name = pod.metadata.name
        pod_usage = metrics_map.get(f"{ns}/{name}", {})

        containers: list[ContainerMetrics] = []
        for c in pod.spec.containers:
            req = (c.resources.requests or {}) if c.resources else {}
            lim = (c.resources.limits or {}) if c.resources else {}
            usage = pod_usage.get(c.name, {})

            containers.append(ContainerMetrics(
                name=c.name,
                cpu_request=parse_cpu(req.get("cpu")),
                cpu_limit=parse_cpu(lim.get("cpu")),
                cpu_usage=parse_cpu(usage.get("cpu")),
                mem_request=parse_memory(req.get("memory")),
                mem_limit=parse_memory(lim.get("memory")),
                mem_usage=parse_memory(usage.get("memory")),
            ))

        results.append(PodMetrics(
            namespace=ns,
            pod_name=name,
            node=pod.spec.node_name or "",
            containers=containers,
        ))

    return results, metrics_available
