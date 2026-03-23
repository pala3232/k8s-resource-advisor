# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-23

### Added
- Initial release
- Cluster-wide scan via in-cluster Kubernetes API
- **Deployment checks:** no resource requests/limits, no liveness/readiness probes, no PodDisruptionBudget, `latest` image tag, running as root, privileged containers, hostNetwork, read-only root filesystem, single replica
- **Service checks:** NodePort services, no matching endpoints
- **Namespace checks:** no ResourceQuota, no NetworkPolicy, secrets mounted as env vars
- `--namespace` flag to limit scan to a single namespace
- `--exclude-namespace` flag to skip namespaces (e.g. `kube-system,argocd`)
- `--output json` flag for machine-readable output
- `--severity` flag to filter findings by severity level
- `--exit-code` flag to exit with code 1 on CRITICAL findings (CI integration)
- `--verbose` / `--quiet` flags for log level control
- Slack webhook notifications via `SLACK_WEBHOOK_URL` secret
- Proper error handling with specific 403 permission messages
- Deployed as a Kubernetes CronJob managed by ArgoCD
- GitHub Actions CI: tests run before image build
- PrometheusRule alerts for CronJob health monitoring
