# Logging Integration

Comprehensive log aggregation, analysis, and management across your distributed system
with support for multiple backends and advanced search capabilities.

## Overview

Logging integration features:

- **Multi-Backend Support**: Elasticsearch, Loki, Fluentd, and file-based logging
- **Log Aggregation**: Centralized collection from all services and infrastructure
- **Advanced Search**: Full-text search, filtering, and pattern matching
- **Real-time Streaming**: Live log tailing and monitoring
- **Log Analysis**: Automated pattern detection and anomaly identification
- **Retention Management**: Automated log rotation and archival

## Configuration

### Logging Backend Configuration

```yaml
# integrations/logging.yaml
logging:
  backends:
    elasticsearch:
      enabled: true
      url: "https://elasticsearch.company.com:9200"
      username_env: "ELASTICSEARCH_USERNAME"
      password_env: "ELASTICSEARCH_PASSWORD"

      indices:
        pattern: "logs-%Y.%m.%d"
        settings:
          number_of_shards: 3
          number_of_replicas: 1
        mappings:
          properties:
            "@timestamp":
              type: "date"
            level:
              type: "keyword"
            message:
              type: "text"
              analyzer: "standard"
            service:
              type: "keyword"
            environment:
              type: "keyword"

    loki:
      enabled: true
      url: "https://loki.company.com:3100"
      tenant_id: "system-control"

      labels:
        - "service"
        - "environment"
        - "level"
        - "pod"
        - "namespace"

      retention:
        logs: "30d"
        chunks: "24h"

    fluentd:
      enabled: true
      host: "fluentd.company.com"
      port: 24224
      tag_prefix: "system-control"

  # Local file logging fallback
  file:
    enabled: true
    path: "/var/log/system-control"
    max_size: "100MB"
    max_files: 10
    compress: true

  # Log processing
  processing:
    structured: true
    format: "json"
    timestamp_format: "RFC3339"

    enrichment:
      - add_hostname
      - add_environment_labels
      - extract_kubernetes_metadata
      - geoip_lookup

    filtering:
      - drop_health_checks
      - sample_debug_logs: 0.1 # 10% sampling
      - anonymize_pii
```

## Log Collection

### Application Logging

```python
# Example: Structured logging in Python
import structlog
import logging
from pythonjsonlogger import jsonlogger

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# JSON formatter for structured logs
json_formatter = jsonlogger.JsonFormatter(
    fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)

# Add context to logs
logger = logger.bind(
    service="api",
    environment="production",
    version="v2.1.0"
)

# Structured logging examples
logger.info("User login", user_id=12345, ip_address="192.168.1.100")
logger.error("Database connection failed",
             error="connection timeout",
             database="primary",
             retry_count=3)
logger.warning("High memory usage",
               memory_usage_percent=85,
               threshold=80)
```

### Kubernetes Log Collection

```yaml
# logging/fluent-bit-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Path              /var/log/containers/*.log
        Parser            docker
        Tag               kube.*
        Refresh_Interval  5
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name            es
        Match           *
        Host            elasticsearch.logging.svc.cluster.local
        Port            9200
        Index           logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix logs
        Logstash_DateFormat %Y.%m.%d
        Include_Tag_Key Off
        Time_Key        @timestamp
```

## System Control CLI Integration

### Log Search and Analysis

```bash
# Search logs across all services
sysctl logs search "database connection failed" --since 1h

# Search with filters
sysctl logs search "error" --service api --level error --since 24h

# Real-time log streaming
sysctl logs stream --service api --follow

# Log analysis
sysctl logs analyze --service api --pattern-detection --since 7d

# Export logs
sysctl logs export --service api --since 1d --format json --output api-logs.json
```

### Advanced Log Queries

