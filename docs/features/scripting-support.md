# Scripting Support

Embedded Python scripting capabilities for advanced automation, custom workflows, and extending
System Control CLI functionality.

## Overview

Scripting features:

- **Embedded Python**: Full Python interpreter integration
- **CLI API Access**: Programmatic access to all CLI commands
- **Script Library**: Reusable script collection and management
- **Event Hooks**: Script triggers for system events
- **Custom Functions**: Extend CLI with Python functions
- **Workflow Automation**: Complex multi-step automations

## Getting Started

### Basic Script Execution

```bash
# Execute Python script
sysctl script run deployment.py

# Execute inline Python
sysctl script exec "print('Hello from System Control')"

# Interactive Python shell with CLI context
sysctl script shell

# Execute script with arguments
sysctl script run migrate.py --arg version=2.1.0 --arg environment=production
```

### Script Structure

```python
#!/usr/bin/env python3
"""
Example System Control script
"""
from system_operations_manager import cli, config, logger

def main():
    """Main script entry point."""

    # Access CLI commands programmatically
    services = cli.run("service list --format json")

    # Use configuration
    env = config.get("environment")

    # Logging
    logger.info(f"Running script in {env} environment")

    # Execute deployment
    for service in services:
        if service['status'] == 'outdated':
            cli.run(f"deploy {service['name']} --env {env}")
            logger.info(f"Deployed {service['name']}")

if __name__ == "__main__":
    main()
```

## CLI API

### Python API Reference

```python
from system_operations_manager import cli, config, metrics, alerts

# CLI command execution
result = cli.run("deploy api --env production")
print(result.status)  # Success/Failed
print(result.output)  # Command output
print(result.duration)  # Execution time

# Async execution
async def deploy_services():
    tasks = [
        cli.run_async("deploy api"),
        cli.run_async("deploy worker"),
        cli.run_async("deploy scheduler")
    ]
    results = await asyncio.gather(*tasks)
    return results

# Configuration access
config.get("services.api.replicas")
config.set("services.api.replicas", 5)
config.save()

# Metrics collection
cpu_usage = metrics.get("cpu_usage", service="api")
memory_usage = metrics.query("avg(memory_usage_percent)")

# Alert management
alerts.create(
    name="high_cpu",
    condition="cpu_usage > 80",
    action="scale_up"
)
```

### Advanced API Usage

```python
from system_operations_manager import (
    Service, Deployment, Environment,
    Health, Backup, Monitor
)

class AutomationScript:
    def __init__(self):
        self.env = Environment("production")
        self.monitor = Monitor()

    def deploy_with_validation(self, service_name, image):
        """Deploy with pre and post validation."""

        service = Service(service_name, environment=self.env)

        # Pre-deployment checks
        if not service.health_check():
            raise Exception(f"{service_name} is not healthy")

        # Create backup
        backup = Backup.create(service_name)

        try:
            # Deploy
            deployment = Deployment(
                service=service,
                image=image,
                strategy="blue-green"
            )
            deployment.execute()

            # Wait for deployment
            deployment.wait_for_completion(timeout=600)

            # Post-deployment validation
            if not service.health_check():
                deployment.rollback()
                raise Exception("Post-deployment health check failed")

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            backup.restore()
            raise

        return deployment.status

# Usage
script = AutomationScript()
script.deploy_with_validation("api", "api:v2.1.0")
```

## Script Library

### Managing Scripts

```bash
# List available scripts
sysctl script list

# Install script to library
sysctl script install monitoring.py --name daily-monitor

# Run library script
sysctl script run-lib daily-monitor

# Update script
sysctl script update daily-monitor --file monitoring-v2.py

# Share script
sysctl script share daily-monitor --team platform
```

### Script Library Structure

```text
~/.config/system-control/scripts/
├── library/
│   ├── deployment/
│   │   ├── blue_green_deploy.py
│   │   ├── canary_deploy.py
│   │   └── rollback_manager.py
│   ├── monitoring/
│   │   ├── health_checker.py
│   │   ├── metric_collector.py
│   │   └── alert_manager.py
│   └── maintenance/
│       ├── backup_rotation.py
│       ├── log_cleanup.py
│       └── certificate_renewal.py
├── templates/
│   ├── basic_deployment.py
│   ├── monitoring_setup.py
│   └── disaster_recovery.py
└── user/
    └── custom_scripts.py
```

### Script Templates

