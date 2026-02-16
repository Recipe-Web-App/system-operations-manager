# Kubernetes Plugin > Commands > Manifests

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Common Options](#common-options)
3. [Apply Command](#apply-command)
4. [Diff Command](#diff-command)
5. [Validate Command](#validate-command)
6. [Example Workflows](#example-workflows)
7. [Troubleshooting](#troubleshooting)
8. [See Also](#see-also)

---

## Overview

The manifests command group provides powerful tools for managing Kubernetes YAML manifests. These commands allow you to
validate manifests locally without cluster access, compare local manifests against live cluster state, and apply
manifests with client-side or server-side validation.

Key capabilities:

- **Validation**: Client-side schema validation before applying to cluster
- **Diff**: See exactly what changes will be made before applying
- **Apply**: Deploy manifests with optional dry-run modes
- **Batch Operations**: Process single files or entire directories of manifests
- **Multiple Output Formats**: Table, JSON, or YAML output for automation

---

## Common Options

Options shared across all manifest commands:

| Option        | Short | Type    | Default                     | Description                         |
| ------------- | ----- | ------- | --------------------------- | ----------------------------------- |
| `--namespace` | `-n`  | string  | config default or 'default' | Kubernetes namespace for resources  |
| `--output`    | `-o`  | string  | table                       | Output format: table, json, or yaml |
| `--dry-run`   |       | boolean | false                       | Client-side dry run (no API calls)  |

**Important**: The `--namespace` option applies to all resources in the manifest that don't already specify a namespace
in their metadata. Resources with explicit namespace declarations are not affected.

---

## Apply Command

### `ops k8s manifests apply`

Deploy or update Kubernetes resources from YAML manifests.

The apply command validates manifests locally before attempting to apply them to the cluster. It supports both
client-side and server-side dry runs for safe testing before making actual changes.

**Syntax:**

```bash
ops k8s manifests apply <path> [OPTIONS]
```

**Arguments:**

| Argument | Required | Type | Description                                                                |
| -------- | -------- | ---- | -------------------------------------------------------------------------- |
| `path`   | Yes      | path | Path to a YAML file or directory of manifests. Must exist and be readable. |

**Options:**

| Option             | Short | Type    | Default        | Description                                            |
| ------------------ | ----- | ------- | -------------- | ------------------------------------------------------ |
| `--namespace`      | `-n`  | string  | config default | Kubernetes namespace for                               |
| `--dry-run`        |       | boolean | false          | Client-side dry run: validates and shows what would be |
| `--server-dry-run` |       | boolean | false          | Server-side dry run: validates on the Kubernetes API   |
| `--force`          | `-f`  | boolean | false          | Skip validation                                        |
| `--output`         | `-o`  | string  | table          | Output format:                                         |

**Behavior:**

1. Loads all manifests from the specified path (recurses into directories)
2. Validates each manifest (requires apiVersion, kind, metadata, metadata.name)
3. If validation fails and `--force` is not set, stops and reports errors
4. For `--dry-run`: simulates the apply operation locally and prints results without API calls
5. For `--server-dry-run`: sends validation request to Kubernetes server without creating resources
6. For normal apply: creates or updates resources on the cluster
7. Returns exit code 1 if any resource fails to apply

**Examples:**

Apply a single deployment file to the current namespace:

```bash
ops k8s manifests apply deployment.yaml
```

Apply all manifests in a directory to the production namespace:

```bash
ops k8s manifests apply ./manifests/ -n production
```

Perform a client-side dry run to see what would be applied:

```bash
ops k8s manifests apply app.yaml --dry-run
```

Perform a server-side dry run (validates on the API server):

```bash
ops k8s manifests apply app.yaml --server-dry-run
```

Apply with force flag to skip validation errors:

```bash
ops k8s manifests apply app.yaml --force
```

Get JSON output for parsing by other tools:

```bash
ops k8s manifests apply app.yaml --output json
```

**Example Output (table format):**

```text
Apply Results
Resource                      Namespace      Action    Status    Message
test-deployment               default        created   OK
test-service                  default        updated   OK
test-configmap                default        created   OK

Total: 3 resource(s)
```

**Example Output (JSON format):**

```json
{
  "results": [
    {
      "resource": "Deployment/test-deployment",
      "namespace": "default",
      "action": "created",
      "success": true,
      "message": ""
    },
    {
      "resource": "Service/test-service",
      "namespace": "default",
      "action": "updated",
      "success": true,
      "message": ""
    }
  ],
  "total": 2
}
```

**Notes:**

- When applying a directory, manifests are processed in order they are discovered by the filesystem
- The `--force` flag skips validation but does not skip API errors
- Both `--dry-run` and `--server-dry-run` can be used together; server-side takes precedence
- Manifests with explicit namespace declarations override the `--namespace` option
- The command respects your kubeconfig context and current cluster connection

---

## Diff Command

### `ops k8s manifests diff`

Compare local manifests against live cluster state and display differences.

The diff command fetches each resource from the cluster and produces a unified diff showing what changes would occur if
the manifest were applied. This helps verify your changes before applying.

**Syntax:**

```bash
ops k8s manifests diff <path> [OPTIONS]
```

**Arguments:**

| Argument | Required | Type | Description                                                                |
| -------- | -------- | ---- | -------------------------------------------------------------------------- |
| `path`   | Yes      | path | Path to a YAML file or directory of manifests. Must exist and be readable. |

**Options:**

| Option        | Short | Type   | Default        | Description                                                   |
| ------------- | ----- | ------ | -------------- | ------------------------------------------------------------- |
| `--namespace` | `-n`  | string | config default | Kubernetes namespace for resources without explicit namespace |
| `--output`    | `-o`  | string | table          | Output format: table, json, or yaml                           |

**Behavior:**

1. Loads all manifests from the specified path
2. For each manifest, attempts to fetch the current resource from the cluster
3. Compares the local manifest with the live resource
4. Displays a summary table and detailed diffs for changed resources
5. Resources not found on the cluster are marked as "New"
6. Resources identical to local manifests are marked as "Identical"
7. Changed resources show inline unified diffs with color-coded additions (green) and deletions (red)

**Examples:**

Show differences for a deployment:

```bash
ops k8s manifests diff deployment.yaml
```

Compare all manifests in a directory against the production cluster:

```bash
ops k8s manifests diff ./manifests/ -n production
```

Output differences in JSON format for programmatic processing:

```bash
ops k8s manifests diff app.yaml --output json
```

**Example Output (table format):**

```text
Diff Summary
Resource                    Namespace    On Cluster    Status
deployment/my-app           production   Yes           Changed
service/my-app              production   Yes           Identical
configmap/app-config        production   No            New

deployment/my-app:
@@ -8,7 +8,7 @@
 spec:
   replicas: 2
   selector:
-    matchLabels:
+    matchLabels:
       app: my-app
       version: v1.0
```

**Example Output (JSON format):**

```json
{
  "results": [
    {
      "resource": "Deployment/my-app",
      "namespace": "production",
      "exists_on_cluster": true,
      "identical": false,
      "diff": "@@ -8,7 +8,7 @@\n spec:\n   replicas: 2\n..."
    },
    {
      "resource": "Service/my-app",
      "namespace": "production",
      "exists_on_cluster": true,
      "identical": true,
      "diff": null
    }
  ],
  "total": 2
}
```

**Notes:**

- Requires cluster connectivity to fetch current resources
- Resources not found on the cluster show as "New" with no comparison data
- Diffs use unified diff format (similar to `git diff`)
- The command respects label selectors and field selectors for advanced filtering
- Inline diffs for large resources may be truncated for readability

---

## Validate Command

### `ops k8s manifests validate`

Validate YAML manifests client-side without connecting to a cluster.

The validate command performs schema validation on manifest files to catch errors before attempting to apply them. This
is useful in CI/CD pipelines or for pre-deployment checks.

**Syntax:**

```bash
ops k8s manifests validate <path> [OPTIONS]
```

**Arguments:**

| Argument | Required | Type | Description                                                                |
| -------- | -------- | ---- | -------------------------------------------------------------------------- |
| `path`   | Yes      | path | Path to a YAML file or directory of manifests. Must exist and be readable. |

**Options:**

| Option     | Short | Type   | Default | Description                         |
| ---------- | ----- | ------ | ------- | ----------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, or yaml |

**Validation Checks:**

The validator ensures each manifest has these required fields:

- `apiVersion`: Kubernetes API version (e.g., "apps/v1", "v1")
- `kind`: Resource type (e.g., "Deployment", "Service", "Pod")
- `metadata`: Object containing resource metadata
- `metadata.name`: Unique name for the resource

Additional validation may include:

- Proper YAML formatting
- Valid field types and values
- Resource-specific schema constraints

**Behavior:**

1. Loads all manifests from the specified path (recurses into directories)
2. Validates each manifest against the required schema
3. Collects validation errors for all manifests
4. Prints results in the requested format
5. Returns exit code 0 if all valid, exit code 1 if any invalid

**Examples:**

Validate a single manifest file:

```bash
ops k8s manifests validate deployment.yaml
```

Validate all manifests in a directory:

```bash
ops k8s manifests validate ./manifests/
```

Validate in JSON format for CI/CD integration:

```bash
ops k8s manifests validate app.yaml --output json
```

Validate and check exit code:

```bash
ops k8s manifests validate *.yaml && echo "All valid" || echo "Validation failed"
```

**Example Output (table format - all valid):**

```text
Validation Results
Resource                      File                       Valid    Errors
Deployment/api-server         manifests/deployment.yaml  Yes
ConfigMap/app-config          manifests/configmap.yaml   Yes
Service/api                   manifests/service.yaml     Yes

All 3 manifest(s) valid
```

**Example Output (table format - with errors):**

```text
Validation Results
Resource              File                      Valid    Errors
Deployment/web        manifests/bad-deploy.yaml No       Missing required field: metadata.name
Pod/broken            manifests/broken.yaml     No       Invalid apiVersion: v1beta1; Unknown kind: Podd

2 manifest(s) invalid
```

**Example Output (JSON format):**

```json
{
  "results": [
    {
      "resource": "Deployment/api-server",
      "file": "manifests/deployment.yaml",
      "valid": true,
      "errors": []
    },
    {
      "resource": "Pod/broken",
      "file": "manifests/broken.yaml",
      "valid": false,
      "errors": ["Invalid apiVersion: v1beta1", "Unknown kind: Podd"]
    }
  ],
  "total": 2
}
```

**Notes:**

- Validation does not require cluster connectivity
- Can be used in offline environments or CI/CD pipelines
- Process returns non-zero exit code if any manifests are invalid
- Validate frequently before applying to catch errors early
- Server-side validation may catch additional issues the client-side validator misses

---

## Example Workflows

### Safe Deployment Workflow

Before applying manifests to a production cluster:

```bash
# 1. Validate locally (no cluster needed)
ops k8s manifests validate ./manifests/

# 2. Perform client-side dry run to see what would happen
ops k8s manifests apply ./manifests/ -n production --dry-run

# 3. Perform server-side dry run (validates against actual API server)
ops k8s manifests apply ./manifests/ -n production --server-dry-run

# 4. Check differences against live cluster
ops k8s manifests diff ./manifests/ -n production

# 5. Apply the changes
ops k8s manifests apply ./manifests/ -n production
```

### CI/CD Pipeline Integration

In a GitOps or CI/CD pipeline:

```bash
# Validate manifest syntax
ops k8s manifests validate ./k8s/ --output json > validation-results.json

# Check exit code
if [ $? -eq 0 ]; then
  echo "Validation passed"

  # Apply to cluster
  ops k8s manifests apply ./k8s/ -n production --output json > apply-results.json
else
  echo "Validation failed, aborting deployment"
  exit 1
fi
```

### Environment-Specific Deployment

Deploy the same manifests to different environments:

```bash
# Deploy to staging
ops k8s manifests apply ./manifests/ -n staging

# Deploy to production after manual approval
ops k8s manifests apply ./manifests/ -n production
```

### Checking Changes Before Merge

In a code review workflow:

```bash
# Branch with manifest changes
git checkout feature/new-config

# Validate changes locally
ops k8s manifests validate ./k8s/

# Show what will change
ops k8s manifests diff ./k8s/ -n production --output json

# If OK, approve and merge
# On main branch, apply the changes
ops k8s manifests apply ./k8s/ -n production
```

---

## Troubleshooting

| Issue                                  | Cause                                           | Solution                  |
| -------------------------------------- | ----------------------------------------------- | ------------------------- |
| "Path not found" error                 | File or directo                                 | Check the path is         |
| "No manifests found"                   | Directory is empty                              | Ensure directory          |
| Validation                             | Manifest missing                                | Add missing fields to the |
| Validation fails: "Unknown kind"       | Typo in the `kind` field or using               | Check spelling and        |
| "Cannot connect to Kubernetes cluster" | kubeconfig is invalid or                        | Check kubeconfig:         |
| Diff shows no output                   | Resources don't                                 | Resources marked as       |
| Timeout during apply                   | Large number of resources                       | Increase timeout          |
| "Permission denied" on apply           | User lacks RBAC                                 | Check RBAC permissio      |
| Changes appear different than expected | Manifest using namespace override with explicit | Remove redundant          |

---

## See Also

- [Kubernetes Plugin Index](../index.md)
- [Streaming Commands](streaming.md) - Logs, exec, port-forward
- [Optimization Commands](optimization.md) - Resource analysis and recommendations
- [Workloads Commands](workloads.md) - Pod, Deployment, StatefulSet management
- [Examples and Use Cases](../examples.md) - Complete workflow examples
- [TUI Overview](../tui.md) - Terminal user interface for Kubernetes management
