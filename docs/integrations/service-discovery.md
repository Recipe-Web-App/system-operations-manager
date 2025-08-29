# Service Discovery Integration

Comprehensive service discovery integration for dynamic service registration, health monitoring,
and load balancing across distributed systems.

## Overview

Service discovery features:

- **Multi-Backend Support**: Consul, etcd, Kubernetes, Eureka, and DNS-based discovery
- **Dynamic Registration**: Automatic service registration and deregistration
- **Health Monitoring**: Continuous health checks and status updates
- **Load Balancing**: Intelligent routing and load distribution
- **Service Mesh Integration**: Automatic sidecar proxy configuration
- **Configuration Management**: Dynamic configuration updates

## Configuration

### Consul Integration

```yaml
# integrations/consul.yaml
consul:
  server:
    address: "consul.company.com:8500"
    datacenter: "dc1"

  authentication:
    token_env: "CONSUL_TOKEN"
    # Alternative: ACL token file
    # token_file: "/etc/consul/token"

  tls:
    enabled: true
    ca_file: "/etc/consul/ca.pem"
    cert_file: "/etc/consul/client.pem"
    key_file: "/etc/consul/client-key.pem"
    verify_ssl: true

  service_registration:
    auto_register: true
    deregister_on_exit: true
    tags: ["system-control", "v2.1.0"]
    meta:
      version: "2.1.0"
      environment: "production"
      team: "platform"

  health_checks:
    enabled: true
    interval: "10s"
    timeout: "5s"
    deregister_after: "30s"

  discovery:
    refresh_interval: "30s"
    cache_ttl: "60s"
    watch_services: true

  connect:
    enabled: true
    sidecar_proxy: true
    intentions: []
```

### Kubernetes Service Discovery

```yaml
# integrations/kubernetes-discovery.yaml
kubernetes_discovery:
  cluster_config:
    kubeconfig: "~/.kube/config"
    context: "production"

  service_discovery:
    namespaces: ["production", "staging"]
    selectors:
      app.kubernetes.io/part-of: "system-control"

  endpoints:
    enabled: true
    ready_only: true
    include_not_ready: false

  annotations:
    service_port: "service.system-control.io/port"
    health_path: "service.system-control.io/health-path"
    metrics_path: "service.system-control.io/metrics-path"

  labels:
    service_name: "app.kubernetes.io/name"
    service_version: "app.kubernetes.io/version"
    environment: "app.kubernetes.io/environment"
```

### etcd Configuration

```yaml
# integrations/etcd.yaml
etcd:
  endpoints:
    - "etcd-1.company.com:2379"
    - "etcd-2.company.com:2379"
    - "etcd-3.company.com:2379"

  authentication:
    username_env: "ETCD_USERNAME"
    password_env: "ETCD_PASSWORD"

  tls:
    enabled: true
    ca_file: "/etc/etcd/ca.pem"
    cert_file: "/etc/etcd/client.pem"
    key_file: "/etc/etcd/client-key.pem"

  service_registration:
    key_prefix: "/services/"
    ttl: 30
    refresh_interval: 10

  discovery:
    watch_prefix: "/services/"
    recursive: true
```

## Service Registration

### System Control CLI Integration

```bash
# Register service
sysctl discovery register api \
  --address 10.0.1.100 \
  --port 8080 \
  --tags "api,v2.1.0,production" \
  --health-check http://10.0.1.100:8080/health

# Deregister service
sysctl discovery deregister api --service-id api-node-1

# List registered services
sysctl discovery list --backend consul

# Check service health
sysctl discovery health api --backend consul

# Watch service changes
sysctl discovery watch api --follow
```

### Automatic Service Registration

```python
# Example: Python service registration
from system_control.discovery import ServiceRegistry
import atexit

# Initialize service registry
registry = ServiceRegistry(backend='consul')

# Register service
service_id = registry.register(
    name="api",
    address="10.0.1.100",
    port=8080,
    tags=["api", "v2.1.0", "production"],
    health_check={
        "http": "http://10.0.1.100:8080/health",
        "interval": "10s",
        "timeout": "5s"
    },
    meta={
        "version": "2.1.0",
        "environment": "production",
        "started_at": "2024-01-15T10:30:00Z"
    }
)

# Deregister on exit
atexit.register(lambda: registry.deregister(service_id))

# Update service metadata
registry.update_meta(service_id, {
    "last_deployed": "2024-01-15T10:30:00Z",
    "health_status": "healthy"
})
```