```python
# templates/deployment_template.py
"""
Deployment script template
Usage: sysctl script run deployment.py --service SERVICE --version VERSION
"""
import argparse
from system_operations_manager import cli, logger, config

def parse_args():
    parser = argparse.ArgumentParser(description='Deploy service')
    parser.add_argument('--service', required=True, help='Service name')
    parser.add_argument('--version', required=True, help='Version to deploy')
    parser.add_argument('--environment', default='staging', help='Target environment')
    parser.add_argument('--strategy', default='rolling', help='Deployment strategy')
    return parser.parse_args()

def pre_deployment_checks(service, environment):
    """Run pre-deployment validations."""
    logger.info("Running pre-deployment checks...")

    # Check service health
    health = cli.run(f"health {service} --env {environment}")
    if not health.success:
        raise Exception(f"Service {service} is not healthy")

    # Check dependencies
    deps = cli.run(f"dependencies {service} --check")
    if not deps.success:
        raise Exception("Dependency check failed")

    # Verify configuration
    config_valid = cli.run(f"config validate {service}")
    if not config_valid.success:
        raise Exception("Configuration validation failed")

    logger.info("Pre-deployment checks passed")

def deploy(service, version, environment, strategy):
    """Execute deployment."""
    logger.info(f"Deploying {service}:{version} to {environment}")

    cmd = f"deploy {service} --image {service}:{version} --env {environment} --strategy {strategy}"
    result = cli.run(cmd)

    if not result.success:
        raise Exception(f"Deployment failed: {result.error}")

    return result

def post_deployment_validation(service, environment):
    """Validate deployment success."""
    logger.info("Running post-deployment validation...")

    # Wait for service to be ready
    ready = cli.run(f"wait {service} --env {environment} --timeout 300")
    if not ready.success:
        raise Exception("Service did not become ready")

    # Run smoke tests
    tests = cli.run(f"test smoke {service} --env {environment}")
    if not tests.success:
        logger.warning("Smoke tests failed")

    logger.info("Post-deployment validation complete")

def main():
    args = parse_args()

    try:
        # Pre-deployment
        pre_deployment_checks(args.service, args.environment)

        # Create backup
        backup = cli.run(f"backup create {args.service}")
        logger.info(f"Created backup: {backup.output}")

        # Deploy
        deployment = deploy(
            args.service,
            args.version,
            args.environment,
            args.strategy
        )

        # Post-deployment
        post_deployment_validation(args.service, args.environment)

        logger.info(f"Deployment successful: {deployment.output}")

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        logger.info("Rolling back...")
        cli.run(f"rollback {args.service} --env {args.environment}")
        raise

if __name__ == "__main__":
    main()
```

## Event Hooks

### Hook Configuration

```yaml
# hooks/event-hooks.yaml
event_hooks:
  pre_deployment:
    - name: "backup_database"
      script: "scripts/backup_db.py"
      timeout: 300

    - name: "notify_team"
      script: "scripts/send_notification.py"
      async: true

  post_deployment:
    - name: "run_tests"
      script: "scripts/integration_tests.py"
      continue_on_failure: true

    - name: "update_documentation"
      script: "scripts/update_docs.py"

  on_failure:
    - name: "create_incident"
      script: "scripts/create_incident.py"

    - name: "rollback"
      script: "scripts/auto_rollback.py"

  on_alert:
    - name: "auto_scale"
      script: "scripts/auto_scale.py"
      conditions:
        - "alert.severity == 'critical'"
        - "alert.type == 'resource'"
```

### Hook Script Example

```python
# hooks/pre_deployment.py
"""
Pre-deployment hook script
"""
from system_operations_manager import cli, logger, context

def main():
    # Get deployment context
    ctx = context.get_current()
    service = ctx.service
    environment = ctx.environment
    version = ctx.version

    logger.info(f"Pre-deployment hook for {service}:{version}")

    # Validate deployment window
    if not is_deployment_window_open():
        logger.error("Outside deployment window")
        return False

    # Check approval status
    if environment == "production":
        approval = check_approval_status(service, version)
        if not approval:
            logger.error("Deployment not approved")
            return False

    # Create pre-deployment snapshot
    snapshot = cli.run(f"snapshot create --name pre-deploy-{service}-{version}")
    logger.info(f"Created snapshot: {snapshot.output}")

    return True

def is_deployment_window_open():
    """Check if current time is within deployment window."""
    from datetime import datetime
    now = datetime.now()

    # No deployments on weekends
    if now.weekday() in [5, 6]:
        return False

    # Only deploy between 9 AM and 5 PM
    if now.hour < 9 or now.hour >= 17:
        return False

    return True

def check_approval_status(service, version):
    """Check if deployment is approved."""
    result = cli.run(f"approval check --service {service} --version {version}")
    return result.success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
```

