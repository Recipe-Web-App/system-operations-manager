# Kubernetes Plugin > Commands > Workloads

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Pod Commands](#pod-commands)
  - [ops k8s pods list](#ops-k8s-pods-list)
  - [ops k8s pods get](#ops-k8s-pods-get)
  - [ops k8s pods delete](#ops-k8s-pods-delete)
  - [ops k8s pods logs](#ops-k8s-pods-logs)
- [Deployment Commands](#deployment-commands)
  - [ops k8s deployments list](#ops-k8s-deployments-list)
  - [ops k8s deployments get](#ops-k8s-deployments-get)
  - [ops k8s deployments create](#ops-k8s-deployments-create)
  - [ops k8s deployments update](#ops-k8s-deployments-update)
  - [ops k8s deployments delete](#ops-k8s-deployments-delete)
  - [ops k8s deployments scale](#ops-k8s-deployments-scale)
  - [ops k8s deployments restart](#ops-k8s-deployments-restart)
  - [ops k8s deployments rollout-status](#ops-k8s-deployments-rollout-status)
  - [ops k8s deployments rollback](#ops-k8s-deployments-rollback)
- [StatefulSet Commands](#statefulset-commands)
  - [ops k8s statefulsets list](#ops-k8s-statefulsets-list)
  - [ops k8s statefulsets get](#ops-k8s-statefulsets-get)
  - [ops k8s statefulsets create](#ops-k8s-statefulsets-create)
  - [ops k8s statefulsets update](#ops-k8s-statefulsets-update)
  - [ops k8s statefulsets delete](#ops-k8s-statefulsets-delete)
  - [ops k8s statefulsets scale](#ops-k8s-statefulsets-scale)
  - [ops k8s statefulsets restart](#ops-k8s-statefulsets-restart)
- [DaemonSet Commands](#daemonset-commands)
  - [ops k8s daemonsets list](#ops-k8s-daemonsets-list)
  - [ops k8s daemonsets get](#ops-k8s-daemonsets-get)
  - [ops k8s daemonsets create](#ops-k8s-daemonsets-create)
  - [ops k8s daemonsets update](#ops-k8s-daemonsets-update)
  - [ops k8s daemonsets delete](#ops-k8s-daemonsets-delete)
  - [ops k8s daemonsets restart](#ops-k8s-daemonsets-restart)
- [ReplicaSet Commands](#replicaset-commands)
  - [ops k8s replicasets list](#ops-k8s-replicasets-list)
  - [ops k8s replicasets get](#ops-k8s-replicasets-get)
  - [ops k8s replicasets delete](#ops-k8s-replicasets-delete)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Workload commands manage Kubernetes workload resources including Pods, Deployments, StatefulSets, DaemonSets, and
ReplicaSets. These commands provide complete lifecycle management for running applications in Kubernetes, including
creation, scaling, updating, and deletion of workloads.

---

## Common Options

Common options are shared across all workload commands:

| Option             | Short | Type    | Default        | Description                                                 |
| ------------------ | ----- | ------- | -------------- | ----------------------------------------------------------- |
| `--output`         | `-o`  | string  | `table`        | Output format: `table`, `json`, or `yaml`                   |
| `--namespace`      | `-n`  | string  | config default | Target Kubernetes namespace                                 |
| `--all-namespaces` | `-A`  | boolean | false          | List resources across all namespaces                        |
| `--selector`       | `-l`  | string  | -              | Label selector for filtering (e.g., `app=nginx`)            |
| `--field-selector` | -     | string  | -              | Field selector for filtering (e.g., `status.phase=Running`) |
| `--force`          | `-f`  | boolean | false          | Skip confirmation prompts                                   |

---

## Pod Commands

Pods are the smallest deployable units in Kubernetes. Typically you manage pods through higher-level workload resources
like Deployments, but you can manage individual pods directly.

### `ops k8s pods list`

List all pods in a namespace or across all namespaces.

This command displays pods with their status, ready containers, restart count, assigned node, and IP address. Use it to
get a quick overview of running workloads.

**Usage:**

```bash
ops k8s pods list
ops k8s pods list -n production
ops k8s pods list --all-namespaces
ops k8s pods list -A
ops k8s pods list -l app=nginx
ops k8s pods list --field-selector status.phase=Running
ops k8s pods list --output json
```

**Options:**

| Option             | Short | Type    | Default        | Description                               |
| ------------------ | ----- | ------- | -------------- | ----------------------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace                          |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces                |
| `--selector`       | `-l`  | string  | -              | Label selector to filter pods             |
| `--field-selector` | -     | string  | -              | Field selector to filter pods             |
| `--output`         | `-o`  | string  | `table`        | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name         ┃ Namespace ┃ Status           ┃ Ready ┃ Restarts ┃ Node     ┃ IP        ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ nginx-1a2b3c │ default   │ Running          │ 1/1   │ 0        │ worker-1 │ 10.1.1.10 │
│ nginx-4d5e6f │ default   │ Running          │ 1/1   │ 0        │ worker-2 │ 10.1.1.20 │
│ db-backup    │ default   │ Completed        │ 1/1   │ 0        │ worker-3 │ 10.1.1.30 │
│ app-crash    │ default   │ CrashLoopBackOff │ 0/1   │ 5        │ worker-1 │ 10.1.1.11 │
└──────────────┴───────────┴──────────────────┴───────┴──────────┴──────────┴───────────┘
```

**Pod Status Reference:**

| Status           | Meaning                                                 |
| ---------------- | ------------------------------------------------------- |
| Running          | Pod is active and running normally                      |
| Pending          | Pod is waiting to be scheduled or waiting for resources |
| Succeeded        | Pod completed successfully (for Jobs)                   |
| Failed           | Pod exited with error                                   |
| CrashLoopBackOff | Pod keeps crashing and restarting                       |
| ImagePullBackOff | Container image cannot be pulled                        |
| Terminating      | Pod is being deleted                                    |

**Filter Examples:**

```bash
# List running pods
ops k8s pods list --field-selector status.phase=Running

# List failed pods
ops k8s pods list --field-selector status.phase=Failed

# List pods by app label
ops k8s pods list -l app=nginx

# List pods by multiple labels
ops k8s pods list -l app=nginx,env=production
```

**Notes:**

- Ready shows current/desired container count (e.g., 1/1 means 1 container running out of 1 desired)
- Restarts shows how many times containers have restarted
- Use filtering to focus on specific pods
- Some fields may show as unknown if not available

---

### `ops k8s pods get`

Get detailed information about a specific pod.

This command displays comprehensive information about a pod including its specification, current state, resource
requests/limits, and lifecycle details.

**Usage:**

```bash
ops k8s pods get my-app
ops k8s pods get my-app -n production
ops k8s pods get my-pod --output json
ops k8s pods get my-pod -o yaml
```

**Arguments:**

| Argument | Type   | Description                |
| -------- | ------ | -------------------------- |
| `name`   | string | Name of the pod (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                               |
| ------------- | ----- | ------ | -------------- | ----------------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing the pod              |
| `--output`    | `-o`  | string | `table`        | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property       ┃ Value        ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Name           │ nginx-1a2b3c │
│ Namespace      │ default      │
│ Status         │ Running      │
│ IP             │ 10.1.1.10    │
│ Node           │ worker-1     │
│ Containers     │ 1            │
│ Ready Count    │ 1            │
│ Restarts       │ 0            │
│ Age            │ 5d           │
│ CPU Request    │ 100m         │
│ Memory Request │ 128Mi        │
│ CPU Limit      │ 500m         │
│ Memory Limit   │ 512Mi        │
└────────────────┴──────────────┘
```

**Example Output (YAML):**

```yaml
pod:
  name: nginx-1a2b3c
  namespace: default
  status: Running
  ip: 10.1.1.10
  node: worker-1
  containers:
    - name: nginx
      image: nginx:1.21
      ready: true
      restarts: 0
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  age: 5d
```

**Notes:**

- Use this to understand pod configuration and current state
- Check resource requests and limits to verify appropriate sizing
- Restart count indicates stability issues if high
- Node information helps identify scheduling distribution

---

### `ops k8s pods delete`

Delete a pod.

This command deletes a pod from the cluster. If the pod is managed by a Deployment or other controller, it will be
automatically recreated.

**Usage:**

```bash
ops k8s pods delete my-pod
ops k8s pods delete my-pod -n production
ops k8s pods delete failing-pod --force
```

**Arguments:**

| Argument | Type   | Description                          |
| -------- | ------ | ------------------------------------ |
| `name`   | string | Name of the pod to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                  |
| ------------- | ----- | ------- | -------------- | ---------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing the pod |
| `--force`     | `-f`  | boolean | false          | Skip confirmation prompt     |

**Example Output:**

```text
Are you sure you want to delete pod 'failing-pod' in namespace 'default'? [y/N]: y
Pod 'failing-pod' deleted successfully
```

**Notes:**

- Deleting a pod does not delete its logs
- If pod is part of a Deployment, a new pod will be created
- Use pod deletion to force restart managed pods
- Consider using Deployment restart instead for managed pods

---

### `ops k8s pods logs`

Get logs from a pod.

This command retrieves logs from one or more containers in a pod. Useful for troubleshooting and debugging pod issues.

**Usage:**

```bash
ops k8s pods logs my-app
ops k8s pods logs my-app -n production
ops k8s pods logs my-app --tail 100
ops k8s pods logs my-app -c main-container
ops k8s pods logs my-app --previous
ops k8s pods logs multi-container -c sidecar
```

**Arguments:**

| Argument | Type   | Description                |
| -------- | ------ | -------------------------- |
| `name`   | string | Name of the pod (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                                        |
| ------------- | ----- | ------- | -------------- | -------------------------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing the pod                       |
| `--container` | `-c`  | string  | -              | Container name (required for multi-container pods) |
| `--tail`      | -     | integer | all            | Number of log lines to show from end               |
| `--previous`  | `-p`  | boolean | false          | Show logs from previous container instance         |

**Example Output:**

```text
[2024-02-16T10:30:45] Starting nginx web server
[2024-02-16T10:30:46] Configuration loaded successfully
[2024-02-16T10:30:47] Listening on port 80
[2024-02-16T10:30:48] Worker process started
[2024-02-16T10:30:49] Ready to accept connections
```

**Tail Examples:**

```bash
# Get last 50 lines of logs
ops k8s pods logs my-app --tail 50

# Get all logs
ops k8s pods logs my-app

# Get last 10 lines
ops k8s pods logs my-app -tail 10
```

**Multi-Container Pod Logs:**

```bash
# List containers in pod first
ops k8s pods get my-pod

# Get logs from specific container
ops k8s pods logs my-pod -c main-container
ops k8s pods logs my-pod -c sidecar

# Get logs from previous instance (after crash)
ops k8s pods logs my-pod --previous
```

**Notes:**

- Logs are limited to recent data; older logs may be lost
- Use `--previous` to see logs from crashed containers
- For multi-container pods, you must specify the container name
- Logs are stored on the node where the pod runs

---

## Deployment Commands

Deployments are the recommended way to run stateless applications. They manage ReplicaSets and Pods automatically.

### `ops k8s deployments list`

List all deployments in a namespace.

This command shows deployments with their replica status, indicating how many pods are ready versus desired.

**Usage:**

```bash
ops k8s deployments list
ops k8s deployments list -n production
ops k8s deployments list --all-namespaces
ops k8s deployments list -l app=web
ops k8s deployments list --output json
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━┓
┃ Name       ┃ Namespace ┃ Ready ┃ Desired ┃ Up-to-date ┃ Available ┃ Age ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━┩
│ nginx      │ default   │ 3     │ 3       │ 3          │ 3         │ 30d │
│ app-api    │ default   │ 2     │ 3       │ 2          │ 2         │ 7d  │
│ worker-job │ default   │ 1     │ 1       │ 1          │ 1         │ 2d  │
└────────────┴───────────┴───────┴─────────┴────────────┴───────────┴─────┘
```

**Status Interpretation:**

| Scenario                    | Meaning                                      |
| --------------------------- | -------------------------------------------- |
| Ready = Desired = Available | Deployment is healthy and fully operational  |
| Ready < Desired             | Deployment is scaling up or has pod failures |
| Up-to-date < Desired        | Deployment is being updated with new version |
| All ready but Age is new    | Deployment just rolled out successfully      |

**Notes:**

- Ready shows pods that are passing readiness probes
- Available shows pods that can receive traffic
- Up-to-date shows pods with the latest configuration

---

### `ops k8s deployments get`

Get detailed information about a deployment.

This command displays the deployment specification, status, and recent events related to the deployment.

**Usage:**

```bash
ops k8s deployments get my-app
ops k8s deployments get web -n production
ops k8s deployments get api --output json
ops k8s deployments get worker -o yaml
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                     |
| ------------- | ----- | ------ | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing deployment |
| `--output`    | `-o`  | string | `table`        | Output format                   |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value                ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Name             │ nginx                │
│ Namespace        │ default              │
│ Desired Replicas │ 3                    │
│ Ready Replicas   │ 3                    │
│ Available        │ 3                    │
│ Image            │ nginx:1.21           │
│ Update Strategy  │ RollingUpdate        │
│ Age              │ 30d                  │
│ Status           │ Successfully Updated │
└──────────────────┴──────────────────────┘
```

**Example Output (YAML):**

```yaml
deployment:
  name: nginx
  namespace: default
  spec:
    replicas: 3
    image: nginx:1.21
    updateStrategy: RollingUpdate
  status:
    desiredReplicas: 3
    readyReplicas: 3
    availableReplicas: 3
    conditions:
      - type: Available
        status: "True"
  age: 30d
```

**Notes:**

- Compare Ready vs Desired replicas to check deployment health
- Image field shows container image being run
- Check conditions for any warnings or issues

---

### `ops k8s deployments create`

Create a new deployment.

This command creates a deployment with specified container image, replicas, and optional labels.

**Usage:**

```bash
ops k8s deployments create my-app --image nginx:1.21
ops k8s deployments create web --image nginx:1.21 --replicas 3
ops k8s deployments create api --image myapp:2.0 --replicas 2 --port 8080
ops k8s deployments create worker --image worker:latest -l app=worker -l env=prod
ops k8s deployments create api --image api:latest -n production --replicas 5
```

**Arguments:**

| Argument | Type   | Description                        |
| -------- | ------ | ---------------------------------- |
| `name`   | string | Name for the deployment (required) |

**Options:**

| Option        | Short | Type        | Default        | Description                             |
| ------------- | ----- | ----------- | -------------- | --------------------------------------- |
| `--image`     | `-i`  | string      | -              | Container image (required)              |
| `--namespace` | `-n`  | string      | config default | Target namespace                        |
| `--replicas`  | `-r`  | integer     | 1              | Number of pod replicas                  |
| `--port`      | `-p`  | integer     | -              | Container port to expose                |
| `--label`     | `-l`  | string list | -              | Labels in key=value format (repeatable) |
| `--output`    | `-o`  | string      | `table`        | Output format                           |

**Example Output:**

```text
Deployment 'nginx' created successfully

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Property         ┃ Value      ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Name             │ nginx      │
│ Namespace        │ default    │
│ Desired Replicas │ 3          │
│ Ready Replicas   │ 0          │
│ Image            │ nginx:1.21 │
│ Age              │ 0s         │
└──────────────────┴────────────┘
```

**Creation Examples:**

```bash
# Simple deployment with 1 replica
ops k8s deployments create simple-app --image nginx:latest

# Deployment with 3 replicas and port
ops k8s deployments create web-app --image nginx:1.21 --replicas 3 --port 80

# Deployment with labels for organization
ops k8s deployments create api-server --image myapi:2.0 --replicas 2 \
  -l app=api -l version=2.0 -l env=production

# Deployment in specific namespace
ops k8s deployments create db-sync --image dbtool:latest -n data-team --replicas 1
```

**Image Reference Format:**

```text
[registry/]image[:tag]

Examples:
- nginx:1.21                          # Docker Hub
- gcr.io/myproject/myapp:v1.0        # Google Container Registry
- myregistry.azurecr.io/app:latest   # Azure Container Registry
- private.registry.com/app:2024-01-15 # Private registry
```

**Notes:**

- Images are pulled from registries at pod startup
- Pods may stay in Pending while image is being pulled
- Use image tags (not latest) in production for reproducibility
- Labels help organize and select deployments

---

### `ops k8s deployments update`

Update an existing deployment.

This command updates the container image or replica count for a deployment, triggering a rolling update.

**Usage:**

```bash
ops k8s deployments update my-app --image nginx:1.22
ops k8s deployments update web --replicas 5
ops k8s deployments update api --image myapp:2.1 --replicas 3 -n production
ops k8s deployments update worker --image worker:v3 --replicas 2
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                     |
| ------------- | ----- | ------- | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing deployment |
| `--image`     | `-i`  | string  | -              | New container image             |
| `--replicas`  | `-r`  | integer | -              | New number of replicas          |
| `--output`    | `-o`  | string  | `table`        | Output format                   |

**Example Output:**

```text
Deployment 'nginx' updated successfully

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Name             │ nginx         │
│ Namespace        │ default       │
│ Desired Replicas │ 3             │
│ Ready Replicas   │ 2             │
│ Image            │ nginx:1.22    │
│ Status           │ RollingUpdate │
└──────────────────┴───────────────┘
```

**Update Examples:**

```bash
# Update just the image
ops k8s deployments update api --image myapi:2.1

# Update just the replica count
ops k8s deployments update web --replicas 5

# Update both image and replicas
ops k8s deployments update app --image app:v2.0 --replicas 4

# Update deployment in specific namespace
ops k8s deployments update service --image service:latest -n production
```

**Rolling Update Process:**

1. New pods with new image start
2. Once new pods are ready, old pods terminate
3. Process continues until all pods are updated
4. No downtime if replicas > 1

**Notes:**

- Updates trigger rolling deployments automatically
- Old pods are terminated as new pods become ready
- Check `rollout-status` to monitor update progress
- Rollback available if update causes problems

---

### `ops k8s deployments delete`

Delete a deployment and its pods.

This command deletes a deployment and all pods it manages.

**Usage:**

```bash
ops k8s deployments delete my-app
ops k8s deployments delete web -n production
ops k8s deployments delete worker --force
```

**Arguments:**

| Argument | Type   | Description                                 |
| -------- | ------ | ------------------------------------------- |
| `name`   | string | Name of the deployment to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                     |
| ------------- | ----- | ------- | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing deployment |
| `--force`     | `-f`  | boolean | false          | Skip confirmation               |

**Example Output:**

```text
Are you sure you want to delete deployment 'web' in namespace 'production'? [y/N]: y
Deployment 'web' deleted successfully
```

**Notes:**

- All pods managed by the deployment are terminated
- Persistent volumes are not deleted by default
- Cannot be undone; backup config before deletion

---

### `ops k8s deployments scale`

Scale a deployment to a different number of replicas.

This command changes the desired replica count without changing the container image.

**Usage:**

```bash
ops k8s deployments scale my-app --replicas 5
ops k8s deployments scale web -r 10
ops k8s deployments scale api --replicas 2 -n production
ops k8s deployments scale worker --replicas 0
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                           |
| ------------- | ----- | ------- | -------------- | ------------------------------------- |
| `--replicas`  | `-r`  | integer | -              | Desired number of replicas (required) |
| `--namespace` | `-n`  | string  | config default | Namespace containing deployment       |
| `--output`    | `-o`  | string  | `table`        | Output format                         |

**Example Output:**

```text
Deployment 'api' scaled to 5 replicas

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Property         ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Name             │ api       │
│ Desired Replicas │ 5         │
│ Ready Replicas   │ 3         │
│ Image            │ myapi:2.0 │
└──────────────────┴───────────┘
```

**Scaling Examples:**

```bash
# Scale up for high traffic
ops k8s deployments scale web --replicas 10

# Scale down during off-hours
ops k8s deployments scale api --replicas 2

# Scale to zero (pause deployment)
ops k8s deployments scale background-job --replicas 0

# Quickly scale during incident response
ops k8s deployments scale critical-app -r 20
```

**Notes:**

- Scaling is immediate; pods are created or terminated
- Setting replicas to 0 pauses the application
- Existing pods remain running until replica count decreases
- No image change occurs, only pod count changes

---

### `ops k8s deployments restart`

Restart a deployment by rolling restart.

This command restarts all pods in the deployment with the same image, useful for forcing config reloads or recovering
from transient issues.

**Usage:**

```bash
ops k8s deployments restart my-app
ops k8s deployments restart web -n production
ops k8s deployments restart api
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                     |
| ------------- | ----- | ------ | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing deployment |
| `--output`    | `-o`  | string | `table`        | Output format                   |

**Example Output:**

```text
Deployment 'web' restarted

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Name             │ web            │
│ Desired Replicas │ 3              │
│ Ready Replicas   │ 1              │
│ Status           │ RollingRestart │
└──────────────────┴────────────────┘
```

**Use Cases:**

```bash
# Force pod restart without image change
ops k8s deployments restart my-app

# Recover from temporary issues
ops k8s deployments restart flaky-service

# Apply configuration changes
ops k8s deployments restart app-with-configmap
```

**Notes:**

- Container image remains unchanged
- Old pods are gracefully terminated
- New pods are created with same configuration
- Useful for applying ConfigMap/Secret updates

---

### `ops k8s deployments rollout-status`

Check the rollout status of a deployment.

This command shows whether a deployment update is in progress and how many replicas are ready.

**Usage:**

```bash
ops k8s deployments rollout-status my-app
ops k8s deployments rollout-status web -n production
ops k8s deployments rollout-status api --output json
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                     |
| ------------- | ----- | ------ | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing deployment |
| `--output`    | `-o`  | string | `table`        | Output format                   |

**Example Output (In Progress):**

```text
Rollout Status: api

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property          ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Status            │ In Progress │
│ Desired Replicas  │ 3           │
│ Ready Replicas    │ 2           │
│ Updated Replicas  │ 3           │
│ Available         │ 2           │
│ Progress Deadline │ 10m         │
└───────────────────┴─────────────┘
```

**Example Output (Complete):**

```text
Rollout Status: api

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Property         ┃ Value      ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Status           │ Successful │
│ Desired Replicas │ 3          │
│ Ready Replicas   │ 3          │
│ Updated Replicas │ 3          │
│ Available        │ 3          │
└──────────────────┴────────────┘
```

**Notes:**

- Shows progress of ongoing rolling updates
- Useful for monitoring deployment changes
- Check status before and after updates

---

### `ops k8s deployments rollback`

Rollback a deployment to a previous revision.

This command reverts a deployment to a previous working version, useful if a bad update was deployed.

**Usage:**

```bash
ops k8s deployments rollback my-app
ops k8s deployments rollback web --revision 3
ops k8s deployments rollback api -n production
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the deployment (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                       |
| ------------- | ----- | ------- | -------------- | --------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing deployment   |
| `--revision`  | -     | integer | -              | Specific revision to roll back to |

**Example Output:**

```text
Deployment 'api' rolled back to previous revision
```

**Rollback Examples:**

```bash
# Rollback to previous revision (immediate)
ops k8s deployments rollback web

# Rollback to specific revision
ops k8s deployments rollback api --revision 5

# Rollback in specific namespace
ops k8s deployments rollback service -n production
```

**Notes:**

- Revisions are numbered starting from 0
- Rollback triggers a rolling update with the previous image
- Cannot rollback if no previous revision exists
- Review revision history before rolling back

---

## StatefulSet Commands

StatefulSets are used for stateful applications like databases that need stable identity and storage.

### `ops k8s statefulsets list`

List all StatefulSets in a namespace.

This command displays StatefulSets with replica status information.

**Usage:**

```bash
ops k8s statefulsets list
ops k8s statefulsets list -n data
ops k8s statefulsets list --all-namespaces
ops k8s statefulsets list -l app=database
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━┓
┃ Name     ┃ Namespace ┃ Ready ┃ Desired ┃ Service  ┃ Age ┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━┩
│ postgres │ data      │ 3     │ 3       │ postgres │ 60d │
│ redis    │ data      │ 2     │ 2       │ redis    │ 30d │
└──────────┴───────────┴───────┴─────────┴──────────┴─────┘
```

**Notes:**

- Service column shows the headless service controlling the StatefulSet
- Ready replicas should match desired replicas for healthy StatefulSet
- Useful for monitoring database clusters

---

### `ops k8s statefulsets get`

Get detailed information about a StatefulSet.

This command displays the StatefulSet specification and current status.

**Usage:**

```bash
ops k8s statefulsets get postgres
ops k8s statefulsets get postgres -n data
ops k8s statefulsets get postgres --output json
```

**Arguments:**

| Argument | Type   | Description                        |
| -------- | ------ | ---------------------------------- |
| `name`   | string | Name of the StatefulSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                      |
| ------------- | ----- | ------ | -------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing StatefulSet |
| `--output`    | `-o`  | string | `table`        | Output format                    |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property         ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name             │ postgres    │
│ Namespace        │ data        │
│ Service Name     │ postgres    │
│ Desired Replicas │ 3           │
│ Ready Replicas   │ 3           │
│ Image            │ postgres:13 │
│ Age              │ 60d         │
└──────────────────┴─────────────┘
```

**Notes:**

- Service name is the headless service for StatefulSet
- Replicas and image information help verify configuration

---

### `ops k8s statefulsets create`

Create a new StatefulSet.

This command creates a StatefulSet with a headless service for managing stateful workloads.

**Usage:**

```bash
ops k8s statefulsets create postgres --image postgres:13 --service-name postgres
ops k8s statefulsets create redis --image redis:7 --service-name redis --replicas 3
ops k8s statefulsets create my-db --image mysql:8 --service-name db --port 3306 -l env=prod
```

**Arguments:**

| Argument | Type   | Description                         |
| -------- | ------ | ----------------------------------- |
| `name`   | string | Name for the StatefulSet (required) |

**Options:**

| Option           | Short | Type        | Default        | Description                      |
| ---------------- | ----- | ----------- | -------------- | -------------------------------- |
| `--image`        | `-i`  | string      | -              | Container image (required)       |
| `--service-name` | -     | string      | -              | Headless service name (required) |
| `--namespace`    | `-n`  | string      | config default | Target namespace                 |
| `--replicas`     | `-r`  | integer     | 1              | Number of replicas               |
| `--port`         | `-p`  | integer     | -              | Container port to expose         |
| `--label`        | `-l`  | string list | -              | Labels in key=value format       |
| `--output`       | `-o`  | string      | `table`        | Output format                    |

**Example Output:**

```text
StatefulSet 'postgres' created successfully

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property         ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name             │ postgres    │
│ Service Name     │ postgres    │
│ Desired Replicas │ 3           │
│ Ready Replicas   │ 0           │
│ Image            │ postgres:13 │
└──────────────────┴─────────────┘
```

**Creation Examples:**

```bash
# Create PostgreSQL cluster
ops k8s statefulsets create postgres --image postgres:13 --service-name pg --replicas 3

# Create Redis cluster
ops k8s statefulsets create redis --image redis:7 --service-name redis --replicas 3 --port 6379

# Create MySQL with labels
ops k8s statefulsets create mysql --image mysql:8 --service-name mysql -l tier=database -l version=8
```

**Important Notes:**

- Service name must exist or be created separately
- StatefulSets require a headless service for network identity
- Pods get stable hostnames (e.g., postgres-0, postgres-1, postgres-2)
- Pod names are predictable and stable across restarts

---

### `ops k8s statefulsets update`

Update a StatefulSet's image or replica count.

This command updates StatefulSet configuration with rolling update semantics.

**Usage:**

```bash
ops k8s statefulsets update postgres --image postgres:14
ops k8s statefulsets update redis --replicas 5
ops k8s statefulsets update my-db --image mysql:8.1 -n data
```

**Arguments:**

| Argument | Type   | Description                        |
| -------- | ------ | ---------------------------------- |
| `name`   | string | Name of the StatefulSet (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                      |
| ------------- | ----- | ------- | -------------- | -------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing StatefulSet |
| `--image`     | `-i`  | string  | -              | New container image              |
| `--replicas`  | `-r`  | integer | -              | New number of replicas           |
| `--output`    | `-o`  | string  | `table`        | Output format                    |

**Example Output:**

```text
StatefulSet 'postgres' updated successfully

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property         ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name             │ postgres    │
│ Desired Replicas │ 3           │
│ Ready Replicas   │ 2           │
│ Image            │ postgres:14 │
└──────────────────┴─────────────┘
```

**Notes:**

- Updates trigger rolling restarts of pods
- Pods are updated in reverse order (newest first for rolling back capability)

---

### `ops k8s statefulsets delete`

Delete a StatefulSet.

This command deletes the StatefulSet and its managed pods.

**Usage:**

```bash
ops k8s statefulsets delete postgres
ops k8s statefulsets delete redis -n data
ops k8s statefulsets delete my-db --force
```

**Arguments:**

| Argument | Type   | Description                                  |
| -------- | ------ | -------------------------------------------- |
| `name`   | string | Name of the StatefulSet to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                      |
| ------------- | ----- | ------- | -------------- | -------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing StatefulSet |
| `--force`     | `-f`  | boolean | false          | Skip confirmation                |

**Warnings:**

- Data in persistent volumes is not deleted by default
- Pods are gracefully terminated with grace period
- Consider backing up data before deletion

**Notes:**

- StatefulSets manage pod identity; deletion removes that identity
- Volumes persist and can be reattached to new StatefulSet

---

### `ops k8s statefulsets scale`

Scale a StatefulSet to a different number of replicas.

This command changes the replica count for a StatefulSet.

**Usage:**

```bash
ops k8s statefulsets scale postgres --replicas 5
ops k8s statefulsets scale redis -r 3
ops k8s statefulsets scale my-cluster --replicas 7 -n data
```

**Arguments:**

| Argument | Type   | Description                        |
| -------- | ------ | ---------------------------------- |
| `name`   | string | Name of the StatefulSet (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                           |
| ------------- | ----- | ------- | -------------- | ------------------------------------- |
| `--replicas`  | `-r`  | integer | -              | Desired number of replicas (required) |
| `--namespace` | `-n`  | string  | config default | Namespace containing StatefulSet      |
| `--output`    | `-o`  | string  | `table`        | Output format                         |

**Example Output:**

```text
StatefulSet 'postgres' scaled to 5 replicas

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property         ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name             │ postgres    │
│ Desired Replicas │ 5           │
│ Ready Replicas   │ 3           │
│ Image            │ postgres:13 │
└──────────────────┴─────────────┘
```

**Notes:**

- Scaling up adds new replicas with sequential names
- Scaling down terminates pods in reverse order
- Supports both scaling up and down

---

### `ops k8s statefulsets restart`

Restart a StatefulSet.

This command restarts all pods in the StatefulSet with the same image.

**Usage:**

```bash
ops k8s statefulsets restart postgres
ops k8s statefulsets restart redis -n data
ops k8s statefulsets restart my-db
```

**Arguments:**

| Argument | Type   | Description                        |
| -------- | ------ | ---------------------------------- |
| `name`   | string | Name of the StatefulSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                      |
| ------------- | ----- | ------ | -------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing StatefulSet |
| `--output`    | `-o`  | string | `table`        | Output format                    |

**Example Output:**

```text
StatefulSet 'postgres' restarted

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Name             │ postgres       │
│ Desired Replicas │ 3              │
│ Ready Replicas   │ 1              │
│ Status           │ RollingRestart │
└──────────────────┴────────────────┘
```

**Notes:**

- Restarts pods in reverse order
- Maintains pod identity and persistent volumes

---

## DaemonSet Commands

DaemonSets ensure a pod runs on every node in the cluster. Typically used for system services like logging or
monitoring.

### `ops k8s daemonsets list`

List all DaemonSets in a namespace.

This command displays DaemonSets with their scheduling status.

**Usage:**

```bash
ops k8s daemonsets list
ops k8s daemonsets list -n kube-system
ops k8s daemonsets list --all-namespaces
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━┓
┃ Name          ┃ Namespace  ┃ Desired ┃ Current ┃ Ready ┃ Age ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━┩
│ fluentd       │ logging    │ 3       │ 3       │ 3     │ 90d │
│ filebeat      │ logging    │ 3       │ 3       │ 3     │ 60d │
│ node-exporter │ monitoring │ 3       │ 3       │ 3     │ 45d │
└───────────────┴────────────┴─────────┴─────────┴───────┴─────┘
```

**Notes:**

- Desired equals number of nodes in cluster
- Ready should equal Desired for healthy DaemonSets
- Common in kube-system for cluster infrastructure

---

### `ops k8s daemonsets get`

Get detailed information about a DaemonSet.

This command displays DaemonSet specification and status.

**Usage:**

```bash
ops k8s daemonsets get fluentd
ops k8s daemonsets get fluentd -n logging
ops k8s daemonsets get fluentd --output json
```

**Arguments:**

| Argument | Type   | Description                      |
| -------- | ------ | -------------------------------- |
| `name`   | string | Name of the DaemonSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                    |
| ------------- | ----- | ------ | -------------- | ------------------------------ |
| `--namespace` | `-n`  | string | config default | Namespace containing DaemonSet |
| `--output`    | `-o`  | string | `table`        | Output format                  |

**Example Output (Table):**

```text
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property  ┃ Value                ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Name      │ fluentd              │
│ Namespace │ logging              │
│ Desired   │ 3                    │
│ Current   │ 3                    │
│ Ready     │ 3                    │
│ Image     │ fluent/fluentd:v1.16 │
│ Age       │ 90d                  │
└───────────┴──────────────────────┘
```

**Notes:**

- Shows how many nodes should run the DaemonSet
- Image information helps verify deployment

---

### `ops k8s daemonsets create`

Create a new DaemonSet.

This command creates a DaemonSet that runs a pod on every node.

**Usage:**

```bash
ops k8s daemonsets create fluentd --image fluent/fluentd:v1.16
ops k8s daemonsets create node-exporter --image prom/node-exporter --port 9100
ops k8s daemonsets create logger --image logging:latest -l component=logging
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name for the DaemonSet (required) |

**Options:**

| Option        | Short | Type        | Default        | Description                |
| ------------- | ----- | ----------- | -------------- | -------------------------- |
| `--image`     | `-i`  | string      | -              | Container image (required) |
| `--namespace` | `-n`  | string      | config default | Target namespace           |
| `--port`      | `-p`  | integer     | -              | Container port to expose   |
| `--label`     | `-l`  | string list | -              | Labels in key=value format |
| `--output`    | `-o`  | string      | `table`        | Output format              |

**Example Output:**

```text
DaemonSet 'fluentd' created successfully

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property ┃ Value                ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Name     │ fluentd              │
│ Desired  │ 3                    │
│ Current  │ 0                    │
│ Image    │ fluent/fluentd:v1.16 │
└──────────┴──────────────────────┘
```

**Use Cases:**

```bash
# Log collector on every node
ops k8s daemonsets create fluentd --image fluent/fluentd:v1.16 -n logging

# Monitoring agent on every node
ops k8s daemonsets create node-exporter --image prom/node-exporter --port 9100

# Storage plugin on every node
ops k8s daemonsets create storage-plugin --image storage:latest -l role=infra
```

**Notes:**

- One pod per node, regardless of node count
- Useful for cluster-wide services (logging, monitoring, storage)
- No replica configuration needed

---

### `ops k8s daemonsets update`

Update a DaemonSet's image.

This command updates the container image for a DaemonSet.

**Usage:**

```bash
ops k8s daemonsets update fluentd --image fluent/fluentd:v1.17
ops k8s daemonsets update node-exporter --image prom/node-exporter:v1.7
```

**Arguments:**

| Argument | Type   | Description                      |
| -------- | ------ | -------------------------------- |
| `name`   | string | Name of the DaemonSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                    |
| ------------- | ----- | ------ | -------------- | ------------------------------ |
| `--namespace` | `-n`  | string | config default | Namespace containing DaemonSet |
| `--image`     | `-i`  | string | -              | New container image            |
| `--output`    | `-o`  | string | `table`        | Output format                  |

**Example Output:**

```text
DaemonSet 'fluentd' updated successfully

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property ┃ Value                ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Name     │ fluentd              │
│ Current  │ 3                    │
│ Ready    │ 2                    │
│ Image    │ fluent/fluentd:v1.17 │
└──────────┴──────────────────────┘
```

**Notes:**

- Pods are updated in rolling fashion across nodes
- New image is pulled during the update

---

### `ops k8s daemonsets delete`

Delete a DaemonSet.

This command deletes the DaemonSet and its pods from all nodes.

**Usage:**

```bash
ops k8s daemonsets delete fluentd
ops k8s daemonsets delete fluentd -n logging
ops k8s daemonsets delete node-exporter --force
```

**Arguments:**

| Argument | Type   | Description                                |
| -------- | ------ | ------------------------------------------ |
| `name`   | string | Name of the DaemonSet to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                    |
| ------------- | ----- | ------- | -------------- | ------------------------------ |
| `--namespace` | `-n`  | string  | config default | Namespace containing DaemonSet |
| `--force`     | `-f`  | boolean | false          | Skip confirmation              |

**Notes:**

- Removes pods from all nodes
- Service depending on DaemonSet will be affected

---

### `ops k8s daemonsets restart`

Restart a DaemonSet.

This command restarts all pods in the DaemonSet.

**Usage:**

```bash
ops k8s daemonsets restart fluentd
ops k8s daemonsets restart fluentd -n logging
ops k8s daemonsets restart node-exporter
```

**Arguments:**

| Argument | Type   | Description                      |
| -------- | ------ | -------------------------------- |
| `name`   | string | Name of the DaemonSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                    |
| ------------- | ----- | ------ | -------------- | ------------------------------ |
| `--namespace` | `-n`  | string | config default | Namespace containing DaemonSet |
| `--output`    | `-o`  | string | `table`        | Output format                  |

**Example Output:**

```text
DaemonSet 'fluentd' restarted

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Property ┃ Value          ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Name     │ fluentd        │
│ Current  │ 1              │
│ Ready    │ 1              │
│ Status   │ RollingRestart │
└──────────┴────────────────┘
```

**Notes:**

- Restarts all pods across all nodes
- Useful for applying configuration changes

---

## ReplicaSet Commands

ReplicaSets manage pod replicas. They are typically managed by Deployments, but can be used directly for advanced use
cases.

### `ops k8s replicasets list`

List all ReplicaSets in a namespace.

This command displays ReplicaSets with their replica status.

**Usage:**

```bash
ops k8s replicasets list
ops k8s replicasets list -n production
ops k8s replicasets list --all-namespaces
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━┓
┃ Name           ┃ Namespace ┃ Ready ┃ Desired ┃ Age ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━┩
│ nginx-abcd1234 │ default   │ 3     │ 3       │ 5d  │
│ app-1234abcd   │ default   │ 2     │ 2       │ 2d  │
└────────────────┴───────────┴───────┴─────────┴─────┘
```

**Notes:**

- ReplicaSets are typically created by Deployments
- Naming often includes hash suffix from parent Deployment
- Direct ReplicaSet use is uncommon

---

### `ops k8s replicasets get`

Get detailed information about a ReplicaSet.

This command displays ReplicaSet specification and status.

**Usage:**

```bash
ops k8s replicasets get nginx-abcd1234
ops k8s replicasets get nginx-abcd1234 -n production
ops k8s replicasets get nginx-abcd1234 --output json
```

**Arguments:**

| Argument | Type   | Description                       |
| -------- | ------ | --------------------------------- |
| `name`   | string | Name of the ReplicaSet (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                     |
| ------------- | ----- | ------ | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing ReplicaSet |
| `--output`    | `-o`  | string | `table`        | Output format                   |

**Example Output (Table):**

```text
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Property  ┃ Value          ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Name      │ nginx-abcd1234 │
│ Namespace │ default        │
│ Desired   │ 3              │
│ Current   │ 3              │
│ Ready     │ 3              │
│ Image     │ nginx:1.21     │
└───────────┴────────────────┘
```

**Notes:**

- Shows replica status and configuration
- Usually managed by Deployment, not directly

---

### `ops k8s replicasets delete`

Delete a ReplicaSet.

This command deletes the ReplicaSet and its pods.

**Usage:**

```bash
ops k8s replicasets delete nginx-abcd1234
ops k8s replicasets delete app-1234abcd -n production
ops k8s replicasets delete old-rs --force
```

**Arguments:**

| Argument | Type   | Description                                 |
| -------- | ------ | ------------------------------------------- |
| `name`   | string | Name of the ReplicaSet to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                     |
| ------------- | ----- | ------- | -------------- | ------------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing ReplicaSet |
| `--force`     | `-f`  | boolean | false          | Skip confirmation               |

**Warnings:**

- Deleting ReplicaSet created by Deployment may be overridden
- Consider deleting Deployment instead
- Pods are terminated immediately

**Notes:**

- ReplicaSets are typically managed by Deployments
- Direct deletion is uncommon in normal workflows

---

## Troubleshooting

| Issue                              | Cause                                            | Solution                |
| ---------------------------------- | ------------------------------------------------ | ----------------------- |
| Pods stuck in Pending              | Resource constraints or scheduling issues        | Check `ops k8s pods get |
| CrashLoopBackOff                   | Container crashes on startup                     | Check pod logs with     |
| ImagePullBackOff                   | Cannot pull container image                      | Verify image name       |
| Deployment not scaling             | Insufficient resources or scheduling constraints | Check node capacity     |
| Replicas not ready                 | Health check failures                            | Check pod logs and      |
| StatefulSet not progressing        | Pod stuck in initialization                      | Check persistent        |
| DaemonSet not running on all nodes | Node affinity or taints prevent scheduling       | Check node taints       |
| Rollout stuck                      | Pod failing to transition                        | Check recent events     |

---

## See Also

- [Core Commands](./core.md) - Manage cluster, nodes, and namespaces
- [Networking Commands](./networking.md) - Manage services, ingresses, and network policies
- [Kubernetes Plugin Index](../index.md) - Complete Kubernetes plugin documentation
- [Examples](../examples.md) - Practical examples and use cases
- [TUI Overview](../tui.md) - Terminal UI for cluster exploration
