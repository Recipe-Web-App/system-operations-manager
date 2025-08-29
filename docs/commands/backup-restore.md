# Backup and Restore Commands

Comprehensive backup and restore operations for services, configurations, databases, and
complete system state management.

## Overview

Backup and restore features:

- **Full System Backups**: Complete infrastructure state snapshots
- **Service-Level Backups**: Individual service data and configuration
- **Database Backups**: Automated database backup and restoration
- **Configuration Backups**: Version-controlled configuration snapshots
- **Point-in-Time Recovery**: Restore to specific timestamps
- **Cross-Environment Restoration**: Copy data between environments

## Core Backup Commands

### `sysctl backup`

Create comprehensive system and service backups.

```bash
# Full system backup
sysctl backup create --all --env production

# Service-specific backup
sysctl backup create api --include data,config,secrets

# Database backup
sysctl backup create database --type postgres --compress

# Configuration backup
sysctl backup create config --env production --include profiles,secrets
```

#### Backup Options

- `--type TYPE`: Backup type (full, incremental, differential)
- `--include ITEMS`: Components to include (data, config, secrets, logs)
- `--exclude ITEMS`: Components to exclude
- `--compress`: Enable compression
- `--encrypt`: Encrypt backup data
- `--retention PERIOD`: Retention period (e.g., 30d, 1y)
- `--tag TAG`: Tag for backup identification
- `--schedule CRON`: Schedule automated backups

#### Backup Examples

```bash
# Full encrypted backup with compression
sysctl backup create --all --encrypt --compress --tag "pre-upgrade" --env production

# Incremental backup
sysctl backup create api --type incremental --since last-backup

# Scheduled backup configuration
sysctl backup create database --schedule "0 2 * * *" --retention 30d --compress
```

## Backup Management

### `sysctl backup list`

List and manage existing backups.

```bash
# List all backups
sysctl backup list

# List backups for specific service
sysctl backup list api --env production

# List backups with filters
sysctl backup list --tag pre-upgrade --since 7d

# Detailed backup information
sysctl backup info backup-20240115-123456
```

#### Backup Information

```bash
# Show backup details
sysctl backup info backup-20240115-123456 --detailed

# Verify backup integrity
sysctl backup verify backup-20240115-123456

# Calculate backup size and metrics
sysctl backup analyze backup-20240115-123456
```

## Restore Commands

### `sysctl restore`

Restore from backups with various strategies.

```bash
# Restore service from backup
sysctl restore api --from backup-20240115-123456

# Point-in-time restore
sysctl restore database --timestamp "2024-01-15T10:30:00Z"

# Cross-environment restore
sysctl restore api --from production --to staging --backup latest

# Selective restore
sysctl restore api --from backup-xyz --include config,secrets --exclude data
```

#### Restore Options

- `--from SOURCE`: Source backup or environment
- `--to TARGET`: Target environment
- `--timestamp TIME`: Point-in-time for restore
- `--include ITEMS`: Components to restore
- `--exclude ITEMS`: Components to exclude
- `--dry-run`: Preview restore operation
- `--force`: Force restore without confirmation
- `--validate`: Validate data after restore

#### Restore Examples

```bash
# Production data to staging
sysctl restore database --from production --to staging --validate --dry-run

# Emergency restore with force
sysctl restore api --from backup-emergency --force --env production

# Partial configuration restore
sysctl restore config --from backup-config-123 --include profiles --exclude secrets
```

## Database Backup and Restore

### PostgreSQL

```bash
# PostgreSQL backup
sysctl backup database postgres --database app_prod --compress --encrypt

# PostgreSQL restore
sysctl restore database postgres --database app_staging --from backup-postgres-123

# Point-in-time recovery
sysctl restore database postgres --pitr "2024-01-15T09:00:00Z" --database app_prod
```

#### PostgreSQL Configuration

