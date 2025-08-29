# Grafana Integration

Comprehensive integration with Grafana for creating rich dashboards, visualizations, and monitoring
interfaces for your distributed system.

## Overview

Grafana integration features:

- **Dashboard Management**: Automated dashboard creation, updates, and versioning
- **Data Source Configuration**: Multiple data source support (Prometheus, InfluxDB, Elasticsearch)
- **Alert Integration**: Grafana-native alerting with notification channels
- **Templating**: Dynamic dashboards with variables and templating
- **Panel Management**: Automated panel configuration and optimization
- **Team Management**: User, team, and permission management

## Configuration

### Basic Grafana Configuration

```yaml
# integrations/grafana.yaml
grafana:
  server:
    url: "https://grafana.company.com"
    timeout: "30s"

  authentication:
    # API Key (recommended)
    api_key_env: "GRAFANA_API_KEY"

    # Basic auth (alternative)
    # username_env: "GRAFANA_USERNAME"
    # password_env: "GRAFANA_PASSWORD"

    # Service account token (Grafana 9+)
    # service_account_token_env: "GRAFANA_SA_TOKEN"

  organization:
    id: 1
    name: "Main Org"

  defaults:
    dashboard_folder: "System Control"
    tags: ["system-control", "automated"]
    timezone: "UTC"
    refresh_interval: "30s"

  features:
    unified_alerting: true
    dashboard_previews: true
    annotations: true
    variables: true
```

### Data Source Configuration

```yaml
# grafana/datasources.yaml
datasources:
  prometheus:
    name: "Prometheus"
    type: "prometheus"
    url: "http://prometheus.company.com:9090"
    access: "proxy"
    isDefault: true
    basicAuth: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: "POST"

  influxdb:
    name: "InfluxDB"
    type: "influxdb"
    url: "http://influxdb.company.com:8086"
    database: "metrics"
    user: "grafana"
    secureJsonData:
      password: "${INFLUXDB_PASSWORD}"

  elasticsearch:
    name: "Elasticsearch Logs"
    type: "elasticsearch"
    url: "https://elasticsearch.company.com:9200"
    database: "[logs-]YYYY.MM.DD"
    interval: "Daily"
    timeField: "@timestamp"
    jsonData:
      esVersion: 70
      includeFrozen: false
      logLevelField: "level"
      logMessageField: "message"
```

## Dashboard Management

### System Control CLI Integration

```bash
# List dashboards
sysctl grafana dashboards list

# Create dashboard from template
sysctl grafana dashboard create system-overview --template templates/system-dashboard.json

# Update existing dashboard
sysctl grafana dashboard update system-overview --file dashboards/updated-system.json

# Export dashboard
sysctl grafana dashboard export system-overview --output system-overview.json

# Import dashboard
sysctl grafana dashboard import --file external-dashboard.json --folder "Imported"

# Delete dashboard
sysctl grafana dashboard delete system-overview
```

### Dashboard Templates

```json
{
  "dashboard": {
    "id": null,
    "title": "System Overview",
    "description": "Comprehensive system monitoring dashboard",
    "tags": ["system-control", "overview"],
    "timezone": "UTC",
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "templating": {
      "list": [
        {
          "name": "environment",
          "type": "query",
          "query": "label_values(up, environment)",
          "refresh": 1,
          "includeAll": false,
          "multi": false
        },
        {
          "name": "service",
          "type": "query",
          "query": "label_values(up{environment=\"$environment\"}, job)",
          "refresh": 1,
          "includeAll": true,
          "multi": true
        }
      ]
    },
    "panels": [
      {
        "id": 1,
        "title": "System CPU Usage",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(instance:cpu_usage:ratio{environment=\"$environment\"}) * 100",
            "legendFormat": "CPU Usage %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 70 },
                { "color": "red", "value": 90 }
              ]
            }
          }
        },
        "gridPos": { "h": 8, "w": 6, "x": 0, "y": 0 }
      },
      {
        "id": 2,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{environment=\"$environment\", job=~\"$service\"}[5m])) by (job)",
            "legendFormat": "{{job}}"
          }
        ],
        "yAxes": [{ "label": "Requests/sec", "min": 0 }],
        "gridPos": { "h": 8, "w": 12, "x": 6, "y": 0 }
      }
    ]
  },
  "folderId": 0,
  "overwrite": false
}
```

