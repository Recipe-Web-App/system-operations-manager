# Configuration Profiles

The System Control CLI uses a flexible profile-based configuration system that allows you to
maintain different settings for various environments, projects, or deployment scenarios.

## Overview

Profiles enable you to:

- Maintain separate configurations for different environments (dev, staging, production)
- Switch between different deployment strategies
- Organize settings by project or team
- Inherit common settings while customizing specific values
- Share configurations across teams

## Profile Structure

### Default Profile Locations

```text
~/.config/system-control/
├── config.yaml              # Global configuration
├── profiles/                 # Profile-specific configurations
│   ├── base.yaml            # Base profile with common settings
│   ├── development.yaml     # Development environment
│   ├── staging.yaml         # Staging environment
│   ├── production.yaml      # Production environment
│   └── custom-project.yaml  # Custom project configuration
```

### Profile Inheritance

Profiles support inheritance, allowing you to define common settings in a base profile and
extend them in specific profiles:

```yaml
# profiles/base.yaml
metadata:
  name: "base"
  description: "Base configuration for all environments"

logging:
  level: "INFO"
  format: "structured"

plugins:
  enabled:
    - "deployment"
    - "monitoring"

confirmation:
  destructive_operations: true
```

```yaml
# profiles/production.yaml
metadata:
  name: "production"
  description: "Production environment configuration"
  inherits: ["base"]

logging:
  level: "WARNING" # Override base setting

security:
  strict_mode: true
  audit_logging: true

deployment:
  strategy: "blue-green"
  health_check_timeout: 300
  rollback_on_failure: true
```

## Creating and Managing Profiles

### Creating a New Profile

```bash
# Create profile interactively
sysctl profile create myproject --interactive

# Create profile from template
sysctl profile create myproject --template development

# Create profile with inheritance
sysctl profile create myproject --inherit base,security

# Clone existing profile
sysctl profile clone development myproject
```

### Profile Operations

```bash
# List available profiles
sysctl profile list

# Show profile details
sysctl profile show production

# Set active profile
sysctl profile set production

# Validate profile configuration
sysctl profile validate production

# Edit profile
sysctl profile edit production

# Delete profile
sysctl profile delete myproject
```

## Profile Configuration Structure

### Complete Profile Example

```yaml
# profiles/production.yaml
metadata:
  name: "production"
  description: "Production environment configuration"
  version: "1.0"
  author: "DevOps Team"
  created: "2024-01-15T10:30:00Z"
  inherits: ["base", "security"]
  tags: ["production", "critical"]

# Environment settings
environment:
  name: "production"
  region: "us-west-2"
  cluster: "prod-cluster"

# Logging configuration
logging:
  level: "WARNING"
  format: "json"
  outputs:
    - "file"
    - "syslog"
  file_path: "/var/log/system-control/production.log"
  rotation:
    max_size: "100MB"
    max_files: 10

# Security settings
security:
  strict_mode: true
  audit_logging: true
  secret_backend: "vault"
  encryption:
    enabled: true
    key_rotation: "30d"

# Deployment configuration
deployment:
  strategy: "blue-green"
  parallel_limit: 3
  health_check:
    enabled: true
    timeout: 300
    retries: 3
    endpoint: "/health"
  rollback:
    enabled: true
    timeout: 600
    automatic: false

# Monitoring settings
monitoring:
  enabled: true
  metrics:
    enabled: true
    interval: "30s"
    retention: "30d"
  alerts:
    enabled: true
    channels: ["slack", "email"]
    escalation_policy: "production-oncall"

# Integration settings
integrations:
  kubernetes:
    config_path: "~/.kube/config-prod"
    context: "production-cluster"
    namespace: "production"

  vault:
    url: "https://vault-prod.company.com:8200"
    auth_method: "kubernetes"
    role: "production-deployer"

  prometheus:
    url: "https://prometheus-prod.company.com:9090"
    basic_auth:
      username_env: "PROMETHEUS_USER"
      password_env: "PROMETHEUS_PASS"

  grafana:
    url: "https://grafana-prod.company.com:3000"
    api_key_env: "GRAFANA_API_KEY"

# Service definitions
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
    health_check:
      path: "/health"
      port: 8080
      initial_delay: 30
      period: 10

  overrides:
    database:
      replicas: 1
      resources:
        requests:
          cpu: "500m"
          memory: "1Gi"
        limits:
          cpu: "2000m"
          memory: "4Gi"

# Notification settings
notifications:
  enabled: true
  channels:
    slack:
      webhook_url_env: "SLACK_WEBHOOK_URL"
      channel: "#deployments"
    email:
      smtp_server: "smtp.company.com:587"
      from_env: "NOTIFICATION_FROM_EMAIL"
      recipients: ["devops@company.com"]

# Custom variables
variables:
  app_version: "v2.1.0"
  database_url: "postgres://prod-db.company.com:5432/app"
  redis_url: "redis://prod-redis.company.com:6379"
  api_base_url: "https://api.company.com"
```

## Advanced Profile Inheritance

### Inheritance Rules

1. **Multiple Inheritance**: Profiles can inherit from multiple parent profiles
2. **Override Precedence**: Child settings override parent settings
3. **Array Merging**: Arrays are merged unless explicitly overridden
4. **Deep Merging**: Nested objects are deeply merged

### Example Inheritance Chain