## Custom Functions

### Extending CLI with Python

```python
# extensions/custom_commands.py
"""
Custom CLI command extensions
"""
from system_operations_manager import cli, register_command
import click

@register_command()
@click.command()
@click.option('--threshold', default=80, help='CPU threshold')
def auto_scale_check(threshold):
    """Check and auto-scale services based on CPU usage."""

    services = cli.run("service list --format json").data

    for service in services:
        cpu_usage = get_cpu_usage(service['name'])

        if cpu_usage > threshold:
            current_replicas = service['replicas']
            new_replicas = min(current_replicas * 2, 20)

            click.echo(f"Scaling {service['name']} from {current_replicas} to {new_replicas}")
            cli.run(f"scale {service['name']} --replicas {new_replicas}")

        elif cpu_usage < threshold / 2:
            current_replicas = service['replicas']
            new_replicas = max(current_replicas // 2, 1)

            if new_replicas < current_replicas:
                click.echo(f"Scaling down {service['name']} to {new_replicas}")
                cli.run(f"scale {service['name']} --replicas {new_replicas}")

def get_cpu_usage(service_name):
    """Get current CPU usage for service."""
    result = cli.run(f"metrics {service_name} --metric cpu --format value")
    return float(result.output)

# Register the command
if __name__ == "__main__":
    auto_scale_check()
```

### Plugin Development

```python
# plugins/monitoring_plugin.py
"""
Custom monitoring plugin
"""
from system_operations_manager.plugin import Plugin, hook
import time

class MonitoringPlugin(Plugin):
    """Advanced monitoring capabilities."""

    def __init__(self):
        super().__init__("monitoring-advanced")
        self.metrics_buffer = []

    @hook("post_deployment")
    def monitor_deployment(self, context):
        """Monitor service after deployment."""
        service = context.service
        duration = 300  # 5 minutes

        self.logger.info(f"Monitoring {service} for {duration} seconds")

        start_time = time.time()
        while time.time() - start_time < duration:
            metrics = self.collect_metrics(service)
            self.analyze_metrics(metrics)
            time.sleep(10)

    def collect_metrics(self, service):
        """Collect service metrics."""
        return {
            'cpu': self.cli.run(f"metrics {service} --metric cpu").data,
            'memory': self.cli.run(f"metrics {service} --metric memory").data,
            'requests': self.cli.run(f"metrics {service} --metric requests").data,
            'errors': self.cli.run(f"metrics {service} --metric errors").data,
        }

    def analyze_metrics(self, metrics):
        """Analyze metrics for anomalies."""
        if metrics['cpu'] > 80:
            self.alert("High CPU usage detected")

        if metrics['errors'] > 10:
            self.alert("High error rate detected")

    def alert(self, message):
        """Send alert."""
        self.cli.run(f"alert send --message '{message}' --channel slack")
```

## Workflow Automation

### Complex Workflow Example

