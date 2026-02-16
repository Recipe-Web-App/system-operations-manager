# Kubernetes Plugin > Commands > Jobs

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Jobs](#jobs)
  - [List Jobs](#list-jobs)
  - [Get Job](#get-job)
  - [Create Job](#create-job)
  - [Delete Job](#delete-job)
- [CronJobs](#cronjobs)
  - [List CronJobs](#list-cronjobs)
  - [Get CronJob](#get-cronjob)
  - [Create CronJob](#create-cronjob)
  - [Update CronJob](#update-cronjob)
  - [Delete CronJob](#delete-cronjob)
  - [Suspend CronJob](#suspend-cronjob)
  - [Resume CronJob](#resume-cronjob)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

The Jobs commands manage Kubernetes workloads that run to completion. These commands organize into two resource types:

- **Jobs** - Run tasks to completion once or multiple times
- **CronJobs** - Schedule Jobs to run on a recurring schedule

Jobs are useful for batch processing, data analysis, backups, and cleanup tasks. CronJobs automate periodic operations
like daily backups, weekly reports, or monthly maintenance tasks.

All commands support multiple output formats (table, JSON, YAML) and comprehensive filtering options.

---

## Common Options

Options available across most Jobs commands:

| Option             | Short | Type   | Default             | Description                          |
| ------------------ | ----- | ------ | ------------------- | ------------------------------------ |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace to operate in   |
| `--all-namespaces` | `-A`  | flag   | false               | List resources across all namespaces |
| `--selector`       | `-l`  | string | none                | Filter by label selector             |
| `--output`         | `-o`  | string | table               | Output format: table, json, or yaml  |
| `--force`          | `-f`  | flag   | false               | Skip confirmation prompts            |
| `--label`          | `-l`  | string | none                | Add labels to created resources      |

---

## Jobs

Jobs run containers to completion, handling retries and pod cleanup automatically. Use Jobs for one-time or multi-pod
batch tasks.

### List Jobs

List all Jobs in a namespace or across all namespaces.

```bash
ops k8s jobs list
ops k8s jobs list -n production
ops k8s jobs list -A
ops k8s jobs list -l app=batch-processor
```

**Options:**

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Jobs
┌────────────────────┬──────────────┬─────────────┬──────────┬────────┬────────┬──────┐
│ Name               │ Namespace    │ Completions │ Succeeded│ Failed │ Active │ Age  │
├────────────────────┼──────────────┼─────────────┼──────────┼────────┼────────┼──────┤
│ backup-job         │ default      │ 1/1         │ 1        │ 0      │ 0      │ 2d   │
│ data-migration     │ default      │ 10/10       │ 10       │ 0      │ 0      │ 1d   │
│ cleanup-task       │ production   │ 1/1         │ 1        │ 0      │ 0      │ 1h   │
│ failed-import      │ production   │ 3/3         │ 2        │ 1      │ 0      │ 30m  │
└────────────────────┴──────────────┴─────────────┴──────────┴────────┴────────┴──────┘
```

**Notes:**

- Completions show requested/completed format
- Succeeded shows successful pod completions
- Failed shows pods that failed even after retries
- Active shows currently running pods
- Use `--all-namespaces` to monitor jobs across cluster
- Filter by labels to find jobs for specific applications

---

### Get Job

Retrieve detailed information about a specific Job.

```bash
ops k8s jobs get my-job
ops k8s jobs get my-job -n production
ops k8s jobs get my-job -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Job: my-job
┌──────────────────────────┬──────────────────────────────┐
│ Field                    │ Value                        │
├──────────────────────────┼──────────────────────────────┤
│ Name                     │ my-job                       │
│ Namespace                │ default                      │
│ Status                   │ Complete                     │
│ Completions              │ 1/1                          │
│ Succeeded                │ 1                            │
│ Failed                   │ 0                            │
│ Active                   │ 0                            │
│ Start Time               │ 2024-02-14T10:00:00Z         │
│ Completion Time          │ 2024-02-14T10:05:30Z         │
│ Duration                 │ 5 minutes 30 seconds         │
│ Image                    │ busybox:latest               │
│ Parallelism              │ 1                            │
│ Age                      │ 2 days                       │
│ Labels                   │ app=batch, type=backup       │
└──────────────────────────┴──────────────────────────────┘
```

**Notes:**

- Shows job status, completion progress, and timing information
- Useful for monitoring job execution and debugging failures
- Duration shows total time from start to completion
- Use `-o json` or `-o yaml` for full manifest details

---

### Create Job

Create a new Job that runs a container to completion.

```bash
ops k8s jobs create my-job --image busybox --command echo --command hello
ops k8s jobs create backup-job --image backup-image --completions 5 --parallelism 2
```

**Options:**

| Option          | Short | Type    | Default             | Description                      |
| --------------- | ----- | ------- | ------------------- | -------------------------------- |
| `--namespace`   | `-n`  | string  | config or 'default' | Kubernetes namespace             |
| `--image`       | `-i`  | string  | required            | Container image to run           |
| `--command`     | `-c`  | string  | none                | Command to run (repeatable)      |
| `--completions` |       | integer | 1                   | Successful completions needed    |
| `--parallelism` |       | integer | 1                   | Pods to run in parallel          |
| `--label`       | `-l`  | string  | none                | Label (key=value, repeatable)    |
| `--output`      | `-o`  | string  | table               | Output format: table, json, yaml |

**Examples:**

Create basic Job:

```bash
ops k8s jobs create simple-job \
  --image busybox \
  --command echo \
  --command "Hello World"
```

Create Job with multiple completions:

```bash
ops k8s jobs create batch-process \
  --image data-processor:latest \
  --completions 10 \
  --parallelism 3
```

Create Job with command and parallelism:

```bash
ops k8s jobs create parallel-export \
  --image exporter:v1 \
  --command /scripts/export.sh \
  --completions 4 \
  --parallelism 2 \
  --label app=export \
  --label type=batch
```

Create Job in production namespace:

```bash
ops k8s jobs create prod-backup \
  -n production \
  --image backup-service:latest \
  --command /bin/backup.sh \
  --completions 1 \
  --label app=backup \
  --label schedule=daily
```

Create Job with specific image and arguments:

```bash
ops k8s jobs create data-migration \
  --image migration-tool:v2 \
  --command migrate \
  --command --source \
  --command /data/old \
  --command --dest \
  --command /data/new \
  --completions 1
```

**Example Output:**

```text
Created Job: my-job
┌────────────┬────────────────────────────┐
│ Field      │ Value                      │
├────────────┼────────────────────────────┤
│ Name       │ my-job                     │
│ Namespace  │ default                    │
│ Status     │ Running                    │
│ Image      │ busybox:latest             │
│ Completions│ 0/1                        │
│ Active     │ 1                          │
│ Created    │ 2024-02-16T10:30:00Z       │
│ Labels     │ app=batch, type=backup     │
└────────────┴────────────────────────────┘
```

**Notes:**

- Container image is required; must be available in the cluster
- Command is optional; if not specified, uses image's default ENTRYPOINT
- Completions > 1 creates multiple pod instances (sequentially or in parallel)
- Parallelism determines how many pods run simultaneously
- Job will retry failed pods automatically (up to backoff limit)
- Labels help organize and filter jobs

---

### Delete Job

Delete a Job and its associated pods from the cluster.

```bash
ops k8s jobs delete my-job
ops k8s jobs delete my-job -n production
ops k8s jobs delete my-job -f
ops k8s jobs delete my-job --propagation-policy Foreground
```

**Options:**

| Option                 | Short | Type   | Default             | Description                                   |
| ---------------------- | ----- | ------ | ------------------- | --------------------------------------------- |
| `--namespace`          | `-n`  | string | config or 'default' | Kubernetes namespace                          |
| `--propagation-policy` |       | string | Background          | Deletion propagation (Background, Foreground, |
| `--force`              | `-f`  | flag   | false               | Skip confirmation                             |

**Propagation Policies:**

| Policy                   | Behavior                                                      |
| ------------------------ | ------------------------------------------------------------- |
| **Background** (default) | Delete Job immediately; pods are cleaned up in the background |
| **Foreground**           | Delete Job only after all pods are terminated                 |
| **Orphan**               | Delete Job but leave pods running; pods become orphaned       |

**Example Output:**

```text
Are you sure you want to delete job 'my-job' in namespace 'default'? [y/N]: y
Job 'my-job' deleted
```

**Examples:**

Delete job immediately:

```bash
ops k8s jobs delete backup-job -f
```

Delete job and wait for pods to finish:

```bash
ops k8s jobs delete batch-job --propagation-policy Foreground
```

Delete job but keep pods running:

```bash
ops k8s jobs delete analysis-job --propagation-policy Orphan
```

**Notes:**

- Requires confirmation unless `--force` is used
- Background propagation is faster; Foreground is safer for stateful workloads
- Orphan mode leaves pods running independently; useful for debugging
- Consider job completion status and data persistence before deletion

---

## CronJobs

CronJobs schedule Jobs to run on a recurring schedule using cron expressions. Use for automated tasks like backups,
reports, and maintenance.

### List CronJobs

List all CronJobs in a namespace or across all namespaces.

```bash
ops k8s cronjobs list
ops k8s cronjobs list -n production
ops k8s cronjobs list -A
ops k8s cronjobs list -l app=maintenance
```

**Options:**

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
CronJobs
┌──────────────────┬──────────────┬──────────────┬─────────┬────────┬────────────────┬──────┐
│ Name             │ Namespace    │ Schedule     │ Suspend │ Active │ Last Schedule  │ Age  │
├──────────────────┼──────────────┼──────────────┼─────────┼────────┼────────────────┼──────┤
│ daily-backup     │ default      │ 0 2 * * *    │ False   │ 0      │ 5 hours ago    │ 30d  │
│ weekly-report    │ default      │ 0 9 * * 1    │ False   │ 0      │ 2 days ago     │ 20d  │
│ maintenance      │ production   │ 0 0 * * *    │ False   │ 0      │ 2 hours ago    │ 15d  │
│ snapshot         │ production   │ */6 * * * *  │ True    │ 0      │ 1 day ago      │ 10d  │
└──────────────────┴──────────────┴──────────────┴─────────┴────────┴────────────────┴──────┘
```

**Notes:**

- Schedule shows cron expression (minute hour day month weekday)
- Suspend shows if cronjob is paused (True/False)
- Active shows number of currently running Job instances
- Last Schedule shows when the most recent Job was created
- Use `--all-namespaces` to monitor cronjobs across cluster

---

### Get CronJob

Retrieve detailed information about a specific CronJob.

```bash
ops k8s cronjobs get daily-backup
ops k8s cronjobs get daily-backup -n production
ops k8s cronjobs get daily-backup -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
CronJob: daily-backup
┌──────────────────────────┬──────────────────────────────┐
│ Field                    │ Value                        │
├──────────────────────────┼──────────────────────────────┤
│ Name                     │ daily-backup                 │
│ Namespace                │ default                      │
│ Schedule                 │ 0 2 * * * (02:00 daily)      │
│ Suspend                  │ False                        │
│ Concurrency Policy       │ Allow                        │
│ Image                    │ backup-service:latest        │
│ Active Count             │ 0                            │
│ Last Successful Schedule │ 2024-02-16T02:00:05Z         │
│ Last Failed Schedule     │ Never                        │
│ Last Schedule Time       │ 2024-02-16T02:00:00Z         │
│ Next Schedule Time       │ 2024-02-17T02:00:00Z         │
│ Age                      │ 30 days                      │
│ Created                  │ 2024-01-17T08:00:00Z         │
│ Labels                   │ app=backup, type=scheduled   │
└──────────────────────────┴──────────────────────────────┘
```

**Notes:**

- Shows schedule and suspension status
- Displays last successful and failed execution times
- Next schedule time shows when the next Job will run
- Useful for monitoring cronjob execution and debugging failures

---

### Create CronJob

Create a new CronJob that runs a Job on a recurring schedule.

```bash
ops k8s cronjobs create my-cron --image busybox --schedule '*/5 * * * *'
ops k8s cronjobs create daily-backup --image backup-image --schedule '0 2 * * *'
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--image`     | `-i`  | string | required            | Container image to run           |
| `--schedule`  | `-s`  | string | required            | Cron schedule expression         |
| `--command`   | `-c`  | string | none                | Command to run (repeatable)      |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)    |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Cron Schedule Format:**

```text
┌────────── minute (0 - 59)
│ ┌──────── hour (0 - 23)
│ │ ┌────── day of month (1 - 31)
│ │ │ ┌──── month (1 - 12)
│ │ │ │ ┌── day of week (0 - 6, 0 is Sunday)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

**Common Schedules:**

| Expression     | Description              | Equivalent      |
| -------------- | ------------------------ | --------------- |
| `0 0 * * *`    | Daily at midnight        | Daily           |
| `0 2 * * *`    | Daily at 2:00 AM         | Nightly backup  |
| `0 0 * * 0`    | Sunday at midnight       | Weekly          |
| `0 0 1 * *`    | 1st of month at midnight | Monthly         |
| `0 9 * * 1-5`  | Weekdays at 9:00 AM      | Business days   |
| `*/30 * * * *` | Every 30 minutes         | Frequent        |
| `0 */6 * * *`  | Every 6 hours            | Six times daily |

**Examples:**

Create daily backup CronJob:

```bash
ops k8s cronjobs create daily-backup \
  --image backup-service:latest \
  --schedule '0 2 * * *' \
  --command /scripts/backup.sh
```

Create hourly maintenance CronJob:

```bash
ops k8s cronjobs create hourly-maintenance \
  --image maintenance-tool:v1 \
  --schedule '0 * * * *' \
  --command /scripts/cleanup.sh
```

Create CronJob with labels:

```bash
ops k8s cronjobs create weekly-report \
  --image reporting-engine:latest \
  --schedule '0 9 * * 1' \
  --command /scripts/generate-report.sh \
  --label app=reporting \
  --label frequency=weekly \
  --label type=scheduled
```

Create CronJob in production namespace:

```bash
ops k8s cronjobs create prod-snapshot \
  -n production \
  --image snapshot-tool:latest \
  --schedule '*/15 * * * *' \
  --command /bin/snapshot.sh
```

Create CronJob with multiple command arguments:

```bash
ops k8s cronjobs create sync-external \
  --image sync-client:v2 \
  --schedule '0 3 * * *' \
  --command /usr/bin/sync \
  --command --source \
  --command external.example.com \
  --command --dest \
  --command /data/sync
```

**Example Output:**

```text
Created CronJob: my-cron
┌────────────┬────────────────────────────┐
│ Field      │ Value                      │
├────────────┼────────────────────────────┤
│ Name       │ my-cron                    │
│ Namespace  │ default                    │
│ Status     │ Created                    │
│ Schedule   │ */5 * * * * (every 5 min) │
│ Image      │ busybox:latest             │
│ Created    │ 2024-02-16T11:00:00Z       │
│ Labels     │ app=batch, type=scheduled  │
└────────────┴────────────────────────────┘
```

**Notes:**

- Schedule is required; use valid cron syntax
- Container image must be available in the cluster
- Command is optional; if not specified, uses image's default ENTRYPOINT
- Jobs are created according to the schedule
- CronJob controller runs inside the cluster, so times are in cluster timezone

---

### Update CronJob

Update a CronJob's schedule or suspension status.

```bash
ops k8s cronjobs update my-cron --schedule '0 * * * *'
ops k8s cronjobs update my-cron --suspend
ops k8s cronjobs update my-cron --no-suspend
```

**Options:**

| Option                   | Short | Type   | Default             | Description                      |
| ------------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`            | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--schedule`             | `-s`  | string | none                | New cron schedule expression     |
| `--suspend/--no-suspend` |       | flag   | none                | Suspend or unsuspend the cronjob |
| `--output`               | `-o`  | string | table               | Output format: table, json, yaml |

**Examples:**

Change execution schedule:

```bash
ops k8s cronjobs update daily-backup --schedule '0 3 * * *'
```

Suspend CronJob temporarily:

```bash
ops k8s cronjobs update daily-backup --suspend
```

Resume suspended CronJob:

```bash
ops k8s cronjobs update daily-backup --no-suspend
```

Update both schedule and keep suspended:

```bash
ops k8s cronjobs update weekly-report \
  --schedule '0 10 * * 1' \
  --suspend
```

**Example Output:**

```text
Updated CronJob: my-cron
┌────────────┬────────────────────────────┐
│ Field      │ Value                      │
├────────────┼────────────────────────────┤
│ Name       │ my-cron                    │
│ Namespace  │ default                    │
│ Status     │ Updated                    │
│ Schedule   │ 0 * * * * (hourly)         │
│ Modified   │ 2024-02-16T11:30:00Z       │
└────────────┴────────────────────────────┘
```

**Notes:**

- Updates take effect immediately
- Suspended CronJobs do not create new Jobs
- Existing active Jobs are not affected by suspension
- Use update to adjust timing without recreating the cronjob

---

### Delete CronJob

Delete a CronJob from the cluster. Existing Jobs may be cleaned up based on history settings.

```bash
ops k8s cronjobs delete my-cronjob
ops k8s cronjobs delete my-cronjob -n production
ops k8s cronjobs delete my-cronjob -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete cronjob 'my-cronjob' in namespace 'default'? [y/N]: y
CronJob 'my-cronjob' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deleting cronjob stops future Job creation but may keep historical Jobs
- Dependent Jobs may remain based on history policy
- Consider impact on scheduled tasks before deletion

---

### Suspend CronJob

Suspend a CronJob to temporarily stop it from creating new Jobs.

```bash
ops k8s cronjobs suspend my-cronjob
ops k8s cronjobs suspend my-cronjob -n production
```

**Options:**

| Option        | Short | Type   | Default             | Description          |
| ------------- | ----- | ------ | ------------------- | -------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace |

**Example Output:**

```text
CronJob 'my-cronjob' suspended
```

**Notes:**

- Suspended CronJobs do not create new Jobs
- Existing active Jobs are not affected
- Previously created Jobs continue running
- Use to pause scheduled work during maintenance
- Equivalent to `update --suspend`

---

### Resume CronJob

Resume a suspended CronJob to resume normal scheduling.

```bash
ops k8s cronjobs resume my-cronjob
ops k8s cronjobs resume my-cronjob -n production
```

**Options:**

| Option        | Short | Type   | Default             | Description          |
| ------------- | ----- | ------ | ------------------- | -------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace |

**Example Output:**

```text
CronJob 'my-cronjob' resumed
```

**Notes:**

- Resumes scheduling according to the cron schedule
- Does not immediately run a Job; waits for next scheduled time
- Useful after maintenance or troubleshooting
- Equivalent to `update --no-suspend`

---

## Troubleshooting

| Issue                                 | Solution                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------ |
| "job not found"                       | Verify namespace with `-n` flag. Use `list` to confirm job               |
| "cronjob schedule not working"        | Verify cron syntax is valid. Check cluster timezone. Ensure              |
| "job stuck in running"                | Check pod logs with `kubectl logs`. Verify image exists and can run.     |
| "job failed with image error"         | Verify image name is correct. Check image exists in registry.            |
| "cronjob not creating jobs"           | Check if cronjob is suspended. Verify schedule is correct.               |
| "pods not cleaning up after job"      | Check Job's TTL settings. Manually delete Job with                       |
| "command format error"                | Ensure command arguments are properly separated. Each                    |
| "job completions not reaching target" | Check pod logs for errors. Verify backoff limit not exceeded. Check      |
| "cronjob runs at wrong time"          | Verify cluster timezone. Check cron expression. Ensure system            |
| "cannot delete active job"            | Use foreground propagation policy. Wait for pods to complete. Use orphan |
| "job history not visible"             | Check history limits in cronjob. Use `list -A` to find                   |
| "parallel jobs not working"           | Verify parallelism value. Check resource limits allow concurrent pods.   |

---

## Best Practices

**Job Creation:**

1. Always specify image with proper tag (avoid `latest` in production)
2. Include meaningful labels for filtering and organization
3. Test job locally before creating in cluster
4. Monitor job completion and log output

**CronJob Configuration:**

1. Use specific schedules; avoid overly frequent runs if not needed
2. Set reasonable backoff and concurrency policies
3. Include history limits to prevent clutter
4. Monitor job history and success rates

**Resource Management:**

1. Set appropriate resource requests/limits for containers
2. Monitor cluster capacity before creating large jobs
3. Use node selectors if specific nodes are needed
4. Clean up completed jobs periodically

**Error Handling:**

1. Always check job logs for failures: `kubectl logs -l job-name=name`
2. Verify images are available before creating jobs
3. Use meaningful command and argument structure
4. Test cron schedules before production deployment

---

## See Also

- [Configuration & Storage Commands](./configuration-storage.md) - Manage ConfigMaps and Secrets for jobs
- [RBAC Commands](./rbac.md) - Create service accounts for job execution
- [Kubernetes Plugin Index](../index.md) - Complete plugin documentation
- [Examples](../examples.md) - Common job patterns and use cases
- [Ecosystem](../ecosystem/) - Related Kubernetes tools and integrations
- [TUI Interface](../tui.md) - Terminal UI for visualizing job resources
