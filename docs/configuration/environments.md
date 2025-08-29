# Environment Management

The System Control CLI provides comprehensive environment management
capabilities, allowing
you to define, configure, and switch between different deployment
environments with ease.

## Overview

Environment management enables you to:

- Define multiple environments (development, staging, production)
- Maintain environment-specific configurations
- Seamlessly switch between environments
- Validate environment configurations
- Monitor environment health and status
- Synchronize configurations across environments

## Environment Configuration

### Environment Definition

Environments are defined in configuration files or through the CLI:

```yaml
# config.yaml
environments:
  development:
    name: "development"
    description: "Development environment for testing"
    active: true

  staging:
    name: "staging"
    description: "Staging environment for pre-production testing"

  production:
    name: "production"
    description: "Production environment"
    protected: true
```

### Environment-Specific Settings

Each environment can have its own configuration:

```yaml
# environments/development.yaml
metadata:
  name: "development"
  type: "development"
  region: "us-west-2"
  availability_zones: ["us-west-2a", "us-west-2b"]

infrastructure:
  kubernetes:
    cluster: "dev-cluster"
    context: "dev-context"
    namespace: "development"

  databases:
    primary:
      host: "dev-db.internal"
      port: 5432
      name: "app_dev"

  cache:
    redis:
      host: "dev-redis.internal"
      port: 6379

services:
  defaults:
    replicas: 1
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

monitoring:
  enabled: false
  debug_logging: true

security:
  strict_mode: false
  tls_required: false
```

```yaml
# environments/production.yaml
metadata:
  name: "production"
  type: "production"
  region: "us-east-1"
  availability_zones: ["us-east-1a", "us-east-1b", "us-east-1c"]

infrastructure:
  kubernetes:
    cluster: "prod-cluster"
    context: "prod-context"
    namespace: "production"

  databases:
    primary:
      host: "prod-db.internal"
      port: 5432
      name: "app_prod"
    read_replicas:
      - "prod-db-read-1.internal"
      - "prod-db-read-2.internal"

  cache:
    redis:
      cluster:
        - "prod-redis-1.internal:6379"
        - "prod-redis-2.internal:6379"
        - "prod-redis-3.internal:6379"

services:
  defaults:
    replicas: 3
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

monitoring:
  enabled: true
  metrics_retention: "90d"
  alerting: true

security:
  strict_mode: true
  tls_required: true
  network_policies: true
```

## Environment Operations

### Listing Environments

```bash
# List all environments
sysctl env list

# List with details
sysctl env list --detailed

# List specific environment types
sysctl env list --type production
```

### Creating Environments

```bash
# Create environment interactively
sysctl env create staging --interactive

# Create from template
sysctl env create staging --template development

# Create with specific configuration
sysctl env create staging --config environments/staging.yaml

# Clone existing environment
sysctl env clone development staging
```

### Environment Information

```bash
# Show environment details
sysctl env show production

# Show environment status
sysctl env status production

# Show environment configuration
sysctl env config production

# Show environment health
sysctl env health production
```

### Switching Environments

```bash
# Set active environment
sysctl env set production

# Switch temporarily
sysctl --env staging deploy myservice

# Switch with confirmation
sysctl env set production --confirm
```

## Environment Types

### Development Environment

Characteristics:

- Minimal resource allocation
- Debug logging enabled
- Relaxed security policies
- Fast deployment strategies
- Single replica services

Configuration focus:

- Quick iteration
- Easy debugging
- Cost optimization
- Developer productivity

### Staging Environment

Characteristics:

- Production-like configuration
- Comprehensive testing
- Security validation
- Performance testing
- Data anonymization

Configuration focus:

- Production simulation
- Integration testing
- Performance validation
- Security verification

### Production Environment

Characteristics:

- High availability
- Security hardening
- Performance optimization
- Comprehensive monitoring
- Backup and disaster recovery

Configuration focus:

- Reliability and stability
- Security and compliance
- Performance and scalability
- Monitoring and alerting

## Multi-Region Support

### Region Configuration

```yaml
# environments/production.yaml
regions:
  primary:
    name: "us-east-1"
    kubernetes:
      cluster: "prod-east-cluster"
      context: "prod-east-context"
    databases:
      primary: "prod-db-east.internal"

  secondary:
    name: "us-west-2"
    kubernetes:
      cluster: "prod-west-cluster"
      context: "prod-west-context"
    databases:
      replica: "prod-db-west.internal"

deployment:
  strategy: "multi-region"
  primary_region: "us-east-1"
  failover_enabled: true
```

### Cross-Region Operations

```bash
# Deploy to specific region
sysctl deploy myservice --region us-east-1

# Deploy to all regions
sysctl deploy myservice --all-regions

# Regional status
sysctl env status production --region us-east-1

# Cross-region sync
sysctl env sync production --from us-east-1 --to us-west-2
```

## Environment Validation

### Configuration Validation

```bash
# Validate environment configuration
sysctl env validate production

# Validate all environments
sysctl env validate --all

# Validate against schema
sysctl env validate production --schema

# Deep validation with connectivity tests
sysctl env validate production --deep
```

### Health Checks

```bash
# Environment health check
sysctl env health production

# Component-specific health
sysctl env health production --component database
sysctl env health production --component kubernetes
sysctl env health production --component monitoring

# Continuous health monitoring
sysctl env monitor production --interval 30s
```

