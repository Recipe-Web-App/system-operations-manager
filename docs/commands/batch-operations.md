# Batch Operations

Execute complex multi-step workflows, parallel operations, and automated sequences across
multiple services and environments efficiently.

## Overview

Batch operation features:

- **Workflow Definition**: YAML/JSON-defined multi-step operations
- **Parallel Execution**: Concurrent operations with dependency management
- **Error Handling**: Comprehensive error recovery and rollback procedures
- **Progress Tracking**: Real-time progress visualization with rich terminal output
- **Conditional Logic**: Dynamic workflow execution based on conditions
- **Template Support**: Parameterized workflows for reusability

## Core Batch Commands

### `sysctl batch`

Execute predefined batch operations and workflows.

```bash
# Execute workflow file
sysctl batch run deployment-workflow.yaml

# Execute with parameters
sysctl batch run deployment-workflow.yaml --set env=production,version=v2.1.0

# List available workflows
sysctl batch list

# Validate workflow before execution
sysctl batch validate deployment-workflow.yaml
```

#### Options

- `--set KEY=VALUE`: Set workflow parameters
- `--env, -e ENV`: Target environment
- `--dry-run`: Preview workflow execution
- `--parallel LIMIT`: Maximum parallel operations
- `--continue-on-error`: Continue execution despite individual failures
- `--timeout DURATION`: Overall workflow timeout
- `--save-state`: Save workflow state for resumption

## Workflow Definition

### Basic Workflow Structure

```yaml
# workflows/basic-deployment.yaml
name: "basic-deployment"
description: "Deploy multiple services in sequence"
version: "1.0"

parameters:
  - name: "environment"
    description: "Target environment"
    default: "staging"
    required: true

  - name: "image_tag"
    description: "Image tag to deploy"
    default: "latest"

  - name: "services"
    description: "Services to deploy"
    default: ["api", "worker", "scheduler"]
    type: "list"

variables:
  namespace: "{{ .environment }}-services"
  timeout: 300

steps:
  - name: "pre_deployment_check"
    description: "Verify environment health"
    command: "sysctl health --all --env {{ .environment }}"
    timeout: 60

  - name: "deploy_services"
    description: "Deploy all services"
    parallel: true
    steps:
      - name: "deploy_api"
        command: "sysctl deploy api --env {{ .environment }} --image api:{{ .image_tag }} --wait"

      - name: "deploy_worker"
        command: "sysctl deploy worker --env {{ .environment }} --image worker:{{ .image_tag }} --wait"
        depends_on: ["deploy_api"]

      - name: "deploy_scheduler"
        command: "sysctl deploy scheduler --env {{ .environment }} --image scheduler:{{ .image_tag }} --wait"
        depends_on: ["deploy_api"]

  - name: "post_deployment_test"
    description: "Run post-deployment tests"
    command: "sysctl test smoke --env {{ .environment }}"
    timeout: 180

on_failure:
  - name: "rollback"
    command: "sysctl rollback --all --env {{ .environment }}"

on_success:
  - name: "notify_team"
    command: "sysctl notify --message 'Deployment completed successfully' --channel slack"
```

### Advanced Workflow Features

