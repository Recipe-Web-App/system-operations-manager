# Interactive Mode (REPL)

The System Control CLI provides a powerful interactive REPL (Read-Eval-Print-Loop) interface
for exploration, experimentation, and advanced system management tasks.

## Overview

Interactive mode features:

- **REPL Interface**: IPython-based interactive shell with advanced features
- **Context Awareness**: Environment and service context persistence
- **Command History**: Persistent command history across sessions
- **Auto-completion**: Intelligent tab completion for commands and parameters
- **Real-time Information**: Live system status and metrics display
- **Scripting Support**: Execute Python code alongside CLI commands

## Starting Interactive Mode

### `sysctl interactive`

Launch the interactive REPL interface.

```bash
# Start interactive mode
sysctl interactive

# Start with specific environment context
sysctl interactive --env production

# Start with service focus
sysctl interactive --focus api

# Start with custom configuration
sysctl interactive --config interactive.yaml
```

#### Options

- `--env, -e ENV`: Set initial environment context
- `--focus SERVICE`: Focus on specific service
- `--config CONFIG`: Custom interactive configuration
- `--profile PROFILE`: Load specific profile
- `--no-banner`: Disable startup banner
- `--minimal`: Minimal interface mode

## Interactive Interface Features

### Command Execution

```python
# In interactive mode
>>> status api
Service: api
Status: Running (3/3 replicas)
Health: Healthy
Uptime: 2d 14h 32m

>>> deploy api --env staging
Deploying api to staging environment...
✓ Deployment successful

>>> logs api --tail 10
[2024-01-15 10:30:15] INFO Starting API server
[2024-01-15 10:30:16] INFO Connected to database
...
```

### Context Management

```python
# Set environment context
>>> env production
Environment context set to: production

# Set service context
>>> focus api
Service context set to: api

# Show current context
>>> context
Environment: production
Service: api
Profile: default

# Clear context
>>> context clear
Context cleared
```

### Real-time Monitoring

```python
# Start real-time dashboard
>>> dashboard
┌─── System Overview ───┐
│ Environment: production │
│ Services: 12 running    │
│ CPU: 45% Memory: 62%    │
└────────────────────────┘

# Watch service status
>>> watch status api --interval 5
# Updates every 5 seconds

# Live metrics
>>> metrics api --live
Requests/sec: 1,247
Avg Response: 123ms
Error Rate: 0.02%
```

### Auto-completion

```python
# Tab completion for commands
>>> dep[TAB]
deploy  dependencies

# Parameter completion
>>> deploy api --env [TAB]
development  staging  production

# Service name completion
>>> status [TAB]
api  worker  database  redis  scheduler

# File path completion
>>> backup create --config [TAB]
config/backup.yaml  templates/backup-template.yaml
```

## Advanced Features

### Python Code Execution

```python
# Execute Python alongside CLI commands
>>> services = !service list --format json
>>> import json
>>> data = json.loads(services)
>>> healthy_services = [s for s in data if s['status'] == 'healthy']
>>> print(f"Healthy services: {len(healthy_services)}")

# Use Python for complex operations
>>> for service in ['api', 'worker', 'scheduler']:
...     result = !status {service} --format json
...     service_data = json.loads(result)
...     if service_data['replicas']['ready'] < service_data['replicas']['desired']:
...         print(f"⚠️  {service} has insufficient replicas")
```

### Magic Commands

```python
# Interactive-specific magic commands
>>> %env
Current environment: production

>>> %services
api       ✓ Running  (3/3)
worker    ✓ Running  (2/2)
database  ✓ Running  (1/1)

>>> %history
1: status api
2: deploy worker --env staging
3: logs api --tail 50

>>> %save session-backup.py
Session saved to session-backup.py

>>> %load session-backup.py
Session loaded from session-backup.py
```

### Multi-line Commands

```python
# Multi-line command construction
>>> deploy api \
... --env production \
... --strategy blue-green \
... --health-check \
... --wait

# Multi-line Python code
>>> def check_all_services():
...     services = ['api', 'worker', 'database']
...     for service in services:
...         result = !health {service}
...         print(f"{service}: {result}")
...

>>> check_all_services()
```

## Interactive Configuration

### Configuration File

```yaml
# config/interactive.yaml
interactive:
  # Interface settings
  interface:
    banner: true
    colors: true
    auto_suggestions: true
    syntax_highlighting: true

  # Command history
  history:
    enabled: true
    file: "~/.config/system-control/history"
    max_entries: 10000
    save_on_exit: true

  # Auto-completion
  completion:
    enabled: true
    fuzzy_matching: true
    case_sensitive: false
    show_descriptions: true

  # Real-time features
  realtime:
    refresh_interval: 5 # seconds
    max_update_frequency: 1 # per second

  # Context settings
  context:
    persist_environment: true
    persist_service: true
    auto_switch_on_deploy: true

  # Display settings
  display:
    max_table_width: 120
    truncate_long_output: true
    pager_threshold: 50 # lines

  # Integration
  python:
    enabled: true
    imports:
      - "json"
      - "datetime"
      - "os"
    startup_script: "~/.config/system-control/startup.py"
```

### Startup Script

