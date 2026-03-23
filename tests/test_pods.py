from unittest.mock import MagicMock
from k8s_advisor.checks.pods import (
    _check_resources,
    _check_probes,
    _check_root,
    _check_latest_tag,
    _check_privileged,
    _check_read_only_root,
    _check_host_network,
    _check_single_replica,
)


def make_container(
    name="app",
    image="nginx:1.0",
    requests=None,
    limits=None,
    liveness_probe=True,
    readiness_probe=True,
    run_as_user=None,
    privileged=None,
    read_only_root_filesystem=None,
):
    container = MagicMock()
    container.name = name
    container.image = image
    container.resources.requests = requests
    container.resources.limits = limits
    container.liveness_probe = MagicMock() if liveness_probe else None
    container.readiness_probe = MagicMock() if readiness_probe else None
    container.security_context.run_as_user = run_as_user
    container.security_context.privileged = privileged
    container.security_context.read_only_root_filesystem = read_only_root_filesystem
    return container


def make_deploy(replicas=2):
    deploy = MagicMock()
    deploy.spec.replicas = replicas
    return deploy


# --- _check_resources ---

def test_check_resources_no_requests():
    container = make_container(requests=None)
    findings = _check_resources(container, "my-deploy", "default")
    assert any("no resource requests" in f.message for f in findings)
    assert all(f.severity == "CRITICAL" for f in findings)


def test_check_resources_no_limits():
    container = make_container(limits=None)
    findings = _check_resources(container, "my-deploy", "default")
    assert any("no resource limits" in f.message for f in findings)


def test_check_resources_ok():
    container = make_container(requests={"cpu": "100m"}, limits={"cpu": "200m"})
    assert _check_resources(container, "my-deploy", "default") == []


# --- _check_probes ---

def test_check_probes_missing_liveness():
    container = make_container(liveness_probe=False)
    findings = _check_probes(container, "my-deploy", "default")
    assert any("liveness" in f.message for f in findings)


def test_check_probes_missing_readiness():
    container = make_container(readiness_probe=False)
    findings = _check_probes(container, "my-deploy", "default")
    assert any("readiness" in f.message for f in findings)


def test_check_probes_ok():
    container = make_container()
    assert _check_probes(container, "my-deploy", "default") == []


# --- _check_root ---

def test_check_root_runs_as_root():
    container = make_container(run_as_user=0)
    findings = _check_root(container, "my-deploy", "default")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_check_root_non_root():
    container = make_container(run_as_user=1000)
    assert _check_root(container, "my-deploy", "default") == []


# --- _check_latest_tag ---

def test_check_latest_tag_explicit():
    container = make_container(image="nginx:latest")
    findings = _check_latest_tag(container, "my-deploy", "default")
    assert len(findings) == 1


def test_check_latest_tag_no_tag():
    container = make_container(image="nginx")
    findings = _check_latest_tag(container, "my-deploy", "default")
    assert len(findings) == 1


def test_check_latest_tag_pinned():
    container = make_container(image="nginx:1.25.3")
    assert _check_latest_tag(container, "my-deploy", "default") == []


# --- _check_privileged ---

def test_check_privileged_true():
    container = make_container(privileged=True)
    findings = _check_privileged(container, "my-deploy", "default")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_check_privileged_false():
    container = make_container(privileged=False)
    assert _check_privileged(container, "my-deploy", "default") == []


# --- _check_read_only_root ---

def test_check_read_only_root_not_set():
    container = make_container(read_only_root_filesystem=None)
    findings = _check_read_only_root(container, "my-deploy", "default")
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"


def test_check_read_only_root_set():
    container = make_container(read_only_root_filesystem=True)
    assert _check_read_only_root(container, "my-deploy", "default") == []


# --- _check_host_network ---

def test_check_host_network_true():
    pod_spec = MagicMock()
    pod_spec.host_network = True
    findings = _check_host_network(pod_spec, "my-deploy", "default")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_check_host_network_false():
    pod_spec = MagicMock()
    pod_spec.host_network = False
    assert _check_host_network(pod_spec, "my-deploy", "default") == []


# --- _check_single_replica ---

def test_check_single_replica_one():
    deploy = make_deploy(replicas=1)
    findings = _check_single_replica(deploy, "my-deploy", "default")
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"


def test_check_single_replica_two():
    deploy = make_deploy(replicas=2)
    assert _check_single_replica(deploy, "my-deploy", "default") == []
