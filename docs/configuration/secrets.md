# Secret Management

The System Control CLI provides comprehensive secret management capabilities, supporting
multiple backends and ensuring secure handling of sensitive data throughout your
infrastructure.

## Overview

Secret management features include:

- **Multiple Backends**: Support for HashiCorp Vault, Kubernetes secrets, cloud providers
- **Encryption at Rest**: All secrets encrypted when stored locally
- **Dynamic Secrets**: Generate secrets on-demand with automatic rotation
- **Access Control**: Fine-grained permissions and audit logging
- **Secret Injection**: Seamless integration with deployment workflows
- **Rotation Policies**: Automated secret rotation with configurable policies

## Supported Backends

### HashiCorp Vault

Primary secret backend for enterprise deployments:

```yaml
# config.yaml
secrets:
  backend: "vault"
  vault:
    url: "https://vault.company.com:8200"
    auth_method: "kubernetes"
    role: "system-control"
    mount_path: "secret"

    # Authentication methods
    auth:
      kubernetes:
        role: "system-control"
        service_account_token_path: "/var/run/secrets/kubernetes.io/serviceaccount/token"

      token:
        token_env: "VAULT_TOKEN"

      userpass:
        username_env: "VAULT_USERNAME"
        password_env: "VAULT_PASSWORD"

      approle:
        role_id_env: "VAULT_ROLE_ID"
        secret_id_env: "VAULT_SECRET_ID"

    # TLS configuration
    tls:
      ca_cert_path: "/etc/ssl/certs/vault-ca.pem"
      client_cert_path: "/etc/ssl/certs/vault-client.pem"
      client_key_path: "/etc/ssl/private/vault-client.key"
      insecure_skip_verify: false

    # Connection settings
    timeout: "30s"
    max_retries: 3
    retry_wait_min: "1s"
    retry_wait_max: "5s"
```

### Kubernetes Secrets

For Kubernetes-native deployments:

```yaml
secrets:
  backend: "kubernetes"
  kubernetes:
    namespace: "system-control"
    encryption_key_secret: "encryption-key"

    # Service account for secret operations
    service_account: "system-control-secrets"

    # Secret naming convention
    naming:
      prefix: "sysctl"
      separator: "-"
```

### AWS Secrets Manager

For AWS cloud deployments:

```yaml
secrets:
  backend: "aws"
  aws:
    region: "us-east-1"

    # Authentication
    auth:
      iam_role: "system-control-secrets"
      # or
      access_key_id_env: "AWS_ACCESS_KEY_ID"
      secret_access_key_env: "AWS_SECRET_ACCESS_KEY"

    # KMS encryption
    kms_key_id: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"

    # Secret naming
    prefix: "system-control/"
```

### Azure Key Vault

For Azure cloud deployments:

```yaml
secrets:
  backend: "azure"
  azure:
    vault_url: "https://mycompany.vault.azure.net/"

    # Authentication
    auth:
      client_id_env: "AZURE_CLIENT_ID"
      client_secret_env: "AZURE_CLIENT_SECRET"
      tenant_id_env: "AZURE_TENANT_ID"
```

### Local Storage (Development)

For development and testing:

```yaml
secrets:
  backend: "local"
  local:
    storage_path: "~/.config/system-control/secrets"
    encryption_key_env: "SYSCTL_ENCRYPTION_KEY"
    cipher: "AES-256-GCM"
```

## Secret Operations

### Basic Secret Management

```bash
# Store a secret
sysctl secret set database_password "secure_password123"

# Retrieve a secret
sysctl secret get database_password

# List all secrets
sysctl secret list

# Delete a secret
sysctl secret delete database_password

# Check if secret exists
sysctl secret exists database_password
```

### Batch Operations

```bash
# Import secrets from file
sysctl secret import secrets.env

# Export secrets
sysctl secret export --format env > secrets.env
sysctl secret export --format yaml > secrets.yaml
sysctl secret export --format json > secrets.json

# Bulk operations
echo "api_key=abc123\ndb_pass=secure456" | sysctl secret import -

# Copy secrets between environments
sysctl secret copy --from development --to staging
```

### Secret Versioning

```bash
# Set secret with version
sysctl secret set api_key "new_value" --version 2

# Get specific version
sysctl secret get api_key --version 1

# List secret versions
sysctl secret versions api_key

# Rollback to previous version
sysctl secret rollback api_key --version 1
```

## Dynamic Secrets

### Database Credentials

```yaml
# secrets/database.yaml
dynamic_secrets:
  database_credentials:
    backend: "vault"
    path: "database/creds/app-role"
    ttl: "1h"
    renewal_threshold: "15m"

    # Auto-renewal settings
    auto_renew: true
    max_renewals: 5

    # Credential mapping
    mapping:
      username: "{{ .Data.username }}"
      password: "{{ .Data.password }}"
```

