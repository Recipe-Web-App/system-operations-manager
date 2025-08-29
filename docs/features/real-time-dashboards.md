# Real-Time Dashboards

Beautiful, interactive terminal-based dashboards for real-time monitoring and system
visualization using Rich and Textual frameworks.

## Overview

Dashboard features:

- **Live Updates**: Real-time metrics and status updates
- **Interactive UI**: Mouse and keyboard navigation
- **Customizable Layouts**: Flexible panel arrangements
- **Multi-View Support**: Switch between different dashboard views
- **Rich Visualizations**: Charts, graphs, tables, and gauges
- **Alert Integration**: Visual alerts and notifications

## Quick Start

### Launching Dashboards

```bash
# Launch default system dashboard
sysctl dashboard

# Service-specific dashboard
sysctl dashboard --service api

# Environment dashboard
sysctl dashboard --env production

# Custom dashboard
sysctl dashboard --config dashboards/custom.yaml

# Multi-service dashboard
sysctl dashboard --services api,worker,database
```

## Built-in Dashboards

### System Overview Dashboard

```bash
sysctl dashboard system

# Display:
```

```text
┌─────────────────────── System Control Dashboard ───────────────────────┐
│ Environment: Production    Updated: 10:30:15    CPU: 45%    MEM: 62%   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─── Service Status ───┐  ┌─── Resource Usage ───────────────────┐    │
│  │ ● api         [OK]   │  │ CPU Usage         ▇▇▇▇▇▇▇░░░░░  45%  │    │
│  │ ● worker      [OK]   │  │ Memory Usage      ▇▇▇▇▇▇▇▇▇▇░░  62%  │    │
│  │ ● database    [OK]   │  │ Disk Usage        ▇▇▇▇░░░░░░░░  34%  │    │
│  │ ○ scheduler   [WARN] │  │ Network I/O       ▇▇▇░░░░░░░░░  28%  │    │
│  │ ● redis       [OK]   │  └──────────────────────────────────────┘    │
│  └──────────────────────┘                                              │
│                                                                        │
│  ┌─── Request Metrics (last 5 min) ─────────────────────────────────┐  │
│  │      1000 │     ╭──╮                                             │  │
│  │       800 │    ╱    ╲                                            │  │
│  │       600 │   ╱      ╲___╱╲                                      │  │
│  │  req/s 400 │__╱            ╲____╱╲___                            │  │
│  │       200 │                        ╲                             │  │
│  │         0 └──────────────────────────────────────────────────    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─── Recent Events ────────────────────────────────────────────────┐  │
│  │ 10:30:00  ✓ Deployment completed: api v2.1.0                     │  │
│  │ 10:28:45  ⚠ High memory usage detected on worker-2               │  │
│  │ 10:25:30  ✓ Backup completed successfully                        │  │
│  │ 10:20:15  ℹ Configuration updated: api-config                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│ [Q]uit [R]efresh [S]ervices [M]etrics [L]ogs [H]elp                    │
└────────────────────────────────────────────────────────────────────────┘
```

### Service Health Dashboard

```bash
sysctl dashboard health --service api

# Display:
```

```text
┌────────────────── Service Health: API ──────────────────┐
│                                                         │
│  Instance Health Matrix                                 │
│  ┌────────────┬──────┬──────┬──────┬──────┬──────────┐  │
│  │ Instance   │ CPU  │ Mem  │ Disk │ Net  │ Status   │  │
│  ├────────────┼──────┼──────┼──────┼──────┼──────────┤  │
│  │ api-pod-1  │  ✅  │  ✅  │  ✅  │  ✅  │ Healthy  │  │
│  │ api-pod-2  │  ✅  │  ⚠️  │  ✅  │  ✅  │ Warning  │  │
│  │ api-pod-3  │  ✅  │  ✅  │  ✅  │  ✅  │ Healthy  │  │
│  └────────────┴──────┴──────┴──────┴──────┴──────────┘  │
│                                                         │
│  Health Check Results                                   │
│  ┌─────────────────────────┬────────────┬────────────┐  │
│  │ Check Name              │ Status     │ Duration   │  │
│  ├─────────────────────────┼────────────┼────────────┤  │
│  │ HTTP /health            │ ✅ Passing │ 45ms       │  │
│  │ Database Connection     │ ✅ Passing │ 12ms       │  │
│  │ Redis Connection        │ ✅ Passing │ 3ms        │  │
│  │ Disk Space             │ ✅ Passing │ 1ms         │  │
│  │ Memory Usage           │ ⚠️ Warning │ 1ms         │  │
│  └─────────────────────────┴────────────┴────────────┘  │
│                                                         │
│  Response Time Distribution (ms)                        │
│  0-50    ████████████████████████████ 78%               │
│  50-100  ████████ 15%                                   │
│  100-200 ███ 5%                                         │
│  200+    █ 2%                                           │
│                                                         │
│  Error Rate: 0.02%  Uptime: 99.98%  Version: v2.1.0     │
└─────────────────────────────────────────────────────────┘
```

### Performance Dashboard

```bash
sysctl dashboard performance

# Display:
```

