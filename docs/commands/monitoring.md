# Monitoring Commands

Comprehensive monitoring capabilities including real-time metrics, alerting,
log analysis,
and performance monitoring across your distributed system.

## Overview

Monitoring features include:

- **Real-time Dashboards**: Terminal-based live metrics and system status
- **Alert Management**: Custom alerting rules and notification channels
- **Performance Monitoring**: Resource usage tracking and bottleneck identification
- **Log Aggregation**: Centralized log viewing with filtering and search
- **Health Check Orchestration**: Custom health check definitions and scheduling
- **Metrics Collection**: Integration with Prometheus, Grafana, and custom metrics

## Dashboard Commands

### `sysctl dashboard`

Launch interactive monitoring dashboards.

```bash
# System overview dashboard
sysctl dashboard

# Service-specific dashboard
sysctl dashboard api

# Environment dashboard
sysctl dashboard --env production

# Custom dashboard
sysctl dashboard --config custom-dashboard.yaml
```

#### Dashboard Types

```bash
# System overview
sysctl dashboard system --env production

# Service health dashboard
sysctl dashboard health --services api,worker,database

# Performance dashboard
sysctl dashboard performance --metrics cpu,memory,network

# Real-time logs dashboard
sysctl dashboard logs --follow --services api,worker

# Resource utilization dashboard
sysctl dashboard resources --env production --detailed
```

#### Dashboard Options

- `--env, -e ENV`: Target environment
- `--services SERVICES`: Comma-separated service list
- `--metrics METRICS`: Specific metrics to display
- `--interval SECONDS`: Refresh interval (default: 5)
- `--duration DURATION`: Auto-close after duration
- `--format FORMAT`: Display format (compact, detailed, minimal)
- `--config CONFIG`: Custom dashboard configuration

#### Dashboard Examples

```bash
# Production monitoring dashboard
sysctl dashboard --env production --interval 10 --services api,worker,database

# Performance monitoring with specific metrics
sysctl dashboard performance --metrics cpu,memory,requests,errors --interval 5

# Custom dashboard with configuration
sysctl dashboard --config monitoring/production-dashboard.yaml --interval 15
```

## Metrics Commands

### `sysctl metrics`

Collect, analyze, and export system and application metrics.

```bash
# Current metrics for service
sysctl metrics api

# Metrics over time period
sysctl metrics api --duration 1h --interval 5m

# System-wide metrics
sysctl metrics --system --env production

# Export metrics
sysctl metrics api --export --format prometheus
```

#### Metrics Options

- `--duration DURATION`: Time period to collect metrics (e.g., 1h, 30m, 1d)
- `--interval INTERVAL`: Collection interval (e.g., 1m, 5m, 30s)
- `--metrics METRICS`: Specific metrics to collect
- `--format FORMAT`: Output format (json, prometheus, csv, table)
- `--export`: Export metrics to file
- `--aggregate`: Aggregate metrics across replicas
- `--percentiles`: Include percentile calculations

#### Available Metrics

```yaml
metrics:
  system:
    - cpu_usage_percent
    - memory_usage_percent
    - disk_usage_percent
    - network_bytes_in
    - network_bytes_out
    - load_average

  application:
    - request_count
    - request_duration_seconds
    - response_status_codes
    - error_rate_percent
    - active_connections

  service:
    - replica_count
    - health_check_success_rate
    - restart_count
    - uptime_seconds
```

#### Metrics Examples

```bash
# Collect CPU and memory metrics for 1 hour
sysctl metrics api --duration 1h --metrics cpu,memory --interval 1m

# Export all system metrics
sysctl metrics --system --duration 24h --export --format json > system-metrics.json

# Real-time metrics monitoring
sysctl metrics api --watch --interval 10s --metrics requests,errors
```

### `sysctl monitor`

Real-time monitoring with alerts and notifications.

```bash
# Monitor service
sysctl monitor api

# Monitor multiple services
sysctl monitor api worker database

# Monitor with alerting
sysctl monitor api --alerts --threshold cpu=80,memory=85

# Continuous monitoring
sysctl monitor --all --env production --duration 24h
```

#### Monitor Options

- `--alerts`: Enable alerting
- `--threshold THRESHOLDS`: Alert thresholds (e.g., cpu=80,memory=90)
- `--duration DURATION`: Monitoring duration
- `--interval SECONDS`: Check interval
- `--notify CHANNELS`: Notification channels
- `--save-report`: Save monitoring report
- `--quiet`: Suppress normal output, show alerts only

#### Monitor Examples

```bash
# Monitor with custom thresholds and notifications
sysctl monitor api --alerts --threshold cpu=75,memory=80,errors=5 --notify slack,email

# Long-term monitoring with reporting
sysctl monitor --all --env production --duration 7d --save-report --interval 60

# Silent monitoring (alerts only)
sysctl monitor api --quiet --alerts --threshold cpu=90,memory=95
```

## Alert Management

### `sysctl alert`

Configure and manage alerting rules.