```yaml
# backups/postgres.yaml
postgresql:
  connection:
    host: "${POSTGRES_HOST}"
    port: 5432
    database: "${POSTGRES_DB}"
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"

  backup:
    format: "custom" # custom, plain, tar
    compression: 9
    exclude_tables:
      - "audit_logs"
      - "temp_*"

    parallel_jobs: 4

  restore:
    clean: true
    create: true
    if_exists: "replace"
    single_transaction: true

  pitr:
    enabled: true
    wal_archive_location: "s3://backups/postgres-wal/"
    recovery_target_time: "latest"
```

### MongoDB

```bash
# MongoDB backup
sysctl backup database mongodb --collection users --oplog

# MongoDB restore
sysctl restore database mongodb --collection users --drop --from backup-mongo-456

# MongoDB cluster backup
sysctl backup database mongodb --cluster --replica-set rs0
```

#### MongoDB Configuration

```yaml
# backups/mongodb.yaml
mongodb:
  connection:
    uri: "${MONGODB_URI}"
    database: "${MONGODB_DATABASE}"

  backup:
    include_oplog: true
    collections:
      - "users"
      - "orders"
      - "products"
    exclude_collections:
      - "temp_data"
      - "cache_*"

    compression: "gzip"

  restore:
    drop_collections: false
    create_indexes: true
    bulk_insert_size: 1000
```

### Redis

```bash
# Redis backup
sysctl backup database redis --rdb --aof

# Redis restore
sysctl restore database redis --from backup-redis-789 --flush-before

# Redis cluster backup
sysctl backup database redis --cluster --all-nodes
```

## Configuration Backup

### `sysctl backup config`

Backup and restore configuration data.

```bash
# Backup all configurations
sysctl backup config --all --env production

# Backup specific profiles
sysctl backup config --profiles production,staging

# Version-controlled config backup
sysctl backup config --git-commit --message "Pre-upgrade backup"

# Export configurations
sysctl backup config --export --format yaml --output configs-backup.yaml
```

#### Configuration Backup Structure

```yaml
# Configuration backup format
config_backup:
  metadata:
    timestamp: "2024-01-15T12:30:00Z"
    environment: "production"
    version: "1.2.0"
    backup_id: "config-backup-123456"

  profiles:
    production:
      # Profile configuration data

  environment_vars:
    # Environment variables (encrypted)

  secrets:
    # Secret references (not actual values)

  templates:
    # Configuration templates

  validation_rules:
    # Custom validation rules
```

## Automated Backup Strategies

### Backup Policies

```yaml
# backup/policies.yaml
backup_policies:
  production_full:
    schedule: "0 2 * * 0" # Weekly on Sunday at 2 AM
    type: "full"
    retention: "90d"
    components:
      - "databases"
      - "configurations"
      - "secrets"
      - "application_data"

    storage:
      primary: "s3://company-backups/production/"
      secondary: "azure://backup-storage/production/"

    encryption: true
    compression: true

  production_incremental:
    schedule: "0 2 * * 1-6" # Daily except Sunday
    type: "incremental"
    retention: "30d"
    components:
      - "databases"
      - "application_data"

  development_config:
    schedule: "0 1 * * *" # Daily at 1 AM
    type: "full"
    retention: "7d"
    components:
      - "configurations"
```

### Backup Monitoring

```bash
# Monitor backup jobs
sysctl backup monitor --env production

# Backup health dashboard
sysctl backup dashboard --show-failures --show-trends

# Backup metrics and reporting
sysctl backup metrics --duration 30d --format prometheus
```

## Disaster Recovery

### `sysctl disaster-recovery`

Comprehensive disaster recovery operations.

```bash
# Create disaster recovery plan
sysctl disaster-recovery plan create --env production

# Test disaster recovery
sysctl disaster-recovery test --scenario region-outage --dry-run

# Execute disaster recovery
sysctl disaster-recovery execute --plan production-dr --confirm

# Monitor recovery progress
sysctl disaster-recovery status --plan production-dr
```

#### Disaster Recovery Configuration

