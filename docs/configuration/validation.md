# Configuration Validation

The System Control CLI includes comprehensive configuration validation to
ensure your settings are correct, secure, and consistent before deployment
operations.

## Overview

Configuration validation provides:

- **Schema Validation**: Ensures configuration structure matches expected format
- **Type Checking**: Validates data types and value ranges
- **Dependency Validation**: Checks required dependencies and relationships
- **Security Validation**: Identifies potential security issues
- **Business Rule Validation**: Enforces organizational policies and constraints
- **Integration Testing**: Validates connectivity to external services

## Validation Levels

### 1. Basic Validation

- Schema compliance
- Required fields
- Data type validation
- Basic value constraints

### 2. Advanced Validation

- Cross-field dependencies
- Business rule enforcement
- Security policy compliance
- Resource constraint checking

### 3. Integration Validation

- External service connectivity
- API endpoint validation
- Authentication testing
- Permission verification

### 4. End-to-End Validation

- Complete workflow testing
- Deployment simulation
- Health check validation
- Rollback capability testing

## Schema Definition

### Core Schema Structure

```yaml
# schema/config.yaml
$schema: "http://json-schema.org/draft-07/schema#"
type: "object"
required: ["metadata", "environment"]

properties:
  metadata:
    type: "object"
    required: ["name", "version"]
    properties:
      name:
        type: "string"
        pattern: "^[a-z0-9-]+$"
        minLength: 1
        maxLength: 63

      version:
        type: "string"
        pattern: "^[0-9]+\\.[0-9]+\\.[0-9]+$"

      description:
        type: "string"
        maxLength: 500

  environment:
    type: "object"
    required: ["name", "type"]
    properties:
      name:
        type: "string"
        enum: ["development", "staging", "production"]

      type:
        type: "string"
        enum: ["development", "testing", "production"]

  services:
    type: "object"
    patternProperties:
      "^[a-z0-9-]+$":
        $ref: "#/definitions/service"

definitions:
  service:
    type: "object"
    required: ["image", "replicas"]
    properties:
      image:
        type: "string"
        pattern: "^[a-z0-9.-]+/[a-z0-9.-]+:[a-z0-9.-]+$"

      replicas:
        type: "integer"
        minimum: 1
        maximum: 100

      resources:
        $ref: "#/definitions/resources"

  resources:
    type: "object"
    properties:
      requests:
        $ref: "#/definitions/resource_spec"
      limits:
        $ref: "#/definitions/resource_spec"

  resource_spec:
    type: "object"
    properties:
      cpu:
        type: "string"
        pattern: "^[0-9]+m?$"
      memory:
        type: "string"
        pattern: "^[0-9]+[MGT]i?$"
```

## Validation Commands

### Basic Validation

```bash
# Validate current configuration
sysctl config validate

# Validate specific profile
sysctl config validate --profile production

# Validate environment configuration
sysctl env validate production

# Validate service configuration
sysctl service validate api --env production
```

### Advanced Validation Options

```bash
# Validate with detailed output
sysctl config validate --verbose

# Validate against specific schema version
sysctl config validate --schema-version 2.0

# Validate with custom rules
sysctl config validate --rules custom-rules.yaml

# Validate and fix common issues
sysctl config validate --fix
```

### Command Validation Levels

```bash
# Basic schema validation only
sysctl config validate --level basic

# Include business rules
sysctl config validate --level advanced

# Include connectivity tests
sysctl config validate --level integration

# Full end-to-end validation
sysctl config validate --level complete
```

## Custom Validation Rules

### Rule Definition

```yaml
# validation/custom-rules.yaml
rules:
  - name: "production_replica_count"
    description: "Production services must have at least 2 replicas"
    level: "error"
    applies_to: ["production"]
    condition: |
      environment.type == "production" &&
      any(services.*.replicas < 2)
    message: "Production services must have at least 2 replicas for high availability"

  - name: "resource_limits_required"
    description: "All services must have resource limits defined"
    level: "warning"
    condition: |
      any(services.*.resources.limits == null)
    message: "Services without resource limits may consume excessive resources"

  - name: "secure_image_registry"
    description: "Images must come from approved registries"
    level: "error"
    condition: |
      any(services.*.image !~ "^(registry.company.com|docker.io)/.*")
    message: "Images must come from approved registries"

  - name: "environment_naming"
    description: "Environment names must follow naming convention"
    level: "error"
    condition: |
      environment.name !~ "^(dev|staging|prod)(-[a-z0-9-]+)?$"
    message: "Environment name must start with dev, staging, or prod"

  - name: "health_check_required"
    description: "Services must have health checks in production"
    level: "error"
    applies_to: ["production"]
    condition: |
      environment.type == "production" &&
      any(services.*.health_check.enabled != true)
    message: "Production services must have health checks enabled"
```

### Rule Categories

#### Security Rules

```yaml
security_rules:
  - name: "no_privileged_containers"
    condition: "any(services.*.security_context.privileged == true)"
    message: "Privileged containers are not allowed"

  - name: "tls_required"
    applies_to: ["production"]
    condition: "any(services.*.tls.enabled != true)"
    message: "TLS must be enabled for production services"

  - name: "secret_management"
    condition: "any(services.*.env contains 'PASSWORD' or services.*.env contains 'SECRET')"
    message: "Sensitive values should use secret management"
```

#### Resource Rules

```yaml
resource_rules:
  - name: "cpu_limits"
    condition: "any(services.*.resources.limits.cpu == null)"
    message: "CPU limits must be specified for all services"

  - name: "memory_requests_reasonable"
    condition: |
      any(services.*.resources.requests.memory matches '^[0-9]+[GT]i?$')
    message: "Memory requests above 1GB should be reviewed"
```

