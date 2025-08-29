# History and Rollback

Comprehensive command history tracking and rollback capabilities for safe
recovery from
failed operations and audit compliance.

## Overview

History and rollback features:

- **Command History**: Complete audit trail of all operations
- **State Snapshots**: Point-in-time system state captures
- **Automatic Rollback**: Smart rollback on failure detection
- **Manual Rollback**: Selective rollback to previous states
- **Time Travel**: Restore to any point in history
- **Audit Compliance**: Detailed tracking for regulatory requirements

## Command History

### Basic History Operations

```bash
# View command history
sysctl history

# View detailed history with filters
sysctl history --service api --env production --since 24h

# Search history
sysctl history search "deploy api" --user alice --since 7d

# Export history
sysctl history export --format json --since 30d --output history.json
```

### History Output Example

```text
📜 Command History
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ID      Timestamp              User     Command                          Status    Duration
────────────────────────────────────────────────────────────────────────────────────────
#1234   2024-01-15 10:30:15   alice    deploy api --env production      ✅ Success   3m 45s
#1233   2024-01-15 10:25:00   bob      scale worker --replicas 5        ✅ Success   45s
#1232   2024-01-15 10:20:30   alice    config update api --file cfg     ✅ Success   12s
#1231   2024-01-15 10:15:00   charlie  backup create --all              ✅ Success   5m 20s
#1230   2024-01-15 10:10:00   alice    deploy worker --env staging      ❌ Failed    2m 15s
#1229   2024-01-15 10:05:00   bob      rollback api --version v2.0      ✅ Success   1m 30s

📊 Summary: 6 commands (5 successful, 1 failed)
```

### Detailed History Entry

````bash
sysctl history show 1234

# Output:
```text

📋 Command Details #1234
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Command ID: 1234
Timestamp: 2024-01-15 10:30:15 UTC
User: alice@company.com
Client: CLI v2.1.0
Environment: production

Command: deploy api --env production --image api:v2.1.0 --strategy rolling

Parameters:
Service: api
Image: api:v2.1.0
Strategy: rolling
Replicas: 3
Timeout: 600s

Execution:
Start Time: 2024-01-15 10:30:15
End Time: 2024-01-15 10:33:00
Duration: 3m 45s
Status: Success

State Changes:

- Image: api:v2.0.5 → api:v2.1.0
- Config Version: v127 → v128
- Last Deployed: 2024-01-14 15:20:00 → 2024-01-15 10:33:00

Resources:
CPU Usage: 250m (peak)
Memory Usage: 512Mi (peak)
Network I/O: 1.2GB

Rollback Information:
Rollback Available: Yes
Rollback Command: sysctl rollback --to-history 1234
State Snapshot: snapshot-1234

````

## Configuration Management

### History Configuration

```yaml
# config/history.yaml
history:
  # Storage settings
  storage:
    backend: "postgresql" # or "sqlite", "elasticsearch"
    retention: "90d"
    max_entries: 100000

  # Tracking settings
  tracking:
    enabled: true
    track_all_commands: true
    exclude_commands: ["status", "list", "get"]
    sensitive_data_masking: true

  # Snapshot settings
  snapshots:
    automatic: true
    before_operations: ["deploy", "scale", "config"]
    retention: "30d"
    compression: true

  # Audit settings
  audit:
    enabled: true
    compliance_mode: "sox" # sox, hipaa, gdpr
    immutable_records: true
    cryptographic_signing: true

  # Rollback settings
  rollback:
    enabled: true
    automatic_on_failure: true
    confirmation_required: true
    max_rollback_age: "7d"
```

## State Snapshots

### Creating Snapshots

```bash
# Manual snapshot
sysctl snapshot create --name "before-major-update" --description "Pre v3.0 deployment"

# Automatic snapshot before operation
sysctl deploy api --env production --snapshot

# Snapshot with specific components
sysctl snapshot create --components "services,configs,secrets" --name daily-backup
```

### Managing Snapshots

```bash
# List snapshots
sysctl snapshot list --env production

# Show snapshot details
sysctl snapshot show snapshot-1234

# Compare snapshots
sysctl snapshot diff snapshot-1234 snapshot-1235

