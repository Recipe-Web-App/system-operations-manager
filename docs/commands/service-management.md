# Service Management Commands

Service management commands provide comprehensive control over service lifecycle
operations including starting, stopping, scaling, and monitoring services
across different
environments.

## Overview

Service management features include:

- **Lifecycle Control**: Start, stop, restart, and scale services
- **Health Monitoring**: Real-time health checks and status monitoring
- **Resource Management**: CPU, memory, and storage scaling
- **Configuration Management**: Dynamic configuration updates
- **Log Management**: Centralized logging and log analysis
- **Performance Monitoring**: Metrics collection and analysis

## Core Service Commands

### `sysctl service`

Main service management command with multiple subcommands.

```bash
# List all services
sysctl service list

# Show service details
sysctl service show api

# Service status
sysctl service status api

# Service logs
sysctl service logs api
```

### `sysctl start`

Start stopped services or create new service instances.

```bash
# Start a service
sysctl start api

# Start multiple services
sysctl start api worker scheduler

# Start all services in environment
sysctl start --all --env production

# Start with custom configuration
sysctl start api --config custom-config.yaml
```

#### Start Options

- `--env, -e ENV`: Target environment
- `--config CONFIG`: Custom configuration file
- `--replicas REPLICAS`: Number of instances to start
- `--wait`: Wait for service to be ready
- `--timeout SECONDS`: Startup timeout (default: 300)
- `--force`: Force start even if dependencies aren't ready
- `--dry-run`: Preview start operation

#### Start Examples

```bash
# Start service with specific replica count
sysctl start api --replicas 3 --env production --wait

# Start service with custom timeout
sysctl start worker --timeout 600 --env production

# Force start without waiting for dependencies
sysctl start api --force --env development
```

### `sysctl stop`

Stop running services gracefully or forcefully.

```bash
# Stop a service
sysctl stop api

# Stop multiple services
sysctl stop api worker

# Stop all services
sysctl stop --all

# Graceful stop with timeout
sysctl stop api --timeout 60
```

#### Stop Options

- `--env, -e ENV`: Target environment
- `--timeout SECONDS`: Graceful shutdown timeout
- `--force`: Force kill after timeout
- `--drain`: Drain connections before stopping
- `--wait`: Wait for complete shutdown
- `--cascade`: Stop dependent services

#### Stop Examples

```bash
# Graceful stop with connection draining
sysctl stop api --drain --timeout 120 --env production

# Force stop after timeout
sysctl stop worker --timeout 30 --force --env development

# Stop service and its dependencies
sysctl stop api --cascade --env staging
```

### `sysctl restart`

Restart services with various strategies.

```bash
# Restart service
sysctl restart api

# Rolling restart
sysctl restart api --rolling

# Restart with new configuration
sysctl restart api --config updated-config.yaml
```

#### Restart Options

- `--env, -e ENV`: Target environment
- `--rolling`: Rolling restart (zero downtime)
- `--config CONFIG`: Apply new configuration
- `--timeout SECONDS`: Restart timeout
- `--wait`: Wait for restart completion
- `--health-check`: Verify health after restart

#### Restart Examples

```bash
# Rolling restart in production
sysctl restart api --rolling --env production --health-check

# Restart with configuration update
sysctl restart api --config api-v2.yaml --wait --env staging

# Quick restart for development
sysctl restart api --timeout 60 --env development
```

### `sysctl scale`

Scale services up or down based on demand.

```bash
# Scale to specific replica count
sysctl scale api --replicas 5

# Scale multiple services
sysctl scale api=5 worker=3 scheduler=1

# Auto-scale based on metrics
sysctl scale api --auto --min 2 --max 10
```

#### Scale Options

- `--replicas REPLICAS`: Target replica count
- `--auto`: Enable auto-scaling
- `--min MIN`: Minimum replicas for auto-scaling
- `--max MAX`: Maximum replicas for auto-scaling
- `--cpu-target PERCENT`: CPU target for auto-scaling
- `--memory-target PERCENT`: Memory target for auto-scaling
- `--wait`: Wait for scaling to complete

#### Scale Examples

```bash
# Scale up for high traffic
sysctl scale api --replicas 10 --env production --wait

# Enable auto-scaling
sysctl scale api --auto --min 2 --max 20 --cpu-target 70 --env production

# Scale down during maintenance
sysctl scale api worker scheduler --replicas 1 --env staging
```

## Health and Status Monitoring