### Service Configuration Template

```yaml
# services/api-service.yaml
service_definition:
  name: "api"
  id: "api-{{ .instance_id }}"
  address: "{{ .host_ip }}"
  port: 8080

  tags:
    - "api"
    - "{{ .version }}"
    - "{{ .environment }}"
    - "http"

  meta:
    version: "{{ .version }}"
    environment: "{{ .environment }}"
    team: "backend"
    repository: "github.com/company/api"

  health_checks:
    - name: "HTTP Health Check"
      http: "http://{{ .host_ip }}:8080/health"
      interval: "10s"
      timeout: "5s"

    - name: "TCP Port Check"
      tcp: "{{ .host_ip }}:8080"
      interval: "30s"
      timeout: "3s"

  connect:
    sidecar_service:
      proxy:
        upstreams:
          - destination_name: "database"
            local_bind_port: 5432
          - destination_name: "redis"
            local_bind_port: 6379
```

## Service Discovery

### Service Lookup

```bash
# Find services by name
sysctl discovery find api --backend consul

# Find services by tag
sysctl discovery find --tag "production" --backend consul

# Find healthy services only
sysctl discovery find api --healthy-only --backend consul

# Service details
sysctl discovery describe api --service-id api-node-1
```

### Load Balancing Integration

```yaml
# load-balancing/consul-template.yaml
# Consul Template for dynamic load balancer configuration
upstream api {
{{ range service "api" }}
server {{ .Address }}:{{ .Port }} max_fails=3 fail_timeout=30s;
{{ end }}
}

upstream worker {
{{ range service "worker" }}
server {{ .Address }}:{{ .Port }} max_fails=3 fail_timeout=30s;
{{ end }}
}

server {
listen 80;
server_name api.company.com;

location / {
proxy_pass http://api;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
}

location /health {
access_log off;
return 200 "healthy\n";
add_header Content-Type text/plain;
}
}
```

### DNS-Based Discovery

```yaml
# dns/dns-discovery.yaml
dns_discovery:
  zones:
    - name: "company.local"
      type: "consul"

  resolution:
    - pattern: "*.service.consul"
      resolver: "consul"

    - pattern: "*.default.svc.cluster.local"
      resolver: "kubernetes"

  caching:
    enabled: true
    ttl: "30s"
    negative_ttl: "10s"

  health_awareness:
    enabled: true
    unhealthy_weight: 0
# Example DNS queries
# api.service.consul -> Returns healthy API service instances
# worker.service.consul -> Returns healthy worker instances
```

## Health Monitoring

### Health Check Configuration

```yaml
# health-checks/comprehensive.yaml
health_checks:
  api_service:
    checks:
      - name: "HTTP Health Endpoint"
        type: "http"
        url: "http://{{ .address }}:{{ .port }}/health"
        method: "GET"
        timeout: "5s"
        interval: "10s"
        expected_status: 200
        expected_body: "healthy"

      - name: "Database Connectivity"
        type: "script"
        script: "curl -f http://{{ .address }}:{{ .port }}/health/db"
        timeout: "10s"
        interval: "30s"

      - name: "Memory Usage"
        type: "script"
        script: |
          #!/bin/bash
          MEMORY=$(curl -s http://{{ .address }}:{{ .port }}/metrics | grep memory_usage | cut -d' ' -f2)
          if (( $(echo "$MEMORY > 0.9" | bc -l) )); then
            exit 1
          fi
          exit 0
        timeout: "5s"
        interval: "60s"

      - name: "Disk Space"
        type: "script"
        script: |
          #!/bin/bash
          DISK=$(df /var/lib/app | tail -1 | awk '{print $5}' | sed 's/%//')
          if [ "$DISK" -gt 85 ]; then
            exit 1
          fi
          exit 0
        timeout: "5s"
        interval: "300s"

    failure_threshold: 3
    success_threshold: 2
    deregister_critical_service_after: "90s"

  database_service:
    checks:
      - name: "TCP Connection"
        type: "tcp"
        address: "{{ .address }}:{{ .port }}"
        timeout: "3s"
        interval: "10s"

      - name: "Query Performance"
        type: "script"
        script: "pg_isready -h {{ .address }} -p {{ .port }} -t 5"
        timeout: "10s"
        interval: "30s"
```

