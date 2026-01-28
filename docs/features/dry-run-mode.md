# Dry Run Mode

Preview and validate operations before execution with comprehensive dry run capabilities across
all System Control CLI commands.

## Overview

Dry run mode features:

- **Safe Preview**: See exactly what would happen without making changes
- **Impact Analysis**: Understand the scope and consequences of operations
- **Validation**: Verify configurations and prerequisites before execution
- **Resource Planning**: Estimate resource requirements and costs
- **Rollback Planning**: Preview rollback scenarios and procedures
- **Diff Output**: Show changes in a clear, readable format

## Basic Usage

### Global Dry Run Flag

```bash
# Add --dry-run to any command
ops deploy api --env production --dry-run

# Alternative syntax
ops --dry-run deploy api --env production

# Verbose dry run with detailed output
ops deploy api --env production --dry-run --verbose
```

### Command-Specific Dry Run

```bash
# Deployment dry run
ops deploy api --image api:v2.1.0 --env production --dry-run

# Configuration changes
ops config set api.replicas 5 --env production --dry-run

# Service scaling
ops scale api --replicas 10 --env production --dry-run

# Batch operations
ops batch run complex-workflow.yaml --dry-run

# Backup operations
ops backup create --all --env production --dry-run
```

## Configuration

### Dry Run Settings

```yaml
# config/dry-run.yaml
dry_run:
  # Global settings
  default_mode: false
  verbose_by_default: true

  # Output formatting
  output:
    format: "detailed" # brief, detailed, json, yaml
    colors: true
    diff_format: "unified" # unified, context, side-by-side

  # Validation levels
  validation:
    syntax: true
    dependencies: true
    resources: true
    permissions: true
    compatibility: true

  # Safety checks
  safety:
    require_confirmation: true
    show_warnings: true
    estimate_impact: true
    check_rollback_path: true

  # Integration settings
  integrations:
    kubernetes:
      server_side_dry_run: true
      validate_admission: true

    terraform:
      plan_output: true
      cost_estimation: true
```

## Deployment Dry Run

### Kubernetes Deployment Preview

```bash
# Basic deployment dry run
ops deploy api --image api:v2.1.0 --env production --dry-run

# Example output:
```

🔍 DRY RUN: Deployment Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Service: api
Environment: production
Strategy: rolling-update
Image: api:v2.1.0 (current: api:v2.0.5)

📋 Changes Summary:
┌─────────────────┬─────────────┬─────────────┐
│ Resource │ Current │ Planned │
├─────────────────┼─────────────┼─────────────┤
│ Replicas │ 3 │ 3 │
│ Image │ api:v2.0.5 │ api:v2.1.0 │
│ CPU Request │ 100m │ 100m │
│ Memory Request │ 128Mi │ 256Mi ⚠️ │
│ CPU Limit │ 500m │ 500m │
│ Memory Limit │ 512Mi │ 1Gi ⚠️ │
└─────────────────┴─────────────┴─────────────┘

⚠️ Resource Changes Detected:

- Memory request increased from 128Mi to 256Mi
- Memory limit increased from 512Mi to 1Gi
- Total cluster memory usage will increase by ~2.5Gi

🔄 Rolling Update Plan:

1. Create new ReplicaSet with image api:v2.1.0
2. Scale new ReplicaSet to 1 replica
3. Wait for readiness checks to pass
4. Scale old ReplicaSet to 2 replicas
5. Scale new ReplicaSet to 2 replicas
6. Continue until migration complete

⏱️ Estimated Duration: 3-5 minutes
🎯 Success Probability: 95% (based on historical data)

✅ Prerequisites Check:

- ✅ Kubernetes cluster connectivity
- ✅ Image api:v2.1.0 exists and is pullable
- ✅ Sufficient cluster resources available
- ✅ Required secrets and configmaps present
- ⚠️ Cluster memory usage will be 87% (threshold: 85%)

🔙 Rollback Plan:
If deployment fails, rollback will:

1. Scale old ReplicaSet back to 3 replicas
2. Delete new ReplicaSet
3. Estimated rollback time: 30-60 seconds

Would execute: kubectl apply --dry-run=server -f deployment.yaml

````text

### Blue-Green Deployment Preview

```bash
ops deploy api --strategy blue-green --env production --dry-run

# Example output:
```text

🔍 DRY RUN: Blue-Green Deployment Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current State (Blue):

- Service: api-blue (3 replicas, healthy)
- Load Balancer: 100% traffic to blue
- Version: v2.0.5

Planned State (Green):

- Service: api-green (3 replicas, new)
- Version: v2.1.0
- Traffic: Initially 0%, then switch to 100%

🚀 Deployment Steps:

