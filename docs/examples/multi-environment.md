# Multi-Environment Management

Comprehensive examples for managing complex multi-environment deployments with
environment-specific configurations and promotion workflows.

## Environment Architecture

### Standard Environment Setup

```yaml
# config/environments.yaml
environments:
  development:
    description: "Local development environment"
    tier: "development"
    region: "local"
    auto_deploy: true
    resource_limits:
      cpu: "2 cores"
      memory: "4Gi"
      storage: "20Gi"
    features:
      debug_mode: true
      hot_reload: true
      mock_external_services: true

  testing:
    description: "Automated testing environment"
    tier: "testing"
    region: "us-east-1a"
    auto_deploy: false
    resource_limits:
      cpu: "4 cores"
      memory: "8Gi"
      storage: "50Gi"
    features:
      debug_mode: true
      test_data_seeding: true
      performance_profiling: true

  staging:
    description: "Pre-production staging environment"
    tier: "pre-production"
    region: "us-east-1"
    auto_deploy: false
    resource_limits:
      cpu: "8 cores"
      memory: "16Gi"
      storage: "100Gi"
    features:
      debug_mode: false
      production_like_data: true
      ssl_required: true

  production:
    description: "Production environment"
    tier: "production"
    region: "us-east-1"
    auto_deploy: false
    resource_limits:
      cpu: "32 cores"
      memory: "64Gi"
      storage: "500Gi"
    features:
      debug_mode: false
      ssl_required: true
      monitoring_enhanced: true
      backup_enabled: true

  production-eu:
    description: "Production environment - Europe"
    tier: "production"
    region: "eu-west-1"
    auto_deploy: false
    resource_limits:
      cpu: "32 cores"
      memory: "64Gi"
      storage: "500Gi"
    features:
      debug_mode: false
      ssl_required: true
      monitoring_enhanced: true
      backup_enabled: true
```

### Environment-Specific Configuration

```yaml
# config/services/api/development.yaml
api:
  replicas: 1
  image_tag: "latest"
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      cpu: "500m"
      memory: "512Mi"
  environment:
    LOG_LEVEL: "DEBUG"
    DATABASE_URL: "postgresql://localhost:5432/myapp_dev"
    REDIS_URL: "redis://localhost:6379/0"
    API_BASE_URL: "http://localhost:8080"
    EXTERNAL_API_MOCK: "true"
  health_check:
    initial_delay: 10
    timeout: 5
    interval: 30
```

```yaml
# config/services/api/production.yaml
api:
  replicas: 5
  image_tag: "v2.1.0"
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "2Gi"
  environment:
    LOG_LEVEL: "INFO"
    DATABASE_URL: "secret://production/database-url"
    REDIS_URL: "secret://production/redis-url"
    API_BASE_URL: "https://api.company.com"
    EXTERNAL_API_MOCK: "false"
  health_check:
    initial_delay: 30
    timeout: 10
    interval: 15
  autoscaling:
    enabled: true
    min_replicas: 3
    max_replicas: 10
    target_cpu: 70
    target_memory: 80
```

## Environment Lifecycle Management

### Environment Creation and Setup

```bash
# Create new environment
sysctl env create qa-v2 --clone-from staging --region us-west-2

# Setup environment with custom configuration
sysctl env setup qa-v2 \
  --config-profile qa \
  --resource-tier medium \
  --enable-features debug_mode,test_data

# Initialize environment infrastructure
sysctl env init qa-v2 \
  --provision-infrastructure \
  --setup-monitoring \
  --configure-networking

# Validate environment setup
sysctl env validate qa-v2 --comprehensive
```

### Environment Configuration Management

```bash
# Apply environment-specific configuration
sysctl config apply --env production --file config/production-overrides.yaml

# Compare configurations between environments
sysctl config diff staging production

# Sync configuration from one environment to another
sysctl config sync --from staging --to qa-v2 --exclude secrets

# Validate configuration consistency
sysctl config validate --all-environments --check-consistency
```

### Environment Promotion Workflows

