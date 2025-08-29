# Traffic Management Commands

Advanced traffic management capabilities including blue-green deployments,
canary releases,
traffic splitting, and load balancing control.

## Overview

Traffic management features:

- **Blue-Green Deployments**: Full environment switches with instant rollback
- **Canary Releases**: Gradual traffic shifting with automated promotion/rollback
- **Traffic Splitting**: Percentage-based traffic distribution
- **Load Balancing**: Dynamic load balancer configuration
- **Circuit Breakers**: Automatic failure detection and traffic rerouting
- **A/B Testing**: Traffic-based feature testing

## Blue-Green Deployment

### `sysctl traffic blue-green`

Manage blue-green deployment strategies.

```bash
# Start blue-green deployment
sysctl traffic blue-green deploy api --env production

# Check deployment status
sysctl traffic blue-green status api --env production

# Promote green environment to live
sysctl traffic blue-green promote api --env production

# Switch traffic back to blue
sysctl traffic blue-green switch-to-blue api --env production
```

#### Blue-Green Configuration

```yaml
# traffic/blue-green.yaml
blue_green:
  api:
    strategy:
      switch_timeout: "300s"
      health_check_timeout: "120s"
      auto_promote: false
      cleanup_delay: "600s"

    traffic:
      load_balancer: "nginx"
      health_endpoint: "/health"
      readiness_timeout: "60s"

    environments:
      blue:
        weight: 100
        instances: 3
      green:
        weight: 0
        instances: 3

    rollback:
      automatic: true
      failure_threshold: 5 # percent
      monitor_duration: "300s"
```

#### Blue-Green Examples

```bash
# Deploy with automatic promotion
sysctl traffic blue-green deploy api --auto-promote --health-threshold 95

# Deploy with extended monitoring
sysctl traffic blue-green deploy api --monitor-duration 600s --env production

# Manual traffic switch
sysctl traffic blue-green switch api --from blue --to green --gradual
```

## Canary Deployment

### `sysctl traffic canary`

Gradual traffic shifting for safe deployments.

```bash
# Start canary deployment
sysctl traffic canary deploy api --env production

# Check canary status
sysctl traffic canary status api --env production

# Manually promote canary
sysctl traffic canary promote api --env production

# Abort canary deployment
sysctl traffic canary abort api --env production
```

#### Canary Configuration

```yaml
# traffic/canary.yaml
canary:
  api:
    steps:
      - traffic_percent: 5
        duration: "5m"
        success_threshold: 99

      - traffic_percent: 10
        duration: "5m"
        success_threshold: 99

      - traffic_percent: 25
        duration: "10m"
        success_threshold: 98

      - traffic_percent: 50
        duration: "10m"
        success_threshold: 98

      - traffic_percent: 100

    metrics:
      success_rate:
        threshold: 99
        window: "5m"
      error_rate:
        threshold: 1
        window: "5m"
      response_time:
        threshold: "500ms"
        percentile: 95

    auto_promote: true
    auto_rollback: true

    notification:
      channels: ["slack", "email"]
      events: ["started", "promoted", "aborted", "completed"]
```

#### Advanced Canary Features

```bash
# Canary with custom metrics
sysctl traffic canary deploy api --metrics custom-metrics.yaml

# Canary with A/B testing
sysctl traffic canary deploy api --ab-test --variant-header "X-Variant"

# Regional canary deployment
sysctl traffic canary deploy api --region us-east-1 --percentage 10
```

## Traffic Splitting

### `sysctl traffic split`

Fine-grained traffic distribution control.

```bash
# Split traffic between versions
sysctl traffic split api --v1=80 --v2=20

# Geographic traffic splitting
sysctl traffic split api --us-east=60 --us-west=40

# Header-based routing
sysctl traffic split api --header "X-User-Type" --premium=70 --standard=30
```

#### Traffic Splitting Configuration