### Advanced Dashboard Configuration

```yaml
# dashboards/advanced-config.yaml
dashboard_config:
  system_overview:
    title: "System Overview - {{environment}}"
    description: "Comprehensive system monitoring for {{environment}} environment"

    variables:
      - name: "environment"
        type: "query"
        query: "label_values(up, environment)"
        refresh: "on_time_range_change"

      - name: "service"
        type: "query"
        query: 'label_values(up{environment="$environment"}, job)'
        multi: true
        include_all: true

      - name: "time_range"
        type: "interval"
        values: ["1m", "5m", "15m", "30m", "1h"]

    panels:
      overview_stats:
        type: "stat"
        title: "System Health"
        queries:
          - name: "cpu_usage"
            expr: 'avg(instance:cpu_usage:ratio{environment="$environment"}) * 100'
            unit: "percent"
            thresholds: [70, 90]

          - name: "memory_usage"
            expr: 'avg(instance:memory_usage:ratio{environment="$environment"}) * 100'
            unit: "percent"
            thresholds: [80, 95]

          - name: "active_services"
            expr: 'count(up{environment="$environment"} == 1)'
            unit: "short"

      request_metrics:
        type: "timeseries"
        title: "Request Metrics"
        queries:
          - name: "request_rate"
            expr: 'sum(rate(http_requests_total{environment="$environment", job=~"$service"}[$time_range])) by (job)'
            legend: "{{job}} requests/sec"

          - name: "error_rate"
            expr: 'sum(rate(http_requests_total{environment="$environment", job=~"$service", status=~"5.."}[$time_range])) by (job)'
            legend: "{{job}} errors/sec"
            color: "red"
```

## Alert Management

### Grafana Alerting Rules

```yaml
# alerts/grafana-alerts.yaml
alert_rules:
  - uid: "high_cpu_usage"
    title: "High CPU Usage"
    condition: "A"
    data:
      - refId: "A"
        queryType: "prometheus"
        model:
          expr: "avg(instance:cpu_usage:ratio) * 100"
          interval: "1m"
          maxDataPoints: 43200
    intervalSeconds: 60
    noDataState: "NoData"
    execErrState: "Alerting"
    for: "5m"
    annotations:
      description: "CPU usage is above 80%"
      runbook_url: "https://runbooks.company.com/high-cpu"
      summary: "High CPU usage detected"
    labels:
      team: "infrastructure"
      severity: "warning"

  - uid: "service_down"
    title: "Service Down"
    condition: "A"
    data:
      - refId: "A"
        queryType: "prometheus"
        model:
          expr: 'up{job=~"api|worker|scheduler"}'
          interval: "30s"
    intervalSeconds: 30
    noDataState: "Alerting"
    execErrState: "Alerting"
    for: "1m"
    annotations:
      description: "Service {{$labels.job}} is down"
      summary: "Critical service outage"
    labels:
      team: "backend"
      severity: "critical"
```

### Notification Channels

```yaml
# alerts/notification-channels.yaml
notification_channels:
  slack:
    name: "Slack Alerts"
    type: "slack"
    settings:
      url: "${SLACK_WEBHOOK_URL}"
      channel: "#alerts"
      username: "Grafana"
      title: "Alert: {{range .Alerts}}{{.Annotations.summary}}{{end}}"
      text: |
        {{range .Alerts}}
        *Alert:* {{.Annotations.summary}}
        *Description:* {{.Annotations.description}}
        *Severity:* {{.Labels.severity}}
        *Team:* {{.Labels.team}}
        {{if .Annotations.runbook_url}}*Runbook:* {{.Annotations.runbook_url}}{{end}}
        {{end}}

  email:
    name: "Email Alerts"
    type: "email"
    settings:
      addresses: ["devops@company.com", "oncall@company.com"]
      subject: "Grafana Alert: {{range .Alerts}}{{.Annotations.summary}}{{end}}"

  pagerduty:
    name: "PagerDuty"
    type: "pagerduty"
    settings:
      integrationKey: "${PAGERDUTY_INTEGRATION_KEY}"
      severity: "{{.CommonLabels.severity}}"
      component: "{{.CommonLabels.service}}"
      group: "{{.CommonLabels.team}}"
```

