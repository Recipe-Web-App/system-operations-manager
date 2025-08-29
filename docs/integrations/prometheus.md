# Prometheus Integration

Comprehensive integration with Prometheus for metrics collection, monitoring, and alerting across
your distributed system.

## Overview

Prometheus integration features:

- **Metrics Collection**: Automatic service discovery and metrics scraping
- **Custom Metrics**: Application-specific metric definitions and collection
- **Alert Rules**: Prometheus-native alerting rules and thresholds
- **Federation**: Multi-cluster Prometheus federation setup
- **Service Discovery**: Kubernetes, Consul, and file-based discovery
- **Recording Rules**: Pre-computed metric aggregations

## Configuration

### Basic Prometheus Configuration

```yaml
# integrations/prometheus.yaml
prometheus:
  server:
    url: "http://prometheus.company.com:9090"
    timeout: "30s"

  authentication:
    # Basic auth
    username_env: "PROMETHEUS_USER"
    password_env: "PROMETHEUS_PASSWORD"

    # Bearer token
    # token_env: "PROMETHEUS_TOKEN"

    # TLS configuration
    tls:
      cert_file: "/etc/ssl/certs/prometheus-client.pem"
      key_file: "/etc/ssl/private/prometheus-client.key"
      ca_file: "/etc/ssl/certs/prometheus-ca.pem"
      insecure_skip_verify: false

  scraping:
    interval: "15s"
    timeout: "10s"

  retention:
    time: "30d"
    size: "100GB"

  storage:
    path: "/var/lib/prometheus"

  external_labels:
    cluster: "production"
    region: "us-east-1"
    environment: "prod"
```

### Service Discovery Configuration

```yaml
# prometheus/service-discovery.yaml
scrape_configs:
  # Kubernetes service discovery
  - job_name: "kubernetes-services"
    kubernetes_sd_configs:
      - role: service
        namespaces:
          names: ["production", "staging"]
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

  # Static service configuration
  - job_name: "system-control-services"
    static_configs:
      - targets:
          - "api.company.com:8080"
          - "worker.company.com:8080"
          - "scheduler.company.com:8080"
    metrics_path: "/metrics"
    scrape_interval: 30s

  # Consul service discovery
  - job_name: "consul-services"
    consul_sd_configs:
      - server: "consul.company.com:8500"
        services: ["api", "worker", "database"]
        tags: ["prometheus"]
```

## Metrics Collection

### Application Metrics

```python
# Example: Instrumenting Python application
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Counter metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint'])

# Histogram metrics
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Gauge metrics
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
DATABASE_CONNECTIONS = Gauge('database_connections', 'Database connection pool', ['pool'])

def track_request(method, endpoint):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status='200').inc()

def track_error(method, endpoint):
    ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()

# Start metrics server
start_http_server(9090)
```

### Custom Metrics Configuration

```yaml
# metrics/custom-metrics.yaml
custom_metrics:
  business_metrics:
    - name: "orders_processed_total"
      type: "counter"
      description: "Total number of orders processed"
      labels: ["status", "payment_method"]

    - name: "revenue_total"
      type: "counter"
      description: "Total revenue generated"
      labels: ["currency", "product_category"]

    - name: "user_sessions_active"
      type: "gauge"
      description: "Currently active user sessions"
      labels: ["user_type"]

  system_metrics:
    - name: "deployment_duration_seconds"
      type: "histogram"
      description: "Time taken for deployments"
      labels: ["service", "environment", "strategy"]
      buckets: [1, 5, 10, 30, 60, 300, 600, 1200]

    - name: "backup_size_bytes"
      type: "gauge"
      description: "Size of backups in bytes"
      labels: ["service", "type", "environment"]
```

## System Control CLI Integration

### Metrics Commands

```bash
# Query Prometheus metrics
sysctl prometheus query 'up{job="api"}' --time now

# Query with time range
sysctl prometheus query-range 'rate(http_requests_total[5m])' --start 1h --end now --step 1m

# Get service metrics
sysctl prometheus metrics api --duration 1h --metrics cpu,memory,requests

# Export metrics
sysctl prometheus export --query 'up' --format json --output metrics.json
```

### Alert Rule Management