## Environment Synchronization

### Configuration Sync

```bash
# Sync configuration between environments
sysctl env sync development staging --config-only

# Sync specific services
sysctl env sync staging production --services "api,worker"

# Dry run sync
sysctl env sync staging production --dry-run

# Sync with exclusions
sysctl env sync development staging --exclude "database,secrets"
```

### Service Promotion

```bash
# Promote service from staging to production
sysctl service promote api --from staging --to production

# Promote with validation
sysctl service promote api --from staging --to production --validate

# Batch promotion
sysctl service promote --from staging --to production --all
```

## Environment Variables

### Variable Management

```bash
# Set environment variable
sysctl env var set DATABASE_URL "postgres://..." --env production

# List environment variables
sysctl env var list --env production

# Import variables from file
sysctl env var import production.env --env production

# Export variables
sysctl env var export --env production --format env
```

### Variable Templates

```yaml
# environments/production.yaml
variables:
  database_url:
    template: "postgres://{{ db_user }}:{{ db_pass }}@{{ db_host }}:{{ db_port }}/{{ db_name }}"
    values:
      db_user: "${DB_USER}"
      db_pass: "${DB_PASS}"
      db_host: "prod-db.internal"
      db_port: 5432
      db_name: "app_prod"

  api_base_url:
    template: "https://api.{{ domain }}"
    values:
      domain: "company.com"
```

## Environment Security

### Access Control

```yaml
# environments/production.yaml
security:
  access_control:
    roles:
      - name: "admin"
        permissions: ["*"]
        users: ["admin@company.com"]

      - name: "deployer"
        permissions: ["deploy", "rollback", "status"]
        users: ["deployer@company.com"]

      - name: "viewer"
        permissions: ["status", "logs"]
        groups: ["developers"]

  protection:
    destructive_operations: true
    require_approval: true
    approval_timeout: "1h"
```

### Sensitive Data

```bash
# Encrypt sensitive environment data
sysctl env encrypt production --fields "database.password,api.keys"

# Use secret backends
sysctl env secret set DATABASE_PASSWORD --backend vault --env production

# Rotate secrets
sysctl env secret rotate --all --env production
```

## Environment Monitoring

### Metrics and Alerting

```yaml
# environments/production.yaml
monitoring:
  metrics:
    collection_interval: "30s"
    retention_period: "90d"
    exporters:
      - "prometheus"
      - "grafana"

  alerts:
    rules:
      - name: "environment_health"
        condition: "environment.health.score < 0.8"
        severity: "warning"
        channels: ["slack", "email"]

      - name: "service_down"
        condition: "service.replicas.available == 0"
        severity: "critical"
        channels: ["pagerduty"]

  dashboards:
    - name: "environment_overview"
      type: "grafana"
      template: "environment-dashboard.json"
```

### Environment Dashboard

```bash
# View environment dashboard
sysctl env dashboard production

# Live monitoring
sysctl env monitor production --live

# Generate environment report
sysctl env report production --format pdf
```

## Disaster Recovery

### Backup Configuration

```yaml
# environments/production.yaml
backup:
  enabled: true
  schedule: "0 2 * * *" # Daily at 2 AM
  retention: "30d"

  targets:
    - type: "configuration"
      destination: "s3://backups/config"

    - type: "database"
      destination: "s3://backups/database"
      encryption: true

    - type: "secrets"
      destination: "vault://backups/secrets"
      encryption: true

restore:
  validation: true
  notification: true
  rollback_on_failure: true
```

### Disaster Recovery Operations

```bash
# Create environment backup
sysctl env backup production

# Restore from backup
sysctl env restore production --from backup-2024-01-15

# Test disaster recovery
sysctl env dr-test production --scenario "region_failure"

# Failover to secondary region
sysctl env failover production --to us-west-2
```

## Best Practices

### Environment Naming

- Use clear, descriptive names
- Include environment type and purpose
- Consider team or project prefixes
- Maintain consistent naming across environments

Examples:

- `webapp-dev`, `webapp-staging`, `webapp-prod`
- `platform-development`, `platform-production`
- `team-alpha-dev`, `team-alpha-prod`

### Configuration Management

1. **Environment Parity**: Keep environments as similar as possible
2. **Infrastructure as Code**: Use configuration files for all settings
3. **Version Control**: Track environment configuration changes
4. **Validation**: Regular validation and health checks
5. **Documentation**: Document environment-specific procedures

### Security Guidelines

1. **Access Control**: Implement role-based access control
2. **Secret Management**: Use dedicated secret management systems
3. **Network Isolation**: Implement network segmentation
4. **Audit Logging**: Track all environment changes
5. **Regular Reviews**: Periodic security assessments

## Troubleshooting

### Common Issues

```bash
# Environment configuration errors
sysctl env validate production --verbose

# Connectivity issues
sysctl env test-connection production

# Service deployment failures
sysctl env debug production --service api

# Configuration drift
sysctl env drift production --baseline
```

### Debug Commands

```bash
# Environment debug information
sysctl env debug production

# Configuration comparison
sysctl env diff staging production

# Environment logs
sysctl env logs production --follow

# Resource utilization
sysctl env resources production --detailed
```
