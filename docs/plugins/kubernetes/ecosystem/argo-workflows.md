# Kubernetes Plugin > Ecosystem > Argo Workflows

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [Workflows Commands](#workflows-commands)
  - [Workflow Templates](#workflow-templates)
  - [Cron Workflows](#cron-workflows)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Argo Workflows is a container-native workflow engine for Kubernetes that uses containers as the main compute resource
unit. It allows you to define complex computational and data processing workflows as a sequence of tasks, with built-in
support for parallelism, conditional logic, loops, and sophisticated scheduling.

The Kubernetes plugin provides comprehensive CLI integration with Argo Workflows through the `workflows` command family.
This integration enables you to:

- Create and manage Workflow resources with dynamic arguments
- Define reusable WorkflowTemplates for standardized processes
- Schedule recurring workflows with CronWorkflows
- Monitor workflow execution and collect artifacts
- View workflow logs and handle workflow lifecycle operations

Argo Workflows is built on Kubernetes CustomResourceDefinitions (CRDs), enabling full integration with the Kubernetes
API. The plugin detects Argo Workflows availability by checking for the presence of the Workflow CRD in your cluster.

## Prerequisites

To use the Argo Workflows integration, you need:

1. **Argo Workflows Controller**: Install the Argo Workflows controller in your cluster

   ```bash
   kubectl create namespace argo
   kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/latest/download/install.yaml
   ```

2. **Kubernetes Access**: Valid kubeconfig with permissions to create and manage Workflow, WorkflowTemplate, and
   CronWorkflow resources

3. **CRDs**: Argo Workflows CRDs must be installed in your cluster (automatically installed with the controller)

4. **Artifact Storage** (optional): Configure S3, MinIO, or other artifact storage for workflow outputs

5. **Version Requirements**:
   - Argo Workflows: 3.0 or later
   - Kubernetes: 1.16 or later
   - kubectl: 1.16 or later

## Detection

The plugin automatically detects whether Argo Workflows is available in your cluster by checking for the presence of the
`Workflow` CRD. Verify detection with:

```bash
ops k8s workflows list
```

If Argo Workflows is not installed, you'll receive a clear error message indicating the Workflow CRD is not found.

## Configuration

Argo Workflows integration uses the standard Kubernetes plugin configuration. No additional ecosystem-specific
configuration is required beyond standard Kubernetes access settings.

Optional configuration for artifact storage and workflow defaults:

```yaml
# In your ops config
kubernetes:
  default_namespace: workflows
  argo_workflows:
    artifact_repository: s3
    artifact_bucket: my-workflows-artifacts
```

---

## Command Reference

### Workflows Commands

#### `ops k8s workflows list`

List all Argo Workflows in a namespace.

```bash
ops k8s workflows list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                                                          |
| ------------- | ----- | ------ | --------- | -------------------------------------------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace to query                                        |
| `--selector`  | `-l`  | string | None      | Label selector filter (e.g., 'app=data-processing')                  |
| `--phase`     |       | string | None      | Filter by workflow phase: Pending, Running, Succeeded, Failed, Error |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml                                  |

**Example Output:**

```text
Workflows

NAME                        NAMESPACE     PHASE       PROGRESS  DURATION   ENTRYPOINT        AGE
data-pipeline-abc123        workflows     Succeeded   15/15     4m 23s     main              2h 15m
email-batch-job-2024-02-16  workflows     Running     7/12      1m 45s     send-emails       1m 45s
ci-build-feature-pr-1234    ci            Succeeded   8/8       2m 10s     build-and-test    45m
data-cleanup-xyz789         workflows     Failed      5/10      3m 15s     cleanup-old-data  2h
```

**Examples:**

```bash
# List all workflows in default namespace
ops k8s workflows list

# List in specific namespace
ops k8s workflows list -n workflows

# Filter by running status
ops k8s workflows list --phase Running

# Filter by label
ops k8s workflows list -l app=data-processing -n workflows

# Get JSON output for integration
ops k8s workflows list -o json

# Get YAML for backup
ops k8s workflows list -o yaml
```

---

#### `ops k8s workflows get`

Get detailed information about a specific Workflow.

```bash
ops k8s workflows get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description            |
| -------- | -------- | ---------------------- |
| `name`   | Yes      | Workflow resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Workflow: data-pipeline-abc123

name              data-pipeline-abc123
namespace         workflows
phase             Succeeded
progress          15/15
duration          4m 23s
entrypoint        main
age               2h 15m
startedAt         2024-02-16T10:30:00Z
finishedAt        2024-02-16T10:34:23Z
```

**Examples:**

```bash
# Get workflow in default namespace
ops k8s workflows get data-pipeline-abc123

# Get in specific namespace
ops k8s workflows get data-pipeline-abc123 -n workflows

# Get full YAML definition
ops k8s workflows get data-pipeline-abc123 -o yaml

# Get JSON for script processing
ops k8s workflows get data-pipeline-abc123 -o json
```

---

#### `ops k8s workflows create`

Create a new Workflow from a WorkflowTemplate.

```bash
ops k8s workflows create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description            |
| -------- | -------- | ---------------------- |
| `name`   | Yes      | Workflow resource name |

**Options:**

| Option           | Short | Type   | Default   | Description                                  |
| ---------------- | ----- | ------ | --------- | -------------------------------------------- |
| `--namespace`    | `-n`  | string | `default` | Kubernetes namespace                         |
| `--template-ref` |       | string | Required  | WorkflowTemplate name to reference           |
| `--argument`     | `-a`  | string | None      | Workflow arguments as key=value (repeatable) |
| `--label`        | `-l`  | string | None      | Labels as key=value (repeatable)             |
| `--output`       | `-o`  | string | `table`   | Output format: table, json, or yaml          |

**Example Output:**

```text
Created Workflow: my-workflow

metadata:
  name: my-workflow
  namespace: workflows
  labels:
    app: data-processing
spec:
  workflowTemplateRef:
    name: data-pipeline
  arguments:
    parameters:
    - name: message
      value: hello
    - name: count
      value: "5"
```

**Examples:**

```bash
# Create workflow from template
ops k8s workflows create my-workflow --template-ref data-pipeline

# Create with arguments
ops k8s workflows create my-workflow \
  --template-ref data-pipeline \
  --argument message=hello \
  --argument count=5

# Create with labels
ops k8s workflows create my-workflow \
  --template-ref data-pipeline \
  --label app=data-processing \
  --label env=production

# Create in specific namespace
ops k8s workflows create my-workflow \
  --template-ref data-pipeline \
  -n workflows

# Create and get YAML output
ops k8s workflows create my-workflow \
  --template-ref data-pipeline \
  -o yaml
```

---

#### `ops k8s workflows delete`

Delete a Workflow.

```bash
ops k8s workflows delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description            |
| -------- | -------- | ---------------------- |
| `name`   | Yes      | Workflow resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
Workflow 'data-pipeline-abc123' deleted
```

**Examples:**

```bash
# Delete with confirmation
ops k8s workflows delete data-pipeline-abc123

# Delete in workflows namespace
ops k8s workflows delete data-pipeline-abc123 -n workflows

# Force delete without confirmation
ops k8s workflows delete data-pipeline-abc123 --force
```

---

#### `ops k8s workflows logs`

Get logs for a Workflow's pods.

```bash
ops k8s workflows logs <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description            |
| -------- | -------- | ---------------------- |
| `name`   | Yes      | Workflow resource name |

**Options:**

| Option        | Short | Type    | Default   | Description                               |
| ------------- | ----- | ------- | --------- | ----------------------------------------- |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace                      |
| `--container` | `-c`  | string  | `main`    | Container name in the pod                 |
| `--follow`    | `-f`  | boolean | False     | Stream logs in real-time (Ctrl+C to stop) |

**Example Output:**

```text
2024-02-16T10:30:15Z Starting data pipeline
2024-02-16T10:30:20Z Loading input data...
2024-02-16T10:30:45Z Processing 1000 records
2024-02-16T10:30:55Z Aggregating results
2024-02-16T10:31:00Z Uploading artifacts
2024-02-16T10:31:05Z Pipeline complete
```

**Examples:**

```bash
# Get logs for workflow
ops k8s workflows logs data-pipeline-abc123

# Follow logs in real-time
ops k8s workflows logs data-pipeline-abc123 --follow

# Get logs from specific container
ops k8s workflows logs data-pipeline-abc123 --container wait

# Get logs from namespace
ops k8s workflows logs data-pipeline-abc123 -n workflows

# Follow logs in production namespace
ops k8s workflows logs data-pipeline-abc123 -n workflows --follow
```

---

#### `ops k8s workflows artifacts`

List artifacts collected from a Workflow execution.

```bash
ops k8s workflows artifacts <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description            |
| -------- | -------- | ---------------------- |
| `name`   | Yes      | Workflow resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Artifacts: data-pipeline-abc123

NAME                NODE                    PATH                           TYPE        BUCKET                  KEY
results.json        process-step-abc123     /outputs/results.json          s3          workflows-artifacts     data-pipeline-abc123/results.json
metrics.csv         analyze-step-def456     /outputs/metrics.csv           s3          workflows-artifacts     data-pipeline-abc123/metrics.csv
logs.txt            final-step-xyz789       /outputs/logs.txt              s3          workflows-artifacts     data-pipeline-abc123/logs.txt
```

**Examples:**

```bash
# List workflow artifacts
ops k8s workflows artifacts data-pipeline-abc123

# List artifacts in specific namespace
ops k8s workflows artifacts data-pipeline-abc123 -n workflows

# Get artifact information as JSON
ops k8s workflows artifacts data-pipeline-abc123 -o json
```

---

### Workflow Templates

#### `ops k8s workflows templates list`

List all WorkflowTemplates in a namespace.

```bash
ops k8s workflows templates list [OPTIONS]
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
Workflow Templates

NAME              NAMESPACE    ENTRYPOINT        TEMPLATES  DESCRIPTION                 AGE
data-pipeline     workflows    main              6          Process and analyze data    5d 2h
email-batch       workflows    send-emails       3          Send batch emails           2d 15h
ci-build          ci           build-and-test    8          Build, test, and deploy     10d
backup-workflow   workflows    backup-all        4          Full cluster backup         1d 8h
```

**Examples:**

```bash
# List all templates
ops k8s workflows templates list

# List in specific namespace
ops k8s workflows templates list -n workflows

# Filter by label
ops k8s workflows templates list -l app=data-processing

# Get JSON output
ops k8s workflows templates list -o json
```

---

#### `ops k8s workflows templates get`

Get details of a specific WorkflowTemplate.

```bash
ops k8s workflows templates get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                    |
| -------- | -------- | ------------------------------ |
| `name`   | Yes      | WorkflowTemplate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
WorkflowTemplate: data-pipeline

name              data-pipeline
namespace         workflows
entrypoint        main
templates_count   6
description       Process and analyze data
age               5d 2h
```

**Examples:**

```bash
# Get template details
ops k8s workflows templates get data-pipeline

# Get in specific namespace
ops k8s workflows templates get data-pipeline -n workflows

# Get full YAML definition
ops k8s workflows templates get data-pipeline -o yaml

# Get JSON for integration
ops k8s workflows templates get data-pipeline -o json
```

---

#### `ops k8s workflows templates create`

Create a new WorkflowTemplate from a YAML spec file.

```bash
ops k8s workflows templates create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                    |
| -------- | -------- | ------------------------------ |
| `name`   | Yes      | WorkflowTemplate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                                  |
| ------------- | ----- | ------ | --------- | -------------------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                         |
| `--spec-file` |       | string | Required  | Path to YAML file with template spec section |
| `--label`     | `-l`  | string | None      | Labels as key=value (repeatable)             |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml          |

**Example Output:**

```text
Created WorkflowTemplate: my-template

metadata:
  name: my-template
  namespace: workflows
spec:
  entrypoint: main
  templates:
  - name: main
    container:
      image: python:3.9
      command: [python]
      args: [main.py]
```

**Spec File Format:**

The spec file should contain the `spec` section of a WorkflowTemplate. Example `template-spec.yaml`:

```yaml
entrypoint: main
arguments:
  parameters:
    - name: message
      default: hello
templates:
  - name: main
    steps:
      - - name: process
          template: process-data
          arguments:
            parameters:
              - name: input
                value: "{{workflow.parameters.message}}"
  - name: process-data
    inputs:
      parameters:
        - name: input
    container:
      image: python:3.9
      command: [python]
      args: [process.py, "{{inputs.parameters.input}}"]
```

**Examples:**

```bash
# Create template from spec file
ops k8s workflows templates create data-pipeline \
  --spec-file pipeline-spec.yaml

# Create with labels
ops k8s workflows templates create data-pipeline \
  --spec-file pipeline-spec.yaml \
  --label app=data-processing \
  --label version=v1

# Create in specific namespace
ops k8s workflows templates create data-pipeline \
  --spec-file pipeline-spec.yaml \
  -n workflows

# Create and get YAML output
ops k8s workflows templates create data-pipeline \
  --spec-file pipeline-spec.yaml \
  -o yaml
```

---

#### `ops k8s workflows templates delete`

Delete a WorkflowTemplate.

```bash
ops k8s workflows templates delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                    |
| -------- | -------- | ------------------------------ |
| `name`   | Yes      | WorkflowTemplate resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
WorkflowTemplate 'data-pipeline' deleted
```

**Examples:**

```bash
# Delete template
ops k8s workflows templates delete data-pipeline

# Force delete without confirmation
ops k8s workflows templates delete data-pipeline --force

# Delete in specific namespace
ops k8s workflows templates delete data-pipeline -n workflows --force
```

---

### Cron Workflows

#### `ops k8s workflows cron list`

List all CronWorkflows in a namespace.

```bash
ops k8s workflows cron list [OPTIONS]
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
Cron Workflows

NAME              NAMESPACE     SCHEDULE         SUSPENDED  ACTIVE  LAST RUN            AGE
backup-daily      workflows     0 2 * * *        False      0       2024-02-16T02:00Z   30d
data-cleanup      workflows     0 */6 * * *      False      1       2024-02-16T18:00Z   15d
report-weekly     workflows     0 9 * * 1        True       0       2024-02-12T09:00Z   8d
metrics-hourly    workflows     0 * * * *        False      0       2024-02-16T20:00Z   45d
```

**Examples:**

```bash
# List cron workflows
ops k8s workflows cron list

# List in specific namespace
ops k8s workflows cron list -n workflows

# Filter by label
ops k8s workflows cron list -l app=automation

# Get JSON output
ops k8s workflows cron list -o json
```

---

#### `ops k8s workflows cron get`

Get details of a specific CronWorkflow.

```bash
ops k8s workflows cron get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| `name`   | Yes      | CronWorkflow resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
CronWorkflow: backup-daily

name              backup-daily
namespace         workflows
schedule          0 2 * * *
suspend           False
active_count      0
last_scheduled    2024-02-16T02:00Z
age               30d
```

**Examples:**

```bash
# Get cron workflow
ops k8s workflows cron get backup-daily

# Get in specific namespace
ops k8s workflows cron get backup-daily -n workflows

# Get full YAML definition
ops k8s workflows cron get backup-daily -o yaml
```

---

#### `ops k8s workflows cron create`

Create a new CronWorkflow.

```bash
ops k8s workflows cron create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| `name`   | Yes      | CronWorkflow resource name |

**Options:**

| Option                 | Short | Type   | Default   | Description                                                 |
| ---------------------- | ----- | ------ | --------- | ----------------------------------------------------------- |
| `--namespace`          | `-n`  | string | `default` | Kubernetes namespace                                        |
| `--schedule`           |       | string | Required  | Cron schedule expression (e.g., '0 0 \* \* \*' for daily at |
| `--template-ref`       |       | string | Required  | WorkflowTemplate name                                       |
| `--timezone`           |       | string | Empty     | Timezone for schedule (e.g., 'America/Los_Angeles           |
| `--concurrency-policy` |       | string | `Allow`   | Policy: Allow, Forbid,                                      |
| `--label`              | `-l`  | string | None      | Labels as key=value                                         |
| `--output`             | `-o`  | string | `table`   | Output format: table,                                       |

**Cron Schedule Format:**

Standard cron syntax: `minute hour day month weekday`

Examples:

- `0 0 * * *` - Daily at midnight
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1` - Weekly on Monday at 9 AM
- `0 * * * *` - Every hour
- `*/15 * * * *` - Every 15 minutes

**Example Output:**

```text
Created CronWorkflow: backup-daily

metadata:
  name: backup-daily
  namespace: workflows
spec:
  schedule: 0 2 * * *
  timezone: America/Los_Angeles
  concurrencyPolicy: Forbid
  workflowSpec:
    workflowTemplateRef:
      name: backup
```

**Examples:**

```bash
# Create daily cron workflow
ops k8s workflows cron create backup-daily \
  --schedule "0 2 * * *" \
  --template-ref backup

# Create with timezone and concurrency policy
ops k8s workflows cron create backup-daily \
  --schedule "0 2 * * *" \
  --template-ref backup \
  --timezone "America/Los_Angeles" \
  --concurrency-policy Forbid

# Create every 6 hours
ops k8s workflows cron create data-cleanup \
  --schedule "0 */6 * * *" \
  --template-ref cleanup

# Create with labels
ops k8s workflows cron create metrics-hourly \
  --schedule "0 * * * *" \
  --template-ref metrics-collection \
  --label app=monitoring \
  --label critical=true

# Create in specific namespace
ops k8s workflows cron create backup-daily \
  --schedule "0 2 * * *" \
  --template-ref backup \
  -n workflows
```

---

#### `ops k8s workflows cron delete`

Delete a CronWorkflow.

```bash
ops k8s workflows cron delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| `name`   | Yes      | CronWorkflow resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
CronWorkflow 'backup-daily' deleted
```

**Examples:**

```bash
# Delete cron workflow
ops k8s workflows cron delete backup-daily

# Force delete without confirmation
ops k8s workflows cron delete backup-daily --force

# Delete in specific namespace
ops k8s workflows cron delete backup-daily -n workflows --force
```

---

#### `ops k8s workflows cron suspend`

Suspend a CronWorkflow (temporarily stop scheduled executions).

```bash
ops k8s workflows cron suspend <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| `name`   | Yes      | CronWorkflow resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Suspended CronWorkflow: backup-daily

suspend           True
lastScheduleTime  2024-02-16T02:00Z
```

**Examples:**

```bash
# Suspend cron workflow
ops k8s workflows cron suspend backup-daily

# Suspend in specific namespace
ops k8s workflows cron suspend backup-daily -n workflows

# Suspend and get YAML
ops k8s workflows cron suspend backup-daily -o yaml
```

---

#### `ops k8s workflows cron resume`

Resume a suspended CronWorkflow.

```bash
ops k8s workflows cron resume <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| `name`   | Yes      | CronWorkflow resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Resumed CronWorkflow: backup-daily

suspend           False
lastScheduleTime  2024-02-16T02:00Z
```

**Examples:**

```bash
# Resume suspended cron workflow
ops k8s workflows cron resume backup-daily

# Resume in specific namespace
ops k8s workflows cron resume backup-daily -n workflows

# Resume and get JSON output
ops k8s workflows cron resume backup-daily -o json
```

---

## Integration Examples

### Example 1: Create and Execute a Data Pipeline Workflow

Define and run a reusable data processing pipeline:

```bash
# Create workflow template with spec file
ops k8s workflows templates create data-pipeline \
  --spec-file pipeline-spec.yaml \
  --label app=data-processing

# Create instance of the workflow
ops k8s workflows create daily-pipeline-20240216 \
  --template-ref data-pipeline \
  --argument date=2024-02-16 \
  --argument output_format=parquet

# Monitor execution
ops k8s workflows list -n workflows --phase Running

# Check workflow status
ops k8s workflows get daily-pipeline-20240216 -n workflows

# Get workflow logs
ops k8s workflows logs daily-pipeline-20240216 --follow

# Collect artifacts when complete
ops k8s workflows artifacts daily-pipeline-20240216
```

### Example 2: Schedule Recurring Workflows with CronWorkflows

Set up automated daily backups and weekly reports:

```bash
# Create daily backup schedule
ops k8s workflows cron create backup-daily \
  --schedule "0 2 * * *" \
  --template-ref backup \
  --timezone "America/Los_Angeles" \
  --concurrency-policy Forbid \
  -n workflows

# Create weekly report schedule (every Monday at 9 AM)
ops k8s workflows cron create report-weekly \
  --schedule "0 9 * * 1" \
  --template-ref generate-report \
  --timezone "America/Los_Angeles" \
  -n workflows

# List all scheduled workflows
ops k8s workflows cron list -n workflows

# Suspend report during maintenance
ops k8s workflows cron suspend report-weekly -n workflows

# Resume when ready
ops k8s workflows cron resume report-weekly -n workflows
```

### Example 3: Monitor Workflow Execution

Track workflow progress and handle failures:

```bash
#!/bin/bash

# Create and monitor a workflow
WORKFLOW_NAME="process-batch-20240216"
TEMPLATE_REF="batch-processor"
NAMESPACE="workflows"

# Create workflow
ops k8s workflows create "$WORKFLOW_NAME" \
  --template-ref "$TEMPLATE_REF" \
  --argument batch_size=1000 \
  -n "$NAMESPACE"

# Wait for completion and monitor
while true; do
  STATUS=$(ops k8s workflows get "$WORKFLOW_NAME" -n "$NAMESPACE" -o json)
  PHASE=$(echo "$STATUS" | grep -o '"phase":"[^"]*"' | cut -d'"' -f4)

  if [ "$PHASE" = "Succeeded" ]; then
    echo "Workflow succeeded"
    # Get artifacts
    ops k8s workflows artifacts "$WORKFLOW_NAME" -n "$NAMESPACE"
    break
  elif [ "$PHASE" = "Failed" ] || [ "$PHASE" = "Error" ]; then
    echo "Workflow failed"
    # Get logs for debugging
    ops k8s workflows logs "$WORKFLOW_NAME" -n "$NAMESPACE"
    break
  fi

  echo "Workflow status: $PHASE"
  sleep 10
done
```

### Example 4: View Workflow Artifacts

Retrieve outputs from completed workflows:

```bash
# List artifacts from workflow
ops k8s workflows artifacts my-workflow -n workflows

# Get detailed artifact information as JSON
ops k8s workflows artifacts my-workflow -n workflows -o json

# Download and process artifacts (integration with your system)
# artifacts are typically stored in S3 or MinIO configured with Argo
```

### Example 5: Manage Workflow Templates

Create and update reusable workflow definitions:

```bash
# Create new workflow template
ops k8s workflows templates create email-batch \
  --spec-file email-template.yaml \
  --label app=notifications \
  --label version=v1 \
  -n workflows

# List templates
ops k8s workflows templates list -n workflows

# Get template details
ops k8s workflows templates get email-batch -n workflows -o yaml

# Use template to create instances
ops k8s workflows create email-batch-20240216 \
  --template-ref email-batch \
  --argument recipients=team@example.com \
  -n workflows

# Delete template (note: doesn't affect running workflows)
ops k8s workflows templates delete email-batch --force -n workflows
```

---

## Troubleshooting

| Issue                                     | Solution                                                              |
| ----------------------------------------- | --------------------------------------------------------------------- |
| "Workflow CRD not found"                  | Argo Workflows controller not installed. Install with: `kubectl apply |
| Workflow stays in "Pending" phase         | Check pod events                                                      |
| "WorkflowTemplate not found"              | Ensure template exists in the same                                    |
| Permission denied when creating workflows | Check RBAC permissio                                                  |
| Artifacts not found in workflow           | Verify artifact                                                       |
| Cron workflow not triggering              | Verify schedule                                                       |
| Cannot find workflow in list              | Verify namespace                                                      |
| Logs not available                        | Wait for workflow                                                     |
| Spec file validation errors               | Validate YAML                                                         |
| Workflow template reference not working   | Verify template                                                       |

---

## See Also

- [Argo Workflows Official Documentation](https://argoproj.github.io/argo-workflows/)
- [Kubernetes Plugin Overview](../index.md)
- [Argo Rollouts Integration](./argo-rollouts.md)
- [Kubernetes Commands Reference](../commands/)
- [Workflow Concepts](https://argoproj.github.io/argo-workflows/concepts/)
- [Workflow Templates](https://argoproj.github.io/argo-workflows/workflow-templates/)
- [Cron Workflows](https://argoproj.github.io/argo-workflows/cron-workflows/)
- [Artifact Management](https://argoproj.github.io/argo-workflows/artifacts/)