```text
┌─────────────────── Performance Dashboard ───────────────────┐
│                                                             │
│  Request Rate (req/s)              Response Time (ms)       │
│  2000│    ╱╲                       200│      ___            │
│  1500│   ╱  ╲                      150│   __╱   ╲___        │
│  1000│  ╱    ╲___                  100│__╱          ╲___    │
│   500│_╱         ╲___               50│                     │
│     0└────────────────               0└────────────────     │
│                                                             │
│  CPU Usage by Service              Memory Usage by Service  │
│  api     ▇▇▇▇▇▇▇▇░░ 75%          api     ▇▇▇▇▇▇░░░░ 60%     │
│  worker  ▇▇▇▇▇░░░░░ 45%          worker  ▇▇▇▇▇▇▇░░░ 65%     │
│  db      ▇▇▇░░░░░░░ 30%          db      ▇▇▇▇▇▇▇▇▇░ 85%     │
│  redis   ▇▇░░░░░░░░ 20%          redis   ▇▇▇░░░░░░░ 25%     │
│                                                             │
│  Top Endpoints by Latency          Error Distribution       │
│  ┌──────────────────┬──────┐      ┌──────────┬─────────┐    │
│  │ /api/users       │ 234ms│      │ 5xx      │ 0.5%    │    │
│  │ /api/orders     │ 189ms │      │ 4xx      │ 2.1%    │    │
│  │ /api/products   │ 156ms │      │ Timeout  │ 0.1%    │    │
│  │ /api/search     │ 145ms │      │ Network  │ 0.2%    │    │
│  └──────────────────┴──────┘      └──────────┴─────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Custom Dashboards

### Dashboard Configuration

```yaml
# dashboards/custom.yaml
dashboard:
  name: "Custom Monitoring Dashboard"
  refresh_rate: 5 # seconds

  layout:
    type: "grid"
    rows: 3
    columns: 2

  panels:
    - id: "service_status"
      type: "table"
      position: [0, 0]
      size: [1, 1]
      title: "Service Status"
      data_source: "services.status"
      columns: ["name", "status", "replicas", "health"]

    - id: "cpu_gauge"
      type: "gauge"
      position: [0, 1]
      size: [1, 1]
      title: "CPU Usage"
      data_source: "metrics.cpu"
      min: 0
      max: 100
      thresholds:
        - value: 70
          color: "yellow"
        - value: 90
          color: "red"

    - id: "request_graph"
      type: "line_chart"
      position: [1, 0]
      size: [1, 2]
      title: "Request Rate"
      data_source: "metrics.requests"
      x_axis: "time"
      y_axis: "requests_per_second"
      window: "5m"

    - id: "logs_stream"
      type: "log_viewer"
      position: [2, 0]
      size: [1, 2]
      title: "Recent Logs"
      data_source: "logs.recent"
      filters:
        level: ["error", "warning"]
      max_lines: 10
```

### Dashboard Components

```python
# Custom dashboard component example
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

class ServiceStatusPanel:
    def __init__(self, services):
        self.services = services

    def render(self):
        table = Table(title="Service Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Replicas")
        table.add_column("Health")

        for service in self.services:
            status_style = "green" if service.healthy else "red"
            table.add_row(
                service.name,
                f"[{status_style}]{service.status}[/]",
                f"{service.ready}/{service.desired}",
                "✅" if service.healthy else "❌"
            )

        return Panel(table, title="Services", border_style="blue")
```

## Interactive Features

### Keyboard Navigation

```text
Key Bindings:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
↑/↓         Navigate panels
←/→         Switch tabs
Tab         Next panel
Shift+Tab   Previous panel
Enter       Select/Expand
Space       Toggle selection
/           Search
f           Filter
r           Refresh
s           Sort
d           Details view
l           Logs view
m           Metrics view
h           Help
q           Quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Mouse Support

```python
# Mouse interaction configuration
mouse_config:
  enabled: true
  actions:
    click: "select"
    double_click: "expand"
    right_click: "context_menu"
    scroll: "navigate"

  hover:
    show_tooltip: true
    highlight: true
    delay_ms: 500
```

### Interactive Filtering

```bash
# In dashboard, press '/' to filter
/error         # Show only error-related items
/api           # Filter to API service
/cpu > 80      # Show high CPU usage
/status:failed # Show failed status only
```

## Dashboard Themes

### Built-in Themes

```yaml
# themes/dark.yaml
theme:
  name: "Dark"

  colors:
    background: "#1e1e1e"
    foreground: "#d4d4d4"
    border: "#3c3c3c"

    success: "#4ec9b0"
    warning: "#dcdcaa"
    error: "#f48771"
    info: "#569cd6"

    chart_colors:
      - "#569cd6"
      - "#4ec9b0"
      - "#dcdcaa"
      - "#c586c0"
      - "#9cdcfe"

  styles:
    title: "bold cyan"
    border: "dim white"
    label: "yellow"
    value: "green"
    unit: "dim white"
```

### Custom Theme

```bash
# Apply custom theme
sysctl dashboard --theme themes/custom.yaml

# Set default theme
sysctl config set dashboard.theme dark
```

## Data Sources

### Metrics Integration