### Health Check Commands

```bash
# Manual health check
sysctl discovery health-check api --check-name "HTTP Health Endpoint"

# Update health check status
sysctl discovery health-update api --status passing --output "All systems healthy"

# List failing health checks
sysctl discovery health-list --status failing

# Health check history
sysctl discovery health-history api --since 24h
```

## Service Mesh Integration

### Consul Connect

```yaml
# connect/intentions.yaml
connect_intentions:
  - source_name: "api"
    destination_name: "database"
    action: "allow"
    description: "API service needs database access"

  - source_name: "worker"
    destination_name: "database"
    action: "allow"
    description: "Worker service needs database access"

  - source_name: "*"
    destination_name: "api"
    action: "allow"
    description: "All services can call API"

  - source_name: "external"
    destination_name: "*"
    action: "deny"
    description: "Block external access by default"

# Sidecar proxy configuration
sidecar_proxies:
  api:
    upstreams:
      - destination_name: "database"
        local_bind_port: 5432
        config:
          connect_timeout_ms: 5000

      - destination_name: "redis"
        local_bind_port: 6379
        config:
          connect_timeout_ms: 1000

    config:
      protocol: "http"
      local_request_timeout_ms: 30000
      local_idle_timeout_ms: 300000
```

### Istio Integration

```yaml
# istio/service-discovery.yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-database
spec:
  hosts:
    - database.company.com
  ports:
    - number: 5432
      name: postgres
      protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: database-destination
spec:
  host: database.company.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30s
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    loadBalancer:
      simple: LEAST_CONN
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 30s
```

## Configuration Management

### Dynamic Configuration

```yaml
# config/dynamic-config.yaml
dynamic_configuration:
  consul_kv:
    enabled: true
    prefix: "config/system-control/"

    mappings:
      database_url: "database/connection_string"
      api_timeout: "api/request_timeout"
      log_level: "logging/level"
      feature_flags: "features/"

    polling:
      enabled: true
      interval: "30s"

    notifications:
      enabled: true
      webhook: "https://hooks.company.com/config-changed"

  kubernetes_configmap:
    enabled: true
    namespace: "production"
    configmaps:
      - name: "api-config"
        keys: ["database_url", "redis_url"]
      - name: "feature-flags"
        keys: ["*"]

  etcd_kv:
    enabled: true
    prefix: "/config/"
    watch: true
```

### Configuration Commands

```bash
# Get configuration
sysctl discovery config get database_url --backend consul

# Set configuration
sysctl discovery config set api_timeout 30s --backend consul

# Watch configuration changes
sysctl discovery config watch feature_flags --backend consul --follow

# Bulk configuration update
sysctl discovery config import config.yaml --backend consul --prefix "config/"
```

## Monitoring and Observability

### Discovery Metrics

```yaml
# metrics/discovery-metrics.yaml
discovery_metrics:
  service_registry:
    - name: "registered_services_total"
      type: "gauge"
      description: "Total number of registered services"
      labels: ["backend", "datacenter"]

    - name: "healthy_services_total"
      type: "gauge"
      description: "Number of healthy services"
      labels: ["service", "backend"]

    - name: "service_registration_duration"
      type: "histogram"
      description: "Time taken to register a service"
      labels: ["backend"]

  health_checks:
    - name: "health_check_duration"
      type: "histogram"
      description: "Health check execution time"
      labels: ["service", "check_name"]

    - name: "health_check_failures_total"
      type: "counter"
      description: "Total health check failures"
      labels: ["service", "check_name", "reason"]

  discovery:
    - name: "service_discovery_duration"
      type: "histogram"
      description: "Service discovery lookup time"
      labels: ["backend", "query_type"]

    - name: "discovery_cache_hits_total"
      type: "counter"
      description: "Service discovery cache hits"
      labels: ["backend"]
```

### Monitoring Commands