1. Create green environment with api:v2.1.0
2. Deploy 3 replicas to green environment
3. Run health checks on green environment
4. Run smoke tests on green environment
5. Manual approval required for traffic switch
6. Switch load balancer from blue to green
7. Monitor for 10 minutes
8. Clean up blue environment (after 1 hour)

💰 Resource Impact:

- Additional resources needed: 6 CPU cores, 12Gi memory
- Duration: ~2-3 hours (including monitoring)
- Cost estimate: $0.50/hour during deployment

⚠️ Considerations:

- Database migration required (detected schema changes)
- Session persistence may cause user disruption
- Green environment will be created in same availability zones

```text

## Configuration Dry Run

### Configuration Changes Preview

```bash
# Configuration update dry run
ops config update api --file new-config.yaml --env production --dry-run

# Example output:
````

🔍 DRY RUN: Configuration Update Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configuration File: api-config
Environment: production

📝 Configuration Diff:
--- Current Configuration
+++ Planned Configuration
@@ -10,7 +10,7 @@
timeout: 30s

logging:

- level: INFO

- level: DEBUG

features:
new_ui: false

- advanced_search: true

🔄 Services Affected:

- api (3 replicas) - restart required
- worker (2 replicas) - reload configuration

⚠️ Impact Analysis:

- Log volume expected to increase 3-5x with DEBUG level
- New feature flag 'advanced_search' will be enabled
- Configuration reload will cause brief service interruption (~5s)

✅ Validation Results:

- ✅ Configuration syntax valid
- ✅ All required fields present
- ✅ Feature flags exist in codebase
- ⚠️ DEBUG log level may impact performance

🔄 Rollback Plan:

- Previous configuration backed up as api-config-v127
- Rollback command: ops config rollback api --version v127

````text

## Batch Operations Dry Run

### Workflow Preview

```bash
ops batch run deployment-workflow.yaml --dry-run

# Example output:
````

🔍 DRY RUN: Batch Workflow Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Workflow: deployment-workflow.yaml
Environment: production
Parameters: version=v2.1.0, replicas=3

📋 Execution Plan:
┌──────────────────────────────────────────────────────────┐
│ Step 1: pre_deployment_checks │
│ ├─ Command: ops health --all --env production │
│ ├─ Expected Duration: 30s │
│ └─ Dependencies: none │
├──────────────────────────────────────────────────────────┤
│ Step 2: deploy_database_migrations │
│ ├─ Command: ops db migrate --env production │
│ ├─ Expected Duration: 2-5 minutes │
│ └─ Dependencies: pre_deployment_checks │
├──────────────────────────────────────────────────────────┤
│ Step 3: deploy_services (parallel) │
│ ├─ 3a: deploy api (3 minutes) │
│ ├─ 3b: deploy worker (2 minutes, depends on 3a) │
│ ├─ 3c: deploy scheduler (1 minute, depends on 3a) │
│ └─ Dependencies: deploy_database_migrations │
├──────────────────────────────────────────────────────────┤
│ Step 4: post_deployment_tests │
│ ├─ Command: ops test integration --env production │
│ ├─ Expected Duration: 5 minutes │
│ └─ Dependencies: deploy_services │
└──────────────────────────────────────────────────────────┘

⏱️ Total Estimated Duration: 12-15 minutes
🎯 Success Probability: 92% (based on historical data)

💰 Resource Impact:

- Peak additional CPU: 8 cores
- Peak additional memory: 16Gi
- Network bandwidth: ~500Mbps during image pulls

🔙 Failure Scenarios:

1. Database migration fails (probability: 3%)
   └─ Rollback: Restore database backup (5 minutes)
2. Service deployment fails (probability: 5%)
   └─ Rollback: Revert to previous versions (3 minutes)

````text

## Scaling Dry Run

### Resource Impact Preview

```bash
ops scale api --replicas 10 --env production --dry-run

# Example output:
````

🔍 DRY RUN: Service Scaling Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Service: api
Environment: production
Current Replicas: 3
Target Replicas: 10
Scaling Factor: 3.33x

📊 Resource Requirements:
┌─────────────────┬─────────────┬─────────────┬─────────────┐
│ Resource │ Current │ Target │ Difference │
├─────────────────┼─────────────┼─────────────┼─────────────┤
│ CPU Requests │ 300m │ 1000m │ +700m │
│ Memory Requests │ 768Mi │ 2560Mi │ +1792Mi │
│ CPU Limits │ 1500m │ 5000m │ +3500m │
│ Memory Limits │ 1536Mi │ 5120Mi │ +3584Mi │
└─────────────────┴─────────────┴─────────────┴─────────────┘

🏗️ Cluster Capacity Analysis:

- Available CPU: 15 cores (5 cores needed)
- Available Memory: 32Gi (3.5Gi needed)
- Available Nodes: 6 (sufficient)
- ✅ Sufficient cluster capacity

🚀 Scaling Timeline:

