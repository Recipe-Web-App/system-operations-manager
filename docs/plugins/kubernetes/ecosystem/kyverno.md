# Kubernetes Plugin > Ecosystem > Kyverno

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
  - [What is Kyverno?](#what-is-kyverno)
  - [Why Use Kyverno?](#why-use-kyverno)
  - [Integration with K8s Plugin](#integration-with-k8s-plugin)
- [Prerequisites](#prerequisites)
  - [CRD Installation](#crd-installation)
  - [Operator Installation](#operator-installation)
  - [Version Requirements](#version-requirements)
- [Detection](#detection)
- [Configuration](#configuration)
  - [Plugin Configuration](#plugin-configuration)
  - [Namespace Configuration](#namespace-configuration)
- [Command Reference](#command-reference)
  - [Cluster Policies](#cluster-policies)
  - [Namespaced Policies](#namespaced-policies)
  - [Cluster Policy Reports](#cluster-policy-reports)
  - [Namespaced Policy Reports](#namespaced-policy-reports)
  - [Admission Controller Status](#admission-controller-status)
- [Integration Examples](#integration-examples)
  - [Enforce Resource Requirements](#enforce-resource-requirements)
  - [Image Registry Restrictions](#image-registry-restrictions)
  - [Label Enforcement](#label-enforcement)
  - [Multi-Policy Setup](#multi-policy-setup)
  - [Policy Validation](#policy-validation)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

### What is Kyverno?

Kyverno is a Kubernetes-native policy engine that enables you to validate, mutate, and generate Kubernetes resources. It
uses standard Kubernetes manifests (CustomResourceDefinitions) to define policies, making it accessible to users
familiar with Kubernetes YAML.

Key capabilities:

- **Validation** - Enforce resource policies at admission time
- **Mutation** - Automatically modify resources to meet policy requirements
- **Generation** - Create resources automatically based on policies
- **Background scanning** - Audit existing resources against policies
- **Policy exceptions** - Temporarily exclude resources from policies
- **Reporting** - Detailed policy compliance reports
- **Integration** - Works with container registries, webhooks, and CI/CD

### Why Use Kyverno?

1. **Security** - Enforce security policies across cluster
2. **Compliance** - Ensure resources meet compliance requirements
3. **Consistency** - Standardize resource configurations
4. **Prevention** - Block non-compliant resources from being deployed
5. **Automation** - Automatically apply required configurations
6. **Visibility** - Understand policy compliance status
7. **Kubernetes-native** - Use standard Kubernetes manifests

### Integration with K8s Plugin

These tools are CRD-based resources managed via Kubernetes CustomResourcesApi. The plugin provides convenient CLI
commands for:

- Listing and viewing ClusterPolicies and Policies
- Creating and managing policy definitions
- Validating policies before deployment
- Viewing policy reports and compliance status
- Checking admission controller health

---

## Prerequisites

### CRD Installation

Kyverno requires Custom Resource Definitions for:

- `ClusterPolicy` - Cluster-scoped policy definitions
- `Policy` - Namespace-scoped policy definitions
- `PolicyReport` - Namespace-scoped compliance reports
- `ClusterPolicyReport` - Cluster-scoped compliance reports
- `PolicyException` - Exception definitions for policy exclusions

CRDs are installed when you deploy the Kyverno operator.

### Operator Installation

Install Kyverno using Helm:

```bash
# Add Kyverno Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/

# Update Helm repositories
helm repo update

# Install Kyverno in kyverno namespace
helm install kyverno kyverno/kyverno \
  -n kyverno \
  --create-namespace \
  --set replicaCount=3 \
  --set installCRDs=true

# Verify installation
kubectl get pods -n kyverno
kubectl get crd | grep kyverno
```

### Version Requirements

| Kyverno Version | Kubernetes | Status        |
| --------------- | ---------- | ------------- |
| 1.9+            | 1.24+      | Full support  |
| 1.8             | 1.22+      | Maintenance   |
| < 1.8           | Legacy     | Not supported |

---

## Detection

The plugin automatically detects Kyverno availability by:

1. **Checking for CRDs** - Looks for `clusterpolicy.kyverno.io` CRD
2. **Verifying controller pods** - Checks if Kyverno controller pods are running in `kyverno` namespace
3. **API accessibility** - Confirms API server can list ClusterPolicy resources
4. **Webhook availability** - Verifies admission webhook is operational

Detection occurs when you first run a Kyverno-related command. If Kyverno is not detected, you'll receive a clear error
message with installation instructions.

---

## Configuration

### Plugin Configuration

Add Kyverno configuration to your ops config file (`~/.config/ops/config.yaml`):

```yaml
plugins:
  kubernetes:
    kyverno:
      # Enable/disable Kyverno commands (default: true if Kyverno is installed)
      enabled: true
      # Default namespace for policy operations
      default_namespace: "default"
      # Timeout for policy validation (seconds)
      validation_timeout: 30
      # Number of retries for failed operations
      retries: 3
      # Enable background scanning (requires time to complete)
      background_scan_enabled: true
      # Validation failure action (default: audit)
      failure_action: "audit"
```

### Namespace Configuration

Configure which namespaces have Policies:

```bash
# Default behavior - use active namespace or 'default'
ops k8s policies list

# Specify namespace
ops k8s policies list -n production

# List cluster-wide policies
ops k8s cluster-policies list

# List policy reports
ops k8s policy-reports list -n production
```

---

## Command Reference

### Cluster Policies

ClusterPolicies are cluster-scoped policy definitions that apply to all namespaces.

#### `ops k8s cluster-policies list`

List all ClusterPolicies.

```bash
ops k8s cluster-policies list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option       | Short | Type   | Default | Description                      |
| ------------ | ----- | ------ | ------- | -------------------------------- |
| `--selector` | `-l`  | string | -       | Label selector                   |
| `--output`   | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List all ClusterPolicies
ops k8s cluster-policies list

# Filter by label
ops k8s cluster-policies list -l policy=security

# JSON output
ops k8s cluster-policies list -o json
```

**Example Output:**

```text
Cluster Policies
Name                 Action   Background  Rules  Ready  Age
require-labels       Audit    true        2      true   7d
require-limits       Enforce  true        1      true   5d
restrict-images      Enforce  true        1      false  2h
restrict-wildcards   Audit    true        3      true   3d
```

#### `ops k8s cluster-policies get`

Get details of a specific ClusterPolicy.

```bash
ops k8s cluster-policies get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| NAME     | yes      | Name of the ClusterPolicy |

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get ClusterPolicy details
ops k8s cluster-policies get require-labels

# View full YAML
ops k8s cluster-policies get require-labels -o yaml
```

**Example Output (YAML):**

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: audit
  background: true
  rules:
    - name: check-labels
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Pod must have app and version labels"
        pattern:
          metadata:
            labels:
              app: "?*"
              version: "?*"
status:
  conditions:
    - type: Ready
      status: "True"
      reason: "Initialized"
      message: "Policy has been initialized"
```

#### `ops k8s cluster-policies create`

Create a new ClusterPolicy.

```bash
ops k8s cluster-policies create NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name for the ClusterPolicy |

**Options:**

| Option            | Short | Type   | Default | Description                         |
| ----------------- | ----- | ------ | ------- | ----------------------------------- |
| `--rule`          | -     | string | -       | Policy rule as JSON (repeatable)    |
| `--background`    | -     | bool   | true    | Enable background scanning          |
| `--no-background` | -     | bool   | -       | Disable background scanning         |
| `--action`        | -     | string | Audit   | Validation action: Audit or Enforce |
| `--label`         | `-l`  | string | -       | Labels (key=value, repeatable)      |
| `--output`        | `-o`  | string | table   | Output format: table, json, yaml    |

**Example:**

```bash
# Create ClusterPolicy enforcing labels
ops k8s cluster-policies create require-app-label \
  --action Enforce \
  --rule '{"name":"check-app-label","match":{"any":[{"resources":{"kinds":["Deployment","StatefulSet","DaemonSet"]}}]},"validate":{"message":"Deployments must have app label","pattern":{"metadata":{"labels":{"app":"?*"}}}}}'

# Create policy with multiple rules
ops k8s cluster-policies create security-baseline \
  --action Audit \
  --rule '{"name":"disallow-privileged","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Privileged pods not allowed","pattern":{"spec":{"containers":[{"securityContext":{"privileged":false}}]}}}}' \
  --rule '{"name":"disallow-root","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Must run as non-root","pattern":{"spec":{"securityContext":{"runAsNonRoot":true}}}}}'

# Create with background scanning disabled (admission-only)
ops k8s cluster-policies create admission-only-policy \
  --no-background \
  --action Enforce \
  --label component=security
```

**Rule JSON Format:**

Policy rules follow standard Kyverno rule structure:

```json
{
  "name": "rule-name",
  "match": {
    "any": [
      {
        "resources": {
          "kinds": ["Pod", "Deployment"],
          "selector": {
            "matchLabels": {
              "enforce": "policy"
            }
          }
        }
      }
    ]
  },
  "validate": {
    "message": "Policy validation message",
    "pattern": {
      "metadata": {
        "labels": {
          "app": "?*"
        }
      }
    }
  }
}
```

#### `ops k8s cluster-policies delete`

Delete a ClusterPolicy.

```bash
ops k8s cluster-policies delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                         |
| -------- | -------- | ----------------------------------- |
| NAME     | yes      | Name of the ClusterPolicy to delete |

**Options:**

| Option    | Short | Type | Default | Description              |
| --------- | ----- | ---- | ------- | ------------------------ |
| `--force` | `-f`  | bool | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s cluster-policies delete require-labels

# Delete without confirmation
ops k8s cluster-policies delete require-labels --force
```

---

### Namespaced Policies

Policies are namespace-scoped policy definitions that apply within a specific namespace.

#### `ops k8s policies list`

List Policies in a namespace.

```bash
ops k8s policies list [OPTIONS]
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
# List Policies in default namespace
ops k8s policies list

# List in production namespace
ops k8s policies list -n production

# Filter by label
ops k8s policies list -l component=api

# JSON output
ops k8s policies list -o json
```

**Example Output:**

```text
Policies
Name                Namespace    Action   Background  Rules  Ready  Age
restrict-registries production    Enforce  true        1      true   7d
require-requests    staging      Audit    true        2      true   5d
security-policy     production    Enforce  true        3      true   3d
```

#### `ops k8s policies get`

Get details of a specific Policy.

```bash
ops k8s policies get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description        |
| -------- | -------- | ------------------ |
| NAME     | yes      | Name of the Policy |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get Policy details
ops k8s policies get restrict-registries -n production

# View full YAML
ops k8s policies get restrict-registries -n production -o yaml
```

#### `ops k8s policies create`

Create a new Policy (namespace-scoped).

```bash
ops k8s policies create NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description         |
| -------- | -------- | ------------------- |
| NAME     | yes      | Name for the Policy |

**Options:**

| Option            | Short | Type   | Default | Description                         |
| ----------------- | ----- | ------ | ------- | ----------------------------------- |
| `--namespace`     | `-n`  | string | default | Kubernetes namespace                |
| `--rule`          | -     | string | -       | Policy rule as JSON (repeatable)    |
| `--background`    | -     | bool   | true    | Enable background scanning          |
| `--no-background` | -     | bool   | -       | Disable background scanning         |
| `--action`        | -     | string | Audit   | Validation action: Audit or Enforce |
| `--label`         | `-l`  | string | -       | Labels (key=value, repeatable)      |
| `--output`        | `-o`  | string | table   | Output format: table, json, yaml    |

**Example:**

```bash
# Create namespace-scoped policy for production
ops k8s policies create prod-image-policy \
  -n production \
  --action Enforce \
  --rule '{"name":"restrict-images","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Only myregistry.io images allowed","pattern":{"spec":{"containers":[{"image":"myregistry.io/*"}]}}}}'

# Create with multiple rules in staging
ops k8s policies create staging-security \
  -n staging \
  --action Audit \
  --rule '{"name":"require-requests","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"CPU and memory requests required","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"}}}]}}}}' \
  --rule '{"name":"require-limits","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"CPU and memory limits required","pattern":{"spec":{"containers":[{"resources":{"limits":{"cpu":"?*","memory":"?*"}}}]}}}}'
```

#### `ops k8s policies delete`

Delete a Policy.

```bash
ops k8s policies delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                  |
| -------- | -------- | ---------------------------- |
| NAME     | yes      | Name of the Policy to delete |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s policies delete prod-image-policy -n production

# Delete without confirmation
ops k8s policies delete prod-image-policy -n production --force
```

#### `ops k8s policies validate`

Validate a policy YAML file before deployment.

```bash
ops k8s policies validate --file FILE [OPTIONS]
```

**Arguments:** None

**Options:**

| Option     | Short | Type   | Default  | Description                              |
| ---------- | ----- | ------ | -------- | ---------------------------------------- |
| `--file`   | `-f`  | string | required | Path to YAML file with policy definition |
| `--output` | `-o`  | string | table    | Output format: table, json, yaml         |

**Example:**

```bash
# Validate a policy file
ops k8s policies validate --file my-policy.yaml

# Validate and output as JSON
ops k8s policies validate -f policies/security.yaml -o json

# Validate before committing to Git
ops k8s policies validate -f ./kyverno/policies/require-labels.yaml
```

**Example YAML file (my-policy.yaml):**

```yaml
apiVersion: kyverno.io/v1
kind: Policy
metadata:
  name: require-labels
spec:
  validationFailureAction: audit
  background: true
  rules:
    - name: check-labels
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Pod must have app label"
        pattern:
          metadata:
            labels:
              app: "?*"
```

**Example Output:**

```text
Policy is valid
Name: require-labels
Kind: Policy
Rules: 1
Failure Action: audit
Background: true
```

---

### Cluster Policy Reports

ClusterPolicyReports are cluster-scoped reports showing policy compliance.

#### `ops k8s cluster-policy-reports list`

List all ClusterPolicyReports.

```bash
ops k8s cluster-policy-reports list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List all ClusterPolicyReports
ops k8s cluster-policy-reports list

# JSON output
ops k8s cluster-policy-reports list -o json
```

**Example Output:**

```text
Cluster Policy Reports
Name                                    Pass   Fail   Warn   Error  Skip
cluster-require-labels                  1200   45     0      0      10
cluster-require-limits                  1100   120    5      2      15
cluster-restrict-images                 900    250    20     5      30
cluster-disallow-privileged             1150   80     0      0      20
```

#### `ops k8s cluster-policy-reports get`

Get details of a specific ClusterPolicyReport.

```bash
ops k8s cluster-policy-reports get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                     |
| -------- | -------- | ------------------------------- |
| NAME     | yes      | Name of the ClusterPolicyReport |

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get ClusterPolicyReport details
ops k8s cluster-policy-reports get cluster-require-labels

# View full YAML with individual rule results
ops k8s cluster-policy-reports get cluster-require-labels -o yaml
```

**Example Output:**

```text
ClusterPolicyReport: cluster-require-labels
Total Resources: 1255
Results Summary:
  Pass: 1200
  Fail: 45
  Warn: 0
  Error: 0
  Skip: 10

Failed Resources:
  - Kind: Pod
    Name: web-app-123
    Namespace: production
    Rule: check-labels
    Message: "Pod must have app label"
```

---

### Namespaced Policy Reports

PolicyReports are namespace-scoped reports showing policy compliance within a namespace.

#### `ops k8s policy-reports list`

List PolicyReports in a namespace.

```bash
ops k8s policy-reports list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List PolicyReports in default namespace
ops k8s policy-reports list

# List in production namespace
ops k8s policy-reports list -n production

# JSON output
ops k8s policy-reports list -o json
```

**Example Output:**

```text
Policy Reports
Name                         Namespace    Pass  Fail  Warn  Error  Skip
pod-require-labels          default      50    5     0     0      2
deploy-require-limits       default      20    3     1     0      1
statefulset-restrict-images default      15    0     0     0      0
```

#### `ops k8s policy-reports get`

Get details of a specific PolicyReport.

```bash
ops k8s policy-reports get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description              |
| -------- | -------- | ------------------------ |
| NAME     | yes      | Name of the PolicyReport |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get PolicyReport details
ops k8s policy-reports get pod-require-labels -n production

# View full YAML
ops k8s policy-reports get pod-require-labels -n production -o yaml
```

**Example Output:**

```text
PolicyReport: pod-require-labels
Namespace: production
Total Resources: 58
Results Summary:
  Pass: 50
  Fail: 5
  Warn: 0
  Error: 0
  Skip: 3

Failed Resources:
  - Kind: Pod
    Name: legacy-app-789
    Rule: check-labels
    Message: "Pod must have app label"

  - Kind: Pod
    Name: test-pod-456
    Rule: check-labels
    Message: "Pod must have app label"
```

---

### Admission Controller Status

#### `ops k8s admission status`

Show Kyverno admission controller health and status.

```bash
ops k8s admission status [OPTIONS]
```

**Arguments:** None

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Check admission controller status
ops k8s admission status

# JSON output
ops k8s admission status -o json
```

**Example Output:**

```text
Kyverno Admission Controller
Namespace: kyverno
Status: Running
Pod Count: 3
Ready Replicas: 3/3

Pods:
Name                                 Ready  Status    Restarts  Age
kyverno-7c5f8b9c4d-abc12            1/1    Running   0         7d
kyverno-7c5f8b9c4d-def34            1/1    Running   0         7d
kyverno-7c5f8b9c4d-ghi56            1/1    Running   0         7d

Webhook Status:
- ValidatingWebhookConfiguration: kyverno-resource-validating-webhook-cfg
  Endpoints: 3 ready

- MutatingWebhookConfiguration: kyverno-resource-mutating-webhook-cfg
  Endpoints: 3 ready

Policies:
- ClusterPolicies: 8
- Namespaced Policies: 12
- Total Rules: 32
```

---

## Integration Examples

### Enforce Resource Requirements

Enforce CPU and memory requests/limits on all pods.

**Create ClusterPolicy:**

```bash
ops k8s cluster-policies create require-resources \
  --action Enforce \
  --rule '{"name":"require-requests","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"CPU and memory requests are required","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"}}}]}}}}' \
  --rule '{"name":"require-limits","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"CPU and memory limits are required","pattern":{"spec":{"containers":[{"resources":{"limits":{"cpu":"?*","memory":"?*"}}}]}}}}'
```

**Effect:**

- Pods without CPU/memory requests and limits are rejected
- Deployment attempts fail with clear error message
- Background scanning reports non-compliant existing pods

**Monitor compliance:**

```bash
# View policy status
ops k8s cluster-policies get require-resources

# Check policy report
ops k8s cluster-policy-reports get cluster-require-resources
```

### Image Registry Restrictions

Restrict pods to only use images from approved registries.

**Create ClusterPolicy for production:**

```bash
ops k8s cluster-policies create restrict-image-registries \
  --action Enforce \
  --rule '{"name":"validate-registries","match":{"any":[{"resources":{"kinds":["Pod"],"namespaceSelector":{"matchLabels":{"environment":"production"}}}}]},"validate":{"message":"Only images from myregistry.io, gcr.io/myproject, and ghcr.io/myorg are allowed","pattern":{"spec":{"containers":[{"image":"myregistry.io/* | gcr.io/myproject/* | ghcr.io/myorg/*"}],"initContainers":[{"image":"myregistry.io/* | gcr.io/myproject/* | ghcr.io/myorg/*"}]}}}}'
```

**Create namespace-scoped policy for dev:**

```bash
ops k8s policies create dev-image-registries \
  -n development \
  --action Audit \
  --rule '{"name":"validate-registries","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Recommend using approved registries: docker.io, gcr.io, ghcr.io","pattern":{"spec":{"containers":[{"image":"docker.io/* | gcr.io/* | ghcr.io/*"}]}}}}'
```

### Label Enforcement

Enforce consistent labeling across resources.

**Create ClusterPolicy:**

```bash
ops k8s cluster-policies create require-labels \
  --action Enforce \
  --rule '{"name":"check-app-label","match":{"any":[{"resources":{"kinds":["Deployment","StatefulSet","DaemonSet","Job"]}}]},"validate":{"message":"Resources must have app and version labels","pattern":{"metadata":{"labels":{"app":"?*","version":"?*"}}}}}' \
  --rule '{"name":"check-owner-label","match":{"any":[{"resources":{"kinds":["Deployment","StatefulSet","DaemonSet"]}}]},"validate":{"message":"Resources must have owner label","pattern":{"metadata":{"labels":{"owner":"?*"}}}}}'
```

**Effect:**

- All Deployments must have `app`, `version`, and `owner` labels
- Existing resources without labels reported in policy reports
- New resources failing validation are rejected

### Multi-Policy Setup

Implement layered policies across environments.

**Cluster-wide baseline (all environments):**

```bash
# Security baseline
ops k8s cluster-policies create security-baseline \
  --action Audit \
  --rule '{"name":"no-privileged-pods","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Privileged pods not recommended","pattern":{"spec":{"containers":[{"securityContext":{"privileged":false}}]}}}}' \
  --rule '{"name":"no-root-containers","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Containers should run as non-root","pattern":{"spec":{"securityContext":{"runAsNonRoot":true}}}}}}'

# Resource baseline
ops k8s cluster-policies create resource-baseline \
  --action Audit \
  --rule '{"name":"require-requests","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Resource requests are recommended","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"}}}]}}}}'
```

**Environment-specific policies:**

```bash
# Production - strict enforcement
ops k8s policies create prod-strict \
  -n production \
  --action Enforce \
  --label environment=production \
  --rule '{"name":"require-resources","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Resource requests and limits required","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"},"limits":{"cpu":"?*","memory":"?*"}}}]}}}}'

# Staging - warnings only
ops k8s policies create staging-audit \
  -n staging \
  --action Audit \
  --label environment=staging \
  --rule '{"name":"recommend-resources","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Resource requests and limits recommended","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"},"limits":{"cpu":"?*","memory":"?*"}}}]}}}}'

# Development - informational only
ops k8s policies create dev-informational \
  -n development \
  --action Audit \
  --no-background \
  --label environment=development \
  --rule '{"name":"informational-resources","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Consider setting resource requests and limits","pattern":{"spec":{"containers":[{"resources":{"requests":{"cpu":"?*","memory":"?*"}}}]}}}}'
```

### Policy Validation

Validate policies before deploying to ensure they work correctly.

**Create policy file:**

```bash
cat > security-policy.yaml <<EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: security-baseline
spec:
  validationFailureAction: enforce
  background: true
  rules:
  - name: disallow-privileged-pods
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Privileged pods not allowed"
      pattern:
        spec:
          containers:
          - securityContext:
              privileged: false
  - name: disallow-root-user
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Must run as non-root user"
      pattern:
        spec:
          securityContext:
            runAsNonRoot: true
EOF
```

**Validate before applying:**

```bash
# Validate policy file
ops k8s policies validate -f security-policy.yaml

# Apply after validation
kubectl apply -f security-policy.yaml

# Verify deployment
ops k8s cluster-policies get security-baseline
```

---

## Troubleshooting

| Issue                                   | Symptoms                                        | Solution             |
| --------------------------------------- | ----------------------------------------------- | -------------------- |
| **Kyverno not detected**                | "Kyverno not                                    | Install Kyverno:     |
| **Webhook not working**                 | Policies created but not enforcing; pods bypass | Check webhook pods   |
| **Policies not ready**                  | ClusterPolicy shows                             | Check policy syntax; |
| **False positives in validation**       | Valid pods rejected; pattern                    | Review policy rule   |
| **Performance impact**                  | Cluster API slow; pod creation                  | Reduce number of     |
| **Policy reports empty**                | Policies ready but no                           | Enable background    |
| **Permission denied creating policies** | "forbidden" error when                          | Verify RBAC permissi |
| **Invalid policy YAML**                 | "Validation failed"                             | Use `ops k8s policie |
| **Webhook timeout errors**              | "webhook timeout" in                            | Increase webhook     |
| **Policy not being applied**            | Policy exists but not enforcing; pods           | Check policy matches |
| **Memory/CPU usage spike**              | High resource usage on                          | Disable background   |
| \*\*Admission webhook service           | "no endpoints available" error                  | Ensure kyverno pods  |

---

## See Also

- **[Kyverno Documentation](https://kyverno.io/)** - Official Kyverno docs
- **[Kyverno Policies](https://kyverno.io/docs/writing-policies/)** - Writing policy rules
- **[Kyverno CLI](https://kyverno.io/docs/kyverno-cli/)** - CLI documentation
- **[Policy Examples](https://kyverno.io/docs/writing-policies/examples/)** - Common policy patterns
- **[Background Scanning](https://kyverno.io/docs/writing-policies/background-scans/)** - Audit existing resources
- **[Policy Reports](https://kyverno.io/docs/policy-reports/)** - Compliance reporting
- **[Policy Exceptions](https://kyverno.io/docs/writing-policies/exceptions/)** - Excluding resources from policies
- **[Kubernetes Plugin Index](../index.md)** - Back to main K8s documentation
- **[Flux Integration](./flux.md)** - GitOps with policy enforcement
- **[RBAC Commands](../commands/rbac.md)** - Permission management
- **[Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)** - Official K8s security docs
