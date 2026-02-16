# Kubernetes Plugin

Comprehensive integration with Kubernetes clusters for cluster management, workload orchestration,
networking, configuration, storage, RBAC, and advanced ecosystem tool management.

[Commands](commands/) | [Ecosystem Tools](ecosystem/) | [TUI Guide](tui.md) | [Examples](examples.md) |
[Troubleshooting](troubleshooting.md)

## Table of Contents

- [Overview](#overview)
  - [Key Features](#key-features)
  - [Supported Kubernetes Versions](#supported-kubernetes-versions)
- [Architecture](#architecture)
- [Kubernetes Concepts](#kubernetes-concepts)
  - [Pods](#pods)
  - [Deployments](#deployments)
  - [Services](#services)
  - [ConfigMaps and Secrets](#configmaps-and-secrets)
  - [Namespaces](#namespaces)
  - [RBAC](#rbac)
- [Installation & Configuration](#installation--configuration)
  - [Enabling the Plugin](#enabling-the-plugin)
  - [Configuration Schema](#configuration-schema)
  - [Authentication Methods](#authentication-methods)
  - [Environment Variable Overrides](#environment-variable-overrides)
  - [Multi-Cluster Configuration](#multi-cluster-configuration)
- [Quick Command Reference](#quick-command-reference)
  - [Core Commands](#core-commands)
  - [Workload Commands](#workload-commands)
  - [Networking Commands](#networking-commands)
  - [Configuration & Storage Commands](#configuration--storage-commands)
  - [RBAC Commands](#rbac-commands)
  - [Job Commands](#job-commands)
  - [Manifest Commands](#manifest-commands)
  - [Streaming Commands](#streaming-commands)
  - [Optimization Commands](#optimization-commands)
  - [Ecosystem Commands](#ecosystem-commands)
- [Documentation Map](#documentation-map)
- [See Also](#see-also)

---

## Overview

The Kubernetes plugin provides a comprehensive command-line interface for managing Kubernetes clusters,
from basic resource operations to advanced ecosystem integrations. Whether you're managing a single
cluster or orchestrating multi-cluster deployments, the plugin offers powerful, unified CLI access.

### Key Features

- **Cluster Management**: Switch contexts, view cluster status, manage multiple clusters
- **Workload Management**: Manage pods, deployments, statefulsets, daemonsets, replicasets
- **Networking**: Create and manage services, ingresses, network policies
- **Configuration & Storage**: Manage ConfigMaps, secrets, persistent volumes, storage classes
- **RBAC**: Create and manage roles, rolebindings, service accounts, cluster-level RBAC
- **Job Management**: Schedule and manage jobs, cronjobs, and job workflows
- **Manifest Operations**: Apply, validate, and diff Kubernetes manifests
- **Streaming Operations**: View logs, execute commands, port-forward to pods
- **Optimization**: Analyze resource usage and get optimization recommendations
- **Ecosystem Integration**: Helm, Kustomize, ArgoCD, Argo Rollouts, Argo Workflows, Flux CD, Kyverno, Cert-Manager,
  External Secrets, and more
- **Multi-Cluster Operations**: Deploy and manage resources across multiple clusters
- **Output Formats**: Table, JSON, and YAML output formats for all commands
- **Dry-Run Support**: Preview changes before applying them to your cluster

### Supported Kubernetes Versions

| Version   | Support Level                     |
| --------- | --------------------------------- |
| 1.28+     | Full support for all features     |
| 1.25-1.27 | Full support (legacy APIs)        |
| < 1.25    | Limited support (deprecated APIs) |

The plugin works with any Kubernetes distribution: AWS EKS, Google GKE, Azure AKS, DigitalOcean DOKS,
Minikube, Kind, on-premises, and more.

---

## Architecture

The Kubernetes plugin follows a layered architecture for clean separation of concerns:

```text
┌─────────────────────────────────────────────────────┐
│              User Interface (CLI)                    │
│         ops k8s <resource> <action>                 │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      Command Processing Layer                        │
│  • Typer CLI routing and argument parsing            │
│  • Validation and error handling                     │
│  • Output formatting (table, JSON, YAML)            │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      Service Layer (Business Logic)                  │
│  • WorkloadManager (pods, deployments, etc.)        │
│  • NetworkingManager (services, ingresses, etc.)    │
│  • ConfigurationManager (configmaps, secrets, etc.) │
│  • StorageManager (PVs, PVCs, storage classes)      │
│  • RBACManager (roles, bindings, accounts)          │
│  • JobManager (jobs, cronjobs)                      │
│  • ManifestManager (apply, diff, validate)          │
│  • StreamingManager (logs, exec, port-forward)      │
│  • OptimizationManager (analysis, recommendations)  │
│  • Ecosystem Managers (Helm, ArgoCD, Flux, etc.)    │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      Integration Layer                               │
│  • Kubernetes Python Client (official SDK)          │
│  • Subprocess calls for CLI tools (helm, kustomize) │
│  • External API clients (ArgoCD, Flux, etc.)        │
│  • File system operations (manifests, configs)      │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      Kubernetes Cluster (API Server)                 │
│  • etcd (data store)                                │
│  • Resource definitions and state                   │
└─────────────────────────────────────────────────────┘
```

---

## Kubernetes Concepts

Before using the Kubernetes plugin, understanding core concepts helps you use it effectively.

### Pods

A **Pod** is the smallest deployable unit in Kubernetes. It contains one or more containers
(usually one) that share storage, network, and specifications for how containers should run.

```text
Pod: my-app-abc123
  ├── Container: app
  │   ├── Image: my-app:1.0
  │   ├── Ports: 8080
  │   └── Resources: 256Mi RAM, 100m CPU
  ├── Volume: config
  │   └── ConfigMap: app-config
  └── Status: Running
```

Use `ops k8s pods list`, `ops k8s pods get <pod>`, and `ops k8s pods describe <pod>`
to view pod information.

### Deployments

A **Deployment** defines a desired state for managing replicated application pods.
Deployments handle scaling, rolling updates, and rollbacks automatically.

```text
Deployment: my-app
  ├── Replicas: 3 (desired) / 3 (current)
  ├── Strategy: RollingUpdate
  │   ├── MaxSurge: 25%
  │   └── MaxUnavailable: 25%
  ├── Template:
  │   ├── Image: my-app:1.0
  │   ├── Replicas: 3
  │   └── Selector: app=my-app
  └── Status: 3 pods running, 0 unavailable
```

Use `ops k8s deployments list`, `ops k8s deployments get <deployment>`, `ops k8s deployments scale`,
and `ops k8s deployments rollout` to manage deployments.

### Services

A **Service** exposes pods on a stable IP address and DNS name, providing load balancing
and service discovery to applications.

```text
Service: my-app-service
  ├── Type: ClusterIP
  ├── Cluster IP: 10.0.0.100
  ├── Port: 80
  ├── Target Port: 8080
  ├── Selector: app=my-app
  └── Endpoints: 3 pods
```

Service types:

- **ClusterIP**: Accessible only within the cluster
- **NodePort**: Accessible via a port on each node
- **LoadBalancer**: Exposed externally via cloud load balancer
- **ExternalName**: Maps to external DNS names

Use `ops k8s services list`, `ops k8s services get <service>`, and `ops k8s services create`
to manage services.

### ConfigMaps and Secrets

**ConfigMaps** store non-sensitive configuration data as key-value pairs.
**Secrets** store sensitive data like passwords, tokens, and certificates.

```text
ConfigMap: app-config
  ├── database_url: "postgres://db:5432"
  ├── log_level: "info"
  └── features: "feature_a=true,feature_b=false"

Secret: app-credentials
  ├── username: "admin" (base64-encoded)
  ├── password: "secret123" (base64-encoded)
  └── api_key: "sk-..." (base64-encoded)
```

Use `ops k8s configmaps` and `ops k8s secrets` commands for management.

### Namespaces

A **Namespace** is a logical cluster partition. Resources can be isolated by namespace
for multi-tenancy, organization, or environment separation.

```text
Namespace: production
  ├── Pods: 42
  ├── Services: 8
  ├── Deployments: 6
  └── Resource Quotas: 32 CPU, 64Gi RAM
```

Use `ops k8s namespaces` commands and the `--namespace` flag to manage namespace context.

### RBAC

**Role-Based Access Control (RBAC)** defines permissions for users and service accounts.
Resources include Roles (namespace-scoped) and ClusterRoles (cluster-scoped).

```text
Role: deployment-manager
  ├── Rules:
  │   ├── API Group: apps
  │   ├── Resources: deployments, replicasets
  │   └── Verbs: get, list, create, update, patch, delete

RoleBinding: deployment-manager-binding
  ├── Role: deployment-manager
  ├── Subject: ServiceAccount/deployer
  └── Namespace: production
```

Use `ops k8s roles`, `ops k8s rolebindings`, `ops k8s service-accounts` for RBAC management.

---

## Installation & Configuration

### Enabling the Plugin

Add `kubernetes` to your enabled plugins in `~/.config/ops/config.yaml`:

```yaml
plugins:
  enabled:
    - core
    - kubernetes
```

Or install with optional Kubernetes dependencies:

```bash
# Using pipx
pipx install system-operations-cli[kubernetes] --python python3.14

# Using uv
uv sync --all-extras
```

### Configuration Schema

The complete configuration schema for the Kubernetes plugin:

```yaml
plugins:
  kubernetes:
    # Cluster definitions
    clusters:
      dev:
        # Kubernetes context name
        context: "minikube"
        # Path to kubeconfig file (supports ~/ expansion)
        kubeconfig: "~/.kube/config"
        # Default namespace for this cluster
        namespace: "development"
        # Request timeout in seconds
        timeout: 300

      staging:
        context: "staging-cluster"
        kubeconfig: "~/.kube/staging.yaml"
        namespace: "staging"
        timeout: 300

      production:
        context: "prod-cluster"
        kubeconfig: "~/.kube/prod.yaml"
        namespace: "default"
        timeout: 600

    # Active cluster for commands (must match a key above)
    active_cluster: "dev"

    # Default settings applied to all requests
    defaults:
      # Default timeout for API requests (seconds)
      timeout: 300
      # Number of retry attempts on transient failures
      retry_attempts: 3
      # Dry-run strategy: none, client (local validation), server (server-side)
      dry_run_strategy: "none"

    # Authentication configuration
    auth:
      # Auth type: kubeconfig, token, service_account, certificate
      type: "kubeconfig"
      # Bearer token (for token auth type)
      token: null
      # Path to client certificate (for certificate auth)
      cert_path: null
      # Path to client key (for certificate auth)
      key_path: null
      # Path to CA certificate (for certificate auth)
      ca_path: null

    # Output formatting
    output_format: "table" # Options: table, json, yaml
```

### Authentication Methods

#### Kubeconfig Authentication (Default)

The default and most common authentication method using a kubeconfig file.

```yaml
plugins:
  kubernetes:
    auth:
      type: "kubeconfig"
    clusters:
      dev:
        kubeconfig: "~/.kube/config"
        context: "minikube"
```

Use when:

- You have a kubeconfig file with embedded credentials
- Using cloud provider CLI tools (aws, gcloud, az) that manage kubeconfig
- Testing or local development

**Setup:**

```bash
# Kubeconfig is typically created by your cloud provider or cluster admin
# AWS EKS
aws eks update-kubeconfig --name my-cluster --region us-east-1

# Google GKE
gcloud container clusters get-credentials my-cluster --zone us-central1-a

# Azure AKS
az aks get-credentials --resource-group my-group --name my-cluster

# Minikube
minikube update-context
```

#### Bearer Token Authentication

Using a bearer token for authentication (common with service accounts, automation).

```yaml
plugins:
  kubernetes:
    auth:
      type: "token"
      token: "${K8S_TOKEN}" # Load from environment variable
    clusters:
      production:
        context: "prod-cluster"
        kubeconfig: "~/.kube/config"
```

Use when:

- Authenticating as a service account
- Running in CI/CD pipelines
- Using bearer tokens from automation tools

**Setup:**

```bash
# Get a service account token
kubectl create serviceaccount automation-user
kubectl create rolebinding automation-admin --clusterrole=admin --serviceaccount=default:automation-user
TOKEN=$(kubectl get secret -n default $(kubectl get secret -n default | grep automation-user-token | awk '{print $1}') -o jsonpath='{.data.token}' | base64 -d)
export K8S_TOKEN=$TOKEN
```

#### Service Account Authentication

Using a mounted service account (primarily for pod-to-cluster communication).

```yaml
plugins:
  kubernetes:
    auth:
      type: "service_account"
      # Paths to the mounted service account (inside pod)
      token_path: "/var/run/secrets/kubernetes.io/serviceaccount/token"
      ca_path: "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
```

Use when:

- Running CLI commands from within a Kubernetes pod
- Using the plugin in workloads or CronJobs
- Native Kubernetes authentication without external credentials

#### Certificate-Based Authentication

Using client certificates for authentication (mTLS).

```yaml
plugins:
  kubernetes:
    auth:
      type: "certificate"
      cert_path: "/etc/kubernetes/pki/client.crt"
      key_path: "/etc/kubernetes/pki/client.key"
      ca_path: "/etc/kubernetes/pki/ca.crt" # Optional, for verifying server
    clusters:
      production:
        context: "prod-cluster"
        kubeconfig: null # Kubeconfig not needed with cert auth
```

Use when:

- Using certificate-based authentication with custom Kubernetes distributions
- Enterprise environments with mTLS enforcement
- Accessing clusters without kubeconfig files

**Setup:**

```bash
# Generate client certificate (example with OpenSSL)
openssl req -new -x509 -days 365 -keyout client.key -out client.crt \
  -subj "/CN=automation-user"

# Create the user in Kubernetes using kubectl on a privileged account
kubectl config set-credentials automation-user \
  --client-certificate=client.crt \
  --client-key=client.key
```

### Environment Variable Overrides

All configuration can be overridden with environment variables for flexibility:

| Variable                 | Description                 | Example           |
| ------------------------ | --------------------------- | ----------------- |
| `OPS_K8S_CONTEXT`        | Override Kubernetes context | `production`      |
| `OPS_K8S_NAMESPACE`      | Override default namespace  | `kube-system`     |
| `OPS_K8S_KUBECONFIG`     | Override kubeconfig path    | `/etc/k8s/config` |
| `OPS_K8S_TOKEN`          | Override bearer token       | `eyJhbGc...`      |
| `OPS_K8S_TIMEOUT`        | Override timeout in seconds | `600`             |
| `OPS_K8S_OUTPUT`         | Override output format      | `json`            |
| `OPS_K8S_DRY_RUN`        | Override dry-run strategy   | `server`          |
| `OPS_K8S_AUTH_TYPE`      | Override auth type          | `token`           |
| `OPS_K8S_RETRY_ATTEMPTS` | Override retry attempts     | `5`               |

**Example:** Override context for a single command:

```bash
OPS_K8S_CONTEXT=production ops k8s pods list
```

### Multi-Cluster Configuration

Configure and switch between multiple Kubernetes clusters:

```yaml
plugins:
  kubernetes:
    # Define three clusters
    clusters:
      dev:
        context: "minikube"
        kubeconfig: "~/.kube/dev.yaml"
        namespace: "development"
        timeout: 300

      staging:
        context: "staging-eks"
        kubeconfig: "~/.kube/staging.yaml"
        namespace: "staging"
        timeout: 300

      production:
        context: "prod-eks"
        kubeconfig: "~/.kube/production.yaml"
        namespace: "default"
        timeout: 600

    # Set the default cluster
    active_cluster: "dev"

    # Default options
    defaults:
      timeout: 300
      retry_attempts: 3
      dry_run_strategy: "none"

    # Authentication (shared across clusters)
    auth:
      type: "kubeconfig"
```

**Switching clusters:**

```bash
# View current active cluster
ops k8s status

# Switch to staging
ops k8s use-cluster staging
ops k8s status

# List all configured clusters
ops k8s clusters list

# Run command against specific cluster (overrides active)
OPS_K8S_CONTEXT=staging ops k8s pods list
```

---

## Quick Command Reference

All commands support `--output` flag for output formatting (table, json, yaml).
Many support `--namespace` to override the default namespace.

### Core Commands

| Command                      | Description                        | Detail Doc                                       |
| ---------------------------- | ---------------------------------- | ------------------------------------------------ |
| `ops k8s status`             | Show cluster connection status     | [commands/core.md](commands/core.md#status)      |
| `ops k8s contexts`           | List available Kubernetes contexts | [commands/core.md](commands/core.md#contexts)    |
| `ops k8s use-context <name>` | Switch to a Kubernetes context     | [commands/core.md](commands/core.md#use-context) |

### Workload Commands

| Command                                        | Description               | Detail Doc                            |
| ---------------------------------------------- | ------------------------- | ------------------------------------- |
| `ops k8s pods list`                            | List pods                 | [commands/workloads.md](comma         |
| `ops k8s pods get <name>`                      | Get pod details           | [commands/workloads.md](comma         |
| `ops k8s pods describe <name>`                 | Describe pod with details | [commands/workloads.md](comma         |
| `ops k8s pods delete <name>`                   | Delete pod                | [commands/workloads.md](comma         |
| `ops k8s deployments list`                     | List deployments          | [commands/workloads.md](commands/wor  |
| `ops k8s deployments get <name>`               | Get deployment details    | [commands/workloads.md](commands/wor  |
| `ops k8s deployments describe <name>`          | Describe deployment       | [commands/workloads.md](commands/wor  |
| `ops k8s deployments create`                   | Create deployment         | [commands/workloads.md](commands/wor  |
| `ops k8s deployments delete <name>`            | Delete deployment         | [commands/workloads.md](commands/wor  |
| `ops k8s deployments scale <name> <replicas>`  | Scale deployment          | [commands/workloads.md](commands/wor  |
| `ops k8s deployments rollout`                  | Rollout management        | [commands/workloads.md](commands/wor  |
| `ops k8s statefulsets list`                    | List statefulsets         | [commands/workloads.md](commands/work |
| `ops k8s statefulsets get <name>`              | Get statefulset details   | [commands/workloads.md](commands/work |
| `ops k8s statefulsets describe <name>`         | Describe statefulset      | [commands/workloads.md](commands/work |
| `ops k8s statefulsets create`                  | Create statefulset        | [commands/workloads.md](commands/work |
| `ops k8s statefulsets delete <name>`           | Delete statefulset        | [commands/workloads.md](commands/work |
| `ops k8s statefulsets scale <name> <replicas>` | Scale statefulset         | [commands/workloads.md](commands/work |
| `ops k8s daemonsets list`                      | List daemonsets           | [commands/workloads.md](commands/wo   |
| `ops k8s daemonsets get <name>`                | Get daemonset details     | [commands/workloads.md](commands/wo   |
| `ops k8s daemonsets describe <name>`           | Describe daemonset        | [commands/workloads.md](commands/wo   |
| `ops k8s daemonsets create`                    | Create daemonset          | [commands/workloads.md](commands/wo   |
| `ops k8s daemonsets delete <name>`             | Delete daemonset          | [commands/workloads.md](commands/wo   |
| `ops k8s replicasets list`                     | List replicasets          | [commands/workloads.md](commands/wor  |
| `ops k8s replicasets get <name>`               | Get replicaset details    | [commands/workloads.md](commands/wor  |
| `ops k8s replicasets describe <name>`          | Describe replicaset       | [commands/workloads.md](commands/wor  |
| `ops k8s replicasets delete <name>`            | Delete replicaset         | [commands/workloads.md](commands/wor  |

### Networking Commands

| Command                                    | Description                | Detail Doc                               |
| ------------------------------------------ | -------------------------- | ---------------------------------------- |
| `ops k8s services list`                    | List services              | [commands/networking.md](command         |
| `ops k8s services get <name>`              | Get service details        | [commands/networking.md](command         |
| `ops k8s services describe <name>`         | Describe service           | [commands/networking.md](command         |
| `ops k8s services create`                  | Create service             | [commands/networking.md](command         |
| `ops k8s services delete <name>`           | Delete service             | [commands/networking.md](command         |
| `ops k8s ingresses list`                   | List ingresses             | [commands/networking.md](commands        |
| `ops k8s ingresses get <name>`             | Get ingress details        | [commands/networking.md](commands        |
| `ops k8s ingresses describe <name>`        | Describe ingress           | [commands/networking.md](commands        |
| `ops k8s ingresses create`                 | Create ingress             | [commands/networking.md](commands        |
| `ops k8s ingresses delete <name>`          | Delete ingress             | [commands/networking.md](commands        |
| `ops k8s network-policies list`            | List network policies      | [commands/networking.md](commands/networ |
| `ops k8s network-policies get <name>`      | Get network policy details | [commands/networking.md](commands/networ |
| `ops k8s network-policies describe <name>` | Describe network policy    | [commands/networking.md](commands/networ |
| `ops k8s network-policies create`          | Create network policy      | [commands/networking.md](commands/networ |
| `ops k8s network-policies delete <name>`   | Delete network policy      | [commands/networking.md](commands/networ |

### Configuration & Storage Commands

| Command                                   | Description                   | Detail Doc                             |
| ----------------------------------------- | ----------------------------- | -------------------------------------- |
| `ops k8s configmaps list`                 | List ConfigMaps               | [commands/configuration-               |
| `ops k8s configmaps get <name>`           | Get ConfigMap details         | [commands/configuration-               |
| `ops k8s configmaps describe <name>`      | Describe ConfigMap            | [commands/configuration-               |
| `ops k8s configmaps create`               | Create ConfigMap              | [commands/configuration-               |
| `ops k8s configmaps delete <name>`        | Delete ConfigMap              | [commands/configuration-               |
| `ops k8s secrets list`                    | List Secrets                  | [commands/configurati                  |
| `ops k8s secrets get <name>`              | Get Secret details            | [commands/configurati                  |
| `ops k8s secrets describe <name>`         | Describe Secret               | [commands/configurati                  |
| `ops k8s secrets create`                  | Create Secret                 | [commands/configurati                  |
| `ops k8s secrets delete <name>`           | Delete Secret                 | [commands/configurati                  |
| `ops k8s pvs list`                        | List Persistent Volumes       | [commands/configuration-storage.       |
| `ops k8s pvs get <name>`                  | Get PV details                | [commands/configuration-storage.       |
| `ops k8s pvs describe <name>`             | Describe PV                   | [commands/configuration-storage.       |
| `ops k8s pvs delete <name>`               | Delete PV                     | [commands/configuration-storage.       |
| `ops k8s pvcs list`                       | List Persistent Volume Claims | [commands/configuration-storage.md](co |
| `ops k8s pvcs get <name>`                 | Get PVC details               | [commands/configuration-storage.md](co |
| `ops k8s pvcs describe <name>`            | Describe PVC                  | [commands/configuration-storage.md](co |
| `ops k8s pvcs create`                     | Create PVC                    | [commands/configuration-storage.md](co |
| `ops k8s pvcs delete <name>`              | Delete PVC                    | [commands/configuration-storage.md](co |
| `ops k8s storage-classes list`            | List Storage Classes          | [commands/configuration-stora          |
| `ops k8s storage-classes get <name>`      | Get Storage Class details     | [commands/configuration-stora          |
| `ops k8s storage-classes describe <name>` | Describe Storage Class        | [commands/configuration-stora          |

### RBAC Commands

| Command                                       | Description                      | Detail Doc                      |
| --------------------------------------------- | -------------------------------- | ------------------------------- |
| `ops k8s roles list`                          | List roles                       | [commands/rbac.md](c            |
| `ops k8s roles get <name>`                    | Get role details                 | [commands/rbac.md](c            |
| `ops k8s roles describe <name>`               | Describe role                    | [commands/rbac.md](c            |
| `ops k8s roles create`                        | Create role                      | [commands/rbac.md](c            |
| `ops k8s roles delete <name>`                 | Delete role                      | [commands/rbac.md](c            |
| `ops k8s rolebindings list`                   | List role bindings               | [commands/rbac.md](comma        |
| `ops k8s rolebindings get <name>`             | Get role binding details         | [commands/rbac.md](comma        |
| `ops k8s rolebindings describe <name>`        | Describe role binding            | [commands/rbac.md](comma        |
| `ops k8s rolebindings create`                 | Create role binding              | [commands/rbac.md](comma        |
| `ops k8s rolebindings delete <name>`          | Delete role binding              | [commands/rbac.md](comma        |
| `ops k8s service-accounts list`               | List service accounts            | [commands/rbac.md](commands/    |
| `ops k8s service-accounts get <name>`         | Get service account details      | [commands/rbac.md](commands/    |
| `ops k8s service-accounts describe <name>`    | Describe service account         | [commands/rbac.md](commands/    |
| `ops k8s service-accounts create`             | Create service account           | [commands/rbac.md](commands/    |
| `ops k8s service-accounts delete <name>`      | Delete service account           | [commands/rbac.md](commands/    |
| `ops k8s clusterroles list`                   | List cluster roles               | [commands/rbac.md](comma        |
| `ops k8s clusterroles get <name>`             | Get cluster role details         | [commands/rbac.md](comma        |
| `ops k8s clusterroles describe <name>`        | Describe cluster role            | [commands/rbac.md](comma        |
| `ops k8s clusterroles create`                 | Create cluster role              | [commands/rbac.md](comma        |
| `ops k8s clusterroles delete <name>`          | Delete cluster role              | [commands/rbac.md](comma        |
| `ops k8s clusterrolebindings list`            | List cluster role bindings       | [commands/rbac.md](commands/rba |
| `ops k8s clusterrolebindings get <name>`      | Get cluster role binding details | [commands/rbac.md](commands/rba |
| `ops k8s clusterrolebindings describe <name>` | Describe cluster role binding    | [commands/rbac.md](commands/rba |
| `ops k8s clusterrolebindings create`          | Create cluster role binding      | [commands/rbac.md](commands/rba |
| `ops k8s clusterrolebindings delete <name>`   | Delete cluster role binding      | [commands/rbac.md](commands/rba |

### Job Commands

| Command                            | Description         | Detail Doc                                    |
| ---------------------------------- | ------------------- | --------------------------------------------- |
| `ops k8s jobs list`                | List jobs           | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s jobs get <name>`          | Get job details     | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s jobs describe <name>`     | Describe job        | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s jobs create`              | Create job          | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s jobs delete <name>`       | Delete job          | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s jobs logs <name>`         | Get job logs        | [commands/jobs.md](commands/jobs.md#jobs)     |
| `ops k8s cronjobs list`            | List cronjobs       | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs get <name>`      | Get cronjob details | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs describe <name>` | Describe cronjob    | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs create`          | Create cronjob      | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs delete <name>`   | Delete cronjob      | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs suspend <name>`  | Suspend cronjob     | [commands/jobs.md](commands/jobs.md#cronjobs) |
| `ops k8s cronjobs resume <name>`   | Resume cronjob      | [commands/jobs.md](commands/jobs.md#cronjobs) |

### Manifest Commands

| Command                     | Description                   | Detail Doc                                     |
| --------------------------- | ----------------------------- | ---------------------------------------------- |
| `ops k8s manifest apply`    | Apply manifest to cluster     | [commands/manifests.md](commands/manifests.md) |
| `ops k8s manifest diff`     | Diff manifest against cluster | [commands/manifests.md](commands/manifests.md) |
| `ops k8s manifest validate` | Validate manifest syntax      | [commands/manifests.md](commands/manifests.md) |

### Streaming Commands

| Command                              | Description            | Detail Doc                                         |
| ------------------------------------ | ---------------------- | -------------------------------------------------- |
| `ops k8s logs <pod>`                 | Get pod logs           | [commands/streaming.md](commands/streaming         |
| `ops k8s exec <pod> <command>`       | Execute command in pod | [commands/streaming.md](commands/streaming         |
| `ops k8s port-forward <pod> <ports>` | Port-forward to pod    | [commands/streaming.md](commands/streaming.md#port |

### Optimization Commands

| Command                            | Description                      | Detail Doc                                 |
| ---------------------------------- | -------------------------------- | ------------------------------------------ |
| `ops k8s optimize analyze`         | Analyze resource usage           | [commands/optimization.md](commands/optimi |
| `ops k8s optimize recommendations` | Get optimization recommendations | [commands/optimization.md](commands/optimi |
| `ops k8s optimize apply`           | Apply recommendations            | [commands/optimization.md](commands/optimi |

### Ecosystem Commands

| Command                                  | Description                      | Detail Doc                           |
| ---------------------------------------- | -------------------------------- | ------------------------------------ |
| `ops k8s helm install`                   | Install Helm chart               | [ecosystem/helm.md](                 |
| `ops k8s helm upgrade`                   | Upgrade Helm release             | [ecosystem/helm.md](                 |
| `ops k8s helm uninstall`                 | Uninstall Helm release           | [ecosystem/helm.md](                 |
| `ops k8s helm list`                      | List Helm releases               | [ecosystem/helm.md](                 |
| `ops k8s kustomize build`                | Build Kustomize manifest         | [ecosystem/kustomize.m               |
| `ops k8s kustomize apply`                | Apply Kustomized manifest        | [ecosystem/kustomize.m               |
| `ops k8s kustomize diff`                 | Diff Kustomized manifest         | [ecosystem/kustomize.m               |
| `ops k8s argocd applications list`       | List ArgoCD applications         | [ecosystem/argocd.md                 |
| `ops k8s argocd applications get <name>` | Get ArgoCD application details   | [ecosystem/argocd.md                 |
| `ops k8s argocd applications create`     | Create ArgoCD application        | [ecosystem/argocd.md                 |
| `ops k8s argocd applications sync`       | Sync ArgoCD application          | [ecosystem/argocd.md                 |
| `ops k8s argocd projects list`           | List ArgoCD projects             | [ecosystem/argocd.md                 |
| `ops k8s rollouts list`                  | List Argo Rollouts               | [ecosystem/argo-rollouts.md](e       |
| `ops k8s rollouts promote <name>`        | Promote rollout to next step     | [ecosystem/argo-rollouts.md](e       |
| `ops k8s workflows list`                 | List Argo Workflows              | [ecosystem/argo-workflows.md](ec     |
| `ops k8s workflows create`               | Create Argo Workflow             | [ecosystem/argo-workflows.md](ec     |
| `ops k8s flux kustomizations list`       | List Flux Kustomizations         | [ecosystem/flux.md](                 |
| `ops k8s flux helm-releases list`        | List Flux HelmReleases           | [ecosystem/flux.md](                 |
| `ops k8s certs certificates list`        | List certificates (Cert-Manager) | [ecosystem/cert-manager.md](         |
| `ops k8s certs issuers list`             | List issuers (Cert-Manager)      | [ecosystem/cert-manager.md](         |
| `ops k8s external-secrets list`          | List External Secrets            | [ecosystem/external-secrets.md](ecos |
| `ops k8s policies list`                  | List Kyverno policies            | [ecosystem/kyverno.m                 |

---

## Documentation Map

Complete documentation files and their purposes:

### Core Commands Reference

- **[commands/core.md](commands/core.md)** - Status, contexts, and cluster switching
  - Detailed examples for `status`, `contexts`, and `use-context`
  - Connection troubleshooting
  - Output format examples

- **[commands/workloads.md](commands/workloads.md)** - Pod and workload management
  - Pods (list, get, describe, delete)
  - Deployments (CRUD, scaling, rollouts)
  - StatefulSets (list, get, describe, create, delete, scale)
  - DaemonSets (list, get, describe, create, delete)
  - ReplicaSets (list, get, describe, delete)
  - Examples and common patterns

- **[commands/networking.md](commands/networking.md)** - Network resource management
  - Services (CRUD)
  - Ingresses (CRUD)
  - Network Policies (CRUD)
  - Service discovery examples

- **[commands/configuration-storage.md](commands/configuration-storage.md)** - Configuration and storage resources
  - ConfigMaps (CRUD)
  - Secrets (CRUD)
  - Persistent Volumes (CRUD)
  - Persistent Volume Claims (CRUD)
  - Storage Classes

- **[commands/rbac.md](commands/rbac.md)** - Role-based access control
  - Roles and RoleBindings
  - ClusterRoles and ClusterRoleBindings
  - Service Accounts
  - Permission management

- **[commands/jobs.md](commands/jobs.md)** - Job and CronJob management
  - Jobs (CRUD)
  - CronJobs (CRUD, suspend, resume)
  - Monitoring job status
  - Debugging job failures

### Ecosystem Tools

- **[ecosystem/helm.md](ecosystem/helm.md)** - Helm package manager integration
  - Install, upgrade, uninstall releases
  - List and status commands
  - Chart management
  - Values file handling

- **[ecosystem/kustomize.md](ecosystem/kustomize.md)** - Kustomize template management
  - Build and apply overlays
  - Diff before applying
  - Patch management
  - Base and overlay examples

- **[ecosystem/argocd.md](ecosystem/argocd.md)** - ArgoCD GitOps integration
  - Application management
  - Project management
  - Sync operations
  - Health and status monitoring

- **[ecosystem/argo-rollouts.md](ecosystem/argo-rollouts.md)** - Argo Rollouts advanced deployment
  - Canary deployments
  - Blue-green deployments
  - Analysis and promotion
  - Rollback operations

- **[ecosystem/argo-workflows.md](ecosystem/argo-workflows.md)** - Argo Workflows engine integration
  - Workflow creation and execution
  - Template management
  - CronWorkflows
  - Artifact handling

- **[ecosystem/flux.md](ecosystem/flux.md)** - Flux CD GitOps operator
  - Kustomization management
  - HelmRelease management
  - Source reconciliation
  - Automated deployment

- **[ecosystem/cert-manager.md](ecosystem/cert-manager.md)** - Cert-Manager certificate automation
  - Certificate management
  - Issuer and ClusterIssuer management
  - Renewal operations
  - Status monitoring

- **[ecosystem/external-secrets.md](ecosystem/external-secrets.md)** - External Secrets Operator
  - Secret synchronization
  - SecretStore management
  - ClusterSecretStore management
  - Provider integration

- **[ecosystem/kyverno.md](ecosystem/kyverno.md)** - Kyverno policy engine
  - Policy management
  - ClusterPolicy management
  - Policy reports
  - Validation and mutation

### Guides and References

- **[tui.md](tui.md)** - Terminal User Interface guide
  - Interactive cluster browsing
  - Real-time resource monitoring
  - TUI navigation and shortcuts
  - Theme customization

- **[examples.md](examples.md)** - Common usage patterns and scenarios
  - Deploying a web application
  - Multi-cluster operations
  - Blue-green deployments
  - Canary rollouts
  - Certificate management
  - Secret rotation

- **[troubleshooting.md](troubleshooting.md)** - Problem diagnosis and solutions
  - Connection errors
  - Authentication failures
  - Permission issues (RBAC)
  - Resource limits and quotas
  - Performance optimization
  - Common error messages

---

## See Also

Related documentation:

- **[System Operations Manager Documentation](../../)** - Main documentation hub
- **[Plugin Development Guide](../development.md)** - Creating custom plugins
- **[Plugin Hot-Loading](../hot-loading.md)** - Dynamic plugin loading
- **[Configuration Management](../../configuration/)** - System-wide configuration
- **[Available Plugins](../available-plugins.md)** - Plugin directory
- **[Kong Gateway Plugin](../kong/)** - Similar comprehensive API gateway documentation
- **[Kubernetes Official Documentation](https://kubernetes.io/docs/)** - Official K8s docs
- **[Kubernetes API Reference](https://kubernetes.io/docs/reference/api-docs/)** - API resource definitions

**Important:** The `--dry-run` flag is available on most mutation commands (create, update, delete).
Use it to preview changes before applying them to your cluster.

**Note:** Most commands support filtering with `--namespace` (or `-n`), `--selector` (or `-l`),
and `--field-selector` options to narrow results and work with specific subsets of resources.
