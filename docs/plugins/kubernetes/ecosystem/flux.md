# Kubernetes Plugin > Ecosystem > Flux CD

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
  - [What is Flux CD?](#what-is-flux-cd)
  - [Why Use Flux?](#why-use-flux)
  - [Integration with K8s Plugin](#integration-with-k8s-plugin)
- [Prerequisites](#prerequisites)
  - [CRD Installation](#crd-installation)
  - [Flux Bootstrap](#flux-bootstrap)
  - [Version Requirements](#version-requirements)
- [Detection](#detection)
- [Configuration](#configuration)
  - [Plugin Configuration](#plugin-configuration)
  - [Namespace Configuration](#namespace-configuration)
- [Command Reference](#command-reference)
  - [GitRepositories](#gitrepositories)
  - [HelmRepositories](#helmrepositories)
  - [Kustomizations](#kustomizations)
  - [HelmReleases](#helmreleases)
- [Integration Examples](#integration-examples)
  - [Basic GitOps Setup](#basic-gitops-setup)
  - [Multi-Environment Deployment](#multi-environment-deployment)
  - [Helm Release Management](#helm-release-management)
  - [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

### What is Flux CD?

Flux CD is a GitOps operator for Kubernetes that keeps your cluster in sync with a Git repository. It automatically
detects changes in your Git repository and applies them to your cluster, enabling declarative, version-controlled
deployments.

Key capabilities:

- **GitOps workflows** - Git as single source of truth for cluster state
- **Continuous deployment** - Automatic synchronization with Git
- **Multi-source support** - Git repositories, Helm charts, Kustomize overlays
- **Reconciliation** - Automatic detection and application of changes
- **Health monitoring** - Real-time status and health checks
- **Notifications** - Integration with Slack, GitHub, and other platforms
- **Security** - Secrets encryption, RBAC integration, audit trails in Git

### Why Use Flux?

1. **Declarative Infrastructure** - Define desired state in Git
2. **Audit Trail** - All changes tracked in Git history
3. **Rollback capability** - Easy rollback to previous Git commits
4. **Team collaboration** - Review and merge deployments like code
5. **Consistency** - Ensures cluster state matches Git
6. **Automation** - Eliminates manual deployments
7. **Multi-cluster** - Manage multiple clusters from single Git repo

### Integration with K8s Plugin

These tools are CRD-based resources managed via Kubernetes CustomResourcesApi. The plugin provides convenient CLI
commands for:

- Listing and viewing GitRepositories and HelmRepositories (sources)
- Creating and managing Kustomizations (GitOps automation)
- Creating and managing HelmReleases (Helm GitOps)
- Triggering reconciliations and checking status
- Suspending and resuming automatic reconciliation

---

## Prerequisites

### CRD Installation

Flux CD requires Custom Resource Definitions for:

- `GitRepository` - Source definitions for Git repositories
- `HelmRepository` - Source definitions for Helm repositories
- `Kustomization` - Deployment automation from Kustomize overlays
- `HelmRelease` - Deployment automation from Helm charts
- `Bucket` - Source for S3 buckets and similar
- `OCIRepository` - Source for OCI registries

CRDs are installed when you bootstrap Flux in your cluster.

### Flux Bootstrap

Install Flux CD using the official CLI:

```bash
# Install Flux CLI (one-time, on your local machine)
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux in your cluster
# Requires GitHub personal access token and repository
flux bootstrap github \
  --owner=<github-username> \
  --repository=<repository-name> \
  --branch=main \
  --path=./clusters/my-cluster \
  --personal

# Or use GitLab
flux bootstrap gitlab \
  --owner=<gitlab-username> \
  --repository=<repository-name> \
  --branch=main \
  --path=./clusters/my-cluster \
  --personal

# Verify installation
flux check
kubectl get ns flux-system
kubectl get pods -n flux-system
```

### Version Requirements

| Flux Version | Kubernetes | Status        |
| ------------ | ---------- | ------------- |
| 2.0+         | 1.24+      | Full support  |
| 1.25+        | 1.20+      | Maintenance   |
| < 1.20       | Legacy     | Not supported |

---

## Detection

The plugin automatically detects Flux CD availability by:

1. **Checking for CRDs** - Looks for `gitrepository.source.fluxcd.io` and related CRDs
2. **Verifying controller pods** - Checks if Flux controllers are running in `flux-system` namespace
3. **API accessibility** - Confirms API server can list GitRepository resources
4. **Source controller** - Verifies source controller is operational

Detection occurs when you first run a Flux-related command. If Flux is not detected, you'll receive a clear error
message with bootstrap instructions.

---

## Configuration

### Plugin Configuration

Add Flux configuration to your ops config file (`~/.config/ops/config.yaml`):

```yaml
plugins:
  kubernetes:
    flux:
      # Enable/disable Flux commands (default: true if Flux is installed)
      enabled: true
      # Default namespace for Flux controllers
      flux_namespace: "flux-system"
      # Namespace for sources (typically same as flux_namespace)
      source_namespace: "flux-system"
      # Timeout for reconciliation operations (seconds)
      reconciliation_timeout: 30
      # Number of retries for failed operations
      retries: 3
      # Default reconciliation interval
      default_interval: "1m"
```

### Namespace Configuration

Flux resources typically reside in the `flux-system` namespace, but you can create sources in other namespaces:

```bash
# List sources in flux-system (default)
ops k8s flux source git list

# List sources in specific namespace
ops k8s flux source git list -n flux-system

# Kustomizations and HelmReleases can be in any namespace
ops k8s flux ks list -n production
ops k8s flux hr list -n kube-system
```

---

## Command Reference

### GitRepositories

GitRepositories are source definitions that tell Flux where your Git repositories are and how to access them.

#### `ops k8s flux source git list`

List all GitRepositories.

```bash
ops k8s flux source git list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default     | Description                      |
| ------------- | ----- | ------ | ----------- | -------------------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace             |
| `--selector`  | `-l`  | string | -           | Label selector                   |
| `--output`    | `-o`  | string | table       | Output format: table, json, yaml |

**Example:**

```bash
# List all GitRepositories
ops k8s flux source git list

# List in production namespace
ops k8s flux source git list -n production

# Filter by label
ops k8s flux source git list -l app=myapp

# JSON output
ops k8s flux source git list -o json
```

**Example Output:**

```text
GitRepositories
Name              Namespace       URL                                       Branch   Ready  Suspended  Age
podinfo           flux-system     https://github.com/stefanprodan/podinfo   main     true   false      7d
app-config        production      https://github.com/myorg/app-config      main     true   false      5d
monitoring        infrastructure  https://github.com/myorg/monitoring       develop  false  false      2h
```

#### `ops k8s flux source git get`

Get details of a specific GitRepository.

```bash
ops k8s flux source git get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| NAME     | yes      | Name of the GitRepository |

**Options:**

| Option        | Short | Type   | Default     | Description                      |
| ------------- | ----- | ------ | ----------- | -------------------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace             |
| `--output`    | `-o`  | string | table       | Output format: table, json, yaml |

**Example:**

```bash
# Get GitRepository details
ops k8s flux source git get podinfo

# Get from specific namespace
ops k8s flux source git get app-config -n production

# View full YAML
ops k8s flux source git get podinfo -o yaml
```

**Example Output (YAML):**

```yaml
apiVersion: source.fluxcd.io/v1
kind: GitRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/stefanprodan/podinfo
  ref:
    branch: main
  secretRef:
    name: git-credentials
status:
  observedGeneration: 42
  conditions:
    - type: Ready
      status: "True"
      reason: "GitOperationSucceeded"
      message: "Fetched revision: main/abc1234567890def"
  lastUpdateTime: "2024-02-16T10:30:45Z"
  artifact:
    path: "gitrepository/flux-system/podinfo/abc1234567890def.tar.gz"
    url: "http://source-controller.flux-system.svc.cluster.local/gitrepository/flux-system/podinfo/abc1234567890def.tar.gz"
    revision: "main/abc1234567890def"
```

#### `ops k8s flux source git create`

Create a new GitRepository.

```bash
ops k8s flux source git create NAME --url URL [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name for the GitRepository |

**Options:**

| Option         | Short | Type   | Default     | Description                                       |
| -------------- | ----- | ------ | ----------- | ------------------------------------------------- |
| `--url`        | -     | string | required    | Git repository URL (HTTPS or SSH)                 |
| `--namespace`  | `-n`  | string | flux-system | Kubernetes namespace                              |
| `--branch`     | -     | string | main        | Branch to track                                   |
| `--tag`        | -     | string | -           | Tag to track (instead of branch)                  |
| `--semver`     | -     | string | -           | Semver range to track (instead of branch)         |
| `--commit`     | -     | string | -           | Specific commit SHA to track                      |
| `--interval`   | -     | string | 1m          | Reconciliation interval                           |
| `--secret-ref` | -     | string | -           | Secret name for authentication (SSH key or token) |
| `--output`     | `-o`  | string | table       | Output format: table, json, yaml                  |

**Example:**

```bash
# Create GitRepository tracking main branch
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/myapp \
  --branch main

# Track specific tag with authentication
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/myapp \
  --tag v2.0.0 \
  --interval 5m \
  --secret-ref github-token

# Track semver range (latest matching version)
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/myapp \
  --semver ">=1.0.0 <2.0.0" \
  --interval 10m

# Track specific commit
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/myapp \
  --commit abc1234567890def
```

#### `ops k8s flux source git delete`

Delete a GitRepository.

```bash
ops k8s flux source git delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                         |
| -------- | -------- | ----------------------------------- |
| NAME     | yes      | Name of the GitRepository to delete |

**Options:**

| Option        | Short | Type   | Default     | Description              |
| ------------- | ----- | ------ | ----------- | ------------------------ |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false       | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s flux source git delete app-repo

# Delete without confirmation
ops k8s flux source git delete app-repo --force
```

#### `ops k8s flux source git suspend`

Suspend automatic reconciliation of a GitRepository.

```bash
ops k8s flux source git suspend NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                          |
| -------- | -------- | ------------------------------------ |
| NAME     | yes      | Name of the GitRepository to suspend |

**Options:**

| Option        | Short | Type   | Default     | Description          |
| ------------- | ----- | ------ | ----------- | -------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace |

**Example:**

```bash
# Suspend GitRepository
ops k8s flux source git suspend app-repo

# Suspend in specific namespace
ops k8s flux source git suspend app-repo -n production
```

#### `ops k8s flux source git resume`

Resume automatic reconciliation of a GitRepository.

```bash
ops k8s flux source git resume NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                         |
| -------- | -------- | ----------------------------------- |
| NAME     | yes      | Name of the GitRepository to resume |

**Options:**

| Option        | Short | Type   | Default     | Description          |
| ------------- | ----- | ------ | ----------- | -------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace |

**Example:**

```bash
# Resume GitRepository
ops k8s flux source git resume app-repo

# Resume in specific namespace
ops k8s flux source git resume app-repo -n production
```

#### `ops k8s flux source git reconcile`

Trigger immediate reconciliation of a GitRepository.

```bash
ops k8s flux source git reconcile NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                            |
| -------- | -------- | -------------------------------------- |
| NAME     | yes      | Name of the GitRepository to reconcile |

**Options:**

| Option        | Short | Type   | Default     | Description          |
| ------------- | ----- | ------ | ----------- | -------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace |

**Example:**

```bash
# Trigger reconciliation
ops k8s flux source git reconcile app-repo

# Force reconciliation in specific namespace
ops k8s flux source git reconcile app-repo -n production
```

#### `ops k8s flux source git status`

Get status of a GitRepository.

```bash
ops k8s flux source git status NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| NAME     | yes      | Name of the GitRepository |

**Options:**

| Option        | Short | Type   | Default     | Description                      |
| ------------- | ----- | ------ | ----------- | -------------------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace             |
| `--output`    | `-o`  | string | table       | Output format: table, json, yaml |

**Example:**

```bash
# Check status
ops k8s flux source git status app-repo

# JSON output
ops k8s flux source git status app-repo -o json
```

---

### HelmRepositories

HelmRepositories are source definitions for Helm chart repositories.

#### `ops k8s flux source helm list`

List all HelmRepositories.

```bash
ops k8s flux source helm list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default     | Description                      |
| ------------- | ----- | ------ | ----------- | -------------------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace             |
| `--selector`  | `-l`  | string | -           | Label selector                   |
| `--output`    | `-o`  | string | table       | Output format: table, json, yaml |

**Example:**

```bash
# List all HelmRepositories
ops k8s flux source helm list

# List in production namespace
ops k8s flux source helm list -n production

# JSON output
ops k8s flux source helm list -o json
```

**Example Output:**

```text
HelmRepositories
Name        Namespace       URL                                  Type     Ready  Suspended  Age
bitnami     flux-system     https://charts.bitnami.com/bitnami   default  true   false      7d
jetstack    flux-system     https://charts.jetstack.io           default  true   false      5d
mycompany   production      oci://ghcr.io/mycompany/charts       oci      true   false      3d
```

#### `ops k8s flux source helm get`

Get details of a specific HelmRepository.

```bash
ops k8s flux source helm get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name of the HelmRepository |

**Options:**

| Option        | Short | Type   | Default     | Description                      |
| ------------- | ----- | ------ | ----------- | -------------------------------- |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace             |
| `--output`    | `-o`  | string | table       | Output format: table, json, yaml |

**Example:**

```bash
# Get HelmRepository details
ops k8s flux source helm get bitnami

# View full YAML
ops k8s flux source helm get bitnami -o yaml
```

#### `ops k8s flux source helm create`

Create a new HelmRepository.

```bash
ops k8s flux source helm create NAME --url URL [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| NAME     | yes      | Name for the HelmRepository |

**Options:**

| Option         | Short | Type   | Default     | Description                                                    |
| -------------- | ----- | ------ | ----------- | -------------------------------------------------------------- |
| `--url`        | -     | string | required    | Helm repository URL (HTTP/S or OCI)                            |
| `--namespace`  | `-n`  | string | flux-system | Kubernetes namespace                                           |
| `--type`       | -     | string | default     | Repository type: default (HTTP) or oci                         |
| `--interval`   | -     | string | 1m          | Reconciliation interval                                        |
| `--secret-ref` | -     | string | -           | Secret name for authentication (credentials for private repos) |
| `--output`     | `-o`  | string | table       | Output format: table, json, yaml                               |

**Example:**

```bash
# Create Helm repository from Bitnami charts
ops k8s flux source helm create bitnami \
  --url https://charts.bitnami.com/bitnami

# Create OCI-based Helm repository
ops k8s flux source helm create mycompany \
  --url oci://ghcr.io/mycompany/charts \
  --type oci \
  --interval 5m \
  --secret-ref ghcr-credentials

# Create private Helm repository with authentication
ops k8s flux source helm create internal \
  --url https://charts.internal.com \
  --interval 10m \
  --secret-ref helm-credentials
```

#### `ops k8s flux source helm delete`

Delete a HelmRepository.

```bash
ops k8s flux source helm delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                          |
| -------- | -------- | ------------------------------------ |
| NAME     | yes      | Name of the HelmRepository to delete |

**Options:**

| Option        | Short | Type   | Default     | Description              |
| ------------- | ----- | ------ | ----------- | ------------------------ |
| `--namespace` | `-n`  | string | flux-system | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false       | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s flux source helm delete bitnami

# Delete without confirmation
ops k8s flux source helm delete mycompany --force
```

#### `ops k8s flux source helm suspend/resume/reconcile/status`

Same as GitRepository commands above, but for HelmRepositories.

```bash
ops k8s flux source helm suspend bitnami
ops k8s flux source helm resume bitnami
ops k8s flux source helm reconcile bitnami
ops k8s flux source helm status bitnami
```

---

### Kustomizations

Kustomizations define how to deploy applications from a GitRepository using Kustomize overlays.

#### `ops k8s flux ks list`

List all Kustomizations.

```bash
ops k8s flux ks list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--selector`  | `-l`  | string | -       | Label selector                   |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List Kustomizations in default namespace
ops k8s flux ks list

# List in production namespace
ops k8s flux ks list -n production

# List all across namespaces
ops k8s flux ks list -n flux-system

# JSON output
ops k8s flux ks list -o json
```

**Example Output:**

```text
Kustomizations
Name          Namespace       Source              Path            Ready  Suspended  Age
app-base      production      app-repo            ./kustomize     true   false      7d
monitoring    infrastructure  monitoring-repo     ./deploy/kube   true   false      5d
ingress-core  kube-system     app-repo            ./ingress       false  false      2h
```

#### `ops k8s flux ks get`

Get details of a specific Kustomization.

```bash
ops k8s flux ks get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| NAME     | yes      | Name of the Kustomization |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get Kustomization details
ops k8s flux ks get app-base -n production

# View full YAML
ops k8s flux ks get app-base -n production -o yaml
```

#### `ops k8s flux ks create`

Create a new Kustomization.

```bash
ops k8s flux ks create NAME --source-name SOURCE --source-kind KIND [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name for the Kustomization |

**Options:**

| Option               | Short | Type   | Default     | Description                                |
| -------------------- | ----- | ------ | ----------- | ------------------------------------------ |
| `--source-name`      | -     | string | required    | Source reference name (GitRepository name) |
| `--source-kind`      | -     | string | required    | Source kind (e.g., GitRepository)          |
| `--namespace`        | `-n`  | string | default     | Kubernetes namespace                       |
| `--source-namespace` | -     | string | flux-system | Namespace of the source                    |
| `--path`             | -     | string | ./          | Path within source repository              |
| `--interval`         | -     | string | 5m          | Reconciliation interval                    |
| `--prune`            | -     | bool   | true        | Prune resources deleted from Git           |
| `--target-namespace` | -     | string | -           | Target namespace for deployed resources    |
| `--output`           | `-o`  | string | table       | Output format: table, json, yaml           |

**Example:**

```bash
# Create Kustomization for app deployment
ops k8s flux ks create app-ks \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./kustomize/overlays/production

# Deploy to specific namespace with custom interval
ops k8s flux ks create database-ks \
  -n production \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./database \
  --target-namespace postgres \
  --interval 10m

# Disable automatic pruning (keep resources if removed from Git)
ops k8s flux ks create monitoring-ks \
  --source-name monitoring-repo \
  --source-kind GitRepository \
  --path ./deploy \
  --no-prune
```

#### `ops k8s flux ks delete`

Delete a Kustomization.

```bash
ops k8s flux ks delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                         |
| -------- | -------- | ----------------------------------- |
| NAME     | yes      | Name of the Kustomization to delete |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s flux ks delete app-ks -n production

# Delete without confirmation
ops k8s flux ks delete app-ks -n production --force
```

#### `ops k8s flux ks suspend/resume/reconcile/status`

Control Kustomization reconciliation.

```bash
# Suspend automatic reconciliation
ops k8s flux ks suspend app-ks -n production

# Resume automatic reconciliation
ops k8s flux ks resume app-ks -n production

# Trigger immediate reconciliation
ops k8s flux ks reconcile app-ks -n production

# Check reconciliation status
ops k8s flux ks status app-ks -n production
```

---

### HelmReleases

HelmReleases define how to deploy applications from a HelmRepository using Helm.

#### `ops k8s flux hr list`

List all HelmReleases.

```bash
ops k8s flux hr list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--selector`  | `-l`  | string | -       | Label selector                   |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List HelmReleases
ops k8s flux hr list

# List in specific namespace
ops k8s flux hr list -n production

# List with label filter
ops k8s flux hr list -l app=monitoring

# JSON output
ops k8s flux hr list -o json
```

**Example Output:**

```text
HelmReleases
Name        Namespace       Chart   Source         Ready  Suspended  Age
nginx       ingress         nginx   bitnami        true   false      7d
prometheus  monitoring      kube-prom-stack  jetstack  true   false      5d
app         production      myapp   mycompany      true   false      3d
```

#### `ops k8s flux hr get`

Get details of a specific HelmRelease.

```bash
ops k8s flux hr get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| NAME     | yes      | Name of the HelmRelease |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get HelmRelease details
ops k8s flux hr get nginx -n ingress

# View full YAML
ops k8s flux hr get nginx -n ingress -o yaml
```

#### `ops k8s flux hr create`

Create a new HelmRelease.

```bash
ops k8s flux hr create NAME --chart CHART --source-name SOURCE [OPTIONS]
```

**Arguments:**

| Argument | Required | Description              |
| -------- | -------- | ------------------------ |
| NAME     | yes      | Name for the HelmRelease |

**Options:**

| Option               | Short | Type   | Default     | Description                                  |
| -------------------- | ----- | ------ | ----------- | -------------------------------------------- |
| `--chart`            | -     | string | required    | Helm chart name                              |
| `--source-name`      | -     | string | required    | Chart source reference name (HelmRepository) |
| `--source-kind`      | -     | string | required    | Chart source kind (e.g., HelmRepository)     |
| `--namespace`        | `-n`  | string | default     | Kubernetes namespace                         |
| `--source-namespace` | -     | string | flux-system | Namespace of the source                      |
| `--interval`         | -     | string | 5m          | Reconciliation interval                      |
| `--target-namespace` | -     | string | NAME        | Target namespace for Helm release            |
| `--output`           | `-o`  | string | table       | Output format: table, json, yaml             |

**Example:**

```bash
# Create HelmRelease for nginx-ingress
ops k8s flux hr create nginx-ingress \
  --chart nginx-ingress-controller \
  --source-name bitnami \
  --source-kind HelmRepository \
  --target-namespace ingress-nginx

# Create in specific namespace with custom interval
ops k8s flux hr create prometheus \
  -n monitoring \
  --chart kube-prometheus-stack \
  --source-name jetstack \
  --source-kind HelmRepository \
  --target-namespace monitoring \
  --interval 10m

# Deploy to different namespace than release
ops k8s flux hr create app \
  --chart myapp \
  --source-name mycompany \
  --source-kind HelmRepository \
  --target-namespace production
```

#### `ops k8s flux hr delete`

Delete a HelmRelease.

```bash
ops k8s flux hr delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                       |
| -------- | -------- | --------------------------------- |
| NAME     | yes      | Name of the HelmRelease to delete |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s flux hr delete nginx-ingress -n ingress

# Delete without confirmation
ops k8s flux hr delete nginx-ingress -n ingress --force
```

#### `ops k8s flux hr suspend/resume/reconcile/status`

Control HelmRelease reconciliation.

```bash
# Suspend automatic reconciliation
ops k8s flux hr suspend nginx-ingress -n ingress

# Resume automatic reconciliation
ops k8s flux hr resume nginx-ingress -n ingress

# Trigger immediate reconciliation
ops k8s flux hr reconcile nginx-ingress -n ingress

# Check reconciliation status
ops k8s flux hr status nginx-ingress -n ingress
```

---

## Integration Examples

### Basic GitOps Setup

This example demonstrates a complete Flux CD setup for deploying applications from Git.

**Step 1: Create GitRepository**

```bash
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/app-deployment \
  --branch main \
  --interval 1m
```

**Step 2: Create Kustomization for deployment**

```bash
ops k8s flux ks create app-kustomization \
  -n production \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./kustomize/overlays/production \
  --target-namespace production \
  --interval 5m
```

**Step 3: Monitor deployment**

```bash
# Check Kustomization status
ops k8s flux ks status app-kustomization -n production

# List all resources deployed by Flux
kubectl get all -n production -l kustomize.fluxcd.io/name=app-kustomization
```

**Step 4: Trigger manual reconciliation**

```bash
# Force immediate sync with Git
ops k8s flux ks reconcile app-kustomization -n production
```

### Multi-Environment Deployment

Deploy the same application to multiple environments using Flux.

**Repository Structure:**

```text
app-deployment/
├── kustomize/
│   ├── base/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/
│       │   ├── kustomization.yaml
│       │   └── patch-replicas.yaml
│       ├── staging/
│       │   ├── kustomization.yaml
│       │   └── patch-replicas.yaml
│       └── production/
│           ├── kustomization.yaml
│           └── patch-replicas.yaml
```

**Create sources and kustomizations:**

```bash
# Create GitRepository
ops k8s flux source git create app-repo \
  --url https://github.com/myorg/app-deployment \
  --branch main

# Development environment
ops k8s flux ks create app-dev \
  -n development \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./kustomize/overlays/dev \
  --target-namespace development

# Staging environment
ops k8s flux ks create app-staging \
  -n staging \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./kustomize/overlays/staging \
  --target-namespace staging

# Production environment
ops k8s flux ks create app-production \
  -n production \
  --source-name app-repo \
  --source-kind GitRepository \
  --path ./kustomize/overlays/production \
  --target-namespace production
```

**Monitor across environments:**

```bash
# Check all deployments
for env in development staging production; do
  echo "=== $env ==="
  ops k8s flux ks status app-$env -n "$env"
done

# Reconcile all
for env in development staging production; do
  ops k8s flux ks reconcile app-$env -n "$env"
done
```

### Helm Release Management

Manage Helm-based deployments using Flux.

**Step 1: Create HelmRepositories**

```bash
# Add Bitnami charts
ops k8s flux source helm create bitnami \
  --url https://charts.bitnami.com/bitnami

# Add Jetstack Helm repository
ops k8s flux source helm create jetstack \
  --url https://charts.jetstack.io
```

**Step 2: Create HelmReleases**

```bash
# Deploy nginx-ingress
ops k8s flux hr create nginx-ingress \
  --chart nginx-ingress-controller \
  --source-name bitnami \
  --source-kind HelmRepository \
  --target-namespace ingress-nginx

# Deploy cert-manager
ops k8s flux hr create cert-manager \
  --chart cert-manager \
  --source-name jetstack \
  --source-kind HelmRepository \
  --target-namespace cert-manager
```

**Step 3: Monitor Helm releases**

```bash
# Check HelmRelease status
ops k8s flux hr list

# Get specific release details
ops k8s flux hr status nginx-ingress

# Verify Helm releases are installed
helm list -A
```

### Monitoring and Troubleshooting

Monitor Flux synchronization status and troubleshoot issues.

**Check Flux system status:**

```bash
# Verify Flux controllers are running
kubectl get pods -n flux-system

# Check Flux version and features
flux check

# View controller logs
flux logs --all-namespaces
```

**Monitor source synchronization:**

```bash
# Check GitRepository status
ops k8s flux source git list
ops k8s flux source git status app-repo

# Check HelmRepository status
ops k8s flux source helm list
ops k8s flux source helm status bitnami
```

**Monitor deployment synchronization:**

```bash
# Check Kustomization status
ops k8s flux ks list -n production
ops k8s flux ks status app-kustomization -n production

# Check HelmRelease status
ops k8s flux hr list -n ingress-nginx
ops k8s flux hr status nginx-ingress -n ingress-nginx
```

**Suspend and resume for maintenance:**

```bash
# Pause all automatic reconciliation during maintenance
ops k8s flux source git suspend app-repo
ops k8s flux ks suspend app-kustomization -n production

# Resume after maintenance
ops k8s flux source git resume app-repo
ops k8s flux ks resume app-kustomization -n production
```

---

## Troubleshooting

| Issue                                   | Symptoms                                          | Solution             |
| --------------------------------------- | ------------------------------------------------- | -------------------- |
| **Flux not detected**                   | "Flux CD not found"                               | Install Flux: `flux  |
| **Source not ready**                    | GitRepository/HelmRepository status shows "False" | Check Git/Helm       |
| **Kustomization/HelmRelease not ready** | Status shows "False", reconciliation failing      | Verify source is     |
| **Resources not deployed**              | Kustomization ready but resources missing         | Check target namespa |
| **Authentication failures**             | "Authentication failed" in status                 | Verify GitHub/GitLab |
| **Infinite reconciliation**             | Reconciliation keeps retrying                     | Check for validation |
| **Permission denied errors**            | "forbidden" in logs                               | Verify service       |
| **Source/reconciliation timeouts**      | Operations timeout or hang                        | Increase timeout     |
| **Webhook failures**                    | Webhook delivery failures in notifications        | Check webhook        |
| **Suspend not working**                 | Resources still reconciling after suspend         | Check suspend        |

---

## See Also

- **[Flux CD Documentation](https://fluxcd.io/)** - Official Flux docs
- **[Flux GitHub Repository](https://github.com/fluxcd/flux2)** - Source code and issues
- **[Flux CLI Reference](https://fluxcd.io/docs/cmd/)** - Official CLI documentation
- **[GitOps Best Practices](https://fluxcd.io/docs/guides/gitops-conventions/)** - Recommended practices
- **[Kustomize Integration](https://fluxcd.io/docs/components/kustomize/kustomization/)** - Kustomize with Flux
- **[Helm Integration](https://fluxcd.io/docs/components/helm/releases/)** - Helm with Flux
- **[Notifications and Webhooks](https://fluxcd.io/docs/components/notification/)** - Slack, GitHub, GitLab integration
- **[Kubernetes Plugin Index](../index.md)** - Back to main K8s documentation
- **[Kyverno Policy Engine](./kyverno.md)** - Policy enforcement with Flux deployments
- **[External Secrets](./external-secrets.md)** - Secret management with Flux
