# Kubernetes Plugin > Ecosystem > ArgoCD

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [app list](#ops-k8s-argocd-app-list)
  - [app get](#ops-k8s-argocd-app-get)
  - [app create](#ops-k8s-argocd-app-create)
  - [app delete](#ops-k8s-argocd-app-delete)
  - [app sync](#ops-k8s-argocd-app-sync)
  - [app rollback](#ops-k8s-argocd-app-rollback)
  - [app health](#ops-k8s-argocd-app-health)
  - [app diff](#ops-k8s-argocd-app-diff)
  - [project list](#ops-k8s-argocd-project-list)
  - [project get](#ops-k8s-argocd-project-get)
  - [project create](#ops-k8s-argocd-project-create)
  - [project delete](#ops-k8s-argocd-project-delete)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

ArgoCD is a declarative, GitOps continuous delivery tool for Kubernetes. It simplifies application deployment by
managing resources directly from Git repositories. The System Control CLI's ArgoCD ecosystem tool provides comprehensive
commands for:

- **Application Management**: Create, list, get, delete, and monitor ArgoCD Applications
- **Synchronization**: Sync applications with Git source and rollback to previous states
- **Health Monitoring**: Check application health and diff status against desired state
- **Project Management**: Create and manage ArgoCD Projects for multi-tenancy and access control
- **GitOps Workflows**: Enable declarative, version-controlled deployments

### Why Use ArgoCD with System Control

- **Declarative Deployments**: Define desired state in Git, ArgoCD ensures cluster state matches
- **Automated Reconciliation**: Applications automatically sync when Git repository changes
- **Pull-based Deployment**: Clusters pull updates instead of CI/CD systems pushing changes (more secure)
- **Multi-cluster Support**: Manage applications across multiple Kubernetes clusters
- **Rollback Capability**: Instantly rollback to any previous Git commit
- **GitOps Compliance**: Leverage Git as the single source of truth for infrastructure
- **Access Control**: Projects enable fine-grained RBAC and multi-team deployments

---

## Prerequisites

### Required

- **ArgoCD Installation**: ArgoCD server must be installed and running in your cluster
- **Kubernetes Access**: Valid kubeconfig and connectivity to ArgoCD cluster
- **Permissions**: RBAC permissions to manage Application and AppProject resources
- **Git Repository**: Git repository containing application manifests or Helm charts

### Optional

- **ArgoCD CLI**: For additional troubleshooting (optional, not required by System Control CLI)
- **SSH Keys**: For private Git repositories (configured in ArgoCD server)
- **Webhook Integration**: Git webhooks for faster synchronization (optional)

### Installation

Install ArgoCD in your cluster:

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD using manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Verify installation
kubectl get pods -n argocd

# Access ArgoCD UI (port forward)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

---

## Detection

The System Control CLI automatically detects ArgoCD availability by:

1. Checking if ArgoCD CRDs (CustomResourceDefinitions) are installed in the cluster
2. Verifying ArgoCD API server is accessible and responding
3. Checking for proper RBAC permissions to list/get Application and AppProject resources

If ArgoCD is not detected, you will see a clear error message:

```text
Error: ArgoCD is not installed in this cluster
Install ArgoCD: https://argo-cd.readthedocs.io/en/stable/getting_started/
```

---

## Configuration

ArgoCD configuration is managed through the cluster itself. System Control CLI communicates with the ArgoCD API server
via Kubernetes API.

### Environment Variables

Configure ArgoCD behavior using environment variables:

```bash
# Set default namespace for ArgoCD operations
export ARGOCD_NAMESPACE=argocd

# Enable verbose API communication
export ARGOCD_DEBUG=true

# Set API timeout
export ARGOCD_TIMEOUT=30s
```

### Git Repository Configuration

Configure Git credentials in ArgoCD server:

```bash
# Add SSH repository (example)
kubectl -n argocd create secret generic git-ssh \
  --from-file=sshPrivateKeyPath=~/.ssh/id_rsa \
  --from-literal=url=git@github.com:company/manifests.git

# Add HTTPS repository with token
kubectl -n argocd create secret generic git-https \
  --from-literal=username=git \
  --from-literal=password=YOUR_GITHUB_TOKEN \
  --from-literal=url=https://github.com/company/manifests.git
```

---

## Command Reference

### `ops k8s argocd app list`

List all ArgoCD Applications.

```bash
ops k8s argocd app list [OPTIONS]
```

**Options:**

| Option        | Short | Type   | Default | Description                                            |
| ------------- | ----- | ------ | ------- | ------------------------------------------------------ |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace where ArgoCD is installed         |
| `--selector`  | `-l`  | string | -       | Label selector filter (e.g., 'environment=production') |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml                    |

**Examples:**

```bash
# List all applications
ops k8s argocd app list

# List applications in specific namespace
ops k8s argocd app list -n argocd

# Filter by label
ops k8s argocd app list -l environment=production

# Filter by multiple labels
ops k8s argocd app list -l "tier=frontend,environment=production"

# Output as JSON
ops k8s argocd app list --output json
```

**Example Output:**

```text
ArgoCD Applications

NAME            NAMESPACE    PROJECT     SYNC        HEALTH      REPOSITORY                               PATH
my-api          default      default     OutOfSync   Healthy     https://github.com/org/repo              k8s/api
my-frontend     default      default     Synced      Healthy     https://github.com/org/repo              k8s/frontend
my-database     production   prod-app    Synced      Progressing https://github.com/org/manifests         k8s/db
my-cache        production   prod-app    Synced      Healthy     https://github.com/org/manifests         k8s/cache
```

---

### `ops k8s argocd app get`

Get detailed information about a specific ArgoCD Application.

```bash
ops k8s argocd app get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option        | Short | Type   | Default | Description                                    |
| ------------- | ----- | ------ | ------- | ---------------------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace where ArgoCD is installed |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml            |

**Examples:**

```bash
# Get application details
ops k8s argocd app get my-api

# Get application in specific namespace
ops k8s argocd app get my-api -n argocd

# Output as JSON
ops k8s argocd app get my-api --output json

# Output as YAML
ops k8s argocd app get my-api --output yaml
```

**Example Output:**

```text
Application: my-api

Property              Value
────────────────────────────────────────────
Name                  my-api
Namespace             default
Project               default
Repository            https://github.com/org/repo
Path                  k8s/api
Target Revision       main
Sync Status           OutOfSync
Health Status         Healthy
Created Age           5 days

Sync Policy:
  Auto Sync: false
  Prune: false
  Self Heal: false

Source:
  Repo URL: https://github.com/org/repo
  Path: k8s/api
  Target Revision: main

Destination:
  Server: https://kubernetes.default.svc
  Namespace: default

Application Resources:
  - deployment: my-api
  - service: my-api
  - configmap: my-api-config
```

---

### `ops k8s argocd app create`

Create a new ArgoCD Application.

```bash
ops k8s argocd app create NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                        |
| -------- | -------- | -------------------------------------------------- |
| `NAME`   | Yes      | Application name (must be unique within namespace) |

**Options:**

| Option              | Short | Type   | Default                        | Description                         |
| ------------------- | ----- | ------ | ------------------------------ | ----------------------------------- |
| `--repo-url`        | -     | string | -                              | Git repository URL (required)       |
| `--path`            | -     | string | -                              | Path within repository (required)   |
| `--dest-server`     | -     | string | https://kubernetes.default.svc | Destination cluster API server URL  |
| `--namespace`       | `-n`  | string | argocd                         | ArgoCD namespace                    |
| `--project`         | -     | string | default                        | ArgoCD project name                 |
| `--target-revision` | -     | string | HEAD                           | Git branch/tag/commit to track      |
| `--dest-namespace`  | -     | string | default                        | Destination namespace in cluster    |
| `--auto-sync`       | -     | flag   | false                          | Enable automatic synchronization    |
| `--output`          | `-o`  | string | table                          | Output format: table, json, or yaml |

**Examples:**

```bash
# Create application from GitHub repository
ops k8s argocd app create my-app \
  --repo-url https://github.com/org/repo \
  --path k8s/overlays/prod

# Create with specific Git branch
ops k8s argocd app create my-app \
  --repo-url https://github.com/org/repo \
  --path charts/myapp \
  --target-revision main

# Create with auto-sync enabled
ops k8s argocd app create my-app \
  --repo-url https://github.com/org/repo \
  --path k8s/overlays/prod \
  --auto-sync

# Create in specific project and namespace
ops k8s argocd app create my-app \
  --repo-url https://github.com/org/repo \
  --path k8s/app \
  --project production \
  --dest-namespace prod-apps \
  -n argocd

# Create multi-cluster application
ops k8s argocd app create remote-app \
  --repo-url https://github.com/org/repo \
  --path k8s/app \
  --dest-server https://remote-cluster.example.com:6443
```

**Example Output:**

```text
Created Application: my-app

Property              Value
────────────────────────────────────────────
Name                  my-app
Namespace             argocd
Project               default
Repository            https://github.com/org/repo
Path                  k8s/overlays/prod
Target Revision       HEAD
Sync Status           Unknown
Health Status         Unknown
Created Age           0s

Application Resources:
  (Syncing in progress...)
```

---

### `ops k8s argocd app delete`

Delete an ArgoCD Application.

```bash
ops k8s argocd app delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false   | Skip confirmation prompt |

**Examples:**

```bash
# Delete application (with confirmation)
ops k8s argocd app delete my-app

# Delete without confirmation
ops k8s argocd app delete my-app --force

# Delete from specific namespace
ops k8s argocd app delete my-app -n argocd --force
```

**Example Output:**

```text
Deleted Application 'my-app'
```

---

### `ops k8s argocd app sync`

Synchronize an ArgoCD Application with its Git source.

```bash
ops k8s argocd app sync NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option        | Short | Type   | Default | Description                           |
| ------------- | ----- | ------ | ------- | ------------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace                  |
| `--revision`  | -     | string | -       | Sync to specific Git revision/branch  |
| `--prune`     | -     | flag   | false   | Prune resources no longer in Git      |
| `--dry-run`   | -     | flag   | false   | Preview sync without applying changes |

**Examples:**

```bash
# Synchronize with current revision
ops k8s argocd app sync my-app

# Sync to specific branch
ops k8s argocd app sync my-app --revision staging

# Sync with pruning
ops k8s argocd app sync my-app --prune

# Preview sync
ops k8s argocd app sync my-app --dry-run

# Sync with pruning (dry run)
ops k8s argocd app sync my-app --prune --dry-run

# Sync to specific commit
ops k8s argocd app sync my-app --revision abc1234def5678
```

**Example Output:**

```text
Sync: my-app

Property              Value
────────────────────────────────────────────
Application           my-app
Sync Status           Syncing
Revision              abc1234def5678
Resources Synced      3
Resources Pruned      0
Duration              2.5s

Synced Resources:
  ✓ deployment: my-app (configured)
  ✓ service: my-app (in sync)
  ✓ configmap: my-app-config (in sync)

Sync completed successfully!
```

---

### `ops k8s argocd app rollback`

Roll back an ArgoCD Application to a previous revision.

```bash
ops k8s argocd app rollback NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option          | Short | Type   | Default | Description                                                   |
| --------------- | ----- | ------ | ------- | ------------------------------------------------------------- |
| `--namespace`   | `-n`  | string | argocd  | Kubernetes namespace                                          |
| `--revision-id` | -     | int    | 0       | History revision ID (0 = previous, 1 = 1 revision back, etc.) |

**Examples:**

```bash
# Rollback to previous revision
ops k8s argocd app rollback my-app

# Rollback to specific history entry
ops k8s argocd app rollback my-app --revision-id 2

# Rollback in specific namespace
ops k8s argocd app rollback my-app -n argocd
```

**Example Output:**

```text
Rollback: my-app

Property              Value
────────────────────────────────────────────
Application           my-app
Previous Revision     abc1234def5678
Rolled Back To        def5678abc1234
Status                Syncing
Duration              1.8s

Rollback initiated. Syncing to previous state...
```

---

### `ops k8s argocd app health`

Check the health status of an ArgoCD Application.

```bash
ops k8s argocd app health NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option        | Short | Type   | Default | Description                         |
| ------------- | ----- | ------ | ------- | ----------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace                |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml |

**Examples:**

```bash
# Check health status
ops k8s argocd app health my-app

# Check in specific namespace
ops k8s argocd app health my-app -n argocd

# Output as JSON
ops k8s argocd app health my-app --output json
```

**Example Output:**

```text
Health: my-app

Status: Healthy

Resource Health Details:
  deployment/my-app: Healthy
    - Ready replicas: 3/3
    - Status condition: Deployment has minimum availability

  service/my-app: Healthy
    - Endpoints available: 3

Overall Application Health: Healthy
```

---

### `ops k8s argocd app diff`

Show differences between Git source and live cluster state.

```bash
ops k8s argocd app diff NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description      |
| -------- | -------- | ---------------- |
| `NAME`   | Yes      | Application name |

**Options:**

| Option        | Short | Type   | Default | Description                         |
| ------------- | ----- | ------ | ------- | ----------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace                |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml |

**Examples:**

```bash
# Show differences
ops k8s argocd app diff my-app

# Show in specific namespace
ops k8s argocd app diff my-app -n argocd

# Output as JSON
ops k8s argocd app diff my-app --output json
```

**Example Output:**

```text
Diff: my-app

Status: OutOfSync

Changes:
  deployment/my-app
    spec.template.spec.containers[0].image
    - myapp:v1.0.0
    + myapp:v1.1.0

  configmap/my-app-config
    data.VERSION
    - 1.0.0
    + 1.1.0

  configmap/my-app-config
    data.LOG_LEVEL
    - info
    + debug
```

---

### `ops k8s argocd project list`

List all ArgoCD Projects.

```bash
ops k8s argocd project list [OPTIONS]
```

**Options:**

| Option        | Short | Type   | Default | Description                                    |
| ------------- | ----- | ------ | ------- | ---------------------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace where ArgoCD is installed |
| `--selector`  | `-l`  | string | -       | Label selector filter                          |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml            |

**Examples:**

```bash
# List all projects
ops k8s argocd project list

# List in specific namespace
ops k8s argocd project list -n argocd

# Filter by label
ops k8s argocd project list -l team=backend

# Output as JSON
ops k8s argocd project list --output json
```

**Example Output:**

```text
ArgoCD Projects

NAME           NAMESPACE    DESCRIPTION                    SOURCE REPOS
default        argocd       Default ArgoCD project         (all)
prod-team      argocd       Production team project        https://github.com/org/prod-*
dev-team       argocd       Development team project       https://github.com/org/dev-*
platform       argocd       Platform infrastructure        https://github.com/org/platform-*
```

---

### `ops k8s argocd project get`

Get detailed information about an ArgoCD Project.

```bash
ops k8s argocd project get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description  |
| -------- | -------- | ------------ |
| `NAME`   | Yes      | Project name |

**Options:**

| Option        | Short | Type   | Default | Description                                    |
| ------------- | ----- | ------ | ------- | ---------------------------------------------- |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace where ArgoCD is installed |
| `--output`    | `-o`  | string | table   | Output format: table, json, or yaml            |

**Examples:**

```bash
# Get project details
ops k8s argocd project get prod-team

# Get in specific namespace
ops k8s argocd project get prod-team -n argocd

# Output as YAML
ops k8s argocd project get prod-team --output yaml
```

**Example Output:**

```text
Project: prod-team

Property              Value
────────────────────────────────────────────
Name                  prod-team
Namespace             argocd
Description           Production team project
Created Age           30 days

Source Repositories:
  - https://github.com/org/prod-manifests
  - https://github.com/org/prod-charts

Destination Clusters:
  - https://prod-cluster.example.com:6443

RBAC Roles:
  - team-lead (edit)
  - team-member (view)
```

---

### `ops k8s argocd project create`

Create a new ArgoCD Project.

```bash
ops k8s argocd project create NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description  |
| -------- | -------- | ------------ |
| `NAME`   | Yes      | Project name |

**Options:**

| Option          | Short | Type     | Default | Description                                           |
| --------------- | ----- | -------- | ------- | ----------------------------------------------------- |
| `--namespace`   | `-n`  | string   | argocd  | Kubernetes namespace                                  |
| `--description` | -     | string   | -       | Project description                                   |
| `--source-repo` | -     | string[] | -       | Allowed source repository URLs (can specify multiple) |
| `--output`      | `-o`  | string   | table   | Output format: table, json, or yaml                   |

**Examples:**

```bash
# Create project with single repository
ops k8s argocd project create prod-team \
  --description "Production team project" \
  --source-repo https://github.com/org/prod-manifests

# Create project with multiple repositories
ops k8s argocd project create backend-team \
  --description "Backend team project" \
  --source-repo https://github.com/org/backend-api \
  --source-repo https://github.com/org/backend-services

# Create in specific namespace
ops k8s argocd project create my-project \
  --description "My project" \
  --source-repo https://github.com/org/manifests \
  -n argocd
```

**Example Output:**

```text
Created Project: prod-team

Property              Value
────────────────────────────────────────────
Name                  prod-team
Namespace             argocd
Description           Production team project
Created Age           0s

Source Repositories:
  - https://github.com/org/prod-manifests

Destination Clusters:
  - https://kubernetes.default.svc
```

---

### `ops k8s argocd project delete`

Delete an ArgoCD Project.

```bash
ops k8s argocd project delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description  |
| -------- | -------- | ------------ |
| `NAME`   | Yes      | Project name |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | argocd  | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false   | Skip confirmation prompt |

**Examples:**

```bash
# Delete project (with confirmation)
ops k8s argocd project delete prod-team

# Delete without confirmation
ops k8s argocd project delete prod-team --force

# Delete from specific namespace
ops k8s argocd project delete prod-team -n argocd --force
```

**Example Output:**

```text
Deleted Project 'prod-team'
```

---

## Integration Examples

### Example 1: Create and Sync Application from Git

Set up a complete GitOps workflow with ArgoCD:

```bash
# Create project for backend team
ops k8s argocd project create backend-team \
  --description "Backend services" \
  --source-repo https://github.com/org/backend-manifests \
  --source-repo https://github.com/org/backend-charts

# Create application from Git repository
ops k8s argocd app create api-service \
  --repo-url https://github.com/org/backend-manifests \
  --path k8s/overlays/prod \
  --project backend-team \
  --target-revision main \
  --auto-sync

# Verify application is created
ops k8s argocd app get api-service

# Monitor synchronization
ops k8s argocd app health api-service

# Check differences
ops k8s argocd app diff api-service
```

### Example 2: Multi-environment Deployment

Deploy the same application across multiple environments:

```bash
# Create projects
ops k8s argocd project create dev-team \
  --description "Development team" \
  --source-repo https://github.com/org/manifests

ops k8s argocd project create prod-team \
  --description "Production team" \
  --source-repo https://github.com/org/manifests

# Deploy to development
ops k8s argocd app create my-app-dev \
  --repo-url https://github.com/org/manifests \
  --path k8s/overlays/dev \
  --project dev-team \
  --dest-namespace development

# Deploy to production
ops k8s argocd app create my-app-prod \
  --repo-url https://github.com/org/manifests \
  --path k8s/overlays/prod \
  --project prod-team \
  --dest-namespace production

# Sync both applications
ops k8s argocd app sync my-app-dev
ops k8s argocd app sync my-app-prod
```

### Example 3: Blue-Green Deployment with Rollback

Manage blue-green deployments with quick rollback:

```bash
# Create applications for blue and green
ops k8s argocd app create my-app-blue \
  --repo-url https://github.com/org/manifests \
  --path k8s/overlays/prod \
  --target-revision v1.0.0

ops k8s argocd app create my-app-green \
  --repo-url https://github.com/org/manifests \
  --path k8s/overlays/prod \
  --target-revision v1.1.0 \
  --auto-sync

# Monitor health
ops k8s argocd app health my-app-green

# Check differences
ops k8s argocd app diff my-app-green

# Switch traffic (external load balancer configuration)
# After verification, delete blue
ops k8s argocd app delete my-app-blue --force

# If needed, quickly rollback
ops k8s argocd app rollback my-app-green
```

### Example 4: Monitoring and Health Checks

Monitor applications and track synchronization status:

```bash
# List all applications and check sync status
ops k8s argocd app list

# Get detailed health information
ops k8s argocd app health my-app

# Check diff to see what's out of sync
ops k8s argocd app diff my-app

# Monitor health across all applications
for app in $(ops k8s argocd app list -o json | jq -r '.[] | .name'); do
  echo "=== $app ==="
  ops k8s argocd app health $app
done

# Check sync status continuously
watch -n 5 'ops k8s argocd app list'
```

### Example 5: GitOps Workflow with Updates

Complete GitOps workflow from Git to cluster:

```bash
# 1. Update manifests in Git
git clone https://github.com/org/manifests
cd manifests

# 2. Update version
cat > k8s/overlays/prod/kustomization.yaml << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

patchesStrategicMerge:
  - deployment-patch.yaml
EOF

cat > k8s/overlays/prod/deployment-patch.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:v1.1.0  # Updated version
EOF

# 3. Commit and push
git add k8s/overlays/prod/
git commit -m "Update app to v1.1.0"
git push origin main

# 4. Sync application
ops k8s argocd app sync my-app

# 5. Monitor
ops k8s argocd app health my-app
ops k8s argocd app diff my-app

# 6. If issues occur, rollback instantly
# ops k8s argocd app rollback my-app
```

---

## Troubleshooting

| Issue                                        | Solution                                                     |
| -------------------------------------------- | ------------------------------------------------------------ |
| **ArgoCD not installed**                     | Install ArgoCD: `kubectl apply -n argocd -f install.yaml`    |
| **Cannot connect to ArgoCD**                 | Check ArgoCD pod status: `kubectl get pods -n argocd`        |
| **Application creation fails**               | Verify Git repository is accessible. Check ArgoCD logs       |
| **Application stuck in OutOfSync**           | Check Git repo for changes. Sync: `ops k8s argocd app sync`  |
| **Permission denied errors**                 | Check RBAC in default project. Verify service account        |
| **Git repository not found**                 | Verify repository URL and credentials in ArgoCD              |
| **Health status stuck on Progressing**       | Check resource status: `kubectl get deployments,pods`        |
| **Synchronization timeout**                  | Increase timeout in ArgoCD settings. Check cluster resources |
| **Diff not showing changes**                 | Verify Git repository has latest changes. Refresh app        |
| **Cannot delete application with resources** | Enable cascading delete. Use `--force` flag                  |
| **Multi-cluster application fails**          | Verify destination cluster is registered in ArgoCD           |
| **Webhook not triggering syncs**             | Configure webhook in Git repository settings                 |
| **Project RBAC not working**                 | Verify RBAC role bindings. Check ArgoCD ConfigMap            |

---

## See Also

- [ArgoCD Official Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Quick Start](https://argo-cd.readthedocs.io/en/stable/getting_started/)
- [Kubernetes Plugin Index](../index.md)
- [Helm Ecosystem](./helm.md)
- [Kustomize Ecosystem](./kustomize.md)
- [Kubernetes Commands Reference](../commands/)
- [Kubernetes Integration Guide](../../integrations/kubernetes.md)
