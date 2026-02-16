# Kubernetes Plugin > Ecosystem > Argo Rollouts

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [Rollouts Commands](#rollouts-commands)
  - [Analysis Templates](#analysis-templates)
  - [Analysis Runs](#analysis-runs)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Argo Rollouts is a Kubernetes controller and set of CRDs that provides advanced deployment strategies for Kubernetes. It
enables progressive delivery techniques like canary deployments, blue-green deployments, and gradual traffic shifting,
allowing you to deploy applications with reduced risk and faster feedback.

The Kubernetes plugin provides comprehensive CLI integration with Argo Rollouts through the `rollouts` command family.
This integration allows you to:

- Manage Rollout resources with standard lifecycle operations
- Define and execute complex deployment strategies with canary steps
- Monitor progressive deployments with real-time status updates
- Analyze deployments using AnalysisTemplates and AnalysisRuns
- Control rollout progression with promote, abort, and retry operations

Argo Rollouts is built on Kubernetes CustomResourceDefinitions (CRDs), so it uses the Kubernetes API to manage all
resources. The plugin discovers Argo Rollouts availability by checking for the presence of the Rollout CRD in your
cluster.

## Prerequisites

To use the Argo Rollouts integration, you need:

1. **Argo Rollouts Controller**: Install the Argo Rollouts controller in your cluster

   ```bash
   kubectl create namespace argo-rollouts
   kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
   ```

2. **Kubernetes Access**: Valid kubeconfig with permissions to create and manage Rollout, AnalysisTemplate, and
   AnalysisRun resources

3. **CRDs**: Argo Rollouts CRDs must be installed in your cluster (automatically installed with the controller)

4. **Version Requirements**:
   - Argo Rollouts: 1.0 or later
   - Kubernetes: 1.16 or later
   - kubectl: 1.16 or later

## Detection

The plugin automatically detects whether Argo Rollouts is available in your cluster by checking for the presence of the
`Rollout` CRD. You can verify detection with:

```bash
ops k8s rollouts list
```

If Argo Rollouts is not installed, you'll receive a clear error message indicating the Rollout CRD is not found.

## Configuration

Argo Rollouts integration uses the standard Kubernetes plugin configuration. No additional ecosystem-specific
configuration is required beyond standard Kubernetes access settings.

However, you may want to configure default namespaces for rollout operations:

```yaml
# In your ops config or environment
kubernetes:
  default_namespace: production
  rollouts_namespace: production
```

---

## Command Reference

### Rollouts Commands

#### `ops k8s rollouts list`

List all Rollouts in a namespace.

```bash
ops k8s rollouts list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                                             |
| ------------- | ----- | ------ | --------- | ------------------------------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace to query                           |
| `--selector`  | `-l`  | string | None      | Label selector filter (e.g., 'app=myapp,tier=frontend') |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml                     |

**Example Output:**

```text
Rollouts

NAME              NAMESPACE     STRATEGY    PHASE       REPLICAS  READY   WEIGHT  IMAGE                    AGE
my-app-rollout    production    canary      Progressing 3         3       50      nginx:1.21.0             2h 30m
payment-service   production    blueGreen   Healthy     2         2       100     python:3.9-slim         15m
api-gateway       staging       canary      Healthy     5         5       100     api-gateway:v2.1.0      5d 12h
```

**Examples:**

```bash
# List rollouts in default namespace
ops k8s rollouts list

# List rollouts in production namespace
ops k8s rollouts list -n production

# List rollouts with label filtering
ops k8s rollouts list -l app=myapp -n production

# Get JSON output for script processing
ops k8s rollouts list -o json

# Get YAML output for backup or analysis
ops k8s rollouts list -o yaml
```

---

#### `ops k8s rollouts get`

Get detailed information about a specific Rollout.

```bash
ops k8s rollouts get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Rollout: my-app-rollout

name                my-app-rollout
namespace           production
strategy            canary
phase               Progressing
replicas            3
ready_replicas      3
canary_weight       50
image               nginx:1.21.0
age                 2h 30m
```

**Examples:**

```bash
# Get rollout in default namespace
ops k8s rollouts get my-rollout

# Get rollout in production namespace
ops k8s rollouts get my-rollout -n production

# Get full YAML definition
ops k8s rollouts get my-rollout -o yaml

# Get JSON for parsing
ops k8s rollouts get my-rollout -o json
```

---

#### `ops k8s rollouts create`

Create a new Rollout with specified deployment strategy.

```bash
ops k8s rollouts create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option           | Short | Type    | Default   | Description                                     |
| ---------------- | ----- | ------- | --------- | ----------------------------------------------- |
| `--namespace`    | `-n`  | string  | `default` | Kubernetes namespace                            |
| `--image`        |       | string  | Required  | Container image URI                             |
| `--strategy`     |       | string  | `canary`  | Strategy: canary or blueGreen                   |
| `--replicas`     |       | integer | 1         | Number of replicas                              |
| `--canary-steps` |       | string  | None      | Canary steps as JSON array (see examples below) |
| `--label`        | `-l`  | string  | None      | Labels as key=value (repeatable)                |
| `--output`       | `-o`  | string  | `table`   | Output format: table, json, or yaml             |

**Example Output:**

```text
Created Rollout: my-app-rollout

metadata:
  name: my-app-rollout
  namespace: production
spec:
  replicas: 3
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {}
      - setWeight: 40
      - pause: {}
      - setWeight: 100
  template:
    spec:
      containers:
      - name: my-app
        image: nginx:1.21.0
```

**Examples:**

```bash
# Create basic canary rollout
ops k8s rollouts create my-app --image nginx:1.21.0 --replicas 3

# Create canary with progressive steps
ops k8s rollouts create my-app --image nginx:1.21.0 \
  --canary-steps '[{"setWeight":20},{"pause":{"duration":"1m"}},{"setWeight":40}]'

# Create blue-green rollout
ops k8s rollouts create payment-service --image payment:v2.0 \
  --strategy blueGreen --replicas 2

# Create with labels in production
ops k8s rollouts create api-gateway \
  --image api-gateway:v2.1.0 \
  --replicas 5 \
  --label app=api-gateway \
  --label team=platform \
  -n production

# Create and get YAML output
ops k8s rollouts create my-app --image nginx:1.21.0 -o yaml
```

**Canary Steps Format:**

The `--canary-steps` option accepts a JSON array of step objects. Common step types:

```json
[
  { "setWeight": 20 },
  { "setWeight": 50 },
  { "pause": {} },
  { "pause": { "duration": "1h" } },
  { "setWeight": 100 }
]
```

Step options:

- `setWeight`: Set traffic weight (0-100) for canary replica set
- `pause`: Pause the rollout (optional duration in Go time format like "1h", "30m", "5m")

---

#### `ops k8s rollouts delete`

Delete a Rollout and its associated resources.

```bash
ops k8s rollouts delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
Rollout 'my-rollout' deleted
```

**Examples:**

```bash
# Delete rollout with confirmation
ops k8s rollouts delete my-rollout

# Delete in production namespace
ops k8s rollouts delete my-rollout -n production

# Force delete without confirmation
ops k8s rollouts delete my-rollout --force

# Delete in specific namespace without prompt
ops k8s rollouts delete my-rollout -n staging --force
```

---

#### `ops k8s rollouts status`

Show detailed status information for a Rollout.

```bash
ops k8s rollouts status <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Rollout Status: my-app-rollout

phase                 Progressing
observedGeneration    2
replicas              3
readyReplicas         3
updatedReplicas       2
availableReplicas     3
canaryReplicas        2
canaryReadyReplicas   2
canaryWeight          50
currentStepIndex      2
currentPodHash        abcd1234
stableRevision        1
canaryRevision        2
conditions:
  - type: Progressing
    status: True
    message: Rollout is progressing
  - type: Healthy
    status: True
    message: Rollout is healthy
```

**Examples:**

```bash
# Get status in default namespace
ops k8s rollouts status my-app

# Get status in production namespace
ops k8s rollouts status my-app -n production

# Get status as JSON
ops k8s rollouts status my-app -o json
```

---

#### `ops k8s rollouts promote`

Promote a Rollout to the next step or fully promote it.

```bash
ops k8s rollouts promote <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type    | Default   | Description                          |
| ------------- | ----- | ------- | --------- | ------------------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace                 |
| `--full`      |       | boolean | False     | Fully promote (skip remaining steps) |
| `--output`    | `-o`  | string  | `table`   | Output format: table, json, or yaml  |

**Example Output:**

```text
Promoted Rollout: my-app-rollout

phase                 Progressing
canaryWeight          100
currentStepIndex      5
conditions:
  - type: Progressing
    status: True
    message: Rollout is progressing
```

**Examples:**

```bash
# Promote to next step
ops k8s rollouts promote my-app

# Fully promote (complete deployment)
ops k8s rollouts promote my-app --full

# Promote in production namespace
ops k8s rollouts promote my-app -n production --full

# Promote and get JSON output
ops k8s rollouts promote my-app -o json
```

---

#### `ops k8s rollouts abort`

Abort a Rollout that is currently in progress.

```bash
ops k8s rollouts abort <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Aborted Rollout: my-app-rollout

phase                 Degraded
message              Rollout aborted by user
```

**Examples:**

```bash
# Abort rollout in default namespace
ops k8s rollouts abort my-app

# Abort in production
ops k8s rollouts abort my-app -n production

# Abort and view result as YAML
ops k8s rollouts abort my-app -o yaml
```

---

#### `ops k8s rollouts retry`

Retry a failed or aborted Rollout to resume the deployment.

```bash
ops k8s rollouts retry <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description           |
| -------- | -------- | --------------------- |
| `name`   | Yes      | Rollout resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Retried Rollout: my-app-rollout

phase                 Progressing
message              Rollout retry initiated
currentStepIndex     1
```

**Examples:**

```bash
# Retry failed rollout
ops k8s rollouts retry my-app

# Retry in production namespace
ops k8s rollouts retry my-app -n production

# Retry and view as JSON
ops k8s rollouts retry my-app -o json
```

---

### Analysis Templates

#### `ops k8s analysis-templates list`

List all AnalysisTemplates in a namespace.

```bash
ops k8s analysis-templates list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--selector`  | `-l`  | string | None      | Label selector filter               |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Analysis Templates

NAME                  NAMESPACE     METRICS  ARGS                    AGE
success-rate-80      production    1        timeout=5m              2d 3h
error-rate-5percent  production    2        duration=10m            1d 12h
canary-validation    staging       3        percentile=p95          5h 45m
```

**Examples:**

```bash
# List analysis templates
ops k8s analysis-templates list

# List in production namespace
ops k8s analysis-templates list -n production

# Filter by label
ops k8s analysis-templates list -l app=myapp

# Get JSON output
ops k8s analysis-templates list -o json
```

---

#### `ops k8s analysis-templates get`

Get details of a specific AnalysisTemplate.

```bash
ops k8s analysis-templates get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                    |
| -------- | -------- | ------------------------------ |
| `name`   | Yes      | AnalysisTemplate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
AnalysisTemplate: success-rate-80

name           success-rate-80
namespace      production
metrics_count  1
args           timeout=5m
age            2d 3h
```

**Examples:**

```bash
# Get analysis template
ops k8s analysis-templates get success-rate-80

# Get in production namespace
ops k8s analysis-templates get success-rate-80 -n production

# Get full YAML definition
ops k8s analysis-templates get success-rate-80 -o yaml
```

---

### Analysis Runs

#### `ops k8s analysis-runs list`

List all AnalysisRuns in a namespace.

```bash
ops k8s analysis-runs list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--selector`  | `-l`  | string | None      | Label selector filter               |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Analysis Runs

NAME                             NAMESPACE     PHASE       METRICS  ROLLOUT           AGE
my-rollout-abc123               production    Successful  1        my-rollout        30m
payment-service-xyz789          production    Running     2        payment-service   5m
api-gateway-def456              staging       Failed      3        api-gateway       2h 15m
```

**Examples:**

```bash
# List analysis runs
ops k8s analysis-runs list

# List in production namespace
ops k8s analysis-runs list -n production

# Filter by rollout label
ops k8s analysis-runs list -l rollout=my-rollout

# Get JSON output for integration
ops k8s analysis-runs list -o json
```

---

#### `ops k8s analysis-runs get`

Get details of a specific AnalysisRun.

```bash
ops k8s analysis-runs get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | AnalysisRun resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
AnalysisRun: my-rollout-abc123

name             my-rollout-abc123
namespace        production
phase            Successful
metrics_count    1
rollout_ref      my-rollout
age              30m
```

**Examples:**

```bash
# Get analysis run
ops k8s analysis-runs get my-rollout-abc123

# Get in production namespace
ops k8s analysis-runs get my-rollout-abc123 -n production

# Get YAML definition
ops k8s analysis-runs get my-rollout-abc123 -o yaml

# Get JSON for parsing
ops k8s analysis-runs get my-rollout-abc123 -o json
```

---

## Integration Examples

### Example 1: Canary Deployment with Progressive Traffic Shifting

Deploy an application with gradual traffic increase:

```bash
# Create a canary rollout with progressive steps
ops k8s rollouts create my-app \
  --image myapp:v2.0 \
  --replicas 5 \
  --strategy canary \
  --canary-steps '[
    {"setWeight":10},
    {"pause":{"duration":"2m"}},
    {"setWeight":25},
    {"pause":{"duration":"5m"}},
    {"setWeight":50},
    {"pause":{"duration":"10m"}},
    {"setWeight":75},
    {"pause":{}},
    {"setWeight":100}
  ]' \
  -n production

# Monitor the rollout status
ops k8s rollouts status my-app -n production

# Promote to next step after verifying metrics
ops k8s rollouts promote my-app -n production

# When ready to complete, fully promote
ops k8s rollouts promote my-app --full -n production
```

### Example 2: Blue-Green Deployment

Deploy with instant cutover when ready:

```bash
# Create blue-green rollout
ops k8s rollouts create payment-service \
  --image payment-api:v3.0 \
  --strategy blueGreen \
  --replicas 3 \
  -n production

# Monitor status
ops k8s rollouts status payment-service -n production

# When ready to switch traffic, promote
ops k8s rollouts promote payment-service --full -n production
```

### Example 3: Abort and Retry Failed Deployment

Handle deployment failures gracefully:

```bash
# Check rollout status and see it's in progress
ops k8s rollouts status my-app -n production

# Issues detected - abort the deployment
ops k8s rollouts abort my-app -n production

# Fix the issue (update image, etc)
# Then retry the deployment
ops k8s rollouts retry my-app -n production
```

### Example 4: View Analysis Results

Monitor analysis during progressive deployment:

```bash
# List all analysis runs
ops k8s analysis-runs list -n production

# Check specific analysis run results
ops k8s analysis-runs get my-rollout-abc123 -n production -o yaml

# Get all analysis templates for reference
ops k8s analysis-templates list -n production
```

### Example 5: Scripting Rollout Operations

Integrate with automation and CI/CD:

```bash
#!/bin/bash

ROLLOUT_NAME="api-service"
NAMESPACE="production"
NEW_IMAGE="api-service:${VERSION}"

# Create rollout
ops k8s rollouts create "$ROLLOUT_NAME" \
  --image "$NEW_IMAGE" \
  -n "$NAMESPACE"

# Wait for health checks (implement your monitoring)
sleep 60

# Get status as JSON for parsing
STATUS=$(ops k8s rollouts status "$ROLLOUT_NAME" -n "$NAMESPACE" -o json)

# Check if healthy and promote if so
if echo "$STATUS" | grep -q '"phase":"Healthy"'; then
  ops k8s rollouts promote "$ROLLOUT_NAME" --full -n "$NAMESPACE"
  echo "Deployment successful"
else
  ops k8s rollouts abort "$ROLLOUT_NAME" -n "$NAMESPACE"
  echo "Deployment failed, rolled back"
  exit 1
fi
```

---

## Troubleshooting

| Issue                                | Solution                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------- |
| "Rollout CRD not found"              | Argo Rollouts controller not installed. Install it with: `kubectl apply -n |
| Rollout stuck in "Progressing" phase | Check pod status with `kubectl get pods -n                                 |
| Permission denied errors             | Ensure your user has                                                       |
| Canary steps not advancing           | Verify AnalysisTempl                                                       |
| Cannot find rollout in list          | Verify you're using                                                        |
| Promote not working                  | Check rollout status with `ops k8s                                         |
| JSON parsing errors in canary-steps  | Validate JSON                                                              |
| Rollout not starting                 | Check for image pull                                                       |

---

## See Also

- [Argo Rollouts Official Documentation](https://argoproj.github.io/argo-rollouts/)
- [Kubernetes Plugin Overview](../index.md)
- [Argo Workflows Integration](./argo-workflows.md)
- [Kubernetes Commands Reference](../commands/)
- [Progressive Delivery Patterns](https://argoproj.github.io/argo-rollouts/concepts/)
- [Analysis and Metrics](https://argoproj.github.io/argo-rollouts/analysis/)