```yaml
# traffic/splitting.yaml
traffic_splitting:
  api:
    rules:
      - name: "version_split"
        type: "version"
        splits:
          v1.0: 80
          v2.0: 20

      - name: "geographic_split"
        type: "geographic"
        splits:
          us-east-1: 50
          us-west-2: 30
          eu-west-1: 20

      - name: "user_type_split"
        type: "header"
        header: "X-User-Type"
        splits:
          premium: 60
          standard: 40

    sticky_sessions: true
    session_affinity: "cookie"

    load_balancer:
      algorithm: "weighted_round_robin"
      health_checks: true
      timeout: "30s"
```

#### Traffic Split Examples

```bash
# Gradual traffic migration
sysctl traffic split api --from v1.0=100 --to v2.0=0
sysctl traffic split api --migrate --from v1.0 --to v2.0 --rate 10 --interval 2m

# Feature flag based splitting
sysctl traffic split api --feature-flag "new_ui" --enabled=25 --disabled=75

# Load balancer weight adjustment
sysctl traffic split api --adjust-weights --target-utilization 70
```

## Load Balancer Management

### `sysctl lb`

Direct load balancer configuration and management.

```bash
# List load balancers
sysctl lb list --env production

# Show load balancer configuration
sysctl lb show nginx-api --env production

# Update load balancer rules
sysctl lb update nginx-api --config new-rules.yaml

# Load balancer health check
sysctl lb health nginx-api --detailed
```

#### Load Balancer Configuration

```yaml
# lb/nginx-api.yaml
load_balancer:
  name: "nginx-api"
  type: "nginx"

  upstream:
    servers:
      - server: "api-v1-1:8080"
        weight: 3
        max_fails: 2
        fail_timeout: "30s"
      - server: "api-v1-2:8080"
        weight: 3
        max_fails: 2
        fail_timeout: "30s"
      - server: "api-v2-1:8080"
        weight: 1
        max_fails: 2
        fail_timeout: "30s"

  health_check:
    uri: "/health"
    interval: "10s"
    timeout: "5s"
    passes: 2
    fails: 3

  algorithms:
    method: "least_conn"

  session:
    persistence: true
    cookie_name: "session_id"
    timeout: "1h"
```

## Circuit Breaker Management

### `sysctl circuit`

Circuit breaker configuration for failure resilience.

```bash
# List circuit breakers
sysctl circuit list --env production

# Show circuit breaker status
sysctl circuit status api-to-database

# Reset circuit breaker
sysctl circuit reset api-to-database

# Configure circuit breaker
sysctl circuit configure api-to-database --config cb-config.yaml
```

#### Circuit Breaker Configuration

```yaml
# circuit-breakers/api-database.yaml
circuit_breakers:
  api-to-database:
    failure_threshold: 5
    recovery_timeout: "30s"
    success_threshold: 3
    timeout: "10s"

    monitoring:
      window_size: "60s"
      minimum_requests: 10

    actions:
      on_open:
        - log_event
        - notify_team
        - switch_to_readonly

      on_half_open:
        - log_event
        - test_connection

      on_close:
        - log_event
        - restore_full_service

    fallback:
      enabled: true
      strategy: "cached_response"
      cache_ttl: "300s"
```

## Service Mesh Integration

### `sysctl mesh`

Service mesh traffic management.

```bash
# Istio traffic management
sysctl mesh istio traffic api --split v1=90,v2=10

# Linkerd traffic policy
sysctl mesh linkerd policy api --retry-budget 10

# Consul Connect routing
sysctl mesh consul route api --upstream database --timeout 30s
```

#### Service Mesh Configuration

```yaml
# mesh/istio-config.yaml
service_mesh:
  type: "istio"

  virtual_services:
    api:
      hosts: ["api.company.com"]
      http:
        - match:
            - headers:
                canary:
                  exact: "true"
          route:
            - destination:
                host: "api"
                subset: "v2"
              weight: 100
        - route:
            - destination:
                host: "api"
                subset: "v1"
              weight: 90
            - destination:
                host: "api"
                subset: "v2"
              weight: 10

  destination_rules:
    api:
      host: "api"
      subsets:
        - name: "v1"
          labels:
            version: "v1.0"
        - name: "v2"
          labels:
            version: "v2.0"
```