### `sysctl health`

Check service health and availability.

```bash
# Check service health
sysctl health api

# Check all services
sysctl health --all

# Detailed health report
sysctl health api --detailed

# Continuous health monitoring
sysctl health api --watch --interval 30s
```

#### Health Check Types

```yaml
health_checks:
  api:
    startup:
      endpoint: "/startup"
      timeout: 5
      retries: 30
      interval: 10

    liveness:
      endpoint: "/health"
      timeout: 5
      retries: 3
      interval: 30

    readiness:
      endpoint: "/ready"
      timeout: 5
      retries: 3
      interval: 10

    custom:
      database_connection:
        type: "tcp"
        host: "database"
        port: 5432
        timeout: 3

      redis_connection:
        type: "redis"
        url: "redis://redis:6379"
        timeout: 3
```

#### Health Examples

```bash
# Health check with custom endpoint
sysctl health api --endpoint /health/deep --timeout 10

# Monitor health during deployment
sysctl health api --watch --interval 10s --duration 5m

# Export health status
sysctl health --all --format json > health-report.json
```

### `sysctl status`

Get comprehensive service status information.

```bash
# Service status
sysctl status api

# Detailed status with metrics
sysctl status api --detailed

# Status in different formats
sysctl status api --format json
sysctl status api --format yaml
sysctl status api --format table
```

#### Status Information

- Current state (running, stopped, failed)
- Resource utilization (CPU, memory, disk)
- Health check results
- Recent events and logs
- Performance metrics
- Configuration version

## Log Management

### `sysctl logs`

Access and analyze service logs.

```bash
# View recent logs
sysctl logs api

# Follow logs in real-time
sysctl logs api --follow

# Filter logs by level
sysctl logs api --level error

# Search logs
sysctl logs api --grep "database connection"
```

#### Logs Options

- `--follow, -f`: Follow logs in real-time
- `--tail LINES`: Number of lines to show (default: 100)
- `--since DURATION`: Show logs since duration (e.g., 1h, 30m)
- `--until TIME`: Show logs until specific time
- `--level LEVEL`: Filter by log level
- `--grep PATTERN`: Search for pattern in logs
- `--format FORMAT`: Output format (text, json)

#### Logs Examples

```bash
# View last 1000 lines
sysctl logs api --tail 1000

# View logs from last hour with errors only
sysctl logs api --since 1h --level error

# Search for specific patterns
sysctl logs api --grep "failed to connect" --since 24h

# Export logs for analysis
sysctl logs api --since 1d --format json > api-logs.json
```

### Log Aggregation

```yaml
logging:
  aggregation:
    enabled: true
    backends:
      - type: "elasticsearch"
        url: "https://elasticsearch.company.com:9200"
        index_pattern: "services-%Y.%m.%d"

      - type: "loki"
        url: "https://loki.company.com:3100"

    processing:
      - type: "json_parser"
        field: "message"

      - type: "timestamp_parser"
        field: "timestamp"
        format: "RFC3339"

      - type: "level_normalizer"
        field: "level"
```

## Performance Monitoring

### `sysctl metrics`

Collect and analyze service performance metrics.

```bash
# Current metrics
sysctl metrics api

# Metrics over time
sysctl metrics api --duration 1h --interval 5m

# Specific metrics
sysctl metrics api --metrics cpu,memory,requests

# Export metrics
sysctl metrics api --duration 24h --format prometheus > metrics.txt
```

#### Available Metrics

- **Resource Metrics**: CPU, memory, disk, network usage
- **Application Metrics**: Request count, response time, error rate
- **Health Metrics**: Health check success rate, uptime
- **Custom Metrics**: Application-specific metrics

### Performance Dashboard

```bash
# Launch performance dashboard
sysctl dashboard performance --service api

# Real-time monitoring
sysctl monitor api --metrics cpu,memory,requests

# Performance report
sysctl report performance api --duration 7d --format pdf
```

## Configuration Management

### `sysctl config`

Manage service configuration dynamically.

```bash
# Show current configuration
sysctl config show api

# Update configuration
sysctl config set api database.host=new-db-host

# Reload configuration without restart
sysctl config reload api

# Validate configuration
sysctl config validate api
```

#### Configuration Operations

```bash
# Environment-specific configuration
sysctl config show api --env production

# Bulk configuration update
sysctl config update api --file config-updates.yaml

# Configuration rollback
sysctl config rollback api --version previous

# Configuration diff
sysctl config diff api --between v1.0 v1.1
```

