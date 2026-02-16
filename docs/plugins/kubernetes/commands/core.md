# Kubernetes Plugin > Commands > Core

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Status Commands](#status-commands)
  - [ops k8s status](#ops-k8s-status)
  - [ops k8s contexts](#ops-k8s-contexts)
  - [ops k8s use-context](#ops-k8s-use-context)
  - [ops k8s cluster-info](#ops-k8s-cluster-info)
- [Node Commands](#node-commands)
  - [ops k8s nodes list](#ops-k8s-nodes-list)
  - [ops k8s nodes get](#ops-k8s-nodes-get)
- [Event Commands](#event-commands)
  - [ops k8s events list](#ops-k8s-events-list)
- [Namespace Commands](#namespace-commands)
  - [ops k8s namespaces list](#ops-k8s-namespaces-list)
  - [ops k8s namespaces get](#ops-k8s-namespaces-get)
  - [ops k8s namespaces create](#ops-k8s-namespaces-create)
  - [ops k8s namespaces delete](#ops-k8s-namespaces-delete)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Core Kubernetes commands manage cluster-level operations and resources. This includes cluster status, context switching,
node management, event monitoring, and namespace administration. These commands provide foundational access to your
Kubernetes infrastructure and are essential for daily cluster operations.

---

## Common Options

Common options are shared across all core Kubernetes commands:

| Option             | Short | Type    | Default        | Description                         |
| ------------------ | ----- | ------- | -------------- | ----------------------------------- |
| `--output`         | `-o`  | string  | `table`        | Output format: `table`, `json`, or  |
| `--namespace`      | `-n`  | string  | config default | Target Kubernetes                   |
| `--all-namespaces` | `-A`  | boolean | false          | List resources across all           |
| `--selector`       | `-l`  | string  | -              | Label selector for filtering (e.g., |
| `--field-selector` | -     | string  | -              | Field selector for filtering (e.g., |
| `--force`          | `-f`  | boolean | false          | Skip confirmation prompts (use with |

---

## Status Commands

Status commands provide information about cluster connectivity, context, and basic cluster details.

### `ops k8s status`

Display the current Kubernetes cluster status and connectivity information.

This command connects to your configured Kubernetes cluster and shows the active context, namespace, connection status,
cluster version, and node count. It helps verify that your cluster is accessible and configured correctly.

**Usage:**

```bash
ops k8s status
ops k8s status --output json
ops k8s status -o yaml
```

**Options:**

| Option     | Short | Type   | Default | Description                               |
| ---------- | ----- | ------ | ------- | ----------------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Property        ┃ Value           ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Context         │ production      │
│ Namespace       │ default         │
│ Connected       │ Yes             │
│ Cluster Version │ v1.27.4         │
│ Nodes           │ 3               │
└─────────────────┴─────────────────┘
```

**Example Output (JSON):**

```json
{
  "context": "production",
  "namespace": "default",
  "connected": "yes",
  "cluster_version": "v1.27.4",
  "nodes": 3
}
```

**Notes:**

- If the cluster is unreachable, the `connected` field shows `No` and additional details will be unavailable
- The cluster version requires active connectivity to retrieve
- Node count is only available when successfully connected

---

### `ops k8s contexts`

List all available Kubernetes contexts configured in your kubeconfig.

This command displays all contexts available in your kubeconfig file, shows which one is currently active (marked with
an asterisk), and displays the associated cluster and namespace for each context.

**Usage:**

```bash
ops k8s contexts
ops k8s contexts --output json
ops k8s contexts -o yaml
```

**Options:**

| Option     | Short | Type   | Default | Description                               |
| ---------- | ----- | ------ | ------- | ----------------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃   ┃ Name       ┃ Cluster        ┃ Namespace ┃
┡━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ * │ production │ prod-cluster   │ default   │
│   │ staging    │ staging-cl     │ default   │
│   │ minikube   │ minikube       │ default   │
│   │ dev-local  │ docker-desktop │ dev       │
└───┴────────────┴────────────────┴───────────┘
```

**Example Output (JSON):**

```json
{
  "contexts": [
    {
      "name": "production",
      "cluster": "prod-cluster",
      "namespace": "default",
      "active": true
    },
    {
      "name": "staging",
      "cluster": "staging-cl",
      "namespace": "default",
      "active": false
    },
    {
      "name": "minikube",
      "cluster": "minikube",
      "namespace": "default",
      "active": false
    }
  ]
}
```

**Notes:**

- The asterisk (\*) in the first column indicates the currently active context
- Each context contains configuration for a specific cluster and default namespace
- Context names must be unique within your kubeconfig file

---

### `ops k8s use-context`

Switch to a different Kubernetes context.

This command changes the active Kubernetes context, which affects which cluster subsequent commands operate against.
This is useful when managing multiple clusters.

**Usage:**

```bash
ops k8s use-context production
ops k8s use-context minikube
ops k8s use-context staging
```

**Arguments:**

| Argument       | Type   | Description                                 |
| -------------- | ------ | ------------------------------------------- |
| `context_name` | string | Name of the context to switch to (required) |

**Example Output:**

```text
Switched to context 'production'
```

**Errors:**

```text
Error: Context 'invalid-context' not found
```

**Notes:**

- The context name must exist in your kubeconfig file
- This change persists for the current shell session and affects all subsequent `ops k8s` commands
- To make permanent changes, update your kubeconfig file directly
- You can verify the active context with `ops k8s contexts`

---

### `ops k8s cluster-info`

Show detailed cluster information including API server, DNS, and other cluster services.

This command retrieves and displays cluster-level information from the Kubernetes API server, including details about
cluster services and their endpoints.

**Usage:**

```bash
ops k8s cluster-info
ops k8s cluster-info --output json
ops k8s cluster-info -o yaml
```

**Options:**

| Option     | Short | Type   | Default | Description                               |
| ---------- | ----- | ------ | ------- | ----------------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property       ┃ Value                  ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ api_server     │ https://10.0.0.1:6443  │
│ version        │ v1.27.4                │
│ platform       │ linux/amd64            │
│ git_version    │ v1.27.4                │
│ git_commit     │ 5abcdef123456          │
│ build_date     │ 2023-08-15T12:00:00Z   │
└────────────────┴────────────────────────┘
```

**Example Output (JSON):**

```json
{
  "api_server": "https://10.0.0.1:6443",
  "version": "v1.27.4",
  "platform": "linux/amd64",
  "git_version": "v1.27.4",
  "git_commit": "5abcdef123456",
  "build_date": "2023-08-15T12:00:00Z"
}
```

**Notes:**

- Requires cluster connectivity to retrieve detailed information
- The API server endpoint shows the Kubernetes master endpoint
- Version information helps verify cluster compatibility with your workloads

---

## Node Commands

Node commands manage and monitor the physical or virtual machines that make up your Kubernetes cluster.

### `ops k8s nodes list`

List all nodes in the cluster with their status, roles, and resource information.

This command displays an overview of all nodes in your Kubernetes cluster, showing their status, assigned roles,
Kubernetes version, internal IP, operating system, and uptime.

**Usage:**

```bash
ops k8s nodes list
ops k8s nodes list -l node-role.kubernetes.io/control-plane=
ops k8s nodes list --selector disktype=ssd
ops k8s nodes list --output json
```

**Options:**

| Option       | Short | Type   | Default | Description                                           |
| ------------ | ----- | ------ | ------- | ----------------------------------------------------- |
| `--selector` | `-l`  | string | -       | Label selector to filter nodes (e.g., `disktype=ssd`) |
| `--output`   | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml`             |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name       ┃ Status ┃ Roles        ┃ Version   ┃ Internal-IP ┃ Age      ┃
┡━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ control-1  │ Ready │ control-plane │ v1.27.4  │ 10.0.0.10   │ 365d     │
│ worker-1   │ Ready │ <none>        │ v1.27.4  │ 10.0.0.11   │ 90d      │
│ worker-2   │ Ready │ <none>        │ v1.27.4  │ 10.0.0.12   │ 45d      │
└────────────┴───────┴──────────────┴──────────┴─────────────┴──────────┘
```

**Example Output (JSON):**

```json
{
  "nodes": [
    {
      "name": "control-1",
      "status": "Ready",
      "roles": "control-plane",
      "version": "v1.27.4",
      "internal_ip": "10.0.0.10",
      "age": "365d"
    },
    {
      "name": "worker-1",
      "status": "Ready",
      "roles": "",
      "version": "v1.27.4",
      "internal_ip": "10.0.0.11",
      "age": "90d"
    }
  ]
}
```

**Label Selector Examples:**

```bash
# List control plane nodes
ops k8s nodes list -l node-role.kubernetes.io/control-plane=

# List nodes with a specific disk type
ops k8s nodes list -l disktype=ssd

# List nodes by multiple labels
ops k8s nodes list -l disktype=ssd,zone=us-west-2a
```

**Notes:**

- Status "Ready" indicates the node is healthy and can accept workloads
- NotReady status means the node is unavailable for scheduling
- The roles column shows node responsibilities (e.g., control-plane, worker)
- Age shows how long the node has been part of the cluster

---

### `ops k8s nodes get`

Get detailed information about a specific node.

This command displays comprehensive information about a single node, including capacity, allocatable resources,
conditions, and metadata.

**Usage:**

```bash
ops k8s nodes get control-1
ops k8s nodes get worker-1 --output json
ops k8s nodes get worker-2 -o yaml
```

**Arguments:**

| Argument | Type   | Description                 |
| -------- | ------ | --------------------------- |
| `name`   | string | Name of the node (required) |

**Options:**

| Option     | Short | Type   | Default | Description                               |
| ---------- | ----- | ------ | ------- | ----------------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property           ┃ Value                    ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Name               │ worker-1                 │
│ Status             │ Ready                    │
│ Roles              │ <none>                   │
│ Version            │ v1.27.4                  │
│ Internal-IP        │ 10.0.0.11                │
│ Hostname           │ ip-10-0-0-11.ec2.internal │
│ OS Image           │ Ubuntu 20.04.6 LTS       │
│ Kernel Version     │ 5.15.0-1050-aws          │
│ Capacity CPU       │ 4                        │
│ Capacity Memory    │ 16Gi                     │
│ Allocatable CPU    │ 3900m                    │
│ Allocatable Memory │ 15500Mi                  │
│ Age                │ 90d                      │
└────────────────────┴──────────────────────────┘
```

**Example Output (YAML):**

```yaml
node:
  name: worker-1
  status: Ready
  roles: []
  version: v1.27.4
  internal_ip: 10.0.0.11
  hostname: ip-10-0-0-11.ec2.internal
  os_image: Ubuntu 20.04.6 LTS
  kernel_version: 5.15.0-1050-aws
  capacity:
    cpu: "4"
    memory: 16Gi
  allocatable:
    cpu: 3900m
    memory: 15500Mi
  age: 90d
```

**Notes:**

- Capacity shows total node resources
- Allocatable shows resources available for pod scheduling (reduced by system reserved)
- Use this command to understand node specifications before deploying resource-intensive workloads
- Check node conditions to identify issues (e.g., DiskPressure, MemoryPressure)

---

## Event Commands

Event commands display cluster events, which record what is happening in the cluster such as pod creation, errors, and
scaling events.

### `ops k8s events list`

List Kubernetes events across the cluster or specific namespaces.

This command shows cluster events sorted by timestamp, which are useful for troubleshooting issues, understanding pod
failures, and monitoring cluster activity.

**Usage:**

```bash
ops k8s events list
ops k8s events list -n default
ops k8s events list --all-namespaces
ops k8s events list -A
ops k8s events list --involved-object my-pod
ops k8s events list --field-selector type=Warning
ops k8s events list --output json
```

**Options:**

| Option              | Short | Type    | Default        | Description                            |
| ------------------- | ----- | ------- | -------------- | -------------------------------------- |
| `--namespace`       | `-n`  | string  | config default | Target namespace (if not using         |
| `--all-namespaces`  | `-A`  | boolean | false          | List events across all                 |
| `--field-selector`  | -     | string  | -              | Filter by field (e.g., `type=Warning`, |
| `--involved-object` | -     | string  | -              | Filter by resource name (e.g., pod     |
| `--output`          | `-o`  | string  | `table`        | Output format: `table`, `json`, or     |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━┓
┃ Last Seen       ┃ Type ┃ Reason        ┃ Source ┃ Message               ┃ Cnt ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━┩
│ 1s             │ Normal │ Pulled       │ kubelet │ Successfully pulled  │ 1   │
│                │       │              │        │ image nginx:latest   │     │
│ 2s             │ Normal │ Created      │ kubelet │ Created container    │ 1   │
│                │       │              │        │ web                  │     │
│ 5s             │ Normal │ Started      │ kubelet │ Started container    │ 1   │
│                │       │              │        │ web                  │     │
│ 1h             │ Warning │ BackOff     │ kubelet │ Back-off restarting  │ 12  │
│                │        │              │        │ failed container     │     │
└─────────────────┴────────┴──────────────┴────────┴───────────────────────┴─────┘
```

**Example Output (JSON):**

```json
{
  "events": [
    {
      "last_timestamp": "2024-02-16T10:30:45Z",
      "type": "Normal",
      "reason": "Pulled",
      "source_component": "kubelet",
      "message": "Successfully pulled image nginx:latest",
      "count": 1
    },
    {
      "last_timestamp": "2024-02-16T10:30:42Z",
      "type": "Warning",
      "reason": "BackOff",
      "source_component": "kubelet",
      "message": "Back-off restarting failed container",
      "count": 12
    }
  ]
}
```

**Field Selector Examples:**

```bash
# List only warning events
ops k8s events list --field-selector type=Warning

# List events for a specific pod
ops k8s events list --involved-object my-pod

# List warning events in specific namespace
ops k8s events list -n production --field-selector type=Warning

# List events across all namespaces
ops k8s events list --all-namespaces
```

**Notes:**

- Events have a retention policy and older events are automatically purged
- High count values indicate repeated occurrences of the same event
- Warning and Error type events often indicate problems that need attention
- Events are invaluable for troubleshooting pod crashes and deployment issues

---

## Namespace Commands

Namespace commands manage Kubernetes namespaces, which provide isolation for resources within a cluster.

### `ops k8s namespaces list`

List all namespaces in the cluster with their status.

This command displays all namespaces available in the cluster, showing their status and how long they have existed.

**Usage:**

```bash
ops k8s namespaces list
ops k8s namespaces list -l env=production
ops k8s namespaces list --output json
```

**Options:**

| Option       | Short | Type   | Default | Description                               |
| ------------ | ----- | ------ | ------- | ----------------------------------------- |
| `--selector` | `-l`  | string | -       | Label selector to filter namespaces       |
| `--output`   | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┓
┃ Name          ┃ Status ┃ Age  ┃
┡━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━┩
│ default       │ Active │ 1y   │
│ kube-system   │ Active │ 1y   │
│ kube-public   │ Active │ 1y   │
│ kube-node-lease │ Active │ 1y │
│ production    │ Active │ 90d  │
│ staging       │ Active │ 60d  │
│ dev           │ Active │ 30d  │
└───────────────┴────────┴──────┘
```

**Example Output (JSON):**

```json
{
  "namespaces": [
    {
      "name": "default",
      "status": "Active",
      "age": "1y"
    },
    {
      "name": "production",
      "status": "Active",
      "age": "90d"
    }
  ]
}
```

**Notes:**

- System namespaces (kube-system, kube-public, kube-node-lease) are created automatically
- Active status indicates the namespace is functioning normally
- Terminating status indicates the namespace is being deleted
- Most custom resources should be created in non-system namespaces

---

### `ops k8s namespaces get`

Get detailed information about a specific namespace.

This command displays comprehensive information about a namespace including its status, labels, and metadata.

**Usage:**

```bash
ops k8s namespaces get default
ops k8s namespaces get production
ops k8s namespaces get staging --output json
```

**Arguments:**

| Argument | Type   | Description                      |
| -------- | ------ | -------------------------------- |
| `name`   | string | Name of the namespace (required) |

**Options:**

| Option     | Short | Type   | Default | Description                               |
| ---------- | ----- | ------ | ------- | ----------------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value            ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Name         │ production       │
│ Status       │ Active           │
│ Age          │ 90d              │
│ Labels       │ env: production  │
│              │ team: platform   │
└──────────────┴──────────────────┘
```

**Example Output (YAML):**

```yaml
namespace:
  name: production
  status: Active
  age: 90d
  labels:
    env: production
    team: platform
  annotations:
    description: "Production environment namespace"
```

**Notes:**

- Labels on namespaces can be used for organization and selection
- Use get to verify namespace configuration before deploying workloads
- Check annotations for namespace-specific documentation

---

### `ops k8s namespaces create`

Create a new namespace.

This command creates a new namespace in the cluster, optionally with labels for organization and identification.

**Usage:**

```bash
ops k8s namespaces create my-namespace
ops k8s namespaces create production --label env=production
ops k8s namespaces create staging --label env=staging --label team=backend
ops k8s namespaces create test -l env=test -o json
```

**Arguments:**

| Argument | Type   | Description                           |
| -------- | ------ | ------------------------------------- |
| `name`   | string | Name for the new namespace (required) |

**Options:**

| Option     | Short | Type        | Default | Description                               |
| ---------- | ----- | ----------- | ------- | ----------------------------------------- |
| `--label`  | `-l`  | string list | -       | Labels in key=value format (repeatable)   |
| `--output` | `-o`  | string      | `table` | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value            ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Name         │ production       │
│ Status       │ Active           │
│ Age          │ 0s               │
│ Labels       │ env: production  │
└──────────────┴──────────────────┘
```

**Example Output (JSON):**

```json
{
  "namespace": {
    "name": "production",
    "status": "Active",
    "age": "0s",
    "labels": {
      "env": "production"
    }
  }
}
```

**Label Examples:**

```bash
# Create namespace with single label
ops k8s namespaces create apps -l env=production

# Create namespace with multiple labels
ops k8s namespaces create db-systems -l env=production -l tier=data

# Create namespace with descriptive labels
ops k8s namespaces create ml-platform -l team=ml -l env=prod -l cost-center=engineering
```

**Naming Guidelines:**

- Use lowercase letters, numbers, and hyphens only
- Must start with a letter and end with alphanumeric
- Maximum 63 characters
- Examples: `production`, `staging`, `app-v2`, `team-data`

**Notes:**

- Labels should follow organizational naming conventions
- Consider using labels like `env`, `team`, `cost-center` for resource organization
- Namespace names are cluster-wide unique
- After creation, you can deploy resources to the namespace

---

### `ops k8s namespaces delete`

Delete a namespace and all resources within it.

This command deletes a namespace and all resources it contains. This is a destructive operation that requires
confirmation unless the `--force` flag is used.

**Usage:**

```bash
ops k8s namespaces delete my-namespace
ops k8s namespaces delete staging --force
ops k8s namespaces delete test-ns -f
```

**Arguments:**

| Argument | Type   | Description                                |
| -------- | ------ | ------------------------------------------ |
| `name`   | string | Name of the namespace to delete (required) |

**Options:**

| Option    | Short | Type    | Default | Description              |
| --------- | ----- | ------- | ------- | ------------------------ |
| `--force` | `-f`  | boolean | false   | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete namespace 'staging'? [y/N]: y
Namespace 'staging' deleted
```

**Example Output (With --force):**

```text
Namespace 'staging' deleted
```

**Warnings:**

- This operation is permanent and cannot be undone
- All resources in the namespace (pods, deployments, services, etc.) will be deleted
- Persistent volumes may or may not be retained depending on reclaim policy
- Database data will be lost if not backed up

**Safe Deletion Steps:**

```bash
# List all resources in the namespace first
ops k8s pods list -n staging
ops k8s deployments list -n staging

# Verify you're deleting the right namespace
ops k8s namespaces get staging

# Delete the namespace
ops k8s namespaces delete staging
```

**Notes:**

- The deletion process is asynchronous and may take a few moments
- If the namespace doesn't exist, you'll get an error
- Cannot delete system namespaces like `default`, `kube-system`, etc.
- Always backup critical data before deleting a namespace

---

## Troubleshooting

| Issue                                     | Cause                        | Solution                              |
| ----------------------------------------- | ---------------------------- | ------------------------------------- |
| Connection refused                        | Cluster unreachable          | Verify kubeconfig path with `ops      |
| Context not found                         | Invalid context name         | Run `ops k8s context                  |
| Authentication failed                     | Insufficient permissions     | Check kubeconfig                      |
| Node not found                            | Node doesn't exist           | Run `ops k8s nodes                    |
| Namespace already exists                  | Creating duplicate namespace | Use `ops k8s namespa                  |
| Permission denied on namespace operations | Missing RBAC permissions     | Contact cluster                       |
| Event list is empty                       | Retention period expired     | Events are automatically purged after |
| Command timeout                           | Cluster responding slowly    | Increase timeout with environment     |

---

## See Also

- [Workloads Commands](./workloads.md) - Manage pods, deployments, and other workload resources
- [Networking Commands](./networking.md) - Manage services, ingresses, and network policies
- [Kubernetes Plugin Index](../index.md) - Complete Kubernetes plugin documentation
- [Examples](../examples.md) - Practical examples and use cases
- [TUI Overview](../tui.md) - Terminal UI for cluster exploration