```bash
# List active alerts
sysctl alert list

# Create alert rule
sysctl alert create high-cpu --condition "cpu > 80" --service api

# Test alert rule
sysctl alert test high-cpu --service api

# Acknowledge alert
sysctl alert ack high-cpu-api-12345
```

#### Alert Rules Configuration

```yaml
# alerts/production.yaml
alerts:
  high_cpu:
    condition: "cpu_usage_percent > 80"
    duration: "5m"
    severity: "warning"
    services: ["api", "worker"]
    channels: ["slack", "email"]

    message: |
      High CPU usage detected on {{ .service }}
      Current: {{ .value }}%
      Threshold: {{ .threshold }}%

  service_down:
    condition: "replica_count == 0"
    severity: "critical"
    services: ["api", "database"]
    channels: ["pagerduty", "slack"]

    escalation:
      - delay: "5m"
        channels: ["pagerduty"]
      - delay: "15m"
        channels: ["phone"]

  high_error_rate:
    condition: "error_rate_percent > 5"
    duration: "2m"
    severity: "warning"
    services: ["api"]

    actions:
      - type: "restart"
        parameters:
          max_restarts: 3
          backoff: "exponential"
```

#### Alert Commands

```bash
# Import alert configuration
sysctl alert import alerts/production.yaml --env production

# List alert rules
sysctl alert rules --env production

# Show alert history
sysctl alert history --service api --duration 24h

# Silence alerts temporarily
sysctl alert silence high-cpu --duration 2h --reason "Planned maintenance"

# Test notification channels
sysctl alert test-channel slack --message "Test notification"
```

### Notification Channels

```yaml
# notifications/channels.yaml
channels:
  slack:
    webhook_url_env: "SLACK_WEBHOOK_URL"
    channel: "#alerts"
    username: "SystemControl"
    icon_emoji: ":warning:"

  email:
    smtp_server: "smtp.company.com:587"
    from_env: "ALERT_FROM_EMAIL"
    to: ["devops@company.com", "oncall@company.com"]
    subject_template: "{{ .severity | upper }}: {{ .alert_name }} - {{ .service }}"

  pagerduty:
    integration_key_env: "PAGERDUTY_INTEGRATION_KEY"
    severity_mapping:
      critical: "critical"
      warning: "warning"
      info: "info"

  webhook:
    url: "https://hooks.company.com/alerts"
    headers:
      Authorization: "Bearer {{ .webhook_token }}"
    payload_template: |
      {
        "alert": "{{ .alert_name }}",
        "service": "{{ .service }}",
        "severity": "{{ .severity }}",
        "value": {{ .value }},
        "timestamp": "{{ .timestamp }}"
      }
```

## Log Analysis

### `sysctl logs`

Advanced log searching, filtering, and analysis.

```bash
# Search logs across services
sysctl logs --search "database connection failed"

# Aggregate logs from multiple services
sysctl logs api worker --aggregate --since 1h

# Log analysis with patterns
sysctl logs api --analyze --patterns error-patterns.yaml

# Export logs for external analysis
sysctl logs api --since 24h --format json > api-logs.json
```

#### Advanced Log Filtering

```bash
# Filter by log level and time range
sysctl logs api --level error --since 2h --until 1h

# Filter by custom fields
sysctl logs api --filter "user_id=12345,action=login"

# Regular expression filtering
sysctl logs api --regex "HTTP [45][0-9][0-9]"

# Exclude patterns
sysctl logs api --exclude "health.*check" --since 1h
```

#### Log Analysis Features

```bash
# Error rate analysis
sysctl logs api --analyze-errors --duration 1h

# Performance analysis
sysctl logs api --analyze-performance --duration 6h

# Pattern detection
sysctl logs api --detect-patterns --duration 24h

# Log correlation across services
sysctl logs api worker --correlate --trace-id request_id
```

### Log Aggregation

```yaml
# logging/aggregation.yaml
aggregation:
  backends:
    elasticsearch:
      url: "https://elasticsearch.company.com:9200"
      index_pattern: "services-{{ .date }}"
      retention_days: 30

    loki:
      url: "https://loki.company.com:3100"
      retention_days: 14

  parsing:
    json:
      enabled: true
      fields: ["timestamp", "level", "message", "service", "trace_id"]

    structured:
      patterns:
        nginx: "%{COMBINEDAPACHELOG}"
        application: "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}"

  enrichment:
    - add_service_metadata
    - add_environment_tags
    - extract_trace_ids
    - geoip_lookup
```

## Performance Analysis

### `sysctl analyze`

Deep performance analysis and bottleneck identification.

```bash
# Performance analysis
sysctl analyze performance api --duration 1h

# Resource utilization analysis
sysctl analyze resources --all --env production

# Request pattern analysis
sysctl analyze requests api --duration 6h

# Database performance analysis
sysctl analyze database --connections --queries --duration 2h
```

#### Analysis Types