1. Scale to 4 replicas (wait for readiness)
2. Scale to 6 replicas (wait for readiness)
3. Scale to 8 replicas (wait for readiness)
4. Scale to 10 replicas (final)

⏱️ Estimated Duration: 3-5 minutes
📈 Performance Impact:

- Request capacity: +233% (from 3000 req/min to 10000 req/min)
- Database connections: +233% (ensure connection pool can handle)

⚠️ Considerations:

- Database connection pool may need adjustment
- Load balancer health check frequency will increase
- Monitoring alerts may need threshold adjustments

````text

## Advanced Dry Run Features

### Impact Analysis

```bash
# Comprehensive impact analysis
ops deploy api --dry-run --impact-analysis

# Cost estimation
ops deploy api --dry-run --estimate-costs

# Dependency analysis
ops deploy api --dry-run --check-dependencies

# Security impact
ops deploy api --dry-run --security-analysis
````

### Custom Dry Run Policies

```yaml
# policies/dry-run-policies.yaml
dry_run_policies:
  production:
    required_for:
      - deployments
      - scaling_operations
      - configuration_changes
      - batch_operations

    mandatory_checks:
      - resource_availability
      - dependency_validation
      - rollback_planning
      - security_scan

    approval_required:
      - resource_increase > 50%
      - replica_count > 10
      - memory_limit > 4Gi

  staging:
    required_for:
      - major_deployments

    mandatory_checks:
      - basic_validation
      - dependency_check
```

### Integration with CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deployment
on:
  pull_request:
    branches: [main]

jobs:
  dry-run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install System Control CLI
        run: pip install system-control-cli

      - name: Dry Run Deployment
        run: |
          ops deploy api --env staging --dry-run --format json > dry-run-results.json

      - name: Comment PR with Dry Run Results
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('dry-run-results.json', 'utf8'));

            const comment = `## 🔍 Deployment Dry Run Results

            **Service:** ${results.service}
            **Environment:** ${results.environment}
            **Strategy:** ${results.strategy}

            ### Changes Summary
            ${results.changes.map(c => `- ${c.resource}: ${c.from} → ${c.to}`).join('\n')}

            ### Resource Impact
            - **Duration:** ${results.estimated_duration}
            - **Success Probability:** ${results.success_probability}
            - **Additional Resources:** ${results.additional_resources}

            ### Prerequisites
            ${results.prerequisites.map(p => `${p.status === 'ok' ? '✅' : '❌'} ${p.name}`).join('\n')}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

## Output Formats

### JSON Output

```bash
ops deploy api --dry-run --format json
```

```json
{
  "dry_run": true,
  "service": "api",
  "environment": "production",
  "strategy": "rolling",
  "changes": [
    {
      "resource": "image",
      "current": "api:v2.0.5",
      "planned": "api:v2.1.0",
      "impact": "medium"
    }
  ],
  "resource_impact": {
    "cpu_cores": 0,
    "memory_gi": 2.5,
    "storage_gi": 0
  },
  "estimated_duration": "3-5 minutes",
  "success_probability": 0.95,
  "prerequisites": [
    {
      "name": "cluster_connectivity",
      "status": "ok"
    }
  ],
  "rollback_plan": {
    "available": true,
    "estimated_time": "30-60 seconds"
  }
}
```

### YAML Output

```bash
ops deploy api --dry-run --format yaml
```

```yaml
dry_run: true
service: api
environment: production
changes:
  - resource: replicas
    current: 3
    planned: 5
    impact: medium
resource_impact:
  additional_cpu: "200m"
  additional_memory: "512Mi"
estimated_duration: "2-3 minutes"
prerequisites:
  - name: "sufficient_resources"
    status: "ok"
  - name: "health_checks_passing"
    status: "ok"
```

## Best Practices

### When to Use Dry Run

1. **Production Changes**: Always use dry run for production operations
2. **Complex Workflows**: Preview batch operations before execution
3. **Resource Changes**: Understand impact of scaling operations
4. **New Configurations**: Validate configuration changes
5. **CI/CD Integration**: Automate dry run in deployment pipelines

### Dry Run Workflow

```bash
# 1. Always start with dry run
ops deploy api --env production --dry-run

# 2. Review the output carefully
# 3. Check resource requirements and impact
# 4. Verify rollback plan is available
# 5. Execute the actual command

ops deploy api --env production
```

### Safety Checks

```yaml
# config/safety-policies.yaml
safety_policies:
  mandatory_dry_run:
    environments: ["production"]
    operations: ["deploy", "scale", "config"]

  approval_required:
    - resource_increase > 100%
    - replica_count > 20
    - critical_services: ["database", "auth"]

  warnings:
    - memory_usage > 80%
    - cpu_usage > 90%
    - disk_usage > 85%
```
