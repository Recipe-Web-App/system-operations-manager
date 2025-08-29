# Deployment Commands

The deployment commands provide comprehensive control over service deployments, including
various deployment strategies, rollback capabilities, and health monitoring.

## Overview

Deployment commands support:

- **Multiple Strategies**: Rolling, blue-green, canary deployments
- **Template-Based**: Parameterized deployment configurations
- **Health Monitoring**: Automatic health checks and validation
- **Rollback Support**: Quick rollback to previous versions
- **Batch Operations**: Deploy multiple services simultaneously
- **Dry Run Mode**: Preview deployments before execution

## Core Commands

### `sysctl deploy`

Deploy services to specified environments.

```bash
# Basic deployment
sysctl deploy api

# Deploy to specific environment
sysctl deploy api --env production

# Deploy with custom image
sysctl deploy api --image myregistry.com/api:v2.1.0

# Deploy multiple services
sysctl deploy api worker scheduler

# Deploy all services
sysctl deploy --all
```

#### Options

- `--env, -e ENV`: Target environment (default: current profile)
- `--image IMAGE`: Override container image
- `--replicas REPLICAS`: Override replica count
- `--strategy STRATEGY`: Deployment strategy (rolling, blue-green, canary)
- `--timeout SECONDS`: Deployment timeout (default: 600)
- `--dry-run`: Preview deployment without executing
- `--force`: Force deployment even if validation fails
- `--wait`: Wait for deployment to complete
- `--follow`: Follow deployment progress in real-time
- `--parallel LIMIT`: Maximum parallel deployments (default: 3)

#### Examples

```bash
# Production deployment with blue-green strategy
sysctl deploy api --env production --strategy blue-green --wait

# Deploy with increased replicas
sysctl deploy api --replicas 5 --env production

# Quick development deployment
sysctl deploy api --env dev --timeout 60 --force

# Deploy with template variables
sysctl deploy api --env production \
  --set version=v2.1.0 \
  --set database_url=postgres://prod-db:5432/app

# Parallel deployment of microservices
sysctl deploy api gateway auth worker --parallel 2 --follow
```

### `sysctl rollback`

Rollback deployments to previous versions.

```bash
# Rollback to previous version
sysctl rollback api

# Rollback to specific version
sysctl rollback api --version v1.2.0

# Rollback multiple services
sysctl rollback api worker --version v1.2.0

# Quick rollback with automatic approval
sysctl rollback api --force --env production
```

#### Rollback Options

- `--version VERSION`: Target version to rollback to
- `--env, -e ENV`: Target environment
- `--revision REVISION`: Rollback to specific revision number
- `--dry-run`: Preview rollback without executing
- `--force`: Skip confirmation prompts
- `--timeout SECONDS`: Rollback timeout
- `--wait`: Wait for rollback to complete

#### Rollback Examples

```bash
# Emergency rollback in production
sysctl rollback api --env production --force --wait

# Rollback to specific revision
sysctl rollback api --revision 5 --env staging

# Preview rollback changes
sysctl rollback api --version v1.1.0 --dry-run
```

### `sysctl status`

Check deployment status and health.

```bash
# Service status
sysctl status api

# All services status
sysctl status --all

# Environment status
sysctl status --env production

# Detailed status with health checks
sysctl status api --detailed
```

#### Status Options

- `--env, -e ENV`: Target environment
- `--all`: Show all services
- `--detailed`: Include detailed health information
- `--watch`: Continuously monitor status
- `--format FORMAT`: Output format (table, json, yaml)
- `--output, -o FORMAT`: Output format shorthand

#### Status Examples

```bash
# Monitor production services
sysctl status --env production --watch --detailed

# Export status as JSON
sysctl status --all --format json > services-status.json

# Quick status check
sysctl status api worker scheduler --format table
```

## Deployment Strategies

### Rolling Deployment

Default strategy for zero-downtime deployments.

```yaml
# deployment-config.yaml
strategy:
  type: "rolling"
  rolling:
    max_unavailable: 1
    max_surge: 1
    pause_between_batches: "30s"

health_check:
  enabled: true
  path: "/health"
  timeout: "30s"
  retries: 3
```