### Alert Management Commands

```bash
# List alert rules
sysctl grafana alerts list

# Create alert rule
sysctl grafana alerts create --rule alerts/high-cpu.yaml

# Test alert rule
sysctl grafana alerts test high_cpu_usage

# Pause/unpause alerts
sysctl grafana alerts pause high_cpu_usage --duration 2h
sysctl grafana alerts unpause high_cpu_usage

# List notification channels
sysctl grafana notifications list

# Test notification channel
sysctl grafana notifications test slack --message "Test alert"
```

## Custom Panel Types

### Application Performance Panel

```json
{
  "type": "stat",
  "title": "Application Performance",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=\"$service\"}[5m]))",
      "legendFormat": "95th Percentile Latency"
    },
    {
      "expr": "rate(http_requests_total{job=\"$service\"}[5m])",
      "legendFormat": "Request Rate"
    },
    {
      "expr": "rate(http_requests_total{job=\"$service\",status=~\"5..\"}[5m]) / rate(http_requests_total{job=\"$service\"}[5m]) * 100",
      "legendFormat": "Error Rate %"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "mappings": [
        {
          "options": {
            "pattern": "95th Percentile Latency",
            "result": { "unit": "s", "decimals": 3 }
          }
        },
        {
          "options": {
            "pattern": "Request Rate",
            "result": { "unit": "reqps", "decimals": 1 }
          }
        },
        {
          "options": {
            "pattern": "Error Rate %",
            "result": { "unit": "percent", "decimals": 2 }
          }
        }
      ]
    }
  }
}
```

### Infrastructure Overview Panel

```json
{
  "type": "table",
  "title": "Infrastructure Overview",
  "targets": [
    {
      "expr": "up{job=~\"node-exporter|kubernetes-.*\"}",
      "format": "table",
      "instant": true
    }
  ],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": { "Time": true, "__name__": true },
        "renameByName": {
          "instance": "Instance",
          "job": "Job",
          "Value": "Status"
        }
      }
    },
    {
      "id": "fieldLookup",
      "options": {
        "lookupField": "Status",
        "outputField": "Health",
        "mapping": {
          "1": "Healthy",
          "0": "Down"
        }
      }
    }
  ],
  "fieldConfig": {
    "overrides": [
      {
        "matcher": { "id": "byName", "options": "Health" },
        "properties": [
          {
            "id": "custom.displayMode",
            "value": "color-background"
          },
          {
            "id": "mappings",
            "value": [
              { "options": { "Healthy": { "color": "green", "index": 0 } } },
              { "options": { "Down": { "color": "red", "index": 1 } } }
            ]
          }
        ]
      }
    ]
  }
}
```

## Dashboard Automation

### Automated Dashboard Generation