### API Tokens

```yaml
dynamic_secrets:
  github_token:
    backend: "vault"
    path: "github/token/system-control"
    ttl: "24h"

    permissions:
      - "repo:read"
      - "workflow:write"
```

### SSH Keys

```yaml
dynamic_secrets:
  ssh_key:
    backend: "vault"
    path: "ssh/sign/server-role"
    ttl: "30m"

    parameters:
      public_key: "{{ .ssh_public_key }}"
      valid_principals: "ubuntu,deploy"
```

## Secret Injection

### Environment Variables

```yaml
# deployment.yaml
services:
  api:
    environment:
      DATABASE_URL:
        secret: "database_url"
      API_KEY:
        secret: "api_key"
        version: "latest"

      # Dynamic secret injection
      DB_USERNAME:
        dynamic_secret: "database_credentials"
        field: "username"
      DB_PASSWORD:
        dynamic_secret: "database_credentials"
        field: "password"
```

### Configuration Files

```yaml
services:
  app:
    config_files:
      - path: "/etc/app/config.yaml"
        template: |
          database:
            host: "{{ env.DB_HOST }}"
            username: "{{ secret.db_username }}"
            password: "{{ secret.db_password }}"

          api:
            key: "{{ secret.api_key }}"
            secret: "{{ secret.api_secret }}"
```

### Kubernetes Integration

```yaml
# Kubernetes secret injection
services:
  api:
    secrets:
      - name: "database-credentials"
        type: "Opaque"
        data:
          username: "{{ secret.db_username | b64encode }}"
          password: "{{ secret.db_password | b64encode }}"

      - name: "api-tokens"
        type: "Opaque"
        from_secrets:
          - "api_key"
          - "jwt_secret"
```

## Secret Rotation

### Automatic Rotation

```yaml
# rotation/database.yaml
rotation_policies:
  database_password:
    schedule: "0 2 * * 0" # Weekly on Sunday at 2 AM
    backends: ["vault"]

    # Pre-rotation hooks
    pre_hooks:
      - name: "backup_old_password"
        command: "sysctl secret backup database_password"

    # Rotation steps
    rotation:
      - name: "generate_new_password"
        type: "generate"
        length: 32
        charset: "alphanumeric-symbols"

      - name: "update_database"
        type: "execute"
        command: 'mysql -u root -p''{{ .old_password }}'' -e "ALTER USER ''app''@''%'' IDENTIFIED BY ''{{ .new_password }}'';"'

      - name: "verify_new_password"
        type: "test"
        command: "mysql -u app -p'{{ .new_password }}' -e 'SELECT 1;'"

    # Post-rotation hooks
    post_hooks:
      - name: "restart_services"
        command: "sysctl service restart api worker"

      - name: "verify_services"
        command: "sysctl service health-check api worker"

    # Rollback configuration
    rollback:
      enabled: true
      timeout: "10m"
      steps:
        - name: "restore_old_password"
          command: 'mysql -u root -p''{{ .new_password }}'' -e "ALTER USER ''app''@''%'' IDENTIFIED BY ''{{ .old_password }}'';"'
```

### Manual Rotation

```bash
# Rotate specific secret
sysctl secret rotate database_password

# Rotate with custom policy
sysctl secret rotate api_key --policy custom-rotation.yaml

# Dry run rotation
sysctl secret rotate --dry-run database_password

# Force rotation (ignore schedule)
sysctl secret rotate --force database_password

# Batch rotation
sysctl secret rotate --all --filter "environment:production"
```

## Access Control

### Role-Based Access Control

```yaml
# rbac/secrets.yaml
roles:
  secret_admin:
    permissions:
      - "secrets:*"
    users:
      - "admin@company.com"

  service_deployer:
    permissions:
      - "secrets:read"
      - "secrets:list"
    paths:
      - "production/*"
      - "staging/*"
    users:
      - "deployer@company.com"
      - "ci-service"

  developer:
    permissions:
      - "secrets:read"
      - "secrets:write"
    paths:
      - "development/*"
    groups:
      - "developers"

policies:
  production_secrets:
    paths: ["production/*"]
    rules:
      - effect: "deny"
        conditions: ["time.hour < 9 OR time.hour > 17"] # Business hours only
      - effect: "allow"
        conditions: ["user in ['deployer@company.com']"]
      - effect: "require_approval"
        conditions: ["action in ['delete', 'rotate']"]
```

### Audit Logging