```bash
# Promote code from development to testing
sysctl promote development testing \
  --validate-tests \
  --auto-merge-config

# Promote with approval requirement
sysctl promote staging production \
  --require-approval \
  --approval-timeout 3600 \
  --approvers "team-lead,devops-admin"

# Promote specific services only
sysctl promote staging production \
  --services api,worker \
  --skip-database

# Rollback promotion if issues found
sysctl promote rollback production staging \
  --reason "Performance regression detected"
```

## Multi-Environment Deployment Strategies

### Progressive Deployment

```yaml
# workflows/progressive-deployment.yaml
name: Progressive Multi-Environment Deployment
description: Deploy through environments with gates and validations

environments:
  - name: development
    auto_promote: true
    gates: []

  - name: testing
    auto_promote: false
    gates:
      - unit_tests
      - integration_tests
      - security_scan

  - name: staging
    auto_promote: false
    gates:
      - acceptance_tests
      - performance_tests
      - manual_approval

  - name: production
    auto_promote: false
    gates:
      - final_approval
      - change_window_check
      - capacity_check

deployment_flow:
  - name: deploy_to_development
    command: sysctl deploy --all --env development --image-tag ${GIT_COMMIT}

  - name: validate_development
    command: sysctl test smoke --env development --timeout 300

  - name: promote_to_testing
    command: sysctl promote development testing
    condition: validate_development.success

  - name: run_comprehensive_tests
    parallel: true
    steps:
      - command: sysctl test unit --env testing
      - command: sysctl test integration --env testing --timeout 1800
      - command: sysctl security scan --env testing

  - name: promote_to_staging
    command: sysctl promote testing staging
    condition: run_comprehensive_tests.all_success

  - name: staging_validation
    parallel: true
    steps:
      - command: sysctl test acceptance --env staging --timeout 2400
      - command: sysctl test performance --env staging --baseline
      - command: sysctl test load --env staging --duration 900

  - name: manual_approval_gate
    command: sysctl approval request --title "Production deployment approval" --timeout 86400
    condition: staging_validation.all_success

  - name: production_pre_checks
    parallel: true
    steps:
      - command: sysctl capacity check --env production --required-resources ${RESOURCE_REQUIREMENTS}
      - command: sysctl maintenance-window check --env production
      - command: sysctl dependencies check --env production --external

  - name: deploy_to_production
    command: sysctl deploy --all --env production --strategy blue-green
    condition: manual_approval_gate.approved AND production_pre_checks.all_success

  - name: production_validation
    command: sysctl health-check --all --env production --timeout 600

  - name: notify_completion
    command: sysctl notify team "Production deployment completed successfully" --channel slack
```

### Canary Deployment Across Environments

```bash
# Start canary deployment in staging
sysctl deploy api --env staging --strategy canary --percentage 25 --image v2.2.0

# Monitor canary metrics
sysctl metrics monitor --env staging --service api --canary --duration 900

# Promote canary based on metrics
if sysctl metrics validate --env staging --service api --canary --thresholds success-criteria.yaml; then
  sysctl deploy canary-promote api --env staging --percentage 100

  # If staging canary succeeds, start production canary
  sysctl deploy api --env production --strategy canary --percentage 10 --image v2.2.0
fi
```

### Feature Flag Management

```yaml
# config/feature-flags.yaml
feature_flags:
  new_checkout_flow:
    development: true
    testing: true
    staging: true
    production: false

  enhanced_search:
    development: true
    testing: true
    staging: false
    production: false

  payment_provider_v2:
    development: false
    testing: true
    staging: false
    production: false
# Conditional deployment based on feature flags
```

```bash
# Deploy with feature flags
sysctl deploy api --env production --feature-flags config/feature-flags.yaml

# Update feature flag across environments
sysctl feature-flag set new_checkout_flow true --env production

# Gradual feature rollout
sysctl feature-flag rollout enhanced_search --env production --percentage 25 --duration 2h
```

## Configuration Management Patterns

### Environment-Specific Secrets