```bash
# Service registry status
sysctl discovery status --backend consul --detailed

# Health check summary
sysctl discovery health-summary --service api

# Discovery performance metrics
sysctl discovery metrics --duration 1h --backend consul

# Generate discovery report
sysctl discovery report --format pdf --include-metrics --period weekly
```

## Advanced Features

### Multi-Datacenter Setup

```yaml
# multi-dc/federation.yaml
datacenter_federation:
  datacenters:
    dc1:
      primary: true
      consul_address: "consul-dc1.company.com:8500"
      wan_address: "consul-dc1-wan.company.com:8302"

    dc2:
      primary: false
      consul_address: "consul-dc2.company.com:8500"
      wan_address: "consul-dc2-wan.company.com:8302"

  cross_dc_services:
    - name: "database"
      failover:
        - "dc1"
        - "dc2"

    - name: "api"
      load_balancing: "round_robin"
      datacenters: ["dc1", "dc2"]

  network_segments:
    - name: "production"
      port: 8301
      bind: "10.0.1.0"
      advertise: "10.0.1.0"

    - name: "staging"
      port: 8302
      bind: "10.0.2.0"
      advertise: "10.0.2.0"
```

### Service Catalog

```bash
# Service catalog management
sysctl discovery catalog create --template service-template.yaml

# Register service from catalog
sysctl discovery catalog deploy api --version v2.1.0 --environment production

# List catalog services
sysctl discovery catalog list --category database

# Update service catalog
sysctl discovery catalog update api --version v2.2.0 --changelog "Bug fixes"
```

## Security

### ACL Configuration

```yaml
# security/acl-policies.yaml
acl_policies:
  service_read:
    description: "Read access to services"
    rules: |
      service_prefix "" {
        policy = "read"
      }
      node_prefix "" {
        policy = "read"
      }

  service_write:
    description: "Write access to services"
    rules: |
      service_prefix "" {
        policy = "write"
      }
      node_prefix "" {
        policy = "write"
      }
      key_prefix "config/" {
        policy = "read"
      }

  operator:
    description: "Full operator access"
    rules: |
      operator = "write"
      service_prefix "" {
        policy = "write"
      }
      node_prefix "" {
        policy = "write"
      }
      key_prefix "" {
        policy = "write"
      }
```

### Security Commands

```bash
# Create ACL token
sysctl discovery acl create-token --policy service_read --description "Read-only token"

# List ACL policies
sysctl discovery acl list-policies

# Test ACL permissions
sysctl discovery acl test-permission --token ${TOKEN} --operation service:read:api

# Rotate ACL tokens
sysctl discovery acl rotate-token --token-id abc123 --keep-old 24h
```

## Troubleshooting

### Common Issues

```bash
# Test connectivity
sysctl discovery test-connection --backend consul

# Debug service registration
sysctl discovery debug register api --verbose

# Check health check status
sysctl discovery debug health-checks api --detailed

# Verify DNS resolution
sysctl discovery debug dns api.service.consul

# Network connectivity test
sysctl discovery debug network --test-ports 8300,8301,8302
```

### Performance Issues

```bash
# Discovery performance analysis
sysctl discovery analyze performance --duration 1h

# Cache hit rate analysis
sysctl discovery analyze cache-performance --backend consul

# Network latency analysis
sysctl discovery analyze network-latency --between-datacenters

# Load balancing efficiency
sysctl discovery analyze load-balancing --service api --duration 24h
```

## Best Practices

### Service Registration Best Practices

1. **Consistent Naming**: Use standardized service names across environments
2. **Meaningful Tags**: Include version, environment, and team information
3. **Health Checks**: Implement comprehensive health checks
4. **Graceful Shutdown**: Deregister services during planned shutdowns
5. **Metadata**: Include useful metadata for debugging and monitoring

### High Availability

```yaml
# Best practices configuration
high_availability:
  service_registration:
    retry_attempts: 3
    retry_delay: "5s"
    register_on_startup: true
    deregister_on_shutdown: true

  health_checks:
    multiple_checks: true
    check_intervals:
      critical_services: "10s"
      standard_services: "30s"
    timeout_configuration:
      http_checks: "5s"
      tcp_checks: "3s"
      script_checks: "10s"

  discovery:
    cache_configuration: true
    failover_mechanisms: true
    load_balancing: "weighted_round_robin"
    circuit_breakers: true
```