```bash
# Rolling deployment with custom parameters
sysctl deploy api --strategy rolling \
  --set rolling.max_unavailable=2 \
  --set rolling.pause_between_batches=60s
```

### Blue-Green Deployment

Full environment switch for maximum safety.

```yaml
strategy:
  type: "blue-green"
  blue_green:
    switch_timeout: "300s"
    health_check_timeout: "120s"
    auto_promote: false
    cleanup_delay: "600s"
```

```bash
# Blue-green deployment
sysctl deploy api --strategy blue-green --env production

# Check green environment status before promotion
sysctl status api --env production --color green

# Promote green to live
sysctl deploy promote api --env production

# Abort and rollback to blue
sysctl deploy abort api --env production
```

### Canary Deployment

Gradual traffic shifting for risk mitigation.

```yaml
strategy:
  type: "canary"
  canary:
    steps:
      - traffic_percent: 10
        duration: "5m"
      - traffic_percent: 25
        duration: "10m"
      - traffic_percent: 50
        duration: "10m"
      - traffic_percent: 100

    success_threshold: 95
    error_threshold: 1
    auto_promote: true
```

```bash
# Start canary deployment
sysctl deploy api --strategy canary --env production

# Check canary metrics
sysctl deploy canary status api --env production

# Manually promote canary
sysctl deploy canary promote api --env production

# Abort canary deployment
sysctl deploy canary abort api --env production
```

## Template-Based Deployment

### Template Definition

```yaml
# templates/api-service.yaml
apiVersion: v1
kind: Template
metadata:
  name: api-service
  description: "API service deployment template"

parameters:
  - name: SERVICE_NAME
    description: "Service name"
    value: "api"

  - name: IMAGE_TAG
    description: "Container image tag"
    required: true

  - name: REPLICAS
    description: "Number of replicas"
    value: "3"

  - name: CPU_REQUEST
    description: "CPU request"
    value: "100m"

  - name: MEMORY_REQUEST
    description: "Memory request"
    value: "128Mi"

spec:
  services:
    "${SERVICE_NAME}":
      image: "registry.company.com/api:${IMAGE_TAG}"
      replicas: ${REPLICAS}
      resources:
        requests:
          cpu: "${CPU_REQUEST}"
          memory: "${MEMORY_REQUEST}"
        limits:
          cpu: "500m"
          memory: "512Mi"

      environment:
        - name: "DATABASE_URL"
          secret: "database_url"
        - name: "API_VERSION"
          value: "${IMAGE_TAG}"

      health_check:
        path: "/health"
        port: 8080
        initial_delay: 30
        timeout: 5
        retries: 3
```

### Template Usage

```bash
# Deploy using template
sysctl deploy --template api-service.yaml \
  --set IMAGE_TAG=v2.1.0 \
  --set REPLICAS=5 \
  --env production

# List available templates
sysctl template list

# Validate template
sysctl template validate api-service.yaml

# Render template without deploying
sysctl template render api-service.yaml \
  --set IMAGE_TAG=v2.1.0 \
  --output rendered-config.yaml
```

## Health Checks and Monitoring

### Health Check Configuration

```yaml
services:
  api:
    health_check:
      startup:
        path: "/startup"
        port: 8080
        initial_delay: 10
        timeout: 5
        period: 10
        failure_threshold: 30

      liveness:
        path: "/health"
        port: 8080
        initial_delay: 30
        timeout: 5
        period: 10
        failure_threshold: 3

      readiness:
        path: "/ready"
        port: 8080
        initial_delay: 5
        timeout: 5
        period: 5
        failure_threshold: 3
```

### Monitoring During Deployment

```bash
# Monitor deployment with health checks
sysctl deploy api --follow --health-check

# Check health status
sysctl health api --env production

# View health check logs
sysctl logs api --filter health --follow

# Health check dashboard
sysctl dashboard health --env production
```

## Batch Operations

### Multi-Service Deployment

```bash
# Deploy related services together
sysctl deploy api gateway auth --parallel 3

# Deploy with dependency order
sysctl deploy database redis api worker --sequential

# Deploy service groups
sysctl deploy --group backend --env production
sysctl deploy --group frontend --env production
```

### Service Groups