## Traffic Monitoring

### `sysctl traffic monitor`

Real-time traffic monitoring and analysis.

```bash
# Monitor traffic distribution
sysctl traffic monitor api --env production

# Traffic analytics dashboard
sysctl traffic dashboard --service api --duration 1h

# Export traffic metrics
sysctl traffic metrics api --duration 24h --format json
```

#### Traffic Metrics

```bash
# Key traffic metrics
sysctl traffic metrics api --metrics requests,errors,latency,distribution

# Geographic traffic analysis
sysctl traffic analyze geographic --service api --duration 7d

# User journey analysis
sysctl traffic analyze journey --service api --trace-headers "X-Request-ID"
```

## A/B Testing

### `sysctl ab-test`

Traffic-based A/B testing capabilities.

```bash
# Create A/B test
sysctl ab-test create new-ui --variants A=50,B=50 --service frontend

# Monitor A/B test results
sysctl ab-test results new-ui --metrics conversion,engagement

# End A/B test and promote winner
sysctl ab-test conclude new-ui --winner B
```

#### A/B Test Configuration

```yaml
# ab-tests/new-ui.yaml
ab_test:
  name: "new-ui"
  service: "frontend"

  variants:
    A: # Control
      weight: 50
      config:
        ui_version: "v1.0"
        feature_flags:
          new_ui: false

    B: # Treatment
      weight: 50
      config:
        ui_version: "v2.0"
        feature_flags:
          new_ui: true

  targeting:
    header: "X-User-Segment"
    segments: ["premium", "standard"]

  duration: "14d"
  minimum_sample_size: 1000

  success_metrics:
    - name: "conversion_rate"
      threshold: 0.05 # 5% improvement
    - name: "bounce_rate"
      threshold: -0.02 # 2% reduction

  monitoring:
    statistical_significance: 0.95
    power: 0.80
```

## Advanced Features

### Traffic Replay

```bash
# Record production traffic
sysctl traffic record api --duration 1h --output traffic-dump.json

# Replay traffic against staging
sysctl traffic replay --input traffic-dump.json --target staging --rate 2x

# Replay with modifications
sysctl traffic replay --input traffic-dump.json --modify headers.yaml
```

### Chaos Engineering

```bash
# Introduce network latency
sysctl traffic chaos latency --service api --delay 100ms --percentage 10

# Simulate service failures
sysctl traffic chaos failure --service api --error-rate 5 --duration 5m

# Geographic traffic simulation
sysctl traffic chaos geographic --simulate-region-outage us-east-1
```

## Best Practices

### Deployment Safety

1. **Gradual Rollouts**: Always start with small traffic percentages
2. **Monitoring**: Implement comprehensive metrics and alerting
3. **Rollback Plans**: Have automatic and manual rollback procedures
4. **Health Checks**: Use robust health checking at all stages
5. **Testing**: Test traffic management in staging environments

### Traffic Management Strategy

```yaml
# Best practices configuration
best_practices:
  blue_green:
    - start_with_zero_traffic: true
    - monitor_before_promotion: true
    - keep_blue_environment_ready: true

  canary:
    - start_small: 5 # percent
    - gradual_increase: true
    - automatic_rollback: true
    - comprehensive_monitoring: true

  load_balancing:
    - health_checks_enabled: true
    - session_persistence: appropriate
    - circuit_breakers: true
    - timeout_configuration: optimized
```

### Troubleshooting

```bash
# Traffic flow debugging
sysctl traffic debug api --trace-requests --duration 5m

# Load balancer troubleshooting
sysctl lb debug nginx-api --check-upstream --check-health

# Circuit breaker analysis
sysctl circuit analyze api-database --failure-patterns --duration 1h

# Service mesh diagnostics
sysctl mesh debug api --check-rules --check-connectivity
```