```bash
# Complex search queries
sysctl logs query '
  service:api AND
  level:error AND
  message:"timeout" AND
  @timestamp:[now-1h TO now]
' --limit 100

# Aggregation queries
sysctl logs aggregate '
  {
    "aggs": {
      "error_by_service": {
        "terms": {"field": "service"},
        "aggs": {
          "error_count": {
            "filter": {"term": {"level": "error"}}
          }
        }
      }
    }
  }
' --since 24h

# Log pattern analysis
sysctl logs patterns --service api --since 7d --top 20
```

## Log Processing and Enrichment

### Log Pipeline Configuration

```yaml
# logging/pipeline.yaml
log_pipeline:
  inputs:
    - name: "kubernetes_pods"
      type: "kubernetes"
      namespace: ["production", "staging"]

    - name: "application_logs"
      type: "file"
      paths: ["/var/log/app/*.log"]

    - name: "system_logs"
      type: "syslog"
      port: 514

  processors:
    - name: "json_parser"
      type: "json"
      field: "message"
      target: "parsed"

    - name: "timestamp_parser"
      type: "date"
      field: "parsed.timestamp"
      formats: ["ISO8601", "UNIX_MS"]

    - name: "level_normalizer"
      type: "script"
      source: |
        if event.get("parsed", {}).get("level"):
          level = event["parsed"]["level"].upper()
          if level in ["ERR", "ERROR", "FATAL"]:
            event["level"] = "ERROR"
          elif level in ["WARN", "WARNING"]:
            event["level"] = "WARN"
          elif level in ["INFO", "INFORMATION"]:
            event["level"] = "INFO"
          elif level in ["DEBUG", "TRACE"]:
            event["level"] = "DEBUG"

    - name: "service_enrichment"
      type: "enrich"
      source: "service_metadata"
      field: "service"
      target: "service_info"

    - name: "geoip_lookup"
      type: "geoip"
      field: "client_ip"
      target: "geo"

    - name: "pii_anonymization"
      type: "script"
      source: |
        import re
        # Anonymize email addresses
        if "message" in event:
          event["message"] = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_ANONYMIZED]',
            event["message"]
          )
        # Anonymize credit card numbers
        event["message"] = re.sub(
          r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
          '[CARD_ANONYMIZED]',
          event["message"]
        )

  outputs:
    - name: "elasticsearch_main"
      type: "elasticsearch"
      hosts: ["elasticsearch-1:9200", "elasticsearch-2:9200"]
      index: "logs-%{+YYYY.MM.dd}"

    - name: "loki_backup"
      type: "loki"
      url: "https://loki.company.com:3100"

    - name: "s3_archive"
      type: "s3"
      bucket: "log-archive"
      prefix: "logs/%{+YYYY/MM/dd}/"
      condition: 'event.get("level") in ["ERROR", "WARN"]'
```

## Log Monitoring and Alerting

### Log-Based Alerts

```yaml
# alerts/log-alerts.yaml
log_alerts:
  high_error_rate:
    name: "High Error Rate"
    query: |
      SELECT count(*)
      FROM logs
      WHERE level = 'ERROR'
        AND timestamp > now() - interval '5 minutes'
        AND service = '{{ service }}'
    threshold: 10
    window: "5m"
    severity: "warning"

  database_connection_errors:
    name: "Database Connection Errors"
    query: |
      SELECT count(*)
      FROM logs
      WHERE message LIKE '%database connection%'
        AND level = 'ERROR'
        AND timestamp > now() - interval '2 minutes'
    threshold: 1
    window: "2m"
    severity: "critical"

  suspicious_login_activity:
    name: "Suspicious Login Activity"
    query: |
      SELECT client_ip, count(*) as attempts
      FROM logs
      WHERE message LIKE '%failed login%'
        AND timestamp > now() - interval '10 minutes'
      GROUP BY client_ip
      HAVING attempts > 5
    threshold: 1
    window: "10m"
    severity: "warning"

  memory_leak_detection:
    name: "Potential Memory Leak"
    query: |
      SELECT service, avg(memory_usage_percent) as avg_memory
      FROM logs
      WHERE message LIKE '%memory usage%'
        AND timestamp > now() - interval '30 minutes'
      GROUP BY service
      HAVING avg_memory > 90
    threshold: 1
    window: "30m"
    severity: "critical"
```