```python
# dashboard-generator/generate_dashboards.py
"""
Generate Grafana dashboards from service configurations
"""
import json
import yaml
from typing import Dict, List

def generate_service_dashboard(service_config: Dict) -> Dict:
    """Generate a service-specific dashboard"""

    dashboard = {
        "dashboard": {
            "title": f"{service_config['name']} - Service Dashboard",
            "description": f"Monitoring dashboard for {service_config['name']} service",
            "tags": ["service", service_config['name'], "auto-generated"],
            "templating": {
                "list": [
                    {
                        "name": "environment",
                        "type": "query",
                        "query": f"label_values(up{{job=\"{service_config['name']}\"}}, environment)"
                    }
                ]
            },
            "panels": []
        }
    }

    # Add standard panels
    panels = [
        create_health_panel(service_config),
        create_performance_panel(service_config),
        create_resource_panel(service_config),
        create_error_panel(service_config)
    ]

    for i, panel in enumerate(panels):
        panel["id"] = i + 1
        panel["gridPos"] = calculate_grid_position(i, len(panels))
        dashboard["dashboard"]["panels"].append(panel)

    return dashboard

def create_health_panel(service_config: Dict) -> Dict:
    """Create service health panel"""
    return {
        "title": f"{service_config['name']} Health",
        "type": "stat",
        "targets": [
            {
                "expr": f"up{{job=\"{service_config['name']}\", environment=\"$environment\"}}",
                "legendFormat": "Service Status"
            }
        ],
        "fieldConfig": {
            "defaults": {
                "mappings": [
                    {"options": {"0": {"text": "Down", "color": "red"}}},
                    {"options": {"1": {"text": "Up", "color": "green"}}}
                ]
            }
        }
    }

# Usage
service_configs = load_service_configs("services/")
for service_config in service_configs:
    dashboard = generate_service_dashboard(service_config)
    save_dashboard(dashboard, f"dashboards/{service_config['name']}.json")
```

### Dashboard Deployment Automation

```bash
# Deploy generated dashboards
sysctl grafana dashboard deploy-batch --directory dashboards/ --folder "Auto Generated"

# Update dashboards from templates
sysctl grafana dashboard update-from-template --template system-template.json --services api,worker,scheduler

# Sync dashboards with configuration
sysctl grafana dashboard sync --config services.yaml --update-existing

# Validate dashboard JSON
sysctl grafana dashboard validate --file dashboard.json --fix-issues
```

## Team and Permission Management

### Team Configuration

```yaml
# teams/team-config.yaml
teams:
  infrastructure:
    name: "Infrastructure Team"
    email: "infrastructure@company.com"
    members:
      - "alice@company.com"
      - "bob@company.com"
    permissions:
      - folder: "Infrastructure"
        permission: "Admin"
      - folder: "System Control"
        permission: "Edit"

  backend:
    name: "Backend Team"
    email: "backend@company.com"
    members:
      - "charlie@company.com"
      - "diana@company.com"
    permissions:
      - folder: "Applications"
        permission: "Admin"
      - folder: "System Control"
        permission: "View"

folders:
  - name: "Infrastructure"
    permissions:
      - team: "infrastructure"
        permission: "Admin"
      - team: "backend"
        permission: "View"

  - name: "Applications"
    permissions:
      - team: "backend"
        permission: "Admin"
      - team: "infrastructure"
        permission: "Edit"
```

### Team Management Commands

```bash
# Create teams
sysctl grafana team create --config teams/team-config.yaml

# Add team members
sysctl grafana team add-member infrastructure alice@company.com

# Set folder permissions
sysctl grafana folder create "Infrastructure" --team infrastructure:Admin

# List team permissions
sysctl grafana team permissions list infrastructure
```

## Advanced Features

### Dashboard Versioning

```bash
# Create dashboard version
sysctl grafana dashboard version create system-overview --message "Added new panels"

# List dashboard versions
sysctl grafana dashboard version list system-overview

# Restore dashboard version
sysctl grafana dashboard version restore system-overview --version 3

# Compare dashboard versions
sysctl grafana dashboard version diff system-overview --versions 2,3
```

### Dashboard Variables and Templating

```yaml
# templates/advanced-variables.yaml
variables:
  environment:
    type: "query"
    query: "label_values(environment)"
    refresh: "on_time_range_change"
    multi: false
    include_all: false

  service:
    type: "query"
    query: 'label_values(up{environment="$environment"}, job)'
    refresh: "on_variable_change"
    multi: true
    include_all: true

  instance:
    type: "query"
    query: 'label_values(up{environment="$environment", job=~"$service"}, instance)'
    refresh: "on_variable_change"
    multi: true
    include_all: true
    hide: "variable" # Hide if only one value

  percentile:
    type: "custom"
    options: ["50", "95", "99"]
    current: "95"

  time_range:
    type: "interval"
    options: ["1m", "5m", "15m", "30m", "1h", "6h", "24h"]
    auto: true
    auto_count: 10
    auto_min: "1m"
```

### Custom Panel Plugins