```bash
# List alert rules
sysctl prometheus alerts list

# Create alert rule
sysctl prometheus alerts create high-cpu-alert --rule alerts/high-cpu.yaml

# Test alert rule
sysctl prometheus alerts test high-cpu-alert --duration 5m

# Silence alerts
sysctl prometheus alerts silence high-cpu-alert --duration 2h --reason "Maintenance"
```

### Recording Rule Management

```bash
# List recording rules
sysctl prometheus recording-rules list

# Create recording rule
sysctl prometheus recording-rules create --file recording-rules/aggregations.yaml

# Validate recording rules
sysctl prometheus recording-rules validate recording-rules/aggregations.yaml
```

## Alert Rules

### System Alert Rules

```yaml
# alerts/system-alerts.yaml
groups:
  - name: system.rules
    rules:
      - alert: HighCPUUsage
        expr: (100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is above 80% on {{ $labels.instance }} for more than 5 minutes"
          runbook_url: "https://runbooks.company.com/alerts/high-cpu"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.85
        for: 10m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is above 85% on {{ $labels.instance }}"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"}) < 0.1
        for: 5m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk space is below 10% on {{ $labels.instance }}"
```

### Application Alert Rules

```yaml
# alerts/application-alerts.yaml
groups:
  - name: application.rules
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }} on {{ $labels.service }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High latency on {{ $labels.service }}"
          description: "95th percentile latency is {{ $value }}s on {{ $labels.service }}"

      - alert: ServiceDown
        expr: up{job=~"api|worker|scheduler"} == 0
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service {{ $labels.job }} has been down for more than 1 minute"
```

## Recording Rules

### Performance Recording Rules

```yaml
# recording-rules/performance.yaml
groups:
  - name: performance.rules
    interval: 30s
    rules:
      # Request rate recording rules
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)

      - record: job:http_requests:rate1h
        expr: sum(rate(http_requests_total[1h])) by (job)

      # Error rate recording rules
      - record: job:http_errors:rate5m
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)

      - record: job:http_error_rate:ratio
        expr: job:http_errors:rate5m / job:http_requests:rate5m

      # Latency recording rules
      - record: job:http_request_duration:p95
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))

      - record: job:http_request_duration:p99
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))

      # Resource utilization
      - record: instance:cpu_usage:ratio
        expr: 1 - avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)

      - record: instance:memory_usage:ratio
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes
```

### Business Recording Rules

```yaml
# recording-rules/business.yaml
groups:
  - name: business.rules
    interval: 60s
    rules:
      # Revenue metrics
      - record: business:revenue:rate1h
        expr: sum(rate(revenue_total[1h])) by (currency)

      - record: business:revenue:rate24h
        expr: sum(rate(revenue_total[24h])) by (currency)

      # Order metrics
      - record: business:orders:rate1h
        expr: sum(rate(orders_processed_total[1h])) by (status)

      - record: business:orders:success_rate
        expr: sum(rate(orders_processed_total{status="completed"}[1h])) / sum(rate(orders_processed_total[1h]))

      # User engagement
      - record: business:active_users:count
        expr: sum(user_sessions_active) by (user_type)
```

## Monitoring Dashboard Integration

### Grafana Dashboard Export

```bash
# Export metrics for Grafana
sysctl prometheus export-for-grafana --dashboard system-overview --output grafana-metrics.json

# Create Grafana data source configuration
sysctl prometheus create-grafana-datasource --output prometheus-datasource.json

# Sync metrics to Grafana
sysctl prometheus sync-to-grafana --dashboard production-overview
```

### Custom Dashboard Metrics

```yaml
# dashboards/system-overview-metrics.yaml
dashboard_metrics:
  system_overview:
    - name: "System CPU Usage"
      query: "avg(instance:cpu_usage:ratio) * 100"
      unit: "percent"

    - name: "System Memory Usage"
      query: "avg(instance:memory_usage:ratio) * 100"
      unit: "percent"

    - name: "Total Request Rate"
      query: "sum(job:http_requests:rate5m)"
      unit: "reqps"

    - name: "Overall Error Rate"
      query: "avg(job:http_error_rate:ratio) * 100"
      unit: "percent"

  service_details:
    - name: "Service Request Rate"
      query: "job:http_requests:rate5m"
      unit: "reqps"
      labels: ["job"]

    - name: "Service Latency P95"
      query: "job:http_request_duration:p95"
      unit: "seconds"
      labels: ["job"]

    - name: "Service Error Rate"
      query: "job:http_error_rate:ratio * 100"
      unit: "percent"
      labels: ["job"]
```