### Alert Management Commands

```bash
# Create log-based alerts
sysctl logs alert create --rule alerts/log-alerts.yaml

# List active log alerts
sysctl logs alert list --active

# Test alert query
sysctl logs alert test database_connection_errors --dry-run

# Acknowledge alert
sysctl logs alert ack high_error_rate_api_12345

# Create custom alert
sysctl logs alert create custom-alert \
  --query 'level:ERROR AND service:api' \
  --threshold 5 \
  --window 5m \
  --notify slack
```

## Log Analysis and Insights

### Automated Pattern Detection

```yaml
# analysis/pattern-detection.yaml
pattern_detection:
  error_patterns:
    - name: "Connection Timeouts"
      pattern: ".*timeout.*connection.*"
      severity: "high"
      category: "network"

    - name: "Out of Memory"
      pattern: ".*out of memory|OOM|memory.*exceeded.*"
      severity: "critical"
      category: "resource"

    - name: "Authentication Failures"
      pattern: ".*authentication.*failed|login.*failed|unauthorized.*"
      severity: "medium"
      category: "security"

  anomaly_detection:
    - name: "Error Rate Spike"
      metric: "error_count_per_minute"
      algorithm: "statistical"
      sensitivity: 0.8

    - name: "Response Time Anomaly"
      metric: "response_time_p95"
      algorithm: "seasonal"
      seasonal_period: "24h"

  correlation_analysis:
    - name: "Error Correlation"
      fields: ["service", "error_type", "timestamp"]
      window: "10m"
      threshold: 0.7
```

### Log Analysis Commands

```bash
# Detect patterns in logs
sysctl logs patterns detect --service api --since 24h --auto-categorize

# Anomaly detection
sysctl logs anomalies detect --metric error_rate --since 7d --sensitivity 0.8

# Correlation analysis
sysctl logs correlate --events "deployment,errors" --window 30m --since 7d

# Generate log insights
sysctl logs insights --service api --duration 7d --format report

# Root cause analysis
sysctl logs root-cause analyze --error-pattern "database.*timeout" --since 1h
```

## Log Retention and Archival

### Retention Policies

```yaml
# retention/policies.yaml
retention_policies:
  production:
    error_logs:
      retention: "90d"
      archive_after: "30d"
      archive_storage: "s3://log-archive/production/errors/"

    info_logs:
      retention: "30d"
      archive_after: "7d"
      archive_storage: "s3://log-archive/production/info/"

    debug_logs:
      retention: "7d"
      no_archive: true

  staging:
    all_logs:
      retention: "14d"
      archive_after: "7d"
      archive_storage: "s3://log-archive/staging/"

  development:
    all_logs:
      retention: "3d"
      no_archive: true

# Index lifecycle management
ilm_policies:
  logs_policy:
    phases:
      hot:
        actions:
          rollover:
            max_size: "10GB"
            max_age: "1d"
      warm:
        min_age: "1d"
        actions:
          allocate:
            number_of_replicas: 0
      cold:
        min_age: "7d"
        actions:
          allocate:
            number_of_replicas: 0
          freeze: {}
      delete:
        min_age: "30d"
```

### Retention Management Commands

```bash
# Apply retention policies
sysctl logs retention apply --policy retention/policies.yaml

# Check retention status
sysctl logs retention status --service api

# Manual archive
sysctl logs archive --service api --older-than 30d --destination s3://archive/

# Cleanup old logs
sysctl logs cleanup --dry-run --older-than 90d

# Restore from archive
sysctl logs restore --from s3://archive/2024/01/15/ --to-index logs-restored
```

## Performance Optimization

### Log Ingestion Optimization