```python
# workflows/disaster_recovery.py
"""
Disaster recovery automation workflow
"""
import asyncio
from datetime import datetime
from system_operations_manager import cli, logger, metrics

class DisasterRecoveryWorkflow:
    def __init__(self, primary_region, backup_region):
        self.primary_region = primary_region
        self.backup_region = backup_region
        self.start_time = datetime.now()

    async def execute(self):
        """Execute disaster recovery workflow."""
        logger.info("Starting disaster recovery workflow")

        try:
            # Phase 1: Assessment
            await self.assess_damage()

            # Phase 2: Backup activation
            await self.activate_backup_region()

            # Phase 3: Data recovery
            await self.recover_data()

            # Phase 4: Traffic switching
            await self.switch_traffic()

            # Phase 5: Validation
            await self.validate_recovery()

            logger.info("Disaster recovery completed successfully")
            return True

        except Exception as e:
            logger.error(f"Disaster recovery failed: {e}")
            await self.emergency_rollback()
            return False

    async def assess_damage(self):
        """Assess the extent of the disaster."""
        logger.info("Assessing damage...")

        # Check primary region status
        primary_health = await cli.run_async(
            f"health --region {self.primary_region} --comprehensive"
        )

        self.damage_report = {
            'services_affected': self.get_affected_services(primary_health),
            'data_loss_potential': self.assess_data_loss(),
            'estimated_recovery_time': self.estimate_recovery_time()
        }

        logger.info(f"Damage assessment: {self.damage_report}")

    async def activate_backup_region(self):
        """Activate backup region resources."""
        logger.info(f"Activating backup region: {self.backup_region}")

        tasks = [
            self.scale_up_backup_resources(),
            self.verify_backup_data(),
            self.prepare_load_balancers()
        ]

        await asyncio.gather(*tasks)

    async def recover_data(self):
        """Recover data from backups."""
        logger.info("Starting data recovery...")

        # Get latest backup
        backup = await cli.run_async(
            f"backup latest --region {self.primary_region}"
        )

        # Restore to backup region
        restore = await cli.run_async(
            f"backup restore {backup.data['id']} --region {self.backup_region}"
        )

        if not restore.success:
            raise Exception("Data recovery failed")

    async def switch_traffic(self):
        """Switch traffic to backup region."""
        logger.info("Switching traffic to backup region...")

        # Update DNS
        await cli.run_async(
            f"dns update --primary {self.backup_region}"
        )

        # Update load balancers
        await cli.run_async(
            f"lb switch --to {self.backup_region} --gradual"
        )

        # Monitor traffic switch
        await self.monitor_traffic_switch()

    async def validate_recovery(self):
        """Validate recovery success."""
        logger.info("Validating recovery...")

        validations = [
            self.validate_services(),
            self.validate_data_integrity(),
            self.validate_performance()
        ]

        results = await asyncio.gather(*validations)

        if not all(results):
            raise Exception("Recovery validation failed")

        logger.info("Recovery validation successful")

    async def emergency_rollback(self):
        """Emergency rollback procedure."""
        logger.error("Executing emergency rollback")
        # Implementation here

# Execute workflow
async def main():
    workflow = DisasterRecoveryWorkflow(
        primary_region="us-east-1",
        backup_region="us-west-2"
    )

    success = await workflow.execute()

    # Generate report
    report = {
        'success': success,
        'duration': (datetime.now() - workflow.start_time).total_seconds(),
        'damage_report': workflow.damage_report
    }

    cli.run(f"report generate disaster-recovery --data '{report}'")

if __name__ == "__main__":
    asyncio.run(main())
```

## Script Configuration

### Script Settings

```yaml
# config/scripting.yaml
scripting:
  enabled: true

  # Python environment
  python:
    version: "3.8+"
    virtual_env: "~/.config/system-control/venv"

  # Script paths
  paths:
    user_scripts: "~/.config/system-control/scripts"
    system_scripts: "/usr/share/system-control/scripts"

  # Execution settings
  execution:
    timeout: 3600 # 1 hour default
    max_memory: "1GB"
    sandbox: false # Enable for restricted execution

  # Import settings
  imports:
    allowed_modules:
      - "system_operations_manager"
      - "requests"
      - "pyyaml"
      - "jinja2"

    blocked_modules:
      - "os.system"
      - "subprocess.call"

  # Logging
  logging:
    script_output: true
    execution_trace: false
    error_details: true
```

## Best Practices

### Script Development

1. **Error Handling**: Always include proper error handling
2. **Logging**: Use structured logging for debugging
3. **Idempotency**: Make scripts safe to run multiple times
4. **Testing**: Include unit tests for complex scripts
5. **Documentation**: Document script purpose and usage

### Security Considerations

```python
# Security best practices
from system_operations_manager import cli, secrets

# Don't hardcode secrets
# Bad:
password = "hardcoded_password"

# Good:
password = secrets.get("database_password")

# Validate input
def deploy_service(service_name):
    # Validate service name
    if not service_name.isalnum():
        raise ValueError("Invalid service name")

    # Use parameterized commands
    cli.run("deploy", service=service_name)  # Safe
    # Not: cli.run(f"deploy {service_name}")  # Vulnerable to injection

# Limit resource usage
import resource
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))  # 60 second CPU limit
resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024, 1024*1024*1024))  # 1GB memory limit
```

## Troubleshooting

### Debug Scripts

```bash
# Run script in debug mode
sysctl script run deployment.py --debug

# Trace script execution
sysctl script trace deployment.py

# Profile script performance
sysctl script profile deployment.py --output profile.txt

# Validate script syntax
sysctl script validate deployment.py
```

### Common Issues

```python
# Import errors
try:
    from system_operations_manager import cli
except ImportError:
    print("Run script with: sysctl script run <script.py>")
    sys.exit(1)

# Context issues
from system_operations_manager import context

# Check if running in System Control context
if not context.is_active():
    print("This script must be run via System Control CLI")
    sys.exit(1)

# Permission issues
from system_operations_manager import permissions

if not permissions.can_deploy("production"):
    logger.error("Insufficient permissions for production deployment")
    sys.exit(1)
```