```javascript
// panels/custom-service-map.js
/**
 * Custom Grafana panel for service dependency mapping
 */
import { PanelPlugin } from "@grafana/data"
import { ServiceMapPanel } from "./ServiceMapPanel"
import { ServiceMapOptions } from "./types"

export const plugin =
  new PanelPlugin() <
  ServiceMapOptions >
  ServiceMapPanel.setPanelOptions(builder => {
    return builder
      .addTextInput({
        path: "serviceQuery",
        name: "Service Query",
        description: "Prometheus query to get service data",
        defaultValue: 'up{job=~".*"}',
      })
      .addTextInput({
        path: "dependencyQuery",
        name: "Dependency Query",
        description: "Query to get service dependencies",
        defaultValue: "service_dependency_info",
      })
      .addBooleanSwitch({
        path: "showMetrics",
        name: "Show Metrics",
        description: "Display service metrics on nodes",
        defaultValue: true,
      })
  })
```

## Performance Optimization

### Dashboard Performance

```bash
# Analyze dashboard performance
sysctl grafana dashboard analyze-performance system-overview --duration 24h

# Optimize dashboard queries
sysctl grafana dashboard optimize-queries system-overview --suggestions

# Cache dashboard data
sysctl grafana dashboard configure-caching system-overview --ttl 300

# Benchmark dashboard loading
sysctl grafana dashboard benchmark system-overview --iterations 10
```

### Query Optimization

```yaml
# query-optimization.yaml
optimization_rules:
  - name: "Use recording rules for expensive queries"
    pattern: "histogram_quantile\\(.*rate\\(.*\\[5m\\]\\).*\\)"
    suggestion: "Create recording rule for this percentile calculation"

  - name: "Limit time range for high-cardinality metrics"
    pattern: ".*\\{.*\\}\\[(?!.*[1-5]m).*\\]"
    suggestion: "Consider shorter time ranges for high-cardinality queries"

  - name: "Use rate() for counter metrics"
    pattern: "^(?!rate|increase).*_total$"
    suggestion: "Use rate() or increase() for counter metrics"
```

## Troubleshooting

### Common Issues

```bash
# Test Grafana connectivity
sysctl grafana health-check

# Debug data source connection
sysctl grafana datasource test prometheus

# Validate dashboard JSON
sysctl grafana dashboard validate system-overview.json

# Check API permissions
sysctl grafana permissions check --api-key ${GRAFANA_API_KEY}

# Debug query issues
sysctl grafana debug query "up" --datasource prometheus --time-range 1h
```

### Performance Issues

```bash
# Identify slow dashboards
sysctl grafana analyze slow-dashboards --threshold 5s --duration 24h

# Memory usage analysis
sysctl grafana analyze memory-usage --top 10

# Query performance breakdown
sysctl grafana analyze query-performance --dashboard system-overview

# Database performance
sysctl grafana analyze database-performance --slow-queries --duration 7d
```

## Best Practices

### Dashboard Design

1. **Clear Hierarchy**: Organize dashboards by team/service/environment
2. **Consistent Styling**: Use consistent colors, units, and formatting
3. **Performance**: Limit panels per dashboard, optimize queries
4. **Responsive Design**: Ensure dashboards work on different screen sizes
5. **Documentation**: Include descriptions and runbook links

### Example Best Practice Dashboard

```json
{
  "dashboard": {
    "title": "Production API Service",
    "description": "Primary monitoring dashboard for the API service in production",
    "tags": ["production", "api", "critical"],
    "refresh": "30s",
    "time": { "from": "now-1h", "to": "now" },

    "annotations": {
      "list": [
        {
          "name": "Deployments",
          "datasource": "Prometheus",
          "expr": "changes(deployment_timestamp{service=\"api\"}[1h])",
          "textFormat": "Deployment",
          "iconColor": "blue"
        }
      ]
    },

    "templating": {
      "list": [
        {
          "name": "instance",
          "type": "query",
          "query": "label_values(up{job=\"api\"}, instance)",
          "multi": true,
          "includeAll": true
        }
      ]
    }
  }
}
```