```yaml
# data-sources/metrics.yaml
data_sources:
  prometheus:
    type: "prometheus"
    url: "http://prometheus:9090"
    queries:
      cpu_usage: "avg(rate(cpu_usage_seconds[5m])) * 100"
      memory_usage: "node_memory_usage_percent"
      request_rate: "sum(rate(http_requests_total[1m]))"
      error_rate: 'rate(http_requests_total{status=~"5.."}[5m])'

  elasticsearch:
    type: "elasticsearch"
    url: "http://elasticsearch:9200"
    queries:
      recent_logs: |
        {
          "query": {"match_all": {}},
          "size": 100,
          "sort": [{"@timestamp": "desc"}]
        }

  custom_api:
    type: "http"
    url: "http://api.company.com/metrics"
    refresh_interval: 5
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

### Real-time Updates

```python
# WebSocket data streaming
import asyncio
import websockets

async def stream_metrics(dashboard):
    uri = "ws://metrics.company.com/stream"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            dashboard.update_metrics(json.loads(data))
            await asyncio.sleep(0.1)
```

## Dashboard Layouts

### Grid Layout

```yaml
layout:
  type: "grid"
  rows: 4
  columns: 3
  gap: 1

  panels:
    - id: "header"
      position: [0, 0]
      span: [1, 3] # 1 row, 3 columns

    - id: "services"
      position: [1, 0]
      span: [2, 1]

    - id: "metrics"
      position: [1, 1]
      span: [2, 2]

    - id: "logs"
      position: [3, 0]
      span: [1, 3]
```

### Responsive Layout

```yaml
layout:
  type: "responsive"
  breakpoints:
    small:
      max_width: 80
      columns: 1
      stack_panels: true

    medium:
      max_width: 120
      columns: 2

    large:
      min_width: 120
      columns: 3
```

## Alert Integration

### Visual Alerts

```yaml
alerts:
  high_cpu:
    condition: "cpu_usage > 80"
    visual:
      flash_panel: true
      border_color: "red"
      show_badge: true
      badge_text: "HIGH CPU"

  service_down:
    condition: "service.status == 'down'"
    visual:
      highlight_row: true
      blink: true
      sound: "alert.wav"
```

### Alert Notifications

```bash
# Dashboard with alert overlay
┌─────────────────────────────────────────────────┐
│ ⚠️  ALERT: High CPU Usage on api-pod-2          │
│    CPU: 92% | Duration: 5m | Action Required    │
└─────────────────────────────────────────────────┘
```

## Export and Sharing

### Dashboard Export

```bash
# Export dashboard as image
sysctl dashboard export --format png --output dashboard.png

# Export as HTML
sysctl dashboard export --format html --output dashboard.html

# Export metrics data
sysctl dashboard export --format csv --data-only --output metrics.csv

# Generate PDF report
sysctl dashboard report --format pdf --period daily --output report.pdf
```

### Dashboard Sharing

```bash
# Share dashboard via URL
sysctl dashboard share --duration 1h
# Returns: https://dashboards.company.com/shared/abc123

# Embed dashboard
sysctl dashboard embed --generate-code
# Returns HTML embed code
```

## Performance Optimization

### Dashboard Performance

```yaml
performance:
  # Update strategies
  update_strategy: "incremental" # or "full"
  batch_updates: true
  update_buffer_ms: 100

  # Data optimization
  data_cache: true
  cache_ttl: 5
  compress_data: true

  # Rendering optimization
  virtualization: true # For large tables
  lazy_loading: true
  max_data_points: 1000

  # Resource limits
  max_memory_mb: 100
  max_cpu_percent: 25
```

### Efficient Queries

```yaml
# Optimize data queries
queries:
  optimized_metrics:
    query: "rate(metric[5m])"
    step: 15 # Reduce resolution
    timeout: 10
    cache: true

  aggregated_logs:
    query: "aggregate by service"
    limit: 100
    fields: ["timestamp", "level", "message"]
```

## Troubleshooting

### Common Issues

```bash
# Dashboard not updating
sysctl dashboard debug --check-connections --verbose

# Performance issues
sysctl dashboard profile --duration 60s

# Data source errors
sysctl dashboard test-datasource prometheus

# Layout problems
sysctl dashboard validate-config custom.yaml
```

### Debug Mode

```bash
# Run dashboard in debug mode
sysctl dashboard --debug

# Shows:
# - Update frequency
# - Data source latency
# - Rendering time
# - Memory usage
# - Error messages
```

## Best Practices

### Dashboard Design

1. **Clear Hierarchy**: Most important metrics at top
2. **Consistent Colors**: Use color meaningfully
3. **Appropriate Refresh**: Balance freshness with performance
4. **Mobile Friendly**: Consider terminal size limitations
5. **Actionable Data**: Show metrics that drive decisions

### Performance Tips

```yaml
best_practices:
  updates:
    - use_incremental_updates
    - batch_similar_queries
    - cache_static_data

  visualization:
    - limit_animation_fps
    - use_simple_charts
    - aggregate_dense_data

  user_experience:
    - provide_keyboard_shortcuts
    - include_help_text
    - allow_customization
```