```yaml
# disaster-recovery/production.yaml
disaster_recovery:
  scenarios:
    region_outage:
      description: "Primary region becomes unavailable"
      rto: "30m" # Recovery Time Objective
      rpo: "15m" # Recovery Point Objective

      steps:
        - name: "failover_database"
          action: "restore"
          source: "backup://latest-full"
          target: "secondary-region"
          timeout: "10m"

        - name: "redirect_traffic"
          action: "traffic_switch"
          from: "us-east-1"
          to: "us-west-2"
          timeout: "5m"

        - name: "scale_services"
          action: "scale"
          services: ["api", "worker"]
          replicas: 5
          timeout: "10m"

        - name: "verify_functionality"
          action: "health_check"
          services: "all"
          timeout: "5m"

    data_corruption:
      description: "Database corruption detected"
      rto: "2h"
      rpo: "1h"

      steps:
        - name: "stop_writes"
          action: "maintenance_mode"
          services: ["api"]

        - name: "restore_from_backup"
          action: "restore"
          source: "backup://latest-clean"
          validate: true

        - name: "replay_transactions"
          action: "replay"
          source: "transaction_log"
          from_timestamp: "{{ .corruption_timestamp }}"
```

## Cross-Environment Operations

### `sysctl sync`

Synchronize data between environments.

```bash
# Sync production data to staging
sysctl sync data --from production --to staging --anonymize

# Sync configurations
sysctl sync config --from production --to staging --exclude secrets

# Selective sync
sysctl sync --from production --to development --include database,config --exclude logs,secrets
```

#### Data Anonymization

```yaml
# sync/anonymization.yaml
anonymization:
  rules:
    users:
      email: "user{{ .id }}@example.com"
      first_name: "{{ fake.first_name }}"
      last_name: "{{ fake.last_name }}"
      phone: "{{ fake.phone_number }}"

    orders:
      customer_name: "{{ fake.name }}"
      shipping_address: "{{ fake.address }}"

    payments:
      credit_card: "xxxx-xxxx-xxxx-{{ .last_four }}"

  preserve:
    - "id"
    - "created_at"
    - "updated_at"
    - "status"
```

## Storage Backends

### S3 Configuration

```yaml
# storage/s3.yaml
s3:
  bucket: "company-backups"
  region: "us-east-1"

  authentication:
    method: "iam_role" # or access_key
    role_arn: "arn:aws:iam::123456789012:role/backup-role"

  encryption:
    enabled: true
    kms_key_id: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"

  lifecycle:
    standard_to_ia: "30d"
    ia_to_glacier: "90d"
    glacier_to_deep_archive: "365d"
    delete_after: "2555d" # 7 years
```

### Azure Blob Storage

```yaml
# storage/azure.yaml
azure:
  storage_account: "companybackups"
  container: "system-control-backups"

  authentication:
    method: "managed_identity"
    # or
    # method: "connection_string"
    # connection_string: "${AZURE_STORAGE_CONNECTION_STRING}"

  encryption:
    enabled: true
    customer_managed_key: true
    key_vault_url: "https://backup-keys.vault.azure.net/"

  lifecycle:
    cool_after: "30d"
    archive_after: "90d"
    delete_after: "2555d"
```

## Best Practices

### Backup Strategy

1. **3-2-1 Rule**: 3 copies, 2 different media types, 1 offsite
2. **Regular Testing**: Test restore procedures regularly
3. **Documentation**: Maintain recovery runbooks
4. **Monitoring**: Alert on backup failures
5. **Encryption**: Always encrypt sensitive backups

### Recovery Planning

```yaml
# Recovery objectives by service tier
recovery_objectives:
  critical:
    rto: "15m"
    rpo: "5m"
    services: ["api", "database", "auth"]

  important:
    rto: "1h"
    rpo: "30m"
    services: ["worker", "scheduler"]

  standard:
    rto: "4h"
    rpo: "2h"
    services: ["analytics", "reporting"]
```

### Troubleshooting

```bash
# Debug backup failures
sysctl backup debug --job-id backup-job-12345 --verbose

# Test restore procedures
sysctl restore test --backup backup-20240115 --target test-env --validate

# Verify backup integrity
sysctl backup verify --all --deep-check --repair

# Recovery diagnostics
sysctl disaster-recovery diagnose --scenario region-outage --check-dependencies
```