# Delete old snapshots
sysctl snapshot cleanup --older-than 30d
```

### Snapshot Details

```yaml
# Example snapshot structure
snapshot:
  id: "snapshot-1234"
  timestamp: "2024-01-15T10:30:00Z"
  name: "pre-deployment"
  description: "Snapshot before api v2.1.0 deployment"

  environment:
    name: "production"
    region: "us-east-1"

  services:
    api:
      image: "api:v2.0.5"
      replicas: 3
      config_version: "v127"
      health: "healthy"

    worker:
      image: "worker:v1.5.0"
      replicas: 2
      config_version: "v89"
      health: "healthy"

  configurations:
    api_config:
      version: "v127"
      checksum: "sha256:abc123..."

  secrets:
    references:
      - "database_password"
      - "api_key"

  metrics:
    cpu_usage: "45%"
    memory_usage: "62%"
    disk_usage: "34%"
```

## Rollback Operations

### Basic Rollback

```bash
# Rollback to previous state
sysctl rollback api --env production

# Rollback to specific version
sysctl rollback api --version v2.0.5 --env production

# Rollback to specific point in time
sysctl rollback api --timestamp "2024-01-15T09:00:00Z" --env production

# Rollback using history ID
sysctl rollback --to-history 1234
```

### Advanced Rollback

```bash
# Rollback with validation
sysctl rollback api --validate --env production

# Partial rollback (specific components)
sysctl rollback api --components "config,secrets" --env production

# Rollback with custom strategy
sysctl rollback api --strategy blue-green --env production

# Emergency rollback (skip confirmations)
sysctl rollback api --emergency --force --env production
```

### Rollback Preview

````bash
sysctl rollback api --dry-run --env production

# Output:
```text

🔄 Rollback Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Service: api
Environment: production
Target State: 2024-01-15 09:00:00 (1 hour ago)

📋 Changes to Revert:
┌─────────────────┬─────────────────┬─────────────────┐
│ Component │ Current │ Rollback To │
├─────────────────┼─────────────────┼─────────────────┤
│ Image │ api:v2.1.0 │ api:v2.0.5 │
│ Replicas │ 5 │ 3 │
│ Config Version │ v128 │ v127 │
│ Memory Limit │ 1Gi │ 512Mi │
└─────────────────┴─────────────────┴─────────────────┘

🔍 Impact Analysis:

- Downtime: Minimal (rolling update)
- Data Loss: None
- Feature Impact: Features X, Y will be unavailable
- User Impact: ~1000 active sessions may be affected

✅ Rollback Prerequisites:

- ✅ Previous version available
- ✅ Configuration backup exists
- ✅ Database compatible
- ⚠️ Some API endpoints will change

⏱️ Estimated Duration: 2-3 minutes

Rollback Plan:

1. Create snapshot of current state
2. Deploy previous image version
3. Restore configuration v127
4. Verify service health
5. Update load balancer rules

````

## Automatic Rollback

### Failure Detection

```yaml
# config/auto-rollback.yaml
auto_rollback:
  enabled: true

  triggers:
    health_check_failures:
      threshold: 3
      window: "5m"
      action: "rollback"

    error_rate_spike:
      threshold: "5%"
      window: "2m"
      action: "rollback"

    memory_leak:
      threshold: "90%"
      duration: "10m"
      action: "rollback"

    deployment_timeout:
      timeout: "15m"
      action: "rollback"

  policies:
    production:
      auto_rollback: true
      confirmation_required: false
      notify_channels: ["slack", "pagerduty"]

    staging:
      auto_rollback: true
      confirmation_required: true
      notify_channels: ["slack"]

    development:
      auto_rollback: false
```

### Rollback Automation

```bash
# Configure automatic rollback
sysctl rollback configure --auto --env production

# Test rollback automation
sysctl rollback test --simulate-failure --env staging

# Disable automatic rollback temporarily
sysctl rollback disable-auto --duration 2h --reason "Maintenance window"
```

## Time Travel

### Point-in-Time Recovery

```bash
# Show system state at specific time
sysctl history travel "2024-01-15T09:00:00Z" --show-state

# Restore to specific point in time
sysctl history restore "2024-01-15T09:00:00Z" --env production

# Interactive time travel
sysctl history travel --interactive
```

### Time Travel Interface

````text
📅 Time Travel Interface
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select point in time (use arrows to navigate):

2024-01-15 12:00:00  ← Current State
2024-01-15 10:30:00  ✅ Deploy api v2.1.0 (alice)
2024-01-15 10:00:00  ✅ Scale worker to 5 replicas (bob)
2024-01-15 09:30:00  ✅ Config update (charlie)
2024-01-15 09:00:00  ✅ Deploy api v2.0.5 (alice)    ← Selected
2024-01-15 08:30:00  ✅ Backup created (system)