```yaml
audit:
  enabled: true
  backends:
    - type: "file"
      path: "/var/log/system-control/secrets-audit.log"
      format: "json"

    - type: "syslog"
      facility: "auth"
      severity: "info"

    - type: "elasticsearch"
      url: "https://es.company.com:9200"
      index: "secrets-audit"

  events:
    - "secret_read"
    - "secret_write"
    - "secret_delete"
    - "secret_rotate"
    - "access_denied"
    - "authentication_failure"

  fields:
    - "timestamp"
    - "user"
    - "action"
    - "secret_path"
    - "source_ip"
    - "user_agent"
    - "success"
```

## Secret Scanning

### Security Scanning

```bash
# Scan for exposed secrets
sysctl secret scan

# Scan specific directories
sysctl secret scan --path ./config

# Scan with custom patterns
sysctl secret scan --patterns custom-patterns.yaml

# Continuous scanning
sysctl secret scan --watch --interval 5m
```

### Custom Patterns

```yaml
# patterns/secrets.yaml
patterns:
  aws_access_key:
    pattern: "AKIA[0-9A-Z]{16}"
    description: "AWS Access Key ID"
    severity: "high"

  private_key:
    pattern: "-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"
    description: "Private Key"
    severity: "critical"

  jwt_token:
    pattern: 'eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*'
    description: "JWT Token"
    severity: "medium"

  database_url:
    pattern: "(mysql|postgres|mongodb)://[^:]+:[^@]+@"
    description: "Database URL with credentials"
    severity: "high"
```

## Backup and Recovery

### Backup Configuration

```yaml
backup:
  enabled: true
  schedule: "0 1 * * *" # Daily at 1 AM
  retention: "30d"

  destinations:
    - type: "s3"
      bucket: "company-secrets-backup"
      prefix: "system-control/"
      encryption: "AES256"

    - type: "vault"
      path: "backups/secrets"
      encryption: true

  # What to backup
  include:
    - "production/*"
    - "staging/*"
    - "shared/*"

  exclude:
    - "*/temp*"
    - "*/cache*"
```

### Recovery Operations

```bash
# List available backups
sysctl secret backup list

# Create manual backup
sysctl secret backup create --name "pre-migration"

# Restore from backup
sysctl secret backup restore --name "2024-01-15-daily"

# Restore specific secrets
sysctl secret backup restore --secrets "database_password,api_key"

# Point-in-time recovery
sysctl secret backup restore --timestamp "2024-01-15T10:30:00Z"
```

## Best Practices

### Secret Naming

```bash
# Good naming conventions
database_password            # Clear and descriptive
api_key_github              # Service-specific
jwt_signing_key_production   # Environment-specific
redis_auth_token            # Component-specific

# Avoid
secret1                     # Non-descriptive
db_pwd                      # Abbreviations
API_KEY                     # All caps
```

### Secret Organization

```yaml
# Hierarchical organization
secrets/
├── production/
│   ├── database/
│   │   ├── primary_password
│   │   └── replica_password
│   ├── api/
│   │   ├── github_token
│   │   └── stripe_key
│   └── infrastructure/
│       ├── vault_token
│       └── k8s_service_account
├── staging/
└── development/
```

### Security Guidelines

1. **Principle of Least Privilege**: Grant minimal necessary access
2. **Regular Rotation**: Implement automatic rotation for critical secrets
3. **Audit Everything**: Log all secret access and modifications
4. **Environment Separation**: Isolate secrets by environment
5. **Backup Regularly**: Maintain encrypted backups with retention policies
6. **Monitor Usage**: Alert on unusual access patterns
7. **Use Dynamic Secrets**: Prefer short-lived, automatically managed secrets

### Development Workflow

```bash
# Development cycle
sysctl secret set db_password "dev_password" --env development
sysctl deploy api --env development

# Testing
sysctl secret copy --from development --to staging --secrets "db_password"
sysctl deploy api --env staging

# Production deployment
sysctl secret rotate db_password --env production
sysctl deploy api --env production
```

## Troubleshooting

### Common Issues

```bash
# Connection issues
sysctl secret test-connection

# Authentication problems
sysctl secret auth-status
sysctl secret auth-refresh

# Permission errors
sysctl secret permissions check
sysctl secret audit --user current --last 24h

# Secret not found
sysctl secret exists database_password
sysctl secret search "database*"

# Rotation failures
sysctl secret rotation status
sysctl secret rotation logs database_password
```

### Debug Mode

```bash
# Enable debug logging
export SYSCTL_SECRET_DEBUG=true
sysctl secret get database_password

# Trace operations
sysctl secret get database_password --trace

# Validate configuration
sysctl secret config validate
```