```python
# ~/.config/system-control/startup.py
"""
Interactive mode startup script
Automatically executed when starting interactive mode
"""

import json
import datetime
from collections import defaultdict

def quick_status():
    """Show quick system status"""
    result = !status --all --format json
    data = json.loads(result)

    healthy = sum(1 for s in data if s['health'] == 'healthy')
    total = len(data)

    print(f"System Status: {healthy}/{total} services healthy")

    if healthy < total:
        unhealthy = [s['name'] for s in data if s['health'] != 'healthy']
        print(f"Unhealthy services: {', '.join(unhealthy)}")

def deploy_history():
    """Show recent deployments"""
    result = !history deployment --limit 5 --format table
    print("Recent Deployments:")
    print(result)

# Custom shortcuts
def q():
    """Quit interactive mode"""
    exit()

def st(service=None):
    """Quick status check"""
    if service:
        !status {service}
    else:
        quick_status()

def dep(service, env="staging"):
    """Quick deployment"""
    !deploy {service} --env {env} --wait

print("🚀 System Control Interactive Mode")
print("Available shortcuts: q(), st(service), dep(service, env)")
print("Type 'help()' for more information")
```

## Session Management

### Session Persistence

```python
# Save current session
>>> %save_session production-debug-2024-01-15
Session saved: production-debug-2024-01-15.py

# List saved sessions
>>> %list_sessions
Available sessions:
- production-debug-2024-01-15.py
- staging-deployment.py
- weekly-maintenance.py

# Load session
>>> %load_session production-debug-2024-01-15
Session loaded: production-debug-2024-01-15.py

# Auto-save on exit
>>> %config auto_save_session=True
Auto-save enabled
```

### Collaborative Sessions

```python
# Share session with team
>>> %share_session --team devops --message "Production troubleshooting session"
Session shared: https://share.system-control.com/sessions/abc123

# Join shared session
>>> %join_session abc123
Joined shared session: Production troubleshooting
Participants: alice, bob, charlie

# Session comments
>>> %comment "Investigating high memory usage on api service"
Comment added to session log
```

## Advanced Workflows

### Monitoring Workflows

```python
# Create custom monitoring dashboard
>>> def monitor_critical_services():
...     services = ['api', 'database', 'auth']
...     while True:
...         clear_output(wait=True)
...         print(f"Critical Services Status - {datetime.now()}")
...         print("=" * 50)
...         for service in services:
...             result = !health {service} --format json
...             data = json.loads(result)
...             status = "🟢" if data['healthy'] else "🔴"
...             print(f"{status} {service}: {data['status']}")
...         time.sleep(10)

>>> monitor_critical_services()
```

### Deployment Workflows

```python
# Complex deployment workflow
>>> def safe_production_deploy(service, version):
...     print(f"🚀 Starting safe deployment of {service}:{version}")
...
...     # Pre-deployment checks
...     print("1. Running pre-deployment checks...")
...     !health {service} --env production
...
...     # Deploy to staging first
...     print("2. Deploying to staging...")
...     !deploy {service} --env staging --image {service}:{version} --wait
...
...     # Run tests
...     print("3. Running integration tests...")
...     !test integration --service {service} --env staging
...
...     # Deploy to production with canary
...     print("4. Starting canary deployment to production...")
...     !traffic canary deploy {service} --env production --image {service}:{version}
...
...     print("✅ Deployment workflow completed")

>>> safe_production_deploy("api", "v2.1.0")
```

### Maintenance Workflows

```python
# Maintenance automation
>>> def weekly_maintenance():
...     services = !service list --format json
...     data = json.loads(services)
...
...     print("🔧 Starting weekly maintenance...")
...
...     for service in data:
...         service_name = service['name']
...
...         # Check resource usage
...         metrics = !metrics {service_name} --duration 7d --format json
...         metric_data = json.loads(metrics)
...
...         if metric_data['cpu_avg'] > 80:
...             print(f"⚠️  {service_name} CPU usage high: {metric_data['cpu_avg']}%")
...
...         if metric_data['memory_avg'] > 85:
...             print(f"⚠️  {service_name} Memory usage high: {metric_data['memory_avg']}%")
...
...     # Run cleanup tasks
...     !cleanup logs --older-than 30d
...     !cleanup backups --keep-last 10
...
...     print("✅ Weekly maintenance completed")

>>> weekly_maintenance()
```

## Troubleshooting and Debugging

### Debug Mode

```python
# Enable debug mode
>>> %debug on
Debug mode enabled

# Show detailed command output
>>> deploy api --env staging --debug
[DEBUG] Loading configuration for staging environment
[DEBUG] Validating deployment parameters
[DEBUG] Connecting to Kubernetes cluster
...

# Interactive debugging
>>> %pdb
Automatic pdb calling has been turned ON

>>> # Any error will drop into debugger
```

### Performance Monitoring

```python
# Profile command execution
>>> %time status --all
CPU times: user 45.2 ms, sys: 12.1 ms, total: 57.3 ms
Wall time: 234 ms

# Memory usage monitoring
>>> %memit metrics api --duration 1h
peak memory: 89.2 MiB, increment: 12.4 MiB
```

## Best Practices

### Interactive Session Tips

1. **Use Context**: Set environment and service context early
2. **Save Sessions**: Save important troubleshooting sessions
3. **Create Shortcuts**: Define Python functions for common tasks
4. **Use History**: Leverage command history for repeated operations
5. **Monitor Resources**: Keep an eye on system resources during operations

### Efficient Workflows

```python
# Set up efficient environment
>>> env production
>>> focus api

# Create reusable functions
>>> def quick_deploy(env="staging"):
...     return !deploy api --env {env} --wait

>>> def check_errors():
...     return !logs api --level error --tail 50

# Use variables for repeated values
>>> image_tag = "v2.1.0"
>>> !deploy api --image api:{image_tag} --env staging
```

### Security Considerations

- Avoid hardcoding secrets in interactive sessions
- Use environment variables for sensitive data
- Clear sensitive history before sharing sessions
- Be cautious with Python code execution in production context