System State at 2024-01-15 09:00:00:
┌──────────────┬─────────────────────────────┐
│ Service      │ State                       │
├──────────────┼─────────────────────────────┤
│ api          │ v2.0.5 (3 replicas)        │
│ worker       │ v1.5.0 (2 replicas)        │
│ database     │ v9.6 (1 replica)           │
└──────────────┴─────────────────────────────┘

Options:
[R] Restore to this point
[C] Compare with current
[D] Show detailed diff
[Q] Quit

Choose option: _
```text

## Audit Trail

### Compliance Reporting

```bash
# Generate audit report
sysctl audit report --period monthly --format pdf

# SOX compliance report
sysctl audit sox-report --quarter Q1-2024

# GDPR compliance check
sysctl audit gdpr-check --include-data-access

# Custom audit query
sysctl audit query --user alice --operations "delete,modify" --since 30d
````

### Audit Log Format

```json
{
  "event_id": "evt_1234567890",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "user": {
    "id": "user_123",
    "email": "alice@company.com",
    "ip_address": "192.168.1.100",
    "user_agent": "SystemControlCLI/2.1.0"
  },
  "command": {
    "raw": "deploy api --env production --image api:v2.1.0",
    "parsed": {
      "action": "deploy",
      "resource": "api",
      "environment": "production",
      "parameters": {
        "image": "api:v2.1.0"
      }
    }
  },
  "result": {
    "status": "success",
    "duration_ms": 225000,
    "changes": [
      {
        "type": "image_update",
        "from": "api:v2.0.5",
        "to": "api:v2.1.0"
      }
    ]
  },
  "metadata": {
    "correlation_id": "corr_abc123",
    "request_id": "req_xyz789",
    "session_id": "sess_456"
  },
  "signature": "sha256:abc123..."
}
```

## Integration with Version Control

### Git Integration

```yaml
# config/git-integration.yaml
git_integration:
  enabled: true
  repository: "git@github.com:company/infrastructure.git"
  branch: "main"

  auto_commit:
    enabled: true
    message_template: "[System Control] {{ .operation }} by {{ .user }}"

  tracking:
    - "/configs/**/*.yaml"
    - "/deployments/**/*.yaml"
    - "/snapshots/**/*.json"

  hooks:
    pre_operation: "git pull"
    post_operation: "git add -A && git commit && git push"
```

### Version Control Commands

```bash
# Commit current state to git
sysctl history git-commit --message "Pre-deployment checkpoint"

# View git history
sysctl history git-log --since 7d

# Rollback using git
sysctl rollback --from-git HEAD~1

# Tag important states
sysctl history git-tag v2.1.0-stable
```

## Best Practices

### History Management

1. **Regular Snapshots**: Create snapshots before major changes
2. **Retention Policies**: Balance storage with compliance needs
3. **Sensitive Data**: Mask sensitive information in logs
4. **Testing**: Regularly test rollback procedures
5. **Documentation**: Document rollback procedures and dependencies

### Rollback Strategy

```yaml
# Best practice rollback strategy
rollback_strategy:
  pre_checks:
    - verify_backup_exists
    - check_dependencies
    - validate_data_compatibility

  execution:
    - create_current_snapshot
    - notify_team
    - execute_rollback
    - verify_health

  post_rollback:
    - run_smoke_tests
    - monitor_metrics
    - document_incident

  failure_handling:
    - preserve_failed_state
    - escalate_to_oncall
    - prepare_manual_recovery
```

### Compliance Configuration

```yaml
# Compliance settings
compliance:
  sox:
    retention_period: "7 years"
    immutable_logs: true
    segregation_of_duties: true
    approval_workflows: true

  hipaa:
    encryption_at_rest: true
    encryption_in_transit: true
    access_logging: true
    phi_masking: true

  gdpr:
    data_retention: "as_required"
    right_to_forget: true
    data_portability: true
    audit_trail: true
```

## Troubleshooting

### Common Issues

```bash
# History not recording
sysctl history debug --check-storage --check-permissions

# Rollback failing
sysctl rollback debug --service api --verbose

# Snapshot corruption
sysctl snapshot verify --repair snapshot-1234

# Audit compliance issues
sysctl audit validate --standard sox --fix-issues
```

### Recovery Procedures

```bash
# Recover from failed rollback
sysctl rollback recover --service api --from-snapshot snapshot-1234

# Rebuild history from logs
sysctl history rebuild --from-logs --since 30d

# Export and reimport history
sysctl history export --all --output history-backup.json
sysctl history import --file history-backup.json --merge
```