```yaml
# workflows/advanced-deployment.yaml
name: "advanced-deployment"
description: "Advanced deployment with blue-green strategy"

parameters:
  - name: "environment"
    type: "string"
    validation:
      pattern: "^(staging|production)$"

  - name: "services"
    type: "array"
    validation:
      min_items: 1
      max_items: 10

conditions:
  - name: "is_production"
    expression: "{{ .environment == 'production' }}"

  - name: "critical_services"
    expression: "{{ 'api' in .services or 'database' in .services }}"

steps:
  - name: "backup_check"
    description: "Ensure recent backup exists"
    command: "sysctl backup verify --latest --env {{ .environment }}"
    when: "{{ .is_production }}"

  - name: "maintenance_mode"
    description: "Enable maintenance mode for critical services"
    command: "sysctl maintenance enable --services {{ join .services ',' }} --env {{ .environment }}"
    when: "{{ .critical_services and .is_production }}"

  - name: "blue_green_deployment"
    description: "Execute blue-green deployment"
    parallel_limit: 2
    steps:
      - name: "prepare_green_environment"
        command: "sysctl traffic blue-green prepare --env {{ .environment }}"

      - name: "deploy_to_green"
        command: |
          for service in {{ .services }}; do
            sysctl deploy $service --env {{ .environment }} --target green --wait
          done
        shell: "bash"

      - name: "test_green_environment"
        command: "sysctl test integration --env {{ .environment }} --target green"
        depends_on: ["deploy_to_green"]

      - name: "switch_traffic"
        command: "sysctl traffic blue-green promote --env {{ .environment }}"
        depends_on: ["test_green_environment"]
        manual_approval: true
        when: "{{ .is_production }}"

  - name: "cleanup"
    description: "Clean up old versions"
    command: "sysctl cleanup --keep-last 3 --env {{ .environment }}"

rollback:
  enabled: true
  automatic: true
  conditions:
    - "health_check_failed"
    - "deployment_timeout"
  steps:
    - name: "traffic_rollback"
      command: "sysctl traffic blue-green rollback --env {{ .environment }}"
    - name: "service_rollback"
      command: "sysctl rollback --all --env {{ .environment }}"

notifications:
  channels: ["slack", "email"]
  events: ["started", "completed", "failed", "requires_approval"]

monitoring:
  metrics: ["deployment_duration", "success_rate", "rollback_count"]
  alerts:
    - condition: "deployment_duration > 1800" # 30 minutes
      severity: "warning"
```

## Parallel Execution

### Parallel Workflows

```yaml
# workflows/parallel-operations.yaml
name: "parallel-operations"
description: "Execute operations in parallel with dependency management"

steps:
  - name: "database_operations"
    description: "Database maintenance tasks"
    parallel: true
    parallel_limit: 3
    steps:
      - name: "backup_primary"
        command: "sysctl backup database --type full --compress"
        priority: 1

      - name: "backup_replicas"
        command: "sysctl backup database --replicas --type incremental"
        priority: 2
        depends_on: ["backup_primary"]

      - name: "analyze_tables"
        command: "sysctl database analyze --all-tables"
        priority: 3

      - name: "vacuum_database"
        command: "sysctl database vacuum --analyze"
        priority: 3
        depends_on: ["analyze_tables"]

  - name: "service_updates"
    description: "Update services in parallel"
    parallel: true
    depends_on: ["database_operations"]
    steps:
      - name: "update_api_configs"
        command: "sysctl config update api --file configs/api-v2.yaml"

      - name: "update_worker_configs"
        command: "sysctl config update worker --file configs/worker-v2.yaml"

      - name: "restart_services"
        command: "sysctl restart api worker --rolling"
        depends_on: ["update_api_configs", "update_worker_configs"]
```

### Resource Management

```yaml
# workflows/resource-management.yaml
name: "resource-management"
description: "Manage system resources efficiently"

resource_limits:
  max_parallel: 5
  memory_limit: "2Gi"
  cpu_limit: "4"

steps:
  - name: "resource_intensive_tasks"
    description: "Tasks that require significant resources"
    resource_requirements:
      memory: "1Gi"
      cpu: "2"
    steps:
      - name: "large_backup"
        command: "sysctl backup create --all --compress"
        resources:
          memory: "512Mi"
          cpu: "1"

      - name: "log_analysis"
        command: "sysctl logs analyze --duration 7d --pattern-detection"
        resources:
          memory: "256Mi"
          cpu: "0.5"

      - name: "metrics_aggregation"
        command: "sysctl metrics aggregate --duration 30d --export"
        resources:
          memory: "256Mi"
          cpu: "0.5"
```

## Conditional Execution

### Dynamic Workflows