```bash
# Set environment-specific secrets
sysctl secret set DATABASE_PASSWORD --env development --prompt
sysctl secret set DATABASE_PASSWORD --env staging --from-file staging-db-password.txt
sysctl secret set DATABASE_PASSWORD --env production --from-vault prod-secrets/db-password

# Sync secrets between environments (excluding production)
sysctl secret sync --from staging --to testing --confirm

# Rotate secrets across environments
sysctl secret rotate DATABASE_PASSWORD --environments staging,production --schedule
```

### Configuration Inheritance

```yaml
# config/base.yaml - Base configuration
base_config:
  logging:
    level: "INFO"
    format: "json"
  database:
    pool_size: 10
    timeout: 30
  cache:
    ttl: 3600
    max_size: "1GB"
```

```yaml
# config/development.yaml - Development overrides
extends: base_config
overrides:
  logging:
    level: "DEBUG"
    format: "console"
  database:
    pool_size: 5
  features:
    debug_mode: true
    mock_services: true
```

```yaml
# config/production.yaml - Production overrides
extends: base_config
overrides:
  database:
    pool_size: 50
    timeout: 60
  cache:
    ttl: 7200
    max_size: "10GB"
  security:
    ssl_required: true
    rate_limiting: true
  monitoring:
    enhanced: true
```

### Configuration Validation

```bash
# Validate configuration across environments
sysctl config validate --all-environments --check-consistency

# Check for configuration drift
sysctl config drift-check --baseline production --compare staging,testing

# Generate configuration report
sysctl config report --environments production,staging --format pdf --output config-audit.pdf
```

## Environment Monitoring and Observability

### Multi-Environment Dashboards

```yaml
# config/monitoring/environments.yaml
dashboards:
  environment_overview:
    title: "Multi-Environment Overview"
    panels:
      - title: "Service Health by Environment"
        type: "heatmap"
        query: |
          up{environment=~"development|testing|staging|production"}

      - title: "Request Rate Comparison"
        type: "graph"
        query: |
          sum(rate(http_requests_total[5m])) by (environment)

      - title: "Error Rate by Environment"
        type: "singlestat"
        query: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (environment) / 
          sum(rate(http_requests_total[5m])) by (environment) * 100

  environment_details:
    title: "Environment Details - ${environment}"
    variables:
      - name: "environment"
        type: "query"
        query: "label_values(up, environment)"
    panels:
      - title: "Service Status"
        type: "table"
        query: |
          up{environment="$environment"}
```

### Cross-Environment Alerting

```yaml
# config/alerts/multi-environment.yaml
alerts:
  cross_environment_comparison:
    - name: "ProductionErrorRateHigh"
      condition: |
        (
          sum(rate(http_requests_total{status=~"5..", environment="production"}[5m])) /
          sum(rate(http_requests_total{environment="production"}[5m]))
        ) > 0.01
      annotations:
        summary: "Production error rate is unusually high"
        runbook: "https://runbooks.company.com/high-error-rate"

    - name: "EnvironmentDrift"
      condition: |
        abs(
          avg(cpu_usage{environment="production"}) - 
          avg(cpu_usage{environment="staging"})
        ) > 0.3
      annotations:
        summary: "Significant performance difference between production and staging"

  environment_health:
    - name: "EnvironmentDown"
      condition: |
        up{environment!="development"} == 0
      annotations:
        summary: "Environment {{ $labels.environment }} is down"
        severity: "critical"
```

### Environment Comparison Tools

```bash
# Compare performance across environments
sysctl metrics compare --environments production,staging --metric response_time --period 24h

# Generate environment health report
sysctl health report --environments all --include-trends --output health-report.html

# Compare resource utilization
sysctl resources compare --environments production,staging --resources cpu,memory,disk

# Analyze cost differences
sysctl cost compare --environments production,staging --breakdown-by-service
```

## Data Management Across Environments

### Database Management

```bash
# Create sanitized database copy for lower environments
sysctl database sanitize --from production --to staging \
  --anonymize-pii \
  --reduce-size 50% \
  --exclude-tables audit_logs,user_sessions

# Sync schema changes across environments
sysctl database schema-sync --from development --to testing,staging

# Backup databases across environments
sysctl backup create --all-environments --exclude development --schedule daily

# Restore database to specific environment
sysctl backup restore --env staging --backup prod-backup-20240115 --confirm
```