### Configuration Templates

```yaml
# config-template.yaml
api:
  database:
    host: "{{ .env.DATABASE_HOST }}"
    port: "{{ .env.DATABASE_PORT | default 5432 }}"
    name: "{{ .env.DATABASE_NAME }}"

  cache:
    redis_url: "{{ .env.REDIS_URL }}"
    ttl: "{{ .env.CACHE_TTL | default 3600 }}"

  server:
    port: 8080
    workers: "{{ .env.WORKERS | default 4 }}"

  monitoring:
    enabled: true
    metrics_port: 9090
```

## Service Dependencies

### Dependency Management

```yaml
# service-dependencies.yaml
services:
  api:
    depends_on:
      - database:
          condition: healthy
          timeout: 60
      - redis:
          condition: running
          timeout: 30

    start_order: 3

  worker:
    depends_on:
      - api:
          condition: ready
          timeout: 120
      - database:
          condition: healthy
          timeout: 60

    start_order: 4
```

### Dependency Operations

```bash
# Start services in dependency order
sysctl start --all --ordered

# Check dependency status
sysctl dependencies api

# Wait for dependencies
sysctl start worker --wait-for-deps --timeout 300

# Force start ignoring dependencies
sysctl start api --ignore-deps
```

## Batch Operations

### Service Groups

```yaml
# groups/microservices.yaml
groups:
  core:
    services: [database, redis, api]
    start_order: sequential

  workers:
    services: [worker, scheduler, notifier]
    start_order: parallel
    depends_on: [core]

  frontend:
    services: [web, cdn]
    depends_on: [core, workers]
```

```bash
# Operate on service groups
sysctl start --group core --env production
sysctl restart --group workers --rolling --env production
sysctl stop --group frontend --drain --env production
```

### Bulk Operations

```bash
# Pattern-based operations
sysctl start "*-worker" --env production
sysctl restart "api-*" --rolling --env staging

# Tag-based operations
sysctl start --tag backend --env production
sysctl scale --tag frontend --replicas 3 --env production

# Environment-wide operations
sysctl restart --all --env development --timeout 60
sysctl stop --all --env staging --graceful
```

## Troubleshooting

### Debug Commands

```bash
# Debug service issues
sysctl debug api --env production

# Service diagnostics
sysctl diagnose api --comprehensive

# Resource analysis
sysctl analyze resources api --duration 1h

# Performance profiling
sysctl profile api --duration 5m --output profile.json
```

### Common Issues

```bash
# Service won't start
sysctl debug api --check-deps --check-config --check-resources

# Service keeps crashing
sysctl logs api --level error --tail 1000
sysctl metrics api --metrics memory,cpu --duration 1h

# Performance issues
sysctl profile api --cpu --memory --duration 10m
sysctl analyze bottlenecks api --duration 30m

# Health check failures
sysctl health api --verbose --trace
sysctl test health-endpoint api --endpoint /health
```

### Recovery Operations

```bash
# Restart failed services
sysctl recover --failed --env production

# Reset service state
sysctl reset api --force --env development

# Service factory reset
sysctl factory-reset api --backup-config --env staging

# Emergency procedures
sysctl emergency stop-all --env production
sysctl emergency drain-traffic --service api --env production
```

## Best Practices

### Service Lifecycle

1. **Graceful Shutdown**: Always use proper shutdown procedures
2. **Health Checks**: Implement comprehensive health checks
3. **Resource Limits**: Set appropriate resource limits
4. **Dependency Management**: Properly configure service dependencies
5. **Monitoring**: Implement comprehensive monitoring and alerting

### Production Operations

```bash
# Safe production restart
sysctl restart api --rolling --env production --health-check --wait

# Production scaling
sysctl scale api --replicas 10 --env production --gradual --monitor

# Maintenance mode
sysctl maintenance enable api --env production --message "Scheduled maintenance"
sysctl restart api --env production
sysctl maintenance disable api --env production
```

### Automation Integration

```yaml
# Automated service management
automation:
  health_checks:
    interval: "30s"
    failure_threshold: 3
    actions:
      - restart_service
      - notify_oncall

  scaling:
    metrics:
      - cpu_usage > 80%
      - memory_usage > 85%
    actions:
      - scale_up: 2
      - max_replicas: 20

  log_rotation:
    max_size: "100MB"
    max_files: 10
    compress: true
```