```yaml
# workflows/conditional-deployment.yaml
name: "conditional-deployment"
description: "Deploy based on dynamic conditions"

steps:
  - name: "environment_check"
    description: "Check environment status"
    command: "sysctl status --all --env {{ .environment }}"
    capture_output: "status_check"

  - name: "conditional_deployment"
    description: "Deploy based on environment status"
    condition: |
      {{- $status := .outputs.status_check | fromJSON -}}
      {{- range $status -}}
        {{- if and (eq .name "api") (lt .health_score 80) -}}
          true
        {{- end -}}
      {{- end -}}
    steps:
      - name: "deploy_api"
        command: "sysctl deploy api --env {{ .environment }}"

  - name: "scale_based_on_load"
    description: "Scale services based on current load"
    dynamic: true
    script: |
      #!/bin/bash
      load=$(sysctl metrics api --metric cpu_usage --format value)
      if (( $(echo "$load > 80" | bc -l) )); then
        sysctl scale api --replicas 5 --env {{ .environment }}
      elif (( $(echo "$load < 30" | bc -l) )); then
        sysctl scale api --replicas 2 --env {{ .environment }}
      fi
```

### Environment-Specific Logic

```yaml
# workflows/environment-specific.yaml
name: "environment-specific"
description: "Different behavior per environment"

steps:
  - name: "development_setup"
    when: "{{ .environment == 'development' }}"
    steps:
      - command: "sysctl config set debug_mode=true"
      - command: "sysctl scale --all --replicas 1"
      - command: "sysctl monitoring disable --non-critical"

  - name: "staging_setup"
    when: "{{ .environment == 'staging' }}"
    steps:
      - command: "sysctl test data-seed --sample-data"
      - command: "sysctl config set log_level=debug"
      - command: "sysctl monitoring enable --all"

  - name: "production_setup"
    when: "{{ .environment == 'production' }}"
    steps:
      - command: "sysctl backup verify --recent"
      - command: "sysctl security scan --comprehensive"
      - command: "sysctl monitoring enable --critical-alerts"
      - command: "sysctl performance optimize --auto"
```

## Error Handling and Recovery

### Comprehensive Error Handling

```yaml
# workflows/error-handling.yaml
name: "error-handling"
description: "Comprehensive error handling and recovery"

error_handling:
  strategy: "fail_fast" # or "continue_on_error", "retry"
  max_retries: 3
  retry_delay: "30s"

steps:
  - name: "risky_operation"
    command: "sysctl deploy api --env production"
    timeout: 300
    retry:
      attempts: 3
      delay: "60s"
      backoff: "exponential"

    on_failure:
      - name: "log_failure"
        command: "echo 'Deployment failed at $(date)' >> deployment.log"

      - name: "notify_oncall"
        command: "sysctl notify --urgent --message 'Production deployment failed'"

      - name: "automatic_rollback"
        command: "sysctl rollback api --env production --force"

    on_retry:
      - name: "cleanup_failed_deployment"
        command: "sysctl cleanup --failed-deployments"

recovery:
  enabled: true
  strategies:
    - name: "service_recovery"
      conditions: ["service_down", "health_check_failed"]
      actions:
        - "restart_service"
        - "scale_up_replicas"
        - "switch_to_backup"

    - name: "data_recovery"
      conditions: ["data_corruption", "backup_needed"]
      actions:
        - "stop_writes"
        - "restore_from_backup"
        - "verify_data_integrity"
```

### Circuit Breaker Pattern

```yaml
# workflows/circuit-breaker.yaml
name: "circuit-breaker"
description: "Implement circuit breaker for external dependencies"

circuit_breakers:
  database_operations:
    failure_threshold: 5
    recovery_timeout: "60s"
    fallback:
      - "use_cache"
      - "read_only_mode"

steps:
  - name: "database_dependent_task"
    command: "sysctl database migrate --env production"
    circuit_breaker: "database_operations"

    fallback_steps:
      - name: "enable_maintenance_mode"
        command: "sysctl maintenance enable --message 'Database maintenance'"

      - name: "notify_team"
        command: "sysctl notify --message 'Database operations failed, maintenance mode enabled'"
```

## Monitoring and Progress Tracking

### Progress Visualization

