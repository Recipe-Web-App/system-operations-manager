# Kubernetes Plugin > Commands > Optimization

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Common Options](#common-options)
4. [Analyze Command](#analyze-command)
5. [Recommend Command](#recommend-command)
6. [Unused Command](#unused-command)
7. [Summary Command](#summary-command)
8. [Understanding Results](#understanding-results)
9. [Example Workflows](#example-workflows)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

---

## Overview

The optimization command group provides deep insights into your Kubernetes cluster's resource utilization and identifies
opportunities for cost savings and efficiency improvements. These commands analyze workload performance, detect waste,
and recommend optimal resource requests and limits.

Key capabilities:

- **Resource Analysis**: Compare actual CPU/memory usage against requested amounts
- **Right-Sizing Recommendations**: Get specific CPU/memory requests and limits suggestions
- **Waste Detection**: Find orphan pods, stale jobs, and idle workloads
- **Cost Optimization**: Identify overprovisioned and underutilized resources
- **Cluster-Wide Overview**: Summarize optimization opportunities across namespaces
- **Metrics-Driven**: Uses Kubernetes metrics-server for accurate utilization data

---

## Prerequisites

The optimization commands require:

1. **Metrics Server**: Must be installed and running in your cluster
   - Check: `kubectl get deployment metrics-server -n kube-system`
   - Install: Follow the [Kubernetes Metrics Server documentation](https://github.com/kubernetes-sigs/metrics-server)

2. **RBAC Permissions**: Your user needs permissions to:
   - Read pods, deployments, statefulsets, and daemonsets
   - Access metrics from metrics-server
   - Read node information

3. **Cluster Access**: Working kubeconfig with cluster connectivity

**Verify prerequisites:**

```bash
# Check metrics-server is running
kubectl get deployment metrics-server -n kube-system

# Test access to metrics
kubectl top nodes
kubectl top pods

# If these commands work, optimization commands should work
ops k8s optimize analyze -A
```

---

## Common Options

Options shared across optimization commands:

| Option             | Short | Type    | Default        | Description                               |
| ------------------ | ----- | ------- | -------------- | ----------------------------------------- |
| `--namespace`      | `-n`  | string  | config default | Kubernetes namespace                      |
| `--all-namespaces` | `-A`  | boolean | false          | Analyze resources across all              |
| `--selector`       | `-l`  | string  |                | Label selector to filter resources (e.g., |
| `--output`         | `-o`  | string  | table          | Output format: table,                     |

**Namespace Scope:**

- Default: Only analyzes resources in the current/default namespace
- `-n production`: Analyzes only the production namespace
- `-A`: Analyzes all namespaces across the cluster
- `-l app=web`: Only analyzes resources with label `app=web`

---

## Analyze Command

### `ops k8s optimize analyze`

Analyze resource utilization for workloads and identify optimization opportunities.

The analyze command compares actual CPU and memory usage (from metrics-server) against the resource requests in your
workloads. This helps identify resources that are overprovisioned (requesting more than they use) or underutilized (idle
resources).

**Syntax:**

```bash
ops k8s optimize analyze [OPTIONS]
```

**Options:**

| Option             | Short | Type    | Default        | Description                                               |
| ------------------ | ----- | ------- | -------------- | --------------------------------------------------------- |
| `--namespace`      | `-n`  | string  | config default | Kubernetes namespace to                                   |
| `--all-namespaces` | `-A`  | boolean | false          | Analyze all namespac                                      |
| `--selector`       | `-l`  | string  |                | Label selector for filtering (e.g.,                       |
| `--threshold`      | `-t`  | float   | 0.5            | Utilization threshold (0.0-1.0); resources below this are |
| `--output`         | `-o`  | string  | table          | Output format: table, json,                               |

**Threshold Explanation:**

The threshold compares actual usage against requested resources:

- Threshold 0.5 = workload must use at least 50% of requested resources to be considered OK
- Threshold 0.3 = workload flagged if using less than 30% of requests
- Threshold 0.8 = workload flagged only if using less than 80% of requests
- Default threshold 0.5 is suitable for most workloads

**Behavior:**

1. Fetches all Deployments, StatefulSets, and DaemonSets matching the filters
2. Retrieves current metrics for each workload's pods from metrics-server
3. Calculates utilization as: (actual usage / requested amount) × 100
4. Compares utilization against the threshold
5. Displays results with status indicators:
   - Green (OK): Utilization above threshold
   - Yellow (Underutilized): Utilization below threshold
   - Red (Critical): Minimal usage detected
6. Returns exit code 0 if resources found, 1 if no resources match criteria

**Examples:**

Analyze workloads in the current namespace:

```bash
ops k8s optimize analyze
```

Analyze all namespaces and find underutilized resources:

```bash
ops k8s optimize analyze -A
```

Strict threshold - flag anything using less than 70% of requests:

```bash
ops k8s optimize analyze --threshold 0.7
```

Analyze production namespace with label filter:

```bash
ops k8s optimize analyze -n production -l environment=prod --threshold 0.5
```

Get analysis results in JSON for further processing:

```bash
ops k8s optimize analyze -A --output json > analysis.json
```

Find workloads consuming very little resources (threshold 0.1):

```bash
ops k8s optimize analyze --threshold 0.1
```

**Example Output (table format):**

```text
Resource Analysis
Name                   Namespace    Kind           Replicas    CPU %    Mem %    Status    Age
api-server             production   Deployment     3           65       45       OK        28d
web-frontend           production   Deployment     5           8        5        OK        15d
cache-warmer           production   Deployment     2           2        1        WARN      5d
legacy-service         staging      StatefulSet    2           3        2        WARN      90d
system-daemon          kube-sys     DaemonSet      4           42       38       OK        120d
batch-processor        production   Deployment     10          12       8        WARN      3d
```

**Example Output (JSON format):**

```json
[
  {
    "name": "api-server",
    "namespace": "production",
    "workload_type": "Deployment",
    "replicas": 3,
    "cpu_utilization_pct": 65,
    "memory_utilization_pct": 45,
    "status": "OK",
    "age": "28d"
  },
  {
    "name": "cache-warmer",
    "namespace": "production",
    "workload_type": "Deployment",
    "replicas": 2,
    "cpu_utilization_pct": 2,
    "memory_utilization_pct": 1,
    "status": "UNDERUTILIZED",
    "age": "5d"
  }
]
```

**Column Descriptions:**

| Column    | Description                                              |
| --------- | -------------------------------------------------------- |
| Name      | Workload name                                            |
| Namespace | Kubernetes namespace                                     |
| Kind      | Resource type (Deployment, StatefulSet, DaemonSet)       |
| Replicas  | Number of pod replicas running                           |
| CPU %     | Actual CPU usage as percentage of request                |
| Mem %     | Actual memory usage as percentage of request             |
| Status    | OK, UNDERUTILIZED, or OVERPROVISIONED based on threshold |
| Age       | How long the workload has been running                   |

**Notes:**

- Requires metrics-server to be installed and functioning
- Metrics typically lag 1-2 minutes behind real-time usage
- Short-running workloads may show incomplete metrics
- Resources without memory requests show as unknown
- DaemonSets show per-node metrics; scale interpretation is different
- Use different thresholds for different workload types (higher for batch jobs, lower for services)

---

## Recommend Command

### `ops k8s optimize recommend`

Get resource request and limit recommendations for a specific workload.

The recommend command analyzes a workload's actual resource consumption and suggests appropriate CPU and memory requests
and limits. These recommendations include a built-in safety buffer above actual usage.

**Syntax:**

```bash
ops k8s optimize recommend <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Type   | Description                     |
| -------- | -------- | ------ | ------------------------------- |
| `name`   | Yes      | string | Name of the workload to analyze |

**Options:**

| Option        | Short | Type   | Default        | Description                                          |
| ------------- | ----- | ------ | -------------- | ---------------------------------------------------- |
| `--namespace` | `-n`  | string | config default | Kubernetes namespace containing the workload         |
| `--type`      |       | string | Deployment     | Workload type: Deployment, StatefulSet, or DaemonSet |
| `--output`    | `-o`  | string | table          | Output format: table, json, or yaml                  |

**Behavior:**

1. Locates the specified workload by name and type
2. Retrieves metrics for all running pods
3. Analyzes CPU and memory consumption patterns
4. Calculates 95th percentile usage (accounts for normal variation)
5. Adds a safety buffer (typically 10-20%) above actual usage
6. Returns recommended request and limit values
7. Provides guidance on when to apply recommendations

**Safety Buffer:**

The recommendation includes a built-in safety margin above actual usage:

- **Request**: Set to slightly above typical usage (prevents throttling)
- **Limit**: Set higher than request to handle traffic spikes (prevents OOMKill)
- Buffer ensures temporary usage spikes don't cause immediate issues

**Examples:**

Get recommendations for a deployment in the current namespace:

```bash
ops k8s optimize recommend my-deployment
```

Get recommendations for a StatefulSet in production:

```bash
ops k8s optimize recommend my-statefulset -n production --type StatefulSet
```

Recommendations in JSON for comparison with current values:

```bash
ops k8s optimize recommend my-deployment --output json
```

Get recommendations for a DaemonSet:

```bash
ops k8s optimize recommend logging-daemon --type DaemonSet
```

**Example Output (table format):**

```text
Recommendation: api-server
Current Configuration       Recommended Configuration
Name: api-server            Name: api-server
Type: Deployment            Type: Deployment
Replicas: 3                 Replicas: 3

CPU Request
Current: 500m              Recommended: 400m
Current: 1000m             Recommended: 800m

Memory Request
Current: 512Mi              Recommended: 384Mi
Limit: 1024Mi               Limit: 768Mi

Change Impact
Estimated Savings: 25%
Risk Level: Low
Notes: Workload is consistently using less than requested. Reducing requests is safe.
```

**Example Output (JSON format):**

```json
{
  "name": "api-server",
  "namespace": "production",
  "workload_type": "Deployment",
  "current_config": {
    "cpu_request": "500m",
    "cpu_limit": "1000m",
    "memory_request": "512Mi",
    "memory_limit": "1024Mi"
  },
  "recommended_config": {
    "cpu_request": "400m",
    "cpu_limit": "800m",
    "memory_request": "384Mi",
    "memory_limit": "768Mi"
  },
  "savings_estimate": "25%",
  "risk_level": "Low",
  "notes": "Workload is consistently using less than requested. Reducing requests is safe."
}
```

**Applying Recommendations:**

To apply recommended values:

1. Update your manifest file with the recommended values
2. Test in a staging environment first
3. Monitor the workload after deployment for any issues
4. Gradually reduce requests if still within safe margins

**Example manifest update:**

```yaml
# Before
spec:
  containers:
  - name: api
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 1000m
        memory: 1024Mi

# After (recommended)
spec:
  containers:
  - name: api
    resources:
      requests:
        cpu: 400m        # Reduced from 500m
        memory: 384Mi    # Reduced from 512Mi
      limits:
        cpu: 800m        # Reduced from 1000m
        memory: 768Mi    # Reduced from 1024Mi
```

**Notes:**

- Recommendations are based on recent metrics (typically 7 days of data)
- Patterns change seasonally; review recommendations periodically
- StatefulSets and DaemonSets have different scaling characteristics
- High-variance workloads may need larger buffers
- Batch jobs should have different values than always-on services
- Risk level indicates confidence in the recommendations

---

## Unused Command

### `ops k8s optimize unused`

Detect orphan pods, stale jobs, and idle workloads consuming cluster resources.

The unused command identifies resources that are consuming cluster resources but may not be serving a purpose. This
includes bare pods without owner controllers, completed jobs lingering past their usefulness, and workloads with
negligible resource usage.

**Syntax:**

```bash
ops k8s optimize unused [OPTIONS]
```

**Options:**

| Option             | Short | Type    | Default        | Description                                            |
| ------------------ | ----- | ------- | -------------- | ------------------------------------------------------ |
| `--namespace`      | `-n`  | string  | config default | Kubernetes namespace                                   |
| `--all-namespaces` | `-A`  | boolean | false          | Scan all namespaces                                    |
| `--stale-hours`    |       | float   | 24             | Hours after job completion before considering it stale |
| `--output`         | `-o`  | string  | table          | Output format: table,                                  |

**Stale Job Threshold:**

The `--stale-hours` option controls how long completed jobs remain before being flagged:

- Default 24 hours: Jobs completed more than 24 hours ago are stale
- Increase to 48 or 72 for stricter retention
- Set to 1 for aggressive cleanup (be careful not to remove needed history)

**Behavior:**

1. Scans all pods across specified namespace(s)
2. Identifies orphan pods (no owner controller like Deployment, StatefulSet, etc.)
3. Finds stale jobs (completed or failed, older than threshold)
4. Detects idle workloads (running controllers with minimal resource usage)
5. Presents results in three separate sections
6. Provides actionable data for cleanup decisions

**Categories:**

**Orphan Pods** - Bare pods with no controller:

- Often created manually or abandoned
- Can consume resources indefinitely
- Safe to delete without data loss if data is backed up

**Stale Jobs** - Completed jobs past their retention period:

- No longer performing work
- May be kept for history/audit but take cluster space
- Safe to delete when logs are archived

**Idle Workloads** - Controllers with running pods using minimal resources:

- May be configuration errors or testing workloads
- Could be intentionally idle
- Review before deletion

**Examples:**

Find unused resources in current namespace:

```bash
ops k8s optimize unused
```

Find all unused resources across the entire cluster:

```bash
ops k8s optimize unused -A
```

Find stale jobs older than 48 hours:

```bash
ops k8s optimize unused --stale-hours 48
```

Get unused resources as JSON for automated cleanup:

```bash
ops k8s optimize unused -A --output json > cleanup.json
```

Find unused resources in production namespace:

```bash
ops k8s optimize unused -n production
```

Strict cleanup: jobs older than 12 hours:

```bash
ops k8s optimize unused --stale-hours 12
```

**Example Output (table format):**

```text
Orphan Pods (no owner controller)
Name                         Namespace    Phase     CPU         Memory    Node      Age
debug-pod-abc123            default      Running   10m         64Mi      node-1    7d
test-manual-pod             staging      Failed    0m          0Mi       node-2    15d

Stale Jobs
Name                         Namespace    Status    Stale (hrs)  Age
backup-job-2026-02-01        production   Failed    168          7d
cleanup-cron-2026-01-30      production   Succeeded 216          9d

Idle Workloads
Name                         Namespace    Kind           Replicas   CPU %   Mem %   Status    Age
legacy-monitor               staging      Deployment     1          1       0       IDLE      60d
experimental-worker         testing      StatefulSet    2          2       3       IDLE      45d
```

**Example Output (JSON format):**

```json
{
  "orphan_pods": [
    {
      "name": "debug-pod-abc123",
      "namespace": "default",
      "phase": "Running",
      "cpu_usage": "10m",
      "memory_usage": "64Mi",
      "node_name": "node-1",
      "age": "7d"
    }
  ],
  "stale_jobs": [
    {
      "name": "backup-job-2026-02-01",
      "namespace": "production",
      "status": "Failed",
      "age_hours": 168,
      "age": "7d"
    }
  ],
  "idle_workloads": [
    {
      "name": "legacy-monitor",
      "namespace": "staging",
      "workload_type": "Deployment",
      "replicas": 1,
      "cpu_utilization_pct": 1,
      "memory_utilization_pct": 0,
      "status": "IDLE",
      "age": "60d"
    }
  ]
}
```

**Cleanup Example:**

```bash
# Review unused resources
ops k8s optimize unused -A

# Delete identified orphan pods (with caution)
kubectl delete pod debug-pod-abc123 -n default

# Delete stale jobs
kubectl delete job backup-job-2026-02-01 -n production

# Consider deleting idle workloads
kubectl delete deployment legacy-monitor -n staging
```

**Notes:**

- Always review results before deleting
- Stale job deletion removes job objects but logs may be retained elsewhere
- Orphan pod deletion is permanent unless backed up
- Some pods may be temporarily idle (batch jobs, scheduled work)
- Review scheduling patterns before removing seemingly idle workloads
- Consider storing logs/metrics before deleting old jobs
- Use `--dry-run` pattern to understand what would be removed

---

## Summary Command

### `ops k8s optimize summary`

Show a high-level summary of cluster optimization opportunities.

The summary command provides a quick overview of the entire cluster's resource optimization status, rolling up findings
from analysis, unused resource detection, and waste calculations into actionable insights.

**Syntax:**

```bash
ops k8s optimize summary [OPTIONS]
```

**Options:**

| Option             | Short | Type    | Default        | Description                         |
| ------------------ | ----- | ------- | -------------- | ----------------------------------- |
| `--namespace`      | `-n`  | string  | config default | Kubernetes namespace to summarize   |
| `--all-namespaces` | `-A`  | boolean | false          | Summarize all namespaces            |
| `--output`         | `-o`  | string  | table          | Output format: table, json, or yaml |

**Behavior:**

1. Runs complete cluster analysis (like analyze command)
2. Scans for unused resources (like unused command)
3. Calculates total resource waste metrics
4. Estimates potential cost savings
5. Presents executive summary with key findings
6. Returns exit code 0 if analysis completes

**Examples:**

Get optimization summary for current namespace:

```bash
ops k8s optimize summary
```

Cluster-wide optimization summary:

```bash
ops k8s optimize summary -A
```

Production namespace summary:

```bash
ops k8s optimize summary -n production
```

Summary in JSON format:

```bash
ops k8s optimize summary -A --output json
```

**Example Output (table format):**

```text
Optimization Summary
Key                      Value
Workloads Analyzed       47
Overprovisioned          12
Underutilized            8
Healthy                  27
Orphan Pods              3
Stale Jobs               5
CPU Waste                24 cores
Memory Waste             128 Gi
```

**Example Output (JSON format):**

```json
{
  "workloads_analyzed": 47,
  "overprovisioned": 12,
  "underutilized": 8,
  "healthy": 27,
  "orphan_pods": 3,
  "stale_jobs": 5,
  "cpu_waste_display": "24 cores",
  "memory_waste_display": "128 Gi"
}
```

**Interpretation:**

- **Workloads Analyzed**: Total number of workloads reviewed
- **Overprovisioned**: Workloads requesting more than they use
- **Underutilized**: Workloads with idle capacity
- **Healthy**: Workloads with appropriate resource requests
- **Orphan Pods**: Bare pods consuming resources
- **Stale Jobs**: Old jobs that can be cleaned up
- **CPU/Memory Waste**: Estimated idle resources available for reclamation

**Using Summary Results:**

```bash
# Get summary
ops k8s optimize summary -A --output json > summary.json

# Analyze specific findings
cat summary.json | jq '.orphan_pods'  # See orphan pod count

# Follow up with detailed analysis
ops k8s optimize analyze --threshold 0.5   # Identify specific workloads
ops k8s optimize unused                    # Find cleanup opportunities
```

**Notes:**

- Provides quick status check for optimization initiatives
- Useful for periodic cluster health reviews
- CPU/memory waste estimates are conservative
- Actual savings depend on specific workload characteristics
- Review detailed commands (analyze, unused) for specific actions

---

## Understanding Results

### Status Indicators

Results use different status labels to indicate resource optimization levels:

| Status              | Meaning                                     | Action                                |
| ------------------- | ------------------------------------------- | ------------------------------------- |
| **OK**              | Workload using 50%+ of requested            | Monitor, no immediate action          |
| **UNDERUTILIZED**   | Workload using less than threshold          | Consider reducing requests            |
| **OVERPROVISIONED** | Workload has excessive requests relative to | Reduce requests to match actual needs |
| **IDLE**            | Workload consuming negligible resources     | Review purpose; consider deletion if  |
| **WARN**            | Marginal utilization, monitor closely       | Watch for patterns before making      |

### Safe Optimization Practices

1. **Analyze First**: Always run `analyze` before making changes
2. **Test in Staging**: Try reduced resources in non-production first
3. **Monitor After Change**: Watch metrics for 1-2 weeks after adjustment
4. **Gradual Reduction**: Reduce resources incrementally (10% at a time)
5. **Keep Headroom**: Maintain 20-30% buffer for traffic spikes
6. **Review Seasonally**: Workload patterns change; re-analyze quarterly

### Common Scenarios

**High CPU, Low Memory Usage:**

- Application is CPU-intensive but memory-efficient
- Increase CPU requests, reduce memory
- Example: Data processing, cryptographic workloads

**Low CPU, High Memory Usage:**

- Application is memory-heavy but CPU-efficient
- Increase memory requests, reduce CPU
- Example: Cache servers, in-memory databases

**Low on Both:**

- Consider if workload is needed or working correctly
- May be idle or incorrectly sized
- Verify with logs: `ops k8s logs <pod>`

**Spiky Usage:**

- Workload has variable consumption
- Use higher threshold (0.7+) to prevent throttling
- Consider HPA (Horizontal Pod Autoscaling)

---

## Example Workflows

### Quarterly Cluster Optimization Review

```bash
# 1. Get overall summary
ops k8s optimize summary -A --output json > q1-summary.json

# 2. Analyze each namespace
ops k8s optimize analyze -n production > prod-analysis.txt
ops k8s optimize analyze -n staging > staging-analysis.txt
ops k8s optimize analyze -n development > dev-analysis.txt

# 3. Find unused resources for cleanup
ops k8s optimize unused -A --stale-hours 48 > stale-items.txt

# 4. Get recommendations for top workloads
ops k8s optimize recommend my-api -n production
ops k8s optimize recommend web-frontend -n production

# 5. Review findings and plan changes
# Identify 5-10 workloads for optimization

# 6. Test in staging before production
ops k8s optimize recommend test-app -n staging
# Manually update and deploy in staging
# Monitor for 1 week
# If successful, apply to production
```

### Cost Optimization Initiative

```bash
# Identify all underutilized workloads
ops k8s optimize analyze -A --threshold 0.4 --output json > underutilized.json

# Focus on high-resource workloads first (biggest savings)
# Review each with recommendations
ops k8s optimize recommend big-workload-1 --output json
ops k8s optimize recommend big-workload-2 --output json

# Create patches with recommended values
# Deploy to staging first
# Monitor for 1-2 weeks
# Deploy to production with staged rollout

# Expected outcome: 20-30% cost reduction
```

### Cluster Health Check

```bash
# Quick summary
ops k8s optimize summary -A

# If issues found, investigate
ops k8s optimize analyze -A --threshold 0.5  # See what's underutilized
ops k8s optimize unused -A                    # See cleanup opportunities

# Follow up with specifics
ops k8s optimize recommend problematic-workload
```

### Pre-Upgrade Optimization

```bash
# Before upgrading cluster or adding new workloads:

# 1. Clean up unused resources
ops k8s optimize unused -A --stale-hours 12
# Delete identified stale jobs and orphan pods

# 2. Right-size existing workloads
ops k8s optimize summary -A
# Apply recommendations to free up capacity

# 3. This creates space for new workloads or higher availability
```

---

## Troubleshooting

| Issue                                     | Cause                                           | Solution                         |
| ----------------------------------------- | ----------------------------------------------- | -------------------------------- |
| "metrics-server not found"                | Metrics Server not installed in cluster         | Install: `kubectl                |
| "No metrics available"                    | Metrics Server installed but not providing data | Wait 1-2 minutes                 |
| "Insufficient permissions"                | User lacks RBAC permissions for metrics         | Contact cluster                  |
| All workloads show "WARN" status          | Threshold too high for your workloads           | Lower threshold:                 |
| No recommendations generated              | Not enough historical data                      | Wait 7+ days and                 |
| Results differ between runs               | Metrics fluctuate during busy                   | Run during consisten             |
| "Cannot connect to cluster"               | kubeconfig invalid or cluster                   | Test: `kubectl get               |
| Analysis takes very long                  | Large number of workloads in cluster            | Analyze specific                 |
| "Workload not found"                      | Typo in workload name                           | Check: `kubectl get deployments` |
| Recommendations are too aggressive        | Safety buffer is low for your workload          | Manually increase                |
| Applied recommendations, workload failing | Reduced too much or                             | Increase back;                   |

---

## See Also

- [Kubernetes Plugin Index](../index.md)
- [Manifests Commands](manifests.md) - YAML manifest validation and deployment
- [Streaming Commands](streaming.md) - Logs, exec, port-forward
- [Workloads Commands](workloads.md) - Pod and workload management
- [Examples and Use Cases](../examples.md) - Complete workflow examples
- [TUI Overview](../tui.md) - Terminal user interface for Kubernetes management
- [Kubernetes Metrics Server](https://github.com/kubernetes-sigs/metrics-server) - Installation guide
- [Resource Requests and Limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) -
  Official Kubernetes documentation