## Advanced Configuration

### Federation Setup

```yaml
# prometheus/federation.yaml
# Main Prometheus server
global:
  scrape_interval: 15s
  external_labels:
    cluster: "main"
    replica: "A"

scrape_configs:
  - job_name: "federate"
    scrape_interval: 15s
    honor_labels: true
    metrics_path: "/federate"
    params:
      "match[]":
        - '{job=~"prometheus|node|blackbox"}'
        - '{__name__=~"job:.*"}'
        - '{__name__=~"instance:.*"}'
    static_configs:
      - targets:
          - "prometheus-cluster-1:9090"
          - "prometheus-cluster-2:9090"
          - "prometheus-cluster-3:9090"
```

### Remote Storage Configuration

```yaml
# prometheus/remote-storage.yaml
remote_write:
  - url: "https://prometheus-remote-write.company.com/api/v1/write"
    basic_auth:
      username: "prometheus"
      password_file: "/etc/prometheus/remote-write-password"
    write_relabel_configs:
      - source_labels: [__name__]
        regex: "go_.*"
        action: drop

remote_read:
  - url: "https://prometheus-remote-read.company.com/api/v1/read"
    basic_auth:
      username: "prometheus"
      password_file: "/etc/prometheus/remote-read-password"
```

## Performance Optimization

### Query Optimization

```bash
# Analyze slow queries
sysctl prometheus analyze-queries --slow-threshold 5s --duration 24h

# Query performance testing
sysctl prometheus test-query 'rate(http_requests_total[5m])' --duration 1h --step 1m

# Index optimization
sysctl prometheus optimize-indexes --duration 7d

# Storage optimization
sysctl prometheus optimize-storage --compress --retention 30d
```

### Resource Monitoring

```bash
# Monitor Prometheus resource usage
sysctl prometheus monitor --metrics cpu,memory,disk,network --duration 1h

# Storage usage analysis
sysctl prometheus storage-usage --breakdown-by-metric --top 20

# Query load analysis
sysctl prometheus query-load --breakdown-by-user --duration 24h
```

## Troubleshooting

### Common Issues

```bash
# Check Prometheus connectivity
sysctl prometheus health-check

# Debug service discovery
sysctl prometheus debug service-discovery --job kubernetes-services

# Validate configuration
sysctl prometheus validate-config --file prometheus.yml

# Check target status
sysctl prometheus targets --unhealthy-only

# Analyze missing metrics
sysctl prometheus debug missing-metrics --service api --expected-metrics requests,errors,latency
```

### Performance Issues

```bash
# Identify expensive queries
sysctl prometheus debug expensive-queries --threshold 10s --duration 1h

# Memory usage analysis
sysctl prometheus debug memory-usage --top-series 50

# Disk usage breakdown
sysctl prometheus debug disk-usage --by-metric --by-label

# Network connectivity issues
sysctl prometheus debug connectivity --targets all
```

## Best Practices

### Metric Design

1. **Naming Convention**: Use consistent metric naming (e.g., `http_requests_total`)
2. **Labels**: Keep cardinality low, avoid high-cardinality labels
3. **Types**: Choose appropriate metric types (counter, gauge, histogram, summary)
4. **Documentation**: Document all custom metrics with descriptions
5. **Aggregation**: Use recording rules for expensive calculations

### Alert Design

```yaml
# Good alert practices
best_practices:
  alerts:
    - name: "Actionable alerts only"
      description: "Every alert should require action"

    - name: "Appropriate severity"
      description: "Use warning/critical appropriately"

    - name: "Clear descriptions"
      description: "Include context and suggested actions"

    - name: "Avoid flapping"
      description: "Use appropriate for: duration"

    - name: "Include runbooks"
      description: "Link to troubleshooting documentation"

  metrics:
    - name: "Low cardinality"
      description: "Avoid labels with high cardinality"

    - name: "Consistent naming"
      description: "Follow metric naming conventions"

    - name: "Proper types"
      description: "Use correct metric types"
```

### Resource Planning

```bash
# Capacity planning
sysctl prometheus capacity-plan --growth-rate 20% --duration 6m

# Retention optimization
sysctl prometheus optimize-retention --storage-limit 500GB --critical-metrics 90d

# Scraping optimization
sysctl prometheus optimize-scraping --target-efficiency 95%
```