```bash
# Run workflow with progress tracking
sysctl batch run complex-deployment.yaml --progress

# Example output:
┌─ Complex Deployment Workflow ─┐
│ ✓ Pre-deployment checks       │
│ ⏳ Database migration (3/5)    │
│ ⏸  Service deployment (waiting)│
│ ⏸  Post-deployment tests      │
│ ⏸  Cleanup operations         │
└─ Progress: 35% (12m remaining)┘
```

### Workflow Metrics

```yaml
# workflows/with-metrics.yaml
name: "with-metrics"
description: "Workflow with comprehensive metrics collection"

metrics:
  enabled: true
  collectors:
    - "prometheus"
    - "grafana"

  custom_metrics:
    - name: "deployment_duration"
      type: "histogram"
      description: "Time taken for deployment"

    - name: "success_rate"
      type: "counter"
      description: "Successful workflow executions"

steps:
  - name: "timed_operation"
    command: "sysctl deploy api --env production"
    metrics:
      track_duration: true
      track_success: true
      custom_labels:
        service: "api"
        environment: "production"
```

## Workflow Management

### Workflow Templates

```bash
# List workflow templates
sysctl batch templates

# Create workflow from template
sysctl batch create microservice-deployment --template deployment --services api,worker

# Generate custom template
sysctl batch template generate --from successful-deployment.yaml --name custom-template
```

### Workflow Scheduling

```bash
# Schedule workflow execution
sysctl batch schedule deployment-workflow.yaml --cron "0 2 * * 0" --env production

# List scheduled workflows
sysctl batch schedule list

# Cancel scheduled workflow
sysctl batch schedule cancel deployment-production-weekly
```

### Workflow State Management

```bash
# Save workflow state during execution
sysctl batch run complex-workflow.yaml --save-state

# Resume failed workflow
sysctl batch resume workflow-state-12345

# List workflow history
sysctl batch history --limit 10

# Cleanup old workflow states
sysctl batch cleanup --older-than 30d
```

## Best Practices

### Workflow Design

1. **Modular Steps**: Break complex operations into small, testable steps
2. **Error Handling**: Always define error handling and recovery procedures
3. **Idempotency**: Ensure steps can be safely retried
4. **Validation**: Validate inputs and prerequisites before execution
5. **Documentation**: Document workflow purpose, parameters, and dependencies

### Example Best Practice Workflow

```yaml
# workflows/best-practice-example.yaml
name: "best-practice-deployment"
description: "Example of well-structured workflow"
version: "1.2.0"
author: "DevOps Team"
documentation: "https://wiki.company.com/deployments/best-practices"

validation:
  - name: "required_parameters"
    expression: "{{ .environment and .services }}"
    message: "Environment and services parameters are required"

  - name: "valid_environment"
    expression: "{{ .environment in ['staging', 'production'] }}"
    message: "Environment must be staging or production"

prerequisites:
  - name: "kubectl_access"
    command: "kubectl auth can-i create deployments --namespace {{ .environment }}"

  - name: "recent_backup"
    command: "sysctl backup verify --within 24h --env {{ .environment }}"

steps:
  - name: "pre_deployment_validation"
    description: "Validate environment and prerequisites"
    idempotent: true
    timeout: 60
    steps:
      - name: "health_check"
        command: "sysctl health --all --env {{ .environment }}"
      - name: "resource_check"
        command: "sysctl resources check --required-capacity 80% --env {{ .environment }}"

  - name: "deployment_execution"
    description: "Execute deployment with proper error handling"
    atomic: true # All or nothing
    rollback_on_failure: true
    steps:
      # Deployment steps here

post_execution:
  success:
    - name: "cleanup_old_resources"
      command: "sysctl cleanup --keep-last 3 --env {{ .environment }}"
    - name: "update_documentation"
      command: "sysctl docs update --deployment-log --env {{ .environment }}"

  failure:
    - name: "collect_debug_info"
      command: "sysctl debug collect --output debug-{{ .workflow_id }}.tar.gz"
    - name: "create_incident"
      command: "sysctl incident create --title 'Deployment failure' --workflow {{ .workflow_id }}"

monitoring:
  health_checks: true
  metrics_collection: true
  log_aggregation: true
  alert_on_failure: true
```