```yaml
# groups/backend.yaml
groups:
  backend:
    services:
      - name: "database"
        priority: 1
      - name: "redis"
        priority: 1
      - name: "api"
        priority: 2
        depends_on: ["database", "redis"]
      - name: "worker"
        priority: 3
        depends_on: ["api"]

    deployment:
      strategy: "rolling"
      parallel_limit: 2
      wait_between_priorities: true
```

```bash
# Deploy service group
sysctl deploy --group backend --env production --wait
```

## Advanced Features

### Deployment Hooks

```yaml
deployment:
  hooks:
    pre_deploy:
      - name: "database_migration"
        command: "sysctl db migrate --env {{ .env }}"
        timeout: "300s"

      - name: "cache_warm"
        command: "sysctl cache warm --env {{ .env }}"
        timeout: "60s"
        continue_on_error: true

    post_deploy:
      - name: "smoke_tests"
        command: "sysctl test smoke --service {{ .service }} --env {{ .env }}"
        timeout: "120s"

      - name: "notify_team"
        command: "sysctl notify --message 'Deployment complete: {{ .service }} {{ .version }}'"
        continue_on_error: true

    rollback:
      - name: "restore_database"
        command: "sysctl db restore --backup pre-deploy-{{ .timestamp }}"
        timeout: "600s"
```

### Configuration Drift Detection

```bash
# Detect configuration drift
sysctl deploy drift api --env production

# Show drift details
sysctl deploy drift api --env production --detailed

# Fix configuration drift
sysctl deploy drift api --env production --fix

# Monitor for drift
sysctl deploy drift --watch --interval 5m --all
```

### Deployment Approval Workflow

```yaml
approval:
  required_for:
    - environment: "production"
    - deployment_strategy: "blue-green"

  approvers:
    - type: "role"
      role: "deployment-approver"
      count: 2

    - type: "user"
      users: ["admin@company.com"]
      count: 1

  timeout: "4h"
  auto_approve_rollbacks: true
```

```bash
# Deploy with approval requirement
sysctl deploy api --env production --request-approval

# Check approval status
sysctl deploy approval status api --env production

# Approve deployment
sysctl deploy approval approve api --env production

# Cancel pending deployment
sysctl deploy approval cancel api --env production
```

## Troubleshooting

### Common Issues

```bash
# Deployment stuck or failing
sysctl deploy debug api --env production

# View deployment logs
sysctl deploy logs api --env production --follow

# Check deployment events
sysctl deploy events api --env production

# Force cleanup of failed deployment
sysctl deploy cleanup api --env production --force
```

### Debug Commands

```bash
# Verbose deployment output
sysctl deploy api --env production --verbose

# Dry run with detailed output
sysctl deploy api --env production --dry-run --verbose

# Test deployment configuration
sysctl deploy test api --env production

# Validate deployment template
sysctl deploy validate --template api-service.yaml
```

### Recovery Operations

```bash
# Emergency stop deployment
sysctl deploy stop api --env production

# Emergency rollback
sysctl deploy emergency-rollback api --env production

# Reset deployment state
sysctl deploy reset api --env production --force

# Recover from partial failure
sysctl deploy recover api --env production --from-checkpoint
```

## Best Practices

### Deployment Safety

1. **Always Use Dry Run**: Test deployments in non-production environments
2. **Health Checks**: Configure comprehensive health checks
3. **Gradual Rollouts**: Use canary deployments for critical services
4. **Monitoring**: Monitor key metrics during and after deployment
5. **Rollback Plan**: Always have a tested rollback procedure

### Environment Promotion

```bash
# Development → Staging
sysctl deploy api --env development
sysctl test integration --env development
sysctl deploy api --env staging --image $(sysctl status api --env development --format json | jq -r '.image')

# Staging → Production
sysctl test acceptance --env staging
sysctl deploy api --env production --strategy blue-green \
  --image $(sysctl status api --env staging --format json | jq -r '.image')
```

### Automation Integration

```yaml
# CI/CD Pipeline Integration
pipeline:
  deploy:
    dev:
      - sysctl deploy api --env development --wait
      - sysctl test smoke --env development

    staging:
      - sysctl deploy api --env staging --strategy rolling --wait
      - sysctl test integration --env staging

    production:
      - sysctl deploy api --env production --strategy blue-green --request-approval
      - sysctl monitor api --env production --duration 10m
```
