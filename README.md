# k8s-resource-advisor

![CI](https://github.com/pala3232/k8s-resource-advisor/actions/workflows/build.yml/badge.svg)

[![asciicast](https://asciinema.org/a/u6eBbwPBb16gb4D6.svg)](https://asciinema.org/a/u6eBbwPBb16gb4D6)

A Kubernetes best-practice linter. Connects to your cluster, scans resources, and reports violations — designed to run as a CronJob managed by ArgoCD.

```
INFO: Scanning cluster...
[CRITICAL] deployment/bad-deployment (advisor-test) - container 'app' has no resource requests
[CRITICAL] deployment/bad-deployment (advisor-test) - container 'app' has no resource limits
[CRITICAL] deployment/bad-deployment (advisor-test) - container 'app' is running in privileged mode
[WARNING]  deployment/bad-deployment (advisor-test) - container 'app' has no liveness probe
[WARNING]  deployment/bad-deployment (advisor-test) - deployment has a single replica — no high availability
[WARNING]  service/orphan-service (advisor-test) - service has no matching ready endpoints
[WARNING]  namespace/advisor-test (advisor-test) - no NetworkPolicy defined — all pod-to-pod traffic is allowed
[INFO]     namespace/advisor-test (advisor-test) - no ResourceQuota defined

Found 3 critical, 5 warning(s), 1 info across 9 finding(s).
```

## Checks

### Deployments / Pods

| Severity | Check |
|---|---|
| CRITICAL | No resource requests |
| CRITICAL | No resource limits |
| CRITICAL | Running as root (`runAsUser: 0`) |
| CRITICAL | Privileged container (`privileged: true`) |
| CRITICAL | Host network enabled (`hostNetwork: true`) |
| WARNING | No liveness probe |
| WARNING | No readiness probe |
| WARNING | No PodDisruptionBudget |
| WARNING | `latest` image tag |
| WARNING | Read-only root filesystem not set |
| WARNING | Single replica (no high availability) |

### Services

| Severity | Check |
|---|---|
| WARNING | NodePort service (exposes port on every node) |
| WARNING | No matching ready endpoints |

### Namespaces

| Severity | Check |
|---|---|
| WARNING | No NetworkPolicy (all pod-to-pod traffic allowed) |
| INFO | No ResourceQuota |

## Usage

### Local

```bash
pip install .
k8s-advisor                                                   # uses ~/.kube/config
k8s-advisor --namespace my-app                                # scan a single namespace
k8s-advisor --exclude-namespace kube-system,argocd            # skip noisy system namespaces
k8s-advisor --severity CRITICAL                               # only show critical findings
k8s-advisor --output json                                     # JSON output
k8s-advisor --output json | jq '.findings[] | select(.severity=="CRITICAL")'
k8s-advisor --exit-code                                       # exit 1 if any CRITICAL findings (useful in CI)
k8s-advisor --verbose                                         # debug logging
k8s-advisor --quiet                                           # suppress logs, findings only
```

### In-cluster (CronJob)

```bash
kubectl apply -f kubernetes-manifests/rbac.yaml
kubectl apply -f kubernetes-manifests/cronjob.yaml
```

Runs every minute. View the latest scan:

```bash
kubectl logs -l job-name=k8s-resource-advisor -n k8s-resource-advisor | cat
```

Example output:

```
INFO: Scanning cluster...
[CRITICAL] deployment/api-server (production) - container 'api' has no resource requests
[CRITICAL] deployment/api-server (production) - container 'api' has no resource limits
[CRITICAL] deployment/worker (production) - container 'worker' is running in privileged mode
[CRITICAL] deployment/debug-pod (staging) - pod uses hostNetwork — shares the node's network namespace
[WARNING]  deployment/api-server (production) - container 'api' has no liveness probe
[WARNING]  deployment/api-server (production) - container 'api' has no readiness probe
[WARNING]  deployment/api-server (production) - container 'api' uses image 'api-server:latest' with 'latest' tag
[WARNING]  deployment/api-server (production) - deployment has a single replica — no high availability
[WARNING]  deployment/api-server (production) - no PodDisruptionBudget found matching this deployment
[WARNING]  service/frontend (production) - service has no matching ready endpoints
[WARNING]  service/debug-svc (staging) - service is of type NodePort, which exposes a port on every node
[WARNING]  namespace/production (production) - no NetworkPolicy defined — all pod-to-pod traffic is allowed
[INFO]     namespace/staging (staging) - no ResourceQuota defined — workloads can consume unlimited cluster resources

Found 4 critical, 8 warning(s), 1 info across 13 finding(s).
```

## CLI Flags

| Flag | Short | Description |
|---|---|---|
| `--kubeconfig` | | Path to kubeconfig file. Defaults to in-cluster config, then `~/.kube/config` |
| `--context` | | Kubeconfig context to use |
| `--namespace` | `-n` | Limit scan to a single namespace. Scans all namespaces by default |
| `--exclude-namespace` | `-e` | Comma-separated list of namespaces to skip (e.g. `kube-system,argocd`) |
| `--output` | `-o` | Output format: `text` (default) or `json` |
| `--severity` | `-s` | Only show findings at this level or above: `CRITICAL`, `WARNING`, `INFO` |
| `--exit-code` | | Exit with code `1` if any CRITICAL findings are found |
| `--verbose` | `-v` | Enable debug logging |
| `--quiet` | `-q` | Suppress all logs, output findings only |

## Slack Notifications

Set a `SLACK_WEBHOOK_URL` secret and the tool will POST a summary to your channel after each scan. If not set, notifications are silently skipped.

```bash
kubectl create secret generic k8s-advisor-secrets \
  --from-literal=SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz \
  -n k8s-resource-advisor
```

## Observability

The CronJob is monitored via `kube-state-metrics` + Prometheus. A `PrometheusRule` is included in `kubernetes-manifests/prometheusrule.yaml` with two alerts:

| Alert | Condition | Severity |
|---|---|---|
| `AdvisorNotRunning` | No successful run in 2 hours | warning |
| `AdvisorJobFailing` | A Job has a failed status | critical |

Alerts are routed to Slack via Alertmanager. Deploy the monitoring stack:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

kubectl create secret generic alertmanager-slack \
  --from-literal=webhook-url=https://hooks.slack.com/services/xxx/yyy/zzz \
  --namespace monitoring

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values alertmanager-values.yaml
```

## Architecture

```
GitHub (source of truth)
    │
    ├── push to main
    │       │
    │       ▼
    │   GitHub Actions
    │   runs tests → builds image → pushes to ghcr.io
    │
    └── kubernetes-manifests/
            │
            ▼
        ArgoCD (watches repo)
        syncs CronJob + RBAC + PrometheusRule to cluster
            │
            ▼
        Kubernetes CronJob (every minute)
        runs k8s-advisor in-cluster
            │
            ├── scans all namespaces via Kubernetes API
            ├── prints findings to stdout (kubectl logs)
            └── POSTs summary to Slack (if webhook configured)

        Prometheus + kube-state-metrics
        monitors CronJob health → alerts via Alertmanager → Slack
```

## Deployment

Apply the ArgoCD Application manifest once to bootstrap:

```bash
kubectl apply -f app.yaml
```

ArgoCD will sync `kubernetes-manifests/` to the cluster and keep it in sync with every push to `main`.

The RBAC grants the tool read-only access to exactly the resources it needs:

```
pods, services, endpoints, namespaces, resourcequotas  (core)
deployments                                             (apps)
poddisruptionbudgets                                    (policy)
networkpolicies                                         (networking.k8s.io)
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## Tech Stack

- [kubernetes Python client](https://github.com/kubernetes-client/python)
- [click](https://click.palletsprojects.com/) — CLI
- [ArgoCD](https://argoproj.github.io/cd/) — GitOps deployment
- [GitHub Actions](https://docs.github.com/en/actions) — CI/CD image build
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) — observability
- [ghcr.io](https://ghcr.io) — container registry