```bash
# CPU profiling
sysctl analyze cpu api --duration 10m --granularity 1s

# Memory analysis
sysctl analyze memory api --include-leaks --duration 1h

# Network analysis
sysctl analyze network --services api,worker --duration 30m

# Dependency analysis
sysctl analyze dependencies api --trace-calls --duration 15m

# Error analysis
sysctl analyze errors api --categorize --duration 24h
```

### Performance Reports

```bash
# Generate performance report
sysctl report performance api --duration 7d --format pdf

# SLA compliance report
sysctl report sla --all --env production --duration 30d

# Capacity planning report
sysctl report capacity --predict 30d --env production

# Cost analysis report
sysctl report cost --all --duration 30d --breakdown service,region
```

## Health Monitoring

### `sysctl health`

Comprehensive health monitoring and diagnostics.

```bash
# System health overview
sysctl health --all --env production

# Deep health check
sysctl health api --deep --include-dependencies

# Health trending
sysctl health api --trend --duration 7d

# Custom health checks
sysctl health api --custom health-checks.yaml
```

#### Health Check Configuration

```yaml
# health-checks.yaml
health_checks:
  api:
    http:
      endpoint: "/health"
      timeout: 5
      expected_status: 200
      expected_body_contains: "healthy"

    database:
      type: "postgres"
      connection_string_env: "DATABASE_URL"
      query: "SELECT 1"
      timeout: 3

    redis:
      type: "redis"
      url_env: "REDIS_URL"
      command: "PING"
      timeout: 2

    external_api:
      type: "http"
      url: "https://api.external-service.com/health"
      timeout: 10
      headers:
        Authorization: "Bearer {{ .api_token }}"

  worker:
    queue:
      type: "rabbitmq"
      url_env: "RABBITMQ_URL"
      queue: "default"
      max_queue_size: 1000

    disk_space:
      type: "disk"
      path: "/var/lib/app"
      min_free_percent: 10
```

### Health Dashboards

```bash
# Health status dashboard
sysctl dashboard health --env production --services api,worker,database

# Health trends dashboard
sysctl dashboard health-trends --duration 7d --env production

# SLA compliance dashboard
sysctl dashboard sla --env production --services api
```

## Integration Monitoring

### External Service Monitoring

```yaml
# integrations/monitoring.yaml
external_services:
  database:
    postgres:
      host: "{{ .database_host }}"
      port: 5432
      database: "{{ .database_name }}"

    monitoring:
      - query_performance
      - connection_count
      - lock_analysis
      - replication_lag

  cache:
    redis:
      url: "{{ .redis_url }}"

    monitoring:
      - memory_usage
      - key_count
      - hit_rate
      - connection_count

  message_queue:
    rabbitmq:
      url: "{{ .rabbitmq_url }}"

    monitoring:
      - queue_depth
      - message_rate
      - consumer_count
      - memory_usage
```

### Cloud Provider Integration

```bash
# AWS CloudWatch integration
sysctl monitor aws --services ec2,rds,elasticache --region us-east-1

# Azure Monitor integration
sysctl monitor azure --resource-group production --subscription-id xxx

# GCP Monitoring integration
sysctl monitor gcp --project-id company-prod --zone us-central1-a
```

## Best Practices

### Monitoring Strategy

1. **Layered Monitoring**: System, application, and business metrics
2. **Proactive Alerting**: Alert on trends, not just thresholds
3. **Correlation**: Link metrics, logs, and traces
4. **SLA Monitoring**: Track service level objectives
5. **Capacity Planning**: Monitor resource trends

### Alert Best Practices Configuration

```yaml
# alert-best-practices.yaml
alert_principles:
  actionable: true # Every alert should require action
  specific: true # Alerts should be specific to issues
  timely: true # Alerts should fire at the right time

thresholds:
  warning: "Issues that need attention but aren't urgent"
  critical: "Issues that need immediate action"

escalation:
  first_responder: "Team member on call"
  escalation_time: "15m"
  executive_escalation: "1h for critical issues"
```

### Dashboard Design

```yaml
# dashboard-guidelines.yaml
dashboard_types:
  executive:
    focus: "Business metrics and SLA compliance"
    update_frequency: "hourly"

  operational:
    focus: "System health and performance"
    update_frequency: "5 minutes"

  debugging:
    focus: "Detailed metrics for troubleshooting"
    update_frequency: "real-time"

layout:
  top_level: "Most critical metrics first"
  grouping: "Related metrics together"
  colors: "Consistent color scheme for status"
```

## Troubleshooting

### Common Issues

```bash
# Monitoring system issues
sysctl diagnose monitoring --check-backends --check-connectivity

# Missing metrics
sysctl debug metrics api --verbose --check-exporters

# Alert not firing
sysctl debug alert high-cpu --test-condition --test-channels

# Dashboard not loading
sysctl debug dashboard --check-config --check-data-sources
```

### Performance Optimization

```bash
# Optimize metric collection
sysctl optimize metrics --reduce-cardinality --efficient-queries

# Optimize log processing
sysctl optimize logs --sampling-rate 0.1 --async-processing

# Optimize alerting
sysctl optimize alerts --batch-notifications --reduce-noise
```