#### Deployment Rules

```yaml
deployment_rules:
  - name: "rolling_update_strategy"
    applies_to: ["production"]
    condition: "deployment.strategy != 'rolling'"
    message: "Production deployments should use rolling update strategy"

  - name: "health_check_timeout"
    condition: "any(services.*.health_check.timeout > 300)"
    message: "Health check timeout should not exceed 5 minutes"
```

## Validation Integration

### CI/CD Integration

```yaml
# .github/workflows/validate.yml
name: Configuration Validation
on:
  pull_request:
    paths:
      - "config/**"
      - "environments/**"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install System Control CLI
        run: pip install system-control-cli

      - name: Validate Configuration
        run: |
          sysctl config validate --all-profiles
          sysctl config validate --level integration

      - name: Security Scan
        run: |
          sysctl config security-scan
          sysctl config validate --rules security-rules.yaml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: config-validation
        name: Validate System Control Configuration
        entry: sysctl config validate
        language: system
        files: '^(config|environments)/.*\.yaml$'

      - id: security-validation
        name: Security Validation
        entry: sysctl config security-scan
        language: system
        files: '^(config|environments)/.*\.yaml$'
```

## Validation Reporting

### Report Formats

```bash
# JSON report
sysctl config validate --format json > validation-report.json

# HTML report
sysctl config validate --format html > validation-report.html

# JUnit XML (for CI systems)
sysctl config validate --format junit > validation-results.xml

# Summary report
sysctl config validate --format summary
```

### Report Content

```json
{
  "validation_summary": {
    "timestamp": "2024-01-15T10:30:00Z",
    "profile": "production",
    "status": "failed",
    "total_rules": 25,
    "passed": 20,
    "warnings": 3,
    "errors": 2,
    "duration_ms": 1500
  },
  "results": [
    {
      "rule": "production_replica_count",
      "level": "error",
      "path": "services.api.replicas",
      "message": "Production services must have at least 2 replicas",
      "current_value": 1,
      "expected": ">= 2"
    },
    {
      "rule": "resource_limits_required",
      "level": "warning",
      "path": "services.worker.resources.limits",
      "message": "Services without resource limits may consume excessive resources",
      "suggestion": "Add CPU and memory limits"
    }
  ],
  "recommendations": [
    "Increase replica count for API service",
    "Add resource limits to worker service",
    "Enable health checks for background services"
  ]
}
```

## Automated Remediation

### Auto-Fix Capabilities

```bash
# Fix common configuration issues
sysctl config validate --fix

# Fix specific rule violations
sysctl config fix --rule "resource_limits_required"

# Interactive fixing
sysctl config validate --interactive-fix

# Generate fix suggestions
sysctl config validate --suggest-fixes
```

### Fix Templates

```yaml
# fixes/resource-limits.yaml
rule: "resource_limits_required"
description: "Add default resource limits to services"
fix_template: |
  services:
    {{ service_name }}:
      resources:
        limits:
          cpu: "{{ default_cpu_limit | default('500m') }}"
          memory: "{{ default_memory_limit | default('512Mi') }}"
        requests:
          cpu: "{{ default_cpu_request | default('100m') }}"
          memory: "{{ default_memory_request | default('128Mi') }}"
```

## Environment-Specific Validation

### Development Environment

```yaml
development_validation:
  rules:
    - relaxed_security: true
    - require_resource_limits: false
    - allow_latest_tags: true

  warnings_as_errors: false
  skip_integration_tests: true
```

### Production Environment

```yaml
production_validation:
  rules:
    - strict_security: true
    - require_resource_limits: true
    - require_health_checks: true
    - require_backup_config: true

  warnings_as_errors: true
  require_manual_approval: true
  validation_timeout: 300
```

## Validation Performance

### Optimization

```bash
# Cache validation results
sysctl config validate --cache

# Parallel validation
sysctl config validate --parallel

# Skip expensive checks in development
sysctl config validate --quick --profile development

# Validate only changed files
sysctl config validate --changed-only
```

### Performance Monitoring

```yaml
validation_metrics:
  timing:
    schema_validation: "50ms"
    business_rules: "200ms"
    integration_tests: "2000ms"
    total: "2250ms"

  cache_hits: 15
  cache_misses: 3
  rules_evaluated: 25
  tests_executed: 8
```

## Best Practices

### Rule Development

1. **Clear Naming**: Use descriptive rule names
2. **Good Messages**: Provide helpful error messages with suggestions
3. **Appropriate Levels**: Use correct severity levels
4. **Performance**: Optimize rule conditions for speed
5. **Testing**: Test rules with various configurations

### Validation Workflow

1. **Early Validation**: Validate during development
2. **Automated Validation**: Include in CI/CD pipelines
3. **Progressive Validation**: Use different levels for different stages
4. **Regular Review**: Periodically review and update rules
5. **Documentation**: Document custom rules and their purpose

### Error Handling

```bash
# Graceful degradation
sysctl config validate --continue-on-error

# Fail fast for critical errors
sysctl config validate --fail-fast

# Retry failed validations
sysctl config validate --retry 3

# Timeout handling
sysctl config validate --timeout 60
```

## Troubleshooting

### Common Validation Issues

```bash
# Debug validation failures
sysctl config validate --debug

# Show rule evaluation details
sysctl config validate --trace-rules

# Test specific rules
sysctl config validate --rule "production_replica_count"

# Validate rule syntax
sysctl validation rule-check custom-rules.yaml
```

### Performance Issues

```bash
# Profile validation performance
sysctl config validate --profile-performance

# Disable slow rules temporarily
sysctl config validate --exclude-rules "integration_tests"

# Use cached results
sysctl config validate --use-cache --max-age 1h
```