```yaml
# optimization/ingestion.yaml
ingestion_optimization:
  batching:
    max_batch_size: 1000
    max_batch_time: "5s"

  compression:
    enabled: true
    algorithm: "gzip"
    level: 6

  buffering:
    memory_limit: "100MB"
    disk_limit: "1GB"
    flush_interval: "10s"

  parallel_processing:
    workers: 4
    queue_size: 10000

  sampling:
    debug_logs: 0.1 # Sample 10% of debug logs
    info_logs: 1.0 # Keep all info logs
    error_logs: 1.0 # Keep all error logs
```

### Search Performance

```bash
# Index optimization
sysctl logs optimize-indices --older-than 1d --force-merge

# Search performance analysis
sysctl logs analyze search-performance --slow-queries --duration 24h

# Cache optimization
sysctl logs optimize-cache --eviction-policy lru --max-size 1GB

# Shard optimization
sysctl logs optimize-shards --target-shard-size 20GB --rebalance
```

## Security and Compliance

### Log Security

```yaml
# security/log-security.yaml
security:
  encryption:
    at_rest: true
    in_transit: true
    key_rotation: "30d"

  access_control:
    - role: "log_admin"
      permissions: ["read", "write", "delete", "admin"]
      users: ["admin@company.com"]

    - role: "log_reader"
      permissions: ["read"]
      users: ["developer@company.com"]
      filters:
        - "service:api OR service:worker"
        - "NOT level:debug"

  audit_logging:
    enabled: true
    events: ["search", "export", "delete", "config_change"]
    destination: "audit-logs"

  data_privacy:
    pii_detection: true
    anonymization: true
    fields_to_anonymize: ["email", "ip_address", "user_id"]
    retention_limits:
      pii_data: "30d"
      non_pii_data: "365d"
```

### Compliance Features

```bash
# Generate compliance reports
sysctl logs compliance report --standard sox --period monthly

# Data lineage tracking
sysctl logs track-lineage --field user_data --since 30d

# Privacy compliance
sysctl logs privacy scan --detect-pii --anonymize --service api

# Audit log analysis
sysctl logs audit analyze --events "data_access" --user "specific@email.com"
```

## Troubleshooting

### Common Issues

```bash
# Test log ingestion
sysctl logs test-ingestion --service api --sample-rate 1

# Debug log parsing
sysctl logs debug parser --log-sample sample.log --parser json

# Check log pipeline health
sysctl logs pipeline health --detailed

# Verify log routing
sysctl logs debug routing --source kubernetes --destination elasticsearch

# Index health check
sysctl logs debug indices --unhealthy-only
```

### Performance Issues

```bash
# Identify slow queries
sysctl logs debug slow-queries --threshold 5s --since 1h

# Memory usage analysis
sysctl logs debug memory-usage --component all

# Disk usage breakdown
sysctl logs debug disk-usage --by-index --by-service

# Network connectivity issues
sysctl logs debug connectivity --test-endpoints
```

## Best Practices

### Structured Logging

1. **Consistent Format**: Use JSON for structured logs
2. **Standard Fields**: Include timestamp, level, service, environment
3. **Correlation IDs**: Add trace/request IDs for distributed tracing
4. **Semantic Levels**: Use appropriate log levels (DEBUG, INFO, WARN, ERROR)
5. **Context**: Include relevant context without sensitive data

### Log Management

```yaml
# Best practices configuration
best_practices:
  logging:
    - use_structured_format: true
    - include_correlation_ids: true
    - avoid_logging_secrets: true
    - use_appropriate_levels: true
    - include_error_context: true

  retention:
    - set_appropriate_retention: true
    - archive_old_logs: true
    - compress_archived_logs: true
    - monitor_storage_costs: true

  performance:
    - batch_log_shipping: true
    - use_async_logging: true
    - implement_sampling: true
    - optimize_queries: true

  security:
    - encrypt_logs: true
    - control_access: true
    - audit_log_access: true
    - anonymize_pii: true
```
