# Kubernetes Plugin > Ecosystem > Helm

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [install](#ops-k8s-helm-install)
  - [upgrade](#ops-k8s-helm-upgrade)
  - [rollback](#ops-k8s-helm-rollback)
  - [uninstall](#ops-k8s-helm-uninstall)
  - [list](#ops-k8s-helm-list)
  - [history](#ops-k8s-helm-history)
  - [status](#ops-k8s-helm-status)
  - [get-values](#ops-k8s-helm-get-values)
  - [template](#ops-k8s-helm-template)
  - [search](#ops-k8s-helm-search)
  - [repo add](#ops-k8s-helm-repo-add)
  - [repo list](#ops-k8s-helm-repo-list)
  - [repo update](#ops-k8s-helm-repo-update)
  - [repo remove](#ops-k8s-helm-repo-remove)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Helm is the package manager for Kubernetes, enabling you to define, install, and upgrade complex Kubernetes applications
through reusable charts. The System Control CLI's Helm ecosystem tool provides comprehensive commands for:

- **Release Management**: Install, upgrade, rollback, and uninstall Helm releases
- **Repository Management**: Add, list, update, and remove chart repositories
- **Chart Operations**: Search, render templates, and retrieve configuration values
- **Multi-cluster Support**: Manage releases across different namespaces and clusters

Helm integrates deeply with the Kubernetes plugin, allowing you to manage application deployments declaratively using
versioned, shareable charts. This makes it ideal for GitOps workflows, multi-environment deployments, and standardizing
application packaging across your infrastructure.

### Why Use Helm with System Control

- **Simplified Chart Management**: Replace complex kubectl manifests with parameterized Helm charts
- **Rollback Capabilities**: Automatically track release history for quick rollbacks
- **Multi-environment Deployment**: Use the same chart with different values files for dev, staging, and production
- **Repository Integration**: Centrally manage and share charts from public and private repositories
- **Declarative Configuration**: Version control your release specifications alongside your infrastructure code

---

## Prerequisites

### Required

- **Helm Binary**: Helm 3.0 or later must be installed and available on your system PATH
- **Kubernetes Access**: Valid kubeconfig and cluster connectivity via the core Kubernetes plugin
- **Permissions**: RBAC permissions to create, update, and delete resources in target namespaces

### Optional

- **Chart Repositories**: Pre-configured Helm repositories (Bitnami, Jetstack, etc.) for chart discovery
- **Values Files**: YAML files containing release-specific configuration
- **Chart Artifacts**: Local or remote Helm charts

### Installation

Install Helm from the official website:

```bash
# macOS with Homebrew
brew install helm

# Linux with curl
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
helm version
```

---

## Detection

The System Control CLI automatically detects Helm availability by:

1. Checking if the `helm` binary exists in your system PATH
2. Verifying Helm version compatibility (3.0+)
3. Testing connection to configured chart repositories

If Helm is not detected, you will see a clear error message with installation guidance:

```text
Error: Helm binary not found
Install helm: https://helm.sh/docs/intro/install/
```

---

## Configuration

Helm configuration is managed through your System Control CLI config files and environment variables. No additional
setup is required beyond having the Helm binary installed.

### Environment Variables

Configure Helm behavior using standard environment variables:

```bash
# Specify kubeconfig location
export KUBECONFIG=~/.kube/config

# Set default namespace for Helm operations
export HELM_NAMESPACE=default

# Increase timeout for long-running operations
export HELM_TIMEOUT=5m

# Enable debug output
export HELM_DEBUG=true
```

### Chart Repositories

Pre-configure trusted chart repositories:

```bash
# Add Bitnami repository
ops k8s helm repo add bitnami https://charts.bitnami.com/bitnami

# Add Jetstack (cert-manager)
ops k8s helm repo add jetstack https://charts.jetstack.io

# Add Kubernetes Dashboard
ops k8s helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/

# Update all repositories
ops k8s helm repo update
```

---

## Command Reference

### `ops k8s helm install`

Install a Helm chart and create a new release.

```bash
ops k8s helm install RELEASE_NAME CHART [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description                                            |
| -------------- | -------- | ------------------------------------------------------ |
| `RELEASE_NAME` | Yes      | Name for the new release (must be unique in namespace) |
| `CHART`        | Yes      | Chart reference: `repo/chart`, local path, or URL      |

**Options:**

| Option               | Short | Type     | Default | Description                                        |
| -------------------- | ----- | -------- | ------- | -------------------------------------------------- |
| `--namespace`        | `-n`  | string   | default | Kubernetes namespace for installation              |
| `--values`           | `-f`  | string[] | -       | Values YAML file(s) (can specify multiple)         |
| `--set`              | -     | string[] | -       | Set individual values (key=value format)           |
| `--version`          | -     | string   | latest  | Chart version constraint (e.g., "1.2.0" or "~1.2") |
| `--create-namespace` | -     | flag     | false   | Create namespace if it doesn't exist               |
| `--wait`             | -     | flag     | false   | Wait for resources to be ready before returning    |
| `--timeout`          | -     | string   | 5m      | Timeout duration (e.g., "5m0s", "30s")             |
| `--dry-run`          | -     | flag     | false   | Preview changes without executing                  |

**Examples:**

```bash
# Install from public repository
ops k8s helm install my-release bitnami/nginx

# Install in specific namespace
ops k8s helm install my-app ./charts/app -n production

# Install with custom values
ops k8s helm install redis bitnami/redis -f values.yaml --set auth.enabled=true

# Install specific version with namespace creation
ops k8s helm install pg bitnami/postgresql --version 12.0.0 --create-namespace -n databases

# Preview before installing
ops k8s helm install my-release bitnami/nginx --dry-run

# Wait for deployment readiness
ops k8s helm install my-app ./charts/app --wait --timeout 10m
```

**Example Output:**

```text
NAME: my-release
LAST DEPLOYED: Thu Feb 16 10:30:45 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None

NOTES:
1. Get the application URL by running these commands:
  export POD_NAME=$(kubectl get pods --namespace default -l "app.kubernetes.io/name=nginx" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace default $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
```

---

### `ops k8s helm upgrade`

Upgrade an existing Helm release or install if it doesn't exist.

```bash
ops k8s helm upgrade RELEASE_NAME CHART [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description                                       |
| -------------- | -------- | ------------------------------------------------- |
| `RELEASE_NAME` | Yes      | Name of existing release to upgrade               |
| `CHART`        | Yes      | Chart reference: `repo/chart`, local path, or URL |

**Options:**

| Option               | Short | Type     | Default | Description                      |
| -------------------- | ----- | -------- | ------- | -------------------------------- |
| `--namespace`        | `-n`  | string   | default | Kubernetes namespace             |
| `--values`           | `-f`  | string[] | -       | Values YAML file(s)              |
| `--set`              | -     | string[] | -       | Set individual values            |
| `--version`          | -     | string   | latest  | Chart version constraint         |
| `--install`          | `-i`  | flag     | false   | Install if release doesn't exist |
| `--create-namespace` | -     | flag     | false   | Create namespace if needed       |
| `--wait`             | -     | flag     | false   | Wait for resources to be ready   |
| `--timeout`          | -     | string   | 5m      | Timeout duration                 |
| `--dry-run`          | -     | flag     | false   | Preview changes only             |
| `--reuse-values`     | -     | flag     | false   | Keep previous release's values   |
| `--reset-values`     | -     | flag     | false   | Reset values to chart defaults   |

**Examples:**

```bash
# Simple upgrade
ops k8s helm upgrade my-release bitnami/nginx

# Upgrade with new values file
ops k8s helm upgrade my-app ./charts/app -f values-prod.yaml

# Upgrade or install if missing
ops k8s helm upgrade my-release bitnami/redis --install --create-namespace

# Upgrade and merge with previous values
ops k8s helm upgrade my-release bitnami/nginx --reuse-values --set image.tag=1.25

# Reset to defaults and apply new values
ops k8s helm upgrade my-release bitnami/nginx --reset-values -f new-values.yaml

# Preview upgrade
ops k8s helm upgrade my-release bitnami/nginx --dry-run
```

**Example Output:**

```text
Release "my-release" has been upgraded. Happy Helming!
NAME: my-release
LAST DEPLOYED: Thu Feb 16 10:35:22 2026
NAMESPACE: default
STATUS: deployed
REVISION: 2
DESCRIPTION: Upgrade complete

NOTES:
The release upgrade completed successfully.
```

---

### `ops k8s helm rollback`

Roll back a release to a previous revision.

```bash
ops k8s helm rollback RELEASE_NAME [REVISION] [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description                                     |
| -------------- | -------- | ----------------------------------------------- |
| `RELEASE_NAME` | Yes      | Name of release to roll back                    |
| `REVISION`     | No       | Revision number (defaults to previous revision) |

**Options:**

| Option        | Short | Type   | Default | Description                    |
| ------------- | ----- | ------ | ------- | ------------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace           |
| `--wait`      | -     | flag   | false   | Wait for resources to be ready |
| `--timeout`   | -     | string | 5m      | Timeout duration               |
| `--dry-run`   | -     | flag   | false   | Preview rollback only          |

**Examples:**

```bash
# Rollback to previous revision
ops k8s helm rollback my-release

# Rollback to specific revision
ops k8s helm rollback my-release 3

# Rollback with wait
ops k8s helm rollback my-release 2 --wait

# Preview rollback
ops k8s helm rollback my-release --dry-run
```

**Example Output:**

```text
Rollback was a success! Happy Helming!
Rollback to release my-release, revision 1
```

---

### `ops k8s helm uninstall`

Uninstall a Helm release.

```bash
ops k8s helm uninstall RELEASE_NAME [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description                  |
| -------------- | -------- | ---------------------------- |
| `RELEASE_NAME` | Yes      | Name of release to uninstall |

**Options:**

| Option           | Short | Type   | Default | Description                          |
| ---------------- | ----- | ------ | ------- | ------------------------------------ |
| `--namespace`    | `-n`  | string | default | Kubernetes namespace                 |
| `--keep-history` | -     | flag   | false   | Keep release history after uninstall |
| `--dry-run`      | -     | flag   | false   | Preview uninstall only               |

**Examples:**

```bash
# Uninstall release
ops k8s helm uninstall my-release

# Uninstall in specific namespace
ops k8s helm uninstall my-release -n production

# Keep release history for future restore
ops k8s helm uninstall my-release --keep-history

# Preview uninstall
ops k8s helm uninstall my-release --dry-run
```

**Example Output:**

```text
release "my-release" uninstalled
```

---

### `ops k8s helm list`

List installed Helm releases.

```bash
ops k8s helm list [OPTIONS]
```

**Options:**

| Option             | Short | Type   | Default | Description                                          |
| ------------------ | ----- | ------ | ------- | ---------------------------------------------------- |
| `--namespace`      | `-n`  | string | default | Kubernetes namespace                                 |
| `--all-namespaces` | `-A`  | flag   | false   | List releases across all namespaces                  |
| `--all`            | `-a`  | flag   | false   | Include releases in all states (failed, uninstalled) |
| `--filter`         | `-q`  | string | -       | Filter releases by name pattern                      |
| `--output`         | `-o`  | string | table   | Output format: table, json, or yaml                  |

**Examples:**

```bash
# List releases in default namespace
ops k8s helm list

# List releases in specific namespace
ops k8s helm list -n production

# List all releases across all namespaces
ops k8s helm list -A

# Filter by name pattern
ops k8s helm list --filter 'my-*'

# Output as JSON
ops k8s helm list -A --output json

# Include failed releases
ops k8s helm list --all -A
```

**Example Output:**

```text
NAME            NAMESPACE   REVISION    STATUS      CHART                   APP VERSION
my-release      default     1           deployed    nginx-13.2.1            1.23.0
my-app         production  5           deployed    postgresql-12.0.0       14.2
redis-cache    default     2           failed      redis-17.0.0            7.0
```

---

### `ops k8s helm history`

Show release history and revisions.

```bash
ops k8s helm history RELEASE_NAME [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description     |
| -------------- | -------- | --------------- |
| `RELEASE_NAME` | Yes      | Name of release |

**Options:**

| Option        | Short | Type   | Default | Description                         |
| ------------- | ----- | ------ | ------- | ----------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace                |
| `--max`       | -     | int    | -       | Maximum number of revisions to show |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml |

**Examples:**

```bash
# Show all revisions
ops k8s helm history my-release

# Show last 5 revisions
ops k8s helm history my-release --max 5

# Show history in JSON
ops k8s helm history my-release --output json

# Show history for release in specific namespace
ops k8s helm history my-release -n production
```

**Example Output:**

```text
REVISION    STATUS          CHART                   APP VERSION     DESCRIPTION
1           superseded      nginx-13.0.0            1.21.0          Install complete
2           superseded      nginx-13.1.0            1.22.0          Upgrade complete
3           superseded      nginx-13.1.5            1.23.0          Upgrade complete
4           deployed        nginx-13.2.1            1.23.0          Upgrade complete
```

---

### `ops k8s helm status`

Show the status of a specific release.

```bash
ops k8s helm status RELEASE_NAME [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description     |
| -------------- | -------- | --------------- |
| `RELEASE_NAME` | Yes      | Name of release |

**Options:**

| Option        | Short | Type   | Default | Description                                   |
| ------------- | ----- | ------ | ------- | --------------------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace                          |
| `--revision`  | -     | int    | -       | Get status for specific revision (not latest) |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml           |

**Examples:**

```bash
# Show current status
ops k8s helm status my-release

# Show status in specific namespace
ops k8s helm status my-release -n production

# Show status of previous revision
ops k8s helm status my-release --revision 3

# Output as JSON
ops k8s helm status my-release --output json
```

**Example Output:**

```text
NAME: my-release
LAST DEPLOYED: Thu Feb 16 10:30:45 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete

NOTES:
1. Get the application URL by running these commands:
  export POD_NAME=$(kubectl get pods --namespace default -l "app.kubernetes.io/name=nginx" -o jsonpath="{.items[0].metadata.name}")
  echo "Visit http://127.0.0.1:8080 to use your application"
```

---

### `ops k8s helm get-values`

Retrieve values for a release.

```bash
ops k8s helm get-values RELEASE_NAME [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description     |
| -------------- | -------- | --------------- |
| `RELEASE_NAME` | Yes      | Name of release |

**Options:**

| Option        | Short | Type   | Default | Description                              |
| ------------- | ----- | ------ | ------- | ---------------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace                     |
| `--all`       | `-a`  | flag   | false   | Show all values including chart defaults |
| `--revision`  | -     | int    | -       | Get values from specific revision        |

**Examples:**

```bash
# Show user-supplied values
ops k8s helm get-values my-release

# Show all values (including defaults)
ops k8s helm get-values my-release --all

# Get values from specific revision
ops k8s helm get-values my-release --revision 2

# Get values for release in specific namespace
ops k8s helm get-values my-release -n production
```

**Example Output:**

```yaml
auth:
  enabled: true
  password: mypassword
image:
  repository: bitnami/redis
  tag: 7.0
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

---

### `ops k8s helm template`

Render chart templates locally without applying to cluster.

```bash
ops k8s helm template RELEASE_NAME CHART [OPTIONS]
```

**Arguments:**

| Argument       | Required | Description                                       |
| -------------- | -------- | ------------------------------------------------- |
| `RELEASE_NAME` | Yes      | Release name for template rendering               |
| `CHART`        | Yes      | Chart reference: `repo/chart`, local path, or URL |

**Options:**

| Option        | Short | Type     | Default | Description              |
| ------------- | ----- | -------- | ------- | ------------------------ |
| `--namespace` | `-n`  | string   | default | Kubernetes namespace     |
| `--values`    | `-f`  | string[] | -       | Values YAML file(s)      |
| `--set`       | -     | string[] | -       | Set individual values    |
| `--version`   | -     | string   | latest  | Chart version constraint |

**Examples:**

```bash
# Template with defaults
ops k8s helm template my-release bitnami/nginx

# Template with custom values
ops k8s helm template my-app ./charts/app -f values.yaml

# Template with value overrides
ops k8s helm template my-release bitnami/redis --set auth.enabled=false

# Template in specific namespace
ops k8s helm template my-release bitnami/nginx -n production

# Template with multiple value files
ops k8s helm template my-app ./charts/app -f values.yaml -f values-prod.yaml
```

**Example Output:**

```yaml
---
# Source: nginx/templates/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: default
---
# Source: nginx/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-release-nginx
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: bitnami/nginx:1.23.0
          ports:
            - containerPort: 8080
```

---

### `ops k8s helm search`

Search chart repositories for available charts.

```bash
ops k8s helm search KEYWORD [OPTIONS]
```

**Arguments:**

| Argument  | Required | Description                         |
| --------- | -------- | ----------------------------------- |
| `KEYWORD` | Yes      | Chart name or keyword to search for |

**Options:**

| Option       | Short | Type   | Default | Description                                  |
| ------------ | ----- | ------ | ------- | -------------------------------------------- |
| `--version`  | -     | string | -       | Version constraint (e.g., "1.2.0" or "^1.2") |
| `--versions` | -     | flag   | false   | Show all versions, not just latest           |
| `--output`   | `-o`  | string | table   | Output format: table, json, or yaml          |

**Examples:**

```bash
# Search for nginx charts
ops k8s helm search nginx

# Search for PostgreSQL with all versions
ops k8s helm search postgresql --versions

# Search for Redis with output as JSON
ops k8s helm search bitnami/redis --output json

# Search for specific version range
ops k8s helm search postgresql --version "^11.0"
```

**Example Output:**

```text
NAME                                    CHART VERSION   APP VERSION     DESCRIPTION
bitnami/nginx                           13.2.1          1.23.0          NGINX Open Source is a web server that can be used as a reverse proxy
bitnami/nginx-ingress-controller        9.3.4           1.4.0           NGINX Ingress Controller
jetstack/cert-manager                   v1.10.0         v1.10.0         A Kubernetes add-on to automate the management of TLS certificates
kubernetes-dashboard/kubernetes-dashboard 6.0.0         2.6.0           General-purpose web UI for Kubernetes clusters
```

---

### `ops k8s helm repo add`

Add a chart repository.

```bash
ops k8s helm repo add NAME URL [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                       |
| -------- | -------- | ------------------------------------------------- |
| `NAME`   | Yes      | Local name for the repository                     |
| `URL`    | Yes      | Repository URL (e.g., https://charts.example.com) |

**Options:**

| Option           | Short | Type | Default | Description                                |
| ---------------- | ----- | ---- | ------- | ------------------------------------------ |
| `--force-update` | -     | flag | false   | Replace existing repository with same name |

**Examples:**

```bash
# Add Bitnami repository
ops k8s helm repo add bitnami https://charts.bitnami.com/bitnami

# Add Jetstack repository
ops k8s helm repo add jetstack https://charts.jetstack.io

# Replace existing repository
ops k8s helm repo add stable https://charts.helm.sh/stable --force-update

# Add private repository
ops k8s helm repo add myrepo https://charts.mycompany.com/helm
```

**Example Output:**

```text
"bitnami" has been added to your repositories
```

---

### `ops k8s helm repo list`

List configured chart repositories.

```bash
ops k8s helm repo list [OPTIONS]
```

**Options:**

| Option     | Short | Type   | Default | Description                         |
| ---------- | ----- | ------ | ------- | ----------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, or yaml |

**Examples:**

```bash
# List all repositories
ops k8s helm repo list

# Output as JSON
ops k8s helm repo list --output json

# Output as YAML
ops k8s helm repo list --output yaml
```

**Example Output:**

```text
NAME            URL
bitnami         https://charts.bitnami.com/bitnami
jetstack        https://charts.jetstack.io
stable          https://charts.helm.sh/stable
kubernetes-dashboard  https://kubernetes.github.io/dashboard/
```

---

### `ops k8s helm repo update`

Update chart repository indexes.

```bash
ops k8s helm repo update [REPO_NAMES...]
```

**Arguments:**

| Argument     | Required | Description                                      |
| ------------ | -------- | ------------------------------------------------ |
| `REPO_NAMES` | No       | Specific repositories to update (all if omitted) |

**Examples:**

```bash
# Update all repositories
ops k8s helm repo update

# Update specific repository
ops k8s helm repo update bitnami

# Update multiple repositories
ops k8s helm repo update bitnami stable jetstack
```

**Example Output:**

```text
Hang tight while we grab the latest from your chart repositories...
...Successfully got an update from the "bitnami" chart repository
...Successfully got an update from the "stable" chart repository
Update Complete. ⎈ Happy Helming!⎈
```

---

### `ops k8s helm repo remove`

Remove a chart repository.

```bash
ops k8s helm repo remove NAME
```

**Arguments:**

| Argument | Required | Description                  |
| -------- | -------- | ---------------------------- |
| `NAME`   | Yes      | Name of repository to remove |

**Examples:**

```bash
# Remove Bitnami repository
ops k8s helm repo remove bitnami

# Remove multiple repositories
ops k8s helm repo remove stable
ops k8s helm repo remove deprecated-repo
```

**Example Output:**

```text
"bitnami" has been removed from your repositories
```

---

## Integration Examples

### Example 1: Install and Manage Application Stack

Deploy a complete application stack using Helm charts from multiple repositories:

```bash
# Add repositories
ops k8s helm repo add bitnami https://charts.bitnami.com/bitnami
ops k8s helm repo add jetstack https://charts.jetstack.io
ops k8s helm repo update

# Create namespaces
kubectl create namespace production
kubectl create namespace cert-system

# Install PostgreSQL database
ops k8s helm install my-db bitnami/postgresql \
  -n production \
  --set auth.username=appuser \
  --set auth.password=securepass123 \
  --set primary.persistence.size=20Gi \
  --wait

# Install Redis cache
ops k8s helm install my-cache bitnami/redis \
  -n production \
  --set auth.enabled=true \
  --set auth.password=cachepass123 \
  --wait

# Install cert-manager for TLS
ops k8s helm install cert-manager jetstack/cert-manager \
  -n cert-system \
  --create-namespace \
  --set installCRDs=true \
  --wait
```

### Example 2: Multi-environment Deployment

Deploy the same chart across environments with different configurations:

```bash
# Create namespace structure
kubectl create namespace production
kubectl create namespace staging
kubectl create namespace development

# Create values files
cat > values-dev.yaml << EOF
replicas: 1
environment: development
image:
  tag: latest
resources:
  limits:
    cpu: 200m
    memory: 256Mi
EOF

cat > values-staging.yaml << EOF
replicas: 2
environment: staging
image:
  tag: v1.2.3
resources:
  limits:
    cpu: 500m
    memory: 512Mi
EOF

cat > values-prod.yaml << EOF
replicas: 3
environment: production
image:
  tag: v1.2.3
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
EOF

# Deploy to each environment
ops k8s helm install my-app ./charts/myapp -f values-dev.yaml -n development
ops k8s helm install my-app ./charts/myapp -f values-staging.yaml -n staging
ops k8s helm install my-app ./charts/myapp -f values-prod.yaml -n production
```

### Example 3: Upgrade with Rollback Safety

Perform a safe upgrade with rollback capability:

```bash
# Check current status
ops k8s helm status my-app -n production

# Preview the upgrade
ops k8s helm upgrade my-app ./charts/myapp \
  -n production \
  --values values-prod.yaml \
  --dry-run

# Show history before upgrade
ops k8s helm history my-app -n production

# Perform actual upgrade
ops k8s helm upgrade my-app ./charts/myapp \
  -n production \
  --values values-prod.yaml \
  --wait \
  --timeout 10m

# If needed, quickly rollback
ops k8s helm rollback my-app -n production
```

### Example 4: Template Validation and Rendering

Preview templates before installation:

```bash
# Render templates to validate structure
ops k8s helm template my-app ./charts/myapp \
  -f values.yaml \
  > rendered.yaml

# Validate YAML syntax
kubectl apply --dry-run=client -f rendered.yaml

# Check differences before applying
ops k8s helm upgrade my-app ./charts/myapp \
  -f values.yaml \
  --dry-run \
  --output json | jq .

# Apply after validation
ops k8s helm upgrade my-app ./charts/myapp \
  -f values.yaml \
  --install \
  --wait
```

### Example 5: Repository and Chart Discovery

Discover and explore charts before installation:

```bash
# Search for available database charts
ops k8s helm search postgresql --versions --output json

# Check specific chart versions
ops k8s helm search bitnami/postgresql --versions

# Get chart details
ops k8s helm template test-release bitnami/postgresql --version 12.0.0 | head -50

# List repository contents
ops k8s helm repo list

# Update and search latest
ops k8s helm repo update
ops k8s helm search nginx
```

---

## Troubleshooting

| Issue                             | Solution                                                                    |
| --------------------------------- | --------------------------------------------------------------------------- |
| **Helm binary not found**         | Install Helm following the [official documentation](https://helm.sh         |
| **Connection refused**            | Verify Kubernetes cluster                                                   |
| **Release already exists**        | Use `--install` flag during upgrade to automatically install if missing, or |
| **Insufficient permissions**      | Check RBAC permissions: `kubectl auth                                       |
| **Chart not found in repository** | Update repositories: `ops                                                   |
| **Timeout during --wait**         | Increase timeout: `--timeout 15m`. Check pod status: `kubectl               |
| **Values file not found**         | Verify file path is                                                         |
| **Namespace does not exist**      | Create namespace first: `kubectl                                            |
| **Rollback failed**               | Check release history: `ops                                                 |
| **Repository connection failed**  | Test connectivity:                                                          |
| **Value syntax errors**           | Validate YAML: Use                                                          |
| **Release stuck in pending**      | Check resource availability: `kubectl                                       |
| **Template rendering errors**     | Validate chart: `ops k8s helm lint ./charts/myapp`.                         |

---

## See Also

- [Helm Official Documentation](https://helm.sh/docs/)
- [Kubernetes Plugin Index](../index.md)
- [Kustomize Ecosystem](./kustomize.md)
- [ArgoCD Ecosystem](./argocd.md)
- [Kubernetes Commands Reference](../commands/)
- [Kubernetes Integration Guide](../../integrations/kubernetes.md)
