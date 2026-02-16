# Kubernetes Plugin - TUI Guide

[< Back to Index](index.md) | [Commands](commands/) | [Ecosystem](ecosystem/) | [Examples](examples.md) | [Troubleshooting](troubleshooting.md)

---

## Table of Contents

- [Overview](#overview)
  - [When to Use the TUI](#when-to-use-the-tui)
  - [Key Capabilities](#key-capabilities)
- [Getting Started](#getting-started)
  - [Launching the TUI](#launching-the-tui)
  - [Initial Screen](#initial-screen)
  - [System Requirements](#system-requirements)
- [Key Bindings Reference](#key-bindings-reference)
  - [Global Key Bindings](#global-key-bindings)
  - [Screen-Specific Key Bindings](#screen-specific-key-bindings)
- [Screens](#screens)
  - [Dashboard Screen](#dashboard-screen---layout)
  - [Resource List Screen](#resource-list-screen---layout)
  - [Resource Detail Screen](#resource-detail-screen---layout)
  - [Ecosystem Tools Screen](#ecosystem-tools-screen)
  - [Create Resource Screen](#create-resource-screen)
  - [Log Viewer Screen](#log-viewer-screen---layout)
- [Widgets & Controls](#widgets--controls)
  - [Namespace Selector](#namespace-selector)
  - [Cluster Selector](#cluster-selector)
  - [Resource Type Filter](#resource-type-filter)
  - [Refresh Timer](#refresh-timer)
  - [Resource Bar](#resource-bar)
- [Supported Resource Types](#supported-resource-types)
  - [Workloads](#workloads)
  - [Networking](#networking)
  - [Configuration & Storage](#configuration--storage)
  - [Cluster Resources](#cluster-resources)
- [Common Workflows](#common-workflows)
  - [Browsing Pod Logs](#browsing-pod-logs)
  - [Viewing Resource Details](#viewing-resource-details)
  - [Switching Namespaces](#switching-namespaces)
  - [Creating Resources](#creating-resources)
  - [Deleting Resources](#deleting-resources)
- [Customization](#customization)
  - [Theme and Styling](#theme-and-styling)
  - [Refresh Intervals](#refresh-intervals)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

The Kubernetes TUI provides an interactive terminal interface for browsing and managing Kubernetes cluster resources in
real-time. Unlike the command-line interface which requires memorizing commands, the TUI offers an interactive,
keyboard-driven experience for cluster exploration, resource inspection, and basic operations.

### When to Use the TUI

**Use the TUI when:**

- Exploring cluster state and resources interactively
- Viewing pod logs and debugging applications
- Monitoring cluster health and resource utilization
- Making quick edits to resources
- Switching between resources and namespaces frequently
- You prefer keyboard navigation over commands

**Use CLI commands when:**

- Scripting cluster operations
- Performing bulk operations
- Integrating with CI/CD pipelines
- Creating repeatable, documented procedures

### Key Capabilities

- Interactive resource browsing with keyboard navigation
- Real-time cluster status and health monitoring
- Pod log viewing with follow mode
- Resource creation via interactive forms
- YAML editing for configuration changes
- Multi-cluster and multi-namespace switching
- Ecosystem tool integration (ArgoCD, Flux, Cert-Manager)
- Auto-refresh with configurable intervals

---

## Getting Started

### Launching the TUI

Start the Kubernetes TUI with a simple command:

```bash
uv run ops k8s tui
```

Or if installed globally via pipx:

```bash
ops k8s tui
```

The TUI will launch with the Resource List screen, displaying pods in your current context's default namespace.

### Initial Screen

When the TUI launches, you'll see the Resource List screen:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Kubernetes Resource Browser                                                │
├────────────────────────────────────────────────────────────────────────────┤
│ NS: All Namespaces  │ Ctx: minikube  │ Type: Pods                          │
├────────────────────────────────────────────────────────────────────────────┤
│ Name               │ Namespace     │ Status        │ Ready  │ Restarts     │
├────────────────────────────────────────────────────────────────────────────┤
│ coredns-558bd4d89c │ kube-system   │ Running       │ 1/1    │ 0            │
│ etcd-minikube      │ kube-system   │ Running       │ 1/1    │ 0            │
│ kube-apiserver     │ kube-system   │ Running       │ 1/1    │ 0            │
│ my-app-abc123      │ default       │ Running       │ 1/1    │ 2            │
│                                                                            │
│ ...more items...                                                           │
├────────────────────────────────────────────────────────────────────────────┤
│ 12 Pods in kube-system                                                     │
└────────────────────────────────────────────────────────────────────────────┘

Legend:
  j/k: Navigate    Enter: Select    n/N: Namespace    c/C: Cluster
  f/F: Resource    r: Refresh       a: Create         d: Delete
  l: Logs          q: Quit
```

### System Requirements

- Terminal with 256-color support (most modern terminals)
- Minimum terminal size: 80 columns x 24 rows (larger recommended)
- Network connectivity to Kubernetes cluster
- Valid kubeconfig with current-context set
- Python 3.10+ with Textual library (included with installation)

---

## Key Bindings Reference

### Global Key Bindings

Available on all screens:

| Key      | Action    | Description                            |
| -------- | --------- | -------------------------------------- |
| `q`      | Quit      | Exit the TUI application               |
| `Escape` | Back      | Return to previous screen              |
| `?`      | Help      | Display keyboard shortcut help message |
| `d`      | Dashboard | Open cluster status dashboard          |
| `e`      | Ecosystem | Open ecosystem tools overview          |

### Screen-Specific Key Bindings

#### Resource List Screen - Layout

| Key      | Action           | Description                                  |
| -------- | ---------------- | -------------------------------------------- |
| `j`      | cursor_down      | Move table cursor down                       |
| `k`      | cursor_up        | Move table cursor up                         |
| `Enter`  | select           | Select and view the highlighted resource     |
| `n`      | cycle_namespace  | Cycle to next namespace                      |
| `N`      | select_namespace | Open namespace picker popup                  |
| `c`      | cycle_cluster    | Cycle to next cluster context                |
| `C`      | select_cluster   | Open cluster context picker popup            |
| `f`      | cycle_filter     | Cycle to next resource type                  |
| `F`      | select_filter    | Open resource type picker popup              |
| `r`      | refresh          | Manually refresh the resource list           |
| `a`      | create           | Open create screen for current resource type |
| `d`      | delete           | Delete selected resource with confirmation   |
| `l`      | logs             | Open log viewer for selected pod             |
| `q`      | quit             | Exit application                             |
| `Escape` | back             | Go back                                      |
| `?`      | help             | Show help                                    |

#### Dashboard Screen - Layout

| Key      | Action            | Description                                 |
| -------- | ----------------- | ------------------------------------------- |
| `Escape` | back              | Return to resource list                     |
| `r`      | refresh           | Manually refresh all dashboard panels       |
| `+`      | increase_interval | Increase auto-refresh interval by 5 seconds |
| `-`      | decrease_interval | Decrease auto-refresh interval by 5 seconds |
| `q`      | quit              | Exit application                            |
| `?`      | help              | Show help                                   |

#### Resource Detail Screen - Layout

| Key      | Action         | Description                                   |
| -------- | -------------- | --------------------------------------------- |
| `Escape` | back           | Return to resource list                       |
| `y`      | toggle_yaml    | Show/hide YAML panel                          |
| `r`      | refresh_events | Refresh the events table                      |
| `e`      | edit           | Open YAML editor (requires editable resource) |
| `d`      | delete         | Delete resource with confirmation             |
| `l`      | logs           | View logs (pods only)                         |
| `x`      | exec           | Execute command in pod (pods only)            |
| `q`      | quit           | Exit application                              |
| `?`      | help           | Show help                                     |

#### Ecosystem Screen

| Key      | Action         | Description                              |
| -------- | -------------- | ---------------------------------------- |
| `Escape` | back           | Return to resource list                  |
| `r`      | refresh        | Manually refresh all ecosystem panels    |
| `1`      | focus_argocd   | Focus on ArgoCD applications panel       |
| `2`      | focus_flux     | Focus on Flux resources panel            |
| `3`      | focus_certs    | Focus on Cert-Manager certificates panel |
| `4`      | focus_rollouts | Focus on Argo Rollouts panel             |
| `q`      | quit           | Exit application                         |
| `?`      | help           | Show help                                |

#### Log Viewer Screen - Layout

| Key            | Action            | Description                                  |
| -------------- | ----------------- | -------------------------------------------- |
| `Escape`       | back              | Stop streaming and return to previous screen |
| `c`            | select_container  | Open container selector popup                |
| `f` or `Space` | toggle_follow     | Toggle between follow and pause modes        |
| `t`            | toggle_timestamps | Show/hide log timestamps                     |
| `Ctrl+L`       | clear_logs        | Clear all displayed log content              |
| `g`            | scroll_top        | Jump to beginning of logs                    |
| `G`            | scroll_bottom     | Jump to end of logs                          |
| `q`            | quit              | Exit application                             |
| `?`            | help              | Show help                                    |

#### Create Screen

| Key         | Action     | Description                              |
| ----------- | ---------- | ---------------------------------------- |
| `Escape`    | cancel     | Cancel creation and return to list       |
| `Ctrl+S`    | submit     | Create resource with current form values |
| `Tab`       | focus_next | Move to next form field                  |
| `Shift+Tab` | focus_prev | Move to previous form field              |
| `q`         | quit       | Exit application                         |
| `?`         | help       | Show help                                |

---

## Screens

### Dashboard Screen - Keyboard Shortcuts

The Dashboard provides a high-level overview of your cluster health and resource utilization.

**Accessed via:** Press `d` from any screen

**Display Layout:**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Cluster: prod-eks  │ K8s: v1.28.2  │ Nodes: 5  │ Namespaces: 12            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ Node Health                     │  Pod Status                              │
│ Name          │ Status │ Roles │ │  Total: 247                             │
│ ──────────────┼────────┼───────│ │    Running: 240 (green)                 │
│ node-1        │ Ready  │ master│ │    Pending: 5 (yellow)                  │
│ node-2        │ Ready  │       │ │    Failed: 2 (red)                      │
│ node-3        │ Ready  │       │ │                                         │
│ node-4        │ NotReady│      │ │  Pods by Namespace                      │
│ node-5        │ Ready  │       │ │    kube-system: 48                      │
│               │        │       │ │    default: 67                          │
│               │        │       │ │    production: 102                      │
│               │        │       │ │    staging: 30                          │
├────────────────────────────────────────────────────────────────────────────┤
│ Resource Capacity                                                          │
│   node-1                                                                   │
│     CPU   [████████░░░░░░░░] 4/8 cores                                     │
│     Mem   [██████░░░░░░░░░░] 6/16 Gi                                       │
│     Pods  [██████████░░░░░░] 42/110                                        │
│                                                                            │
│   node-2                                                                   │
│     CPU   [██████░░░░░░░░░░] 3/8 cores                                     │
│     Mem   [████████░░░░░░░░] 8/16 Gi                                       │
│     Pods  [████████░░░░░░░░] 38/110                                        │
├────────────────────────────────────────────────────────────────────────────┤
│ Recent Warnings                                                            │
│ Type    │ Reason               │ Object            │ Message      │ Count  │
│ Warning │ FailedScheduling     │ pod/pending-123   │ Insufficient │ 3      │
│ Warning │ CrashLoopBackOff     │ pod/app-crash     │ Error        │ 12     │
├────────────────────────────────────────────────────────────────────────────┤
│ Refresh: 15s  │  r: Refresh  │  +/-: Interval  │  d: Dashboard             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Features:**

- **Cluster Info Header**: Shows current context, Kubernetes version, node count, and namespace count
- **Node Health Panel**: Lists all nodes with status (Ready/NotReady) and assigned roles
- **Pod Status Summary**: Shows pod phase breakdown (Running, Pending, Failed, etc.) and distribution across namespaces
- **Resource Capacity Bars**: Visual representation of CPU, memory, and pod capacity per node
- **Recent Warnings**: Last 20 warning events for quick problem identification
- **Auto-Refresh**: Automatically refreshes every 30 seconds (configurable)

**Interpreting Status Colors:**

- Green: Healthy status (Running, Ready, Healthy)
- Yellow: Warning status (Pending, Progressing)
- Red: Error status (Failed, NotReady, Degraded)
- Dim: Unknown or disabled status

### Resource List Screen - Keyboard Shortcuts

The primary interface for browsing Kubernetes resources. Displays a table of resources with filtering and selection
capabilities.

**Initial Display:** First screen when TUI launches

**Display Layout (Example - Pods):**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Kubernetes Resource Browser                                                │
├────────────────────────────────────────────────────────────────────────────┤
│ NS: default  │ Ctx: minikube  │ Type: Pods                                 │
├────────────────────────────────────────────────────────────────────────────┤
│ Name                       │ Namespace     │ Status     │ Ready │ Restarts │
├────────────────────────────────────────────────────────────────────────────┤
│ my-app-abc123              │ default       │ Running    │ 1/1   │ 0        │
│ my-app-def456              │ default       │ Running    │ 1/1   │ 1        │
│ redis-cache-xyz789         │ default       │ Running    │ 1/1   │ 0        │
│ postgres-0                 │ default       │ Pending    │ 0/1   │ 0        │
│ test-runner-batch-1        │ default       │ Failed     │ 0/1   │ 5        │
│ debug-utility              │ default       │ Running    │ 1/1   │ 0        │
│                                                                            │
│ ...more items...                                                           │
├────────────────────────────────────────────────────────────────────────────┤
│ 6 Pods in default                                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

**Features:**

- **Toolbar**: Namespace, Cluster Context, and Resource Type selectors
- **DataTable**: Scrollable, zebra-striped table with context-aware columns
- **Status Bar**: Shows resource count and current filter context
- **Keyboard Navigation**: Use `j`/`k` to move up/down, `Enter` to select

**Column Definitions by Resource Type:**

**Pods:** Name, Namespace, Status, Ready, Restarts, Node, Age
**Deployments:** Name, Namespace, Ready, Up-to-date, Available, Age
**StatefulSets:** Name, Namespace, Ready, Age
**DaemonSets:** Name, Namespace, Desired, Current, Ready, Age
**ReplicaSets:** Name, Namespace, Desired, Ready, Age
**Services:** Name, Namespace, Type, Cluster-IP, Ports, Age
**Ingresses:** Name, Namespace, Class, Hosts, Addresses, Age
**ConfigMaps:** Name, Namespace, Data Keys, Age
**Secrets:** Name, Namespace, Type, Data Keys, Age
**Namespaces:** Name, Status, Age
**Nodes:** Name, Status, Roles, Version, Age
**Events:** Type, Reason, Object, Message, Count, Age

### Resource Detail Screen - Keyboard Shortcuts

Displays comprehensive information about a selected resource.

**Accessed via:** Press `Enter` on a selected resource in the Resource List

**Display Layout:**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Pod / my-app-abc123  ns: default  [green]Running[/green]                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ Metadata                          │ Status                                 │
│ ────────────────────────────────  │ ──────────────────────────────────     │
│ Namespace: default                │ Phase:        Running                  │
│ UID: f47ac10b-58cc-4372           │ Ready:        1/1                      │
│ Created: 2024-02-10T15:30:00Z     │ Restarts:     0                        │
│ Age: 3d5h                         │ Node:         minikube                 │
│                                   │ Pod IP:       10.244.0.42              │
│                                                                            │
│ Labels                            │ Annotations                            │
│ ────────────────────────────────  │ ──────────────────────────────────     │
│   app=my-app                      │ prometheus.io/scrape=true              │
│   version=v1.0                    │ prometheus.io/port=8080                │
│   tier=backend                    │ description=Production backend pod     │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ YAML  (y to toggle)                                                        │
│ ────────────────────────────────────────────────────────────────────────── │
│ apiVersion: v1                                                             │
│ kind: Pod                                                                  │
│ metadata:                                                                  │
│   name: my-app-abc123                                                      │
│   namespace: default                                                       │
│   uid: f47ac10b-58cc-4372                                                  │
│   creationTimestamp: '2024-02-10T15:30:00Z'                                │
│ ...                                                                        │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ Events  (r to refresh)                                                     │
│ Type   │ Reason       │ Object              │ Message          │ Count │   │
│ Normal │ Scheduled    │ pod/my-app-abc123   │ Successfully...  │ 1     │   │
│ Normal │ Pulling      │ pod/my-app-abc123   │ Pulling image... │ 1     │   │
│ Normal │ Pulled       │ pod/my-app-abc123   │ Successfully...  │ 1     │   │
│ Normal │ Created      │ pod/my-app-abc123   │ Created container│ 1     │   │
│ Normal │ Started      │ pod/my-app-abc123   │ Started container│ 1     │   │
├────────────────────────────────────────────────────────────────────────────┤
│ Back: Esc  │  YAML: y  │  Refresh: r  │  Edit: e  │  Delete: d             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Panels:**

- **Header**: Resource kind, name, namespace, and status badge
- **Metadata Panel**: UID, creation timestamp, age, namespace
- **Status Panel**: Type-specific status information
- **Labels Panel**: All labels applied to the resource
- **Annotations Panel**: All annotations with truncated values
- **YAML Panel**: Complete YAML representation (toggleable with `y`)
- **Events Panel**: Related events with timestamps and messages

**Available Actions:**

- `y`: Toggle YAML visibility
- `r`: Refresh events table
- `e`: Edit resource YAML (opens $EDITOR, applies as patch)
- `d`: Delete with confirmation
- `l`: View logs (pods only)
- `x`: Execute interactive shell (pods only)

### Ecosystem Tools Screen

Displays the status of installed ecosystem tools including ArgoCD, Flux, Cert-Manager, and Argo Rollouts.

**Accessed via:** Press `e` from any screen

**Display Layout:**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Ecosystem Tools Overview                                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ ArgoCD Applications             │ Flux Resources                           │
│ Name      │ NS      │ Sync      │ │ Name         │ NS       │ Ready │      │
│ ──────────┼─────────┼──────────  │ │ ────────────┼──────────┼───────       │
│ app-prod  │ argocd  │ Synced ✓  │ │ repos-main   │ flux-sys │ Yes   │      │
│ app-staging│argocd  │ OutOfSync │ │ kustomize-dev│ flux-sys │ No    │      │
│ app-dev   │ argocd  │ Synced ✓  │ │ helm-release │ default  │ Yes   │      │
│                                   │                                        │
│ Cert-Manager Certificates        │ Argo Rollouts                           │
│ Name            │ NS        │ Ready│ │ Name         │ Phase      │ Ready │ │
│ ─────────────────┼──────────┼─────  │ │ ────────────┼──────────┼──────     │
│ api.example.com  │ default  │ Yes  │ │ app-canary   │ Progressing│ 3/5     │
│ web.example.com  │ default  │ No   │ │ api-bg       │ Healthy   │ 5/5      │
│ cdn.example.com  │ platform │ Yes  │ │                                     │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ Refresh: 25s  │  1: ArgoCD  │  2: Flux  │  3: Certs  │  4: Rollouts        │
└────────────────────────────────────────────────────────────────────────────┘
```

**Panels:**

- **ArgoCD Applications**: Name, namespace, project, sync status, health status, repository
- **Flux Resources**: Name, namespace, type (GitRepo/Kustomization/HelmRelease), ready status, sync status
- **Cert-Manager Certificates**: Name, namespace, ready status, expiry date, issuer, DNS names
- **Argo Rollouts**: Name, namespace, strategy (canary/bluegreen), phase, replica readiness, weight

**Status Indicators:**

- ArgoCD Sync: Synced (green) | OutOfSync (yellow) | Unknown (dim)
- ArgoCD Health: Healthy (green) | Degraded (red) | Progressing (yellow)
- Flux Ready: Yes (green) | No (red)
- Flux Status: Ready (green) | Reconciling (cyan) | Suspended (dim)
- Certificates Ready: Yes (green) | No (red)

**Features:**

- Background thread loading with graceful error handling
- Missing CRD detection (shows "not installed" message if tool not present)
- Auto-refresh every 30 seconds
- Configurable refresh interval with `+` and `-` keys
- Focus individual panels with `1-4` keys for keyboard navigation

### Create Resource Screen

Interactive form for creating new Kubernetes resources.

**Accessed via:** Press `a` on Resource List (for creatable resource types)

**Display Layout (Example - Deployment):**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Create Deployment                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ Namespace                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ default                                                                  │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                            │
│ Name *                                                                     │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ my-app                                                                   │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                            │
│ Image *                                                                    │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ nginx:latest                                                             │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                            │
│ Replicas                                                                   │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ 3                                                                        │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                            │
│ Container Port                                                             │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ 8080                                                                     │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                            │
│ Labels                                                                     │
│ ┌──────────────────────────────────────────────────────────────────────────┐
│ │ app=my-app                                                               │
│ │ version=v1.0                                                             │
│ │ tier=backend                                                             │
│ └──────────────────────────────────────────────────────────────────────────┘
│ Labels as key=value pairs, one per line                                    │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│                             [Create]  [Cancel]                             │
│ Cancel: Esc  │  Create: Ctrl+S                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Supported Resource Types for Creation:**

- Deployments
- StatefulSets
- DaemonSets
- Services
- Ingresses
- NetworkPolicies
- ConfigMaps
- Secrets
- Namespaces

**Field Types:**

- **Text Input**: Single-line text fields (name, image, ports)
- **Select**: Dropdown selection (service type, secret type)
- **Textarea**: Multi-line fields (labels, rules, data)
- **Integer**: Numeric fields (replicas)

**Form Validation:**

- Required fields marked with `*` - form validates before submission
- Integer fields must contain valid numbers
- YAML fields are parsed (for Ingress rules, TLS config)
- Labels must be in `key=value` format (one per line)

**Creating a Resource:**

1. Navigate fields with `Tab`/`Shift+Tab`
2. Enter values in each field
3. Press `Ctrl+S` or click Create button
4. Confirmation message appears and list refreshes

### Log Viewer Screen - Keyboard Shortcuts

Real-time log streaming from pod containers with pause/follow controls.

**Accessed via:** Press `l` on a selected pod (from List or Detail screen)

**Display Layout:**

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Pod Logs / my-app-abc123  ns: default                                      │
├────────────────────────────────────────────────────────────────────────────┤
│ Container: my-app  │                        │ [bold green]FOLLOWING[/green]│
├────────────────────────────────────────────────────────────────────────────┤
│ 2024-02-10T15:42:38Z INFO Starting application server...                   │
│ 2024-02-10T15:42:39Z INFO Loading configuration from /etc/app/config.yaml  │
│ 2024-02-10T15:42:40Z INFO Database connection established                  │
│ 2024-02-10T15:42:41Z INFO Starting HTTP server on port 8080                │
│ 2024-02-10T15:42:42Z INFO Server ready to accept connections               │
│ 2024-02-10T15:43:01Z DEBUG Processing request GET /api/health              │
│ 2024-02-10T15:43:01Z DEBUG Request completed with status 200               │
│ 2024-02-10T15:43:15Z DEBUG Processing request POST /api/data               │
│ 2024-02-10T15:43:16Z WARNING Request processing took 1200ms                │
│ 2024-02-10T15:43:17Z DEBUG Request completed with status 201               │
│                                                                            │
│ [streaming in real-time...]                                                │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ c: Container  │  f: Follow  │  t: Timestamps  │  Ctrl+L: Clear             │
│ g: Top  │  G: Bottom  │  Back: Esc                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

**Features:**

- **Real-time Streaming**: Logs stream in real-time when in follow mode
- **Container Selection**: For multi-container pods, press `c` to select container
- **Follow Mode**: Default on, shows new logs as they arrive (press `f` to toggle)
- **Pause Mode**: When paused, logs are static but still scrollable
- **Timestamps**: Toggle timestamp display with `t` key
- **Navigation**: Scroll with arrow keys or jump to top/bottom with `g`/`G`
- **Search**: Logs are in a scrollable widget (scroll to search manually)

**Controls:**

| Key            | Action                                  |
| -------------- | --------------------------------------- |
| `c`            | Select container (multi-container pods) |
| `f` or `Space` | Toggle follow/pause mode                |
| `t`            | Toggle timestamp display                |
| `Ctrl+L`       | Clear displayed logs                    |
| `g`            | Jump to beginning                       |
| `G`            | Jump to end                             |
| `↑` / `↓`      | Scroll manually                         |
| `Escape`       | Stop streaming and return               |

**Follow Mode Behavior:**

- **Following**: Shows last 200 lines initially, then streams new lines as they arrive
- **Paused**: Shows last 500 lines, allows manual scrolling and review

---

## Widgets & Controls

### Namespace Selector

Located in the toolbar on Resource List and Dashboard screens.

**Display:** `NS: default`

**Functions:**

- **Quick Cycle** (`n`): Cycles through available namespaces + "All Namespaces" option
- **Popup Select** (`N`): Opens a scrollable popup to select any namespace

**All Namespaces Option:** Selecting "All Namespaces" (position 0) filters resources across all namespaces in the
cluster.

**Behavior:** When you change namespaces, the resource list automatically refreshes to show resources in the new
namespace.

### Cluster Selector

Located in the toolbar on Resource List and Dashboard screens.

**Display:** `Ctx: minikube`

**Functions:**

- **Quick Cycle** (`c`): Cycles through configured Kubernetes contexts
- **Popup Select** (`C`): Opens a popup to select any configured context

**Behavior:** When you change contexts, the TUI reconnects to the new cluster. Namespaces and resources refresh
automatically. The namespace list is reloaded from the new cluster.

**Configuration:** Contexts come from your kubeconfig file and any configured multi-cluster setup in your ops config.

### Resource Type Filter

Located in the toolbar on Resource List screen.

**Display:** `Type: Pods`

**Functions:**

- **Quick Cycle** (`f`): Cycles through supported resource types
- **Popup Select** (`F`): Opens a popup to select any resource type

**Available Types (in order):**

1. Pods
2. Deployments
3. StatefulSets
4. DaemonSets
5. ReplicaSets
6. Services
7. Ingresses
8. NetworkPolicies
9. ConfigMaps
10. Secrets
11. Namespaces
12. Nodes
13. Events

**Behavior:** When you change the resource type, the table columns change to match the selected type, and the resource
list refreshes with resources of that type.

### Refresh Timer

Located in the top-right of Dashboard and Ecosystem screens.

**Display:** `Refresh: 15s`

**Functions:**

- **Manual Refresh** (`r`): Immediately refresh all panels
- **Increase Interval** (`+`): Add 5 seconds to the interval (max 300s)
- **Decrease Interval** (`-`): Subtract 5 seconds from the interval (min 5s)

**Default Interval:** 30 seconds

**Behavior:** Countdown timer that automatically triggers a full refresh when it reaches zero, then resets. Resets when
you press `r` manually.

### Resource Bar

Displayed on the Dashboard screen showing CPU, memory, and pod capacity per node.

**Display Example:**

```text
  node-1
    CPU   [████████░░░░░░░░] 4/8 cores
    Mem   [██████░░░░░░░░░░] 6/16 Gi
    Pods  [██████████░░░░░░] 42/110
```

**Color Coding:**

- Green (`[████]`): < 70% utilization (healthy)
- Yellow: 70-90% utilization (warning)
- Red: >= 90% utilization (critical)
- Dim: Unknown capacity

**Note:** Actual usage requires metrics-server in the cluster. If unavailable, bars show capacity only with "N/A" for
usage.

---

## Supported Resource Types

### Workloads

| Resource Type | Viewable | Creatable | Editable | Deletable | Loggable | Executable |
| ------------- | -------- | --------- | -------- | --------- | -------- | ---------- |
| Pods          | Yes      | No        | Yes      | Yes       | Yes      | Yes        |
| Deployments   | Yes      | Yes       | Yes      | Yes       | No       | No         |
| StatefulSets  | Yes      | Yes       | Yes      | Yes       | No       | No         |
| DaemonSets    | Yes      | Yes       | Yes      | Yes       | No       | No         |
| ReplicaSets   | Yes      | No        | Yes      | Yes       | No       | No         |

### Networking

| Resource Type   | Viewable | Creatable | Editable | Deletable |
| --------------- | -------- | --------- | -------- | --------- |
| Services        | Yes      | Yes       | Yes      | Yes       |
| Ingresses       | Yes      | Yes       | Yes      | Yes       |
| NetworkPolicies | Yes      | Yes       | Yes      | Yes       |

### Configuration & Storage

| Resource Type | Viewable | Creatable | Editable | Deletable |
| ------------- | -------- | --------- | -------- | --------- |
| ConfigMaps    | Yes      | Yes       | Yes      | Yes       |
| Secrets       | Yes      | Yes       | Yes      | Yes       |

### Cluster Resources

| Resource Type | Viewable | Creatable | Editable | Deletable |
| ------------- | -------- | --------- | -------- | --------- |
| Namespaces    | Yes      | Yes       | Yes      | Yes       |
| Nodes         | Yes      | No        | No       | No        |
| Events        | Yes      | No        | No       | No        |

---

## Common Workflows

### Browsing Pod Logs

1. Launch the TUI: `ops k8s tui`
2. Ensure "Pods" is selected in the Type filter
3. Navigate to your pod with `j`/`k` arrow keys
4. Press `l` to open log viewer
5. Logs stream in real-time (FOLLOWING mode)
6. Press `f` to pause and scroll through logs manually
7. Press `t` to show/hide timestamps
8. Press `g` to jump to the beginning of logs
9. Press `Escape` to return to pod list

### Viewing Resource Details

1. Launch the TUI: `ops k8s tui`
2. Change resource type with `f`/`F` to the type you want
3. Navigate with `j`/`k` to find your resource
4. Press `Enter` to open detail screen
5. View metadata, status, labels, annotations in the panels
6. Press `y` to show/hide YAML representation
7. Press `r` to refresh events table
8. Press `Escape` to return to list

### Switching Namespaces

**Quick cycle method:**

1. From any screen, press `n` to cycle to next namespace
2. Resource list updates automatically

**Popup selection method:**

1. From any screen, press `N` to open namespace picker
2. Use arrow keys to navigate options
3. Press `Enter` to select
4. Resource list updates to show resources in selected namespace

**Pro tip:** Press `n` multiple times rapidly to find your namespace, or use `N` for a full list if you know the name.

### Creating Resources

1. Navigate to desired resource type with `f`/`F`
2. Ensure you're in the correct namespace (shown in NS selector)
3. Press `a` to open create form
4. Fill in required fields (marked with `*`)
5. Use `Tab` to navigate between fields
6. For list fields (labels, ports, rules), enter values one per line
7. Press `Ctrl+S` to create
8. Success message appears and list refreshes
9. Your new resource is now visible in the list

**Example - Create a Deployment:**

```text
Namespace: default
Name: my-web-app
Image: nginx:1.24
Replicas: 3
Container Port: 80
Labels:
  app=my-web-app
  tier=frontend
```

### Deleting Resources

1. Navigate with `j`/`k` to select resource
2. Press `d` to delete
3. Confirmation modal appears showing resource and namespace
4. Confirm with "Delete" button or dismiss with "Cancel"
5. Resource is deleted and list refreshes
6. Confirmation message shown

**Note:** Deletion is immediate without additional warnings after confirmation. Be careful with critical resources.

---

## Customization

### Theme and Styling

The TUI uses Textual CSS for styling. Customization can be done by editing the styles file:

**Location:** `src/system_operations_manager/tui/apps/kubernetes/styles.tcss`

**Customizable Elements:**

- Colors and borders for panels
- Table styling and cursor highlighting
- Form field appearance
- Widget spacing and sizing
- Text styles (bold, italic, etc.)

**Example customizations:**

- Change primary color from cyan to your brand color
- Adjust panel borders (solid, dashed, double)
- Modify text padding and margins
- Custom colors for different resource statuses

**To apply custom styles:**

1. Edit the `.tcss` file
2. Reload the TUI (restart the application)

### Refresh Intervals

Refresh behavior can be customized:

**Dashboard Auto-Refresh:**

- Default interval: 30 seconds
- Minimum: 5 seconds
- Maximum: 300 seconds (5 minutes)
- Adjust with `+` and `-` keys in real-time

**Pod Log Streaming:**

- Follow mode: Real-time with 200-line initial buffer
- Pause mode: Static view of last 500 lines

**Resource List Refresh:**

- Manual only via `r` key
- No automatic refresh in resource list (prevents disruption during navigation)

---

## Troubleshooting

| Issue                                 | Symptoms                                | Solution                                     |
| ------------------------------------- | --------------------------------------- | -------------------------------------------- |
| TUI doesn't start                     | "Connection refused" or blank screen    | Check kubeconfig is                          |
| Terminal rendering issues             | Garbled characters or incorrect colors  | Verify terminal                              |
| Resources not appearing               | Empty list in resource table            | Check namespace                              |
| Slow to refresh                       | Lag between actions and display updates | Large clusters may                           |
| Cannot create resources               | "Cannot create X" warning message       | Not all resource                             |
| Cannot edit/delete resource           | "Cannot edit/delete X" message          | Only certain resourc                         |
| Logs not streaming                    | Log viewer opens but shows no content   | Ensure pod is running and has                |
| Command shows as "Exec not available" | Cannot execute into pod                 | Exec requires the                            |
| Ecosystem panels show errors          | "Error loading ArgoCD" or similar       | Tool may not be installed. Check CRDs exist. |
| Cannot switch contexts                | "Failed to switch context" error        | Context may not                              |

**Debug Mode:**

For development/debugging, run with additional logging:

```bash
RUST_LOG=debug ops k8s tui
```

---

## See Also

- [Kubernetes Plugin Index](index.md) - Main plugin documentation
- [CLI Commands Reference](commands/) - Command-line interface guide
- [Ecosystem Tools](ecosystem/) - ArgoCD, Flux, Helm integration docs
- [Examples](examples.md) - Common usage patterns
- [Troubleshooting](troubleshooting.md) - Detailed problem solving
- [Textual Documentation](https://textual.textualize.io/) - TUI framework docs
- [Kubernetes Official Docs](https://kubernetes.io/docs/) - K8s concepts and APIs