### Test Data Management

```yaml
# config/test-data.yaml
test_data:
  development:
    users:
      count: 100
      type: "synthetic"
    orders:
      count: 1000
      date_range: "30d"

  testing:
    users:
      count: 1000
      type: "anonymized_production"
    orders:
      count: 10000
      date_range: "90d"

  staging:
    users:
      count: 10000
      type: "anonymized_production"
    orders:
      count: 100000
      date_range: "365d"
```

```bash
# Generate test data for environment
sysctl test-data generate --env testing --config config/test-data.yaml

# Refresh test data from production
sysctl test-data refresh --env staging --from production --anonymize

# Clear test data
sysctl test-data clear --env development --confirm
```

## Advanced Multi-Environment Patterns

### Environment Branching Strategy

```bash
# Create feature environment from branch
sysctl env create feature-new-api --from-branch feature/new-api --clone-config staging

# Auto-deploy feature branch to feature environment
sysctl config set --env feature-new-api auto_deploy.branch feature/new-api
sysctl config set --env feature-new-api auto_deploy.enabled true

# Merge feature environment back when ready
sysctl env merge feature-new-api --to development --cleanup
```

### Multi-Tenant Environment Management

```yaml
# config/tenants.yaml
tenants:
  customer-a:
    environments:
      staging: "customer-a-staging"
      production: "customer-a-production"
    resources:
      tier: "enterprise"
      isolation: "dedicated"

  customer-b:
    environments:
      staging: "customer-b-staging"
      production: "customer-b-production"
    resources:
      tier: "standard"
      isolation: "shared"
```

```bash
# Deploy to tenant-specific environments
sysctl deploy --tenant customer-a --env production --image v2.1.0-enterprise

# Manage tenant configuration
sysctl tenant config set customer-a feature_limits.api_calls 100000
sysctl tenant config apply customer-a --env production
```

### Environment Automation

```yaml
# workflows/environment-lifecycle.yaml
name: Environment Lifecycle Management
description: Automated environment creation, maintenance, and cleanup

schedule:
  - name: "daily-environment-health-check"
    cron: "0 6 * * *"
    command: sysctl health-check --all-environments --report

  - name: "weekly-test-data-refresh"
    cron: "0 2 * * 1"
    command: sysctl test-data refresh --env testing,staging --from production

  - name: "monthly-environment-cleanup"
    cron: "0 3 1 * *"
    command: sysctl env cleanup --unused --older-than 30d --dry-run

triggers:
  - name: "auto-create-feature-environment"
    event: "git.branch.created"
    condition: "branch.name starts_with 'feature/'"
    command: sysctl env create ${branch.name} --from-template feature-template

  - name: "auto-deploy-to-development"
    event: "git.push"
    condition: "branch.name == 'develop'"
    command: sysctl deploy --all --env development --image ${commit.sha}
```

## Troubleshooting Multi-Environment Issues

### Environment Debugging

```bash
# Compare environment configurations
sysctl env debug --compare staging production --show-differences

# Check environment connectivity
sysctl network test --from development --to staging,production --services all

# Validate environment state
sysctl env validate staging --against-baseline production --fix-issues

# Generate environment troubleshooting report
sysctl env troubleshoot staging --comprehensive --output troubleshoot-report.html
```

### Common Issues and Solutions

```bash
# Configuration drift between environments
sysctl config sync-check --baseline production --targets staging,testing
sysctl config drift-fix --from production --to staging --interactive

# Environment-specific performance issues
sysctl performance compare --environments production,staging --identify-bottlenecks
sysctl resources optimize --env staging --match-performance production

# Cross-environment dependency issues
sysctl dependencies validate --cross-environment --fix-connectivity
sysctl service-mesh config-sync --environments all

# Data inconsistency issues
sysctl database compare --environments production,staging --check-schema
sysctl test-data validate --env staging --against-rules data-validation.yaml
```

This comprehensive guide provides patterns and examples for managing complex multi-environment
scenarios, ensuring consistency, reliability, and efficient workflows across your entire
deployment pipeline.