```yaml
# profiles/base.yaml
logging:
  level: "INFO"
  format: "text"
plugins:
  enabled: ["core"]

# profiles/security.yaml
security:
  audit_logging: true
  strict_mode: false

# profiles/production.yaml
inherits: ["base", "security"]
logging:
  level: "WARNING"  # Overrides base
security:
  strict_mode: true  # Overrides security
plugins:
  enabled: ["core", "monitoring"]  # Merges with base
```

Result:

```yaml
logging:
  level: "WARNING"
  format: "text"
security:
  audit_logging: true
  strict_mode: true
plugins:
  enabled: ["core", "monitoring"]
```

## Environment-Specific Profiles

### Development Profile

```yaml
# profiles/development.yaml
metadata:
  name: "development"
  inherits: ["base"]

logging:
  level: "DEBUG"
  format: "colorized"

security:
  strict_mode: false
  audit_logging: false

deployment:
  strategy: "rolling"
  parallel_limit: 1
  health_check:
    timeout: 60

confirmation:
  destructive_operations: false
```

### Staging Profile

```yaml
# profiles/staging.yaml
metadata:
  name: "staging"
  inherits: ["base"]

logging:
  level: "INFO"

security:
  strict_mode: true
  audit_logging: true

deployment:
  strategy: "blue-green"
  parallel_limit: 2
  health_check:
    timeout: 120
```

## Profile Templates

### Creating Templates

```bash
# Create a template from existing profile
sysctl profile template create microservice --from production

# Create template with variables
sysctl profile template create webapp --variables "app_name,domain,replicas"
```

### Template Example

```yaml
# templates/microservice.yaml
metadata:
  name: "{{ app_name }}-profile"
  template: true
  variables:
    - name: "app_name"
      description: "Application name"
      required: true
    - name: "domain"
      description: "Application domain"
      default: "company.com"
    - name: "replicas"
      description: "Number of replicas"
      default: 3
      type: "integer"

services:
  "{{ app_name }}":
    replicas: { { replicas } }
    domain: "{{ app_name }}.{{ domain }}"
    health_check:
      path: "/health"
```

## Profile Validation

### Schema Validation

```bash
# Validate profile against schema
sysctl profile validate production

# Validate with detailed output
sysctl profile validate production --verbose

# Validate all profiles
sysctl profile validate --all
```

### Validation Rules

The CLI validates:

- Required fields are present
- Field types are correct
- Value ranges and constraints
- Profile inheritance is valid
- Referenced profiles exist
- Integration configurations are valid

### Custom Validation

```yaml
# profiles/production.yaml
validation:
  rules:
    - name: "resource_limits"
      description: "Ensure production services have resource limits"
      condition: "services.*.resources.limits != null"

    - name: "replica_count"
      description: "Production services must have multiple replicas"
      condition: "services.*.replicas >= 2"

    - name: "health_checks"
      description: "All services must have health checks"
      condition: "services.*.health_check.enabled == true"
```

## Advanced Profile Features

### Conditional Configuration

```yaml
# profiles/multi-env.yaml
environment:
  name: "{{ env | default('development') }}"

# Conditional blocks based on environment
{% if env == 'production' %}
security:
  strict_mode: true
  audit_logging: true
{% else %}
security:
  strict_mode: false
  audit_logging: false
{% endif %}

replicas: "{{ 3 if env == 'production' else 1 }}"
```

### Profile Composition

```yaml
# profiles/composed.yaml
metadata:
  name: "composed"
  composition:
    - profile: "base"
      sections: ["logging", "plugins"]
    - profile: "security"
      sections: ["security", "vault"]
    - profile: "monitoring"
      sections: ["monitoring", "alerts"]
```

### Profile Encryption

```bash
# Encrypt sensitive profile data
sysctl profile encrypt production --fields "integrations.vault.token"

# Decrypt for use
sysctl profile decrypt production
```

## Best Practices

### Profile Organization

1. **Base Profile**: Common settings for all environments
2. **Environment Profiles**: Environment-specific configurations
3. **Feature Profiles**: Feature-specific settings (monitoring, security)
4. **Project Profiles**: Project or team-specific configurations

### Naming Conventions

- **Environment**: `development`, `staging`, `production`
- **Features**: `monitoring`, `security`, `logging`
- **Projects**: `project-name-env` (e.g., `webapp-prod`)
- **Teams**: `team-name` (e.g., `platform-team`)

### Security Considerations

1. **Sensitive Data**: Use environment variables or secret backends
2. **Profile Sharing**: Avoid storing secrets in shared profiles
3. **Access Control**: Implement profile-level access controls
4. **Encryption**: Encrypt sensitive profile sections

### Version Control

```bash
# Initialize profile repository
git init ~/.config/system-control/profiles
cd ~/.config/system-control/profiles
git add .
git commit -m "Initial profile configuration"

# Use version control for profile changes
sysctl profile commit "Update production deployment strategy"
```

## Troubleshooting

### Common Issues

1. **Inheritance Conflicts**: Use `sysctl profile resolve` to see final configuration
2. **Validation Errors**: Use `--verbose` flag for detailed error messages
3. **Variable Resolution**: Check variable values with `sysctl profile variables`
4. **Profile Not Found**: Verify profile exists with `sysctl profile list`

### Debug Commands

```bash
# Show resolved profile configuration
sysctl profile resolve production

# Show profile inheritance chain
sysctl profile inheritance production

# Show profile variables
sysctl profile variables production

# Test profile against environment
sysctl profile test production --dry-run
```
