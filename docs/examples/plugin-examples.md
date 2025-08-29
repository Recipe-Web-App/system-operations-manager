# Plugin Examples

Real-world examples demonstrating plugin development patterns, integration techniques, and best
practices for extending the system control framework.

## Simple Command Plugin

### Basic Service Management Plugin

```python
# plugins/service_manager/plugin.py
from system_control.plugin import CommandPlugin
from system_control.decorators import command, group, option, argument
from system_control.exceptions import PluginError
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import time

class ServiceManagerPlugin(CommandPlugin):
    """Advanced service management plugin with custom commands."""

    name = "service-manager"
    version = "1.0.0"
    description = "Advanced service management capabilities"
    author = "DevOps Team <devops@company.com>"

    def initialize(self):
        """Initialize plugin resources."""
        self.console = Console()
        self.config = self.get_config("service_manager", {})

        # Initialize service discovery client
        self.service_discovery = self.get_service("service_discovery")
        self.monitoring = self.get_service("monitoring")

        self.debug("Service Manager plugin initialized")

    @group("svc")
    def service_group(self):
        """Service management commands."""
        pass

    @service_group.command("list")
    @option("--env", help="Environment filter")
    @option("--status", help="Status filter (running, stopped, unhealthy)")
    @option("--format", default="table", help="Output format (table, json, yaml)")
    def list_services(self, env: str = None, status: str = None, format: str = "table"):
        """List services with detailed information."""

        try:
            # Get services from all environments or specific environment
            environments = [env] if env else self.get_all_environments()

            services_data = []

            for environment in environments:
                services = self.service_discovery.get_services(environment)

                for service in services:
                    service_info = {
                        'name': service.name,
                        'environment': environment,
                        'status': service.status,
                        'replicas': f"{service.ready_replicas}/{service.desired_replicas}",
                        'cpu_usage': self.get_service_metric(service.name, environment, 'cpu_usage'),
                        'memory_usage': self.get_service_metric(service.name, environment, 'memory_usage'),
                        'last_deployed': service.last_deployed.strftime('%Y-%m-%d %H:%M:%S') if service.last_deployed else 'Never'
                    }

                    # Apply status filter
                    if status and service_info['status'].lower() != status.lower():
                        continue

                    services_data.append(service_info)

            # Output in requested format
            if format == "table":
                self._display_services_table(services_data)
            elif format == "json":
                import json
                self.console.print(json.dumps(services_data, indent=2))
            elif format == "yaml":
                import yaml
                self.console.print(yaml.dump(services_data, default_flow_style=False))
            else:
                self.error(f"Unsupported format: {format}")

        except Exception as e:
            raise PluginError(f"Failed to list services: {e}")

    @service_group.command("health")
    @argument("service", help="Service name to check")
    @option("--env", help="Environment (default: current)")
    @option("--detailed", is_flag=True, help="Show detailed health information")
    def service_health(self, service: str, env: str = None, detailed: bool = False):
        """Check service health with detailed diagnostics."""

        environment = env or self.get_current_environment()

        with self.console.status(f"Checking health of {service} in {environment}..."):
            health_data = self._check_service_health(service, environment, detailed)

        # Display health status
        if health_data['overall_status'] == 'healthy':
            self.console.print(f"✅ {service} is [green]healthy[/green] in {environment}")
        elif health_data['overall_status'] == 'unhealthy':
            self.console.print(f"❌ {service} is [red]unhealthy[/red] in {environment}")
        else:
            self.console.print(f"⚠️ {service} is [yellow]degraded[/yellow] in {environment}")

        if detailed:
            self._display_health_details(health_data)

    @service_group.command("restart-rolling")
    @argument("service", help="Service to restart")
    @option("--env", help="Environment (default: current)")
    @option("--batch-size", type=int, default=1, help="Number of instances to restart at once")
    @option("--wait-time", type=int, default=30, help="Wait time between batches (seconds)")
    def rolling_restart(self, service: str, env: str = None, batch_size: int = 1, wait_time: int = 30):
        """Perform rolling restart of service instances."""

        environment = env or self.get_current_environment()

        try:
            # Get service instances
            instances = self.service_discovery.get_service_instances(service, environment)

            if not instances:
                self.warning(f"No instances found for service {service} in {environment}")
                return

            total_instances = len(instances)
            self.info(f"Starting rolling restart of {total_instances} instances")

            with Progress() as progress:
                restart_task = progress.add_task(
                    f"Rolling restart of {service}",
                    total=total_instances
                )

                # Process instances in batches
                for i in range(0, total_instances, batch_size):
                    batch = instances[i:i + batch_size]
                    batch_names = [inst.name for inst in batch]

                    self.info(f"Restarting batch: {', '.join(batch_names)}")

                    # Restart instances in current batch
                    for instance in batch:
                        self._restart_instance(instance, environment)
                        progress.update(restart_task, advance=1)

                    # Wait for batch to become healthy
                    if not self._wait_for_instances_healthy(batch, environment, timeout=120):
                        raise PluginError(f"Batch {batch_names} failed to become healthy")

                    # Wait before next batch (except for last batch)
                    if i + batch_size < total_instances:
                        time.sleep(wait_time)

            self.success(f"Rolling restart completed for {service}")

        except Exception as e:
            raise PluginError(f"Rolling restart failed: {e}")

    @service_group.command("scale-auto")
    @argument("service", help="Service to auto-scale")
    @option("--env", help="Environment (default: current)")
    @option("--min-replicas", type=int, help="Minimum replicas")
    @option("--max-replicas", type=int, help="Maximum replicas")
    @option("--target-cpu", type=int, default=70, help="Target CPU utilization %")
    @option("--target-memory", type=int, default=80, help="Target memory utilization %")
    def auto_scale_service(self, service: str, env: str = None, min_replicas: int = None,
                          max_replicas: int = None, target_cpu: int = 70, target_memory: int = 80):
        """Configure auto-scaling for a service."""

        environment = env or self.get_current_environment()

        # Get current service configuration
        current_config = self.service_discovery.get_service_config(service, environment)

        # Build auto-scaling configuration
        autoscaling_config = {
            'enabled': True,
            'min_replicas': min_replicas or current_config.get('min_replicas', 1),
            'max_replicas': max_replicas or current_config.get('max_replicas', 10),
            'metrics': [
                {
                    'type': 'cpu',
                    'target': target_cpu
                },
                {
                    'type': 'memory',
                    'target': target_memory
                }
            ],
            'behavior': {
                'scale_up': {
                    'stabilization_window': '60s',
                    'policies': [
                        {'type': 'percent', 'value': 100, 'period': '120s'},
                        {'type': 'pods', 'value': 2, 'period': '60s'}
                    ]
                },
                'scale_down': {
                    'stabilization_window': '300s',
                    'policies': [
                        {'type': 'percent', 'value': 50, 'period': '120s'}
                    ]
                }
            }
        }

        # Apply auto-scaling configuration
        self.service_discovery.configure_autoscaling(service, environment, autoscaling_config)

        self.success(f"Auto-scaling configured for {service} in {environment}")
        self.info(f"Min replicas: {autoscaling_config['min_replicas']}")
        self.info(f"Max replicas: {autoscaling_config['max_replicas']}")
        self.info(f"CPU target: {target_cpu}%")
        self.info(f"Memory target: {target_memory}%")

    # Helper methods
    def _display_services_table(self, services_data):
        """Display services in a formatted table."""
        table = Table(title="Services Overview")

        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Environment", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Replicas", justify="center")
        table.add_column("CPU", justify="right")
        table.add_column("Memory", justify="right")
        table.add_column("Last Deployed", style="dim")

        for service in services_data:
            status_style = "green" if service['status'] == 'running' else "red"

            table.add_row(
                service['name'],
                service['environment'],
                f"[{status_style}]{service['status']}[/{status_style}]",
                service['replicas'],
                f"{service['cpu_usage']}%",
                f"{service['memory_usage']}%",
                service['last_deployed']
            )

        self.console.print(table)

    def _check_service_health(self, service: str, environment: str, detailed: bool = False):
        """Check comprehensive service health."""
        health_data = {
            'service': service,
            'environment': environment,
            'overall_status': 'healthy',
            'checks': {}
        }

        # Basic health check
        health_data['checks']['basic'] = self.service_discovery.health_check(service, environment)

        if detailed:
            # Performance metrics check
            cpu_usage = self.get_service_metric(service, environment, 'cpu_usage')
            memory_usage = self.get_service_metric(service, environment, 'memory_usage')

            health_data['checks']['performance'] = {
                'status': 'healthy' if cpu_usage < 90 and memory_usage < 90 else 'degraded',
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            }

            # Dependency check
            dependencies = self.service_discovery.get_service_dependencies(service)
            health_data['checks']['dependencies'] = self._check_dependencies(dependencies, environment)

            # Network connectivity check
            health_data['checks']['network'] = self._check_network_connectivity(service, environment)

        # Determine overall status
        statuses = [check.get('status', 'unknown') for check in health_data['checks'].values()]

        if 'unhealthy' in statuses:
            health_data['overall_status'] = 'unhealthy'
        elif 'degraded' in statuses:
            health_data['overall_status'] = 'degraded'

        return health_data

    def _display_health_details(self, health_data):
        """Display detailed health information."""
        table = Table(title=f"Health Details - {health_data['service']}")

        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        for check_name, check_data in health_data['checks'].items():
            if isinstance(check_data, dict):
                status = check_data.get('status', 'unknown')
                details = ', '.join([f"{k}: {v}" for k, v in check_data.items() if k != 'status'])
            else:
                status = 'healthy' if check_data else 'unhealthy'
                details = str(check_data)

            status_style = "green" if status == 'healthy' else "yellow" if status == 'degraded' else "red"

            table.add_row(
                check_name.title(),
                f"[{status_style}]{status}[/{status_style}]",
                details
            )

        self.console.print(table)

    def get_service_metric(self, service: str, environment: str, metric: str):
        """Get service metric value."""
        try:
            return self.monitoring.get_metric(
                metric=f"{metric}{{service='{service}', environment='{environment}'}}",
                time_range='5m'
            ).average()
        except:
            return 0

    def get_all_environments(self):
        """Get list of all environments."""
        return self.get_config("environments", ["development", "staging", "production"])

    def get_current_environment(self):
        """Get current environment context."""
        return self.get_config("default_environment", "development")

    def cleanup(self):
        """Cleanup plugin resources."""
        self.debug("Service Manager plugin cleaned up")

# Plugin registration
plugin = ServiceManagerPlugin()
```

## Integration Plugin Example

### Slack Integration Plugin

```python
# plugins/slack_integration/plugin.py
from system_control.plugin import IntegrationPlugin, ConfigPlugin
from system_control.decorators import command, option, argument
from system_control.events import event_handler
from system_control.exceptions import PluginError, ConfigurationError
from marshmallow import fields, validate
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

class SlackIntegrationPlugin(IntegrationPlugin, ConfigPlugin):
    """Slack integration for notifications and interactive commands."""

    name = "slack"
    version = "2.0.0"
    description = "Slack integration for notifications and bot commands"
    author = "Platform Team <platform@company.com>"

    # Plugin dependencies
    requires = ["notifications", "monitoring"]

    def initialize(self):
        """Initialize Slack integration."""
        config = self.get_config("slack", {})

        # Validate required configuration
        self.webhook_url = config.get("webhook_url")
        self.bot_token = config.get("bot_token")
        self.signing_secret = config.get("signing_secret")

        if not self.webhook_url and not self.bot_token:
            raise ConfigurationError("Either webhook_url or bot_token must be configured")

        # Initialize Slack client
        self.slack_client = SlackClient(self.bot_token) if self.bot_token else None

        # Register as notification channel
        notification_service = self.get_service("notifications")
        notification_service.register_channel("slack", self.send_notification)

        # Set up event handlers
        self.setup_event_handlers()

        self.info("Slack integration initialized")

    def get_schema_extensions(self) -> Dict:
        """Return configuration schema extensions."""
        return {
            "slack": {
                "webhook_url": fields.Url(),
                "bot_token": fields.Str(),
                "signing_secret": fields.Str(),
                "default_channel": fields.Str(default="#alerts"),
                "notification_settings": {
                    "deployment_success": fields.Bool(default=True),
                    "deployment_failure": fields.Bool(default=True),
                    "health_alerts": fields.Bool(default=True),
                    "performance_alerts": fields.Bool(default=True)
                },
                "channel_mappings": fields.Dict(
                    keys=fields.Str(),
                    values=fields.Str(),
                    description="Map alert types to specific channels"
                )
            }
        }

    @command("slack-test")
    @option("--channel", help="Slack channel to test")
    @option("--message", default="Test message from System Control", help="Test message")
    def test_slack(self, channel: str = None, message: str = None):
        """Test Slack integration."""

        config = self.get_config("slack", {})
        target_channel = channel or config.get("default_channel", "#general")

        try:
            self.send_message(
                channel=target_channel,
                text=message,
                title="🧪 Slack Integration Test"
            )

            self.success(f"Test message sent to {target_channel}")

        except Exception as e:
            raise PluginError(f"Slack test failed: {e}")

    @command("slack-deploy-notify")
    @argument("service", help="Service name")
    @argument("environment", help="Environment")
    @argument("status", help="Deployment status (success/failure)")
    @option("--version", help="Deployed version")
    @option("--duration", help="Deployment duration")
    @option("--details", help="Additional details")
    def deployment_notification(self, service: str, environment: str, status: str,
                              version: str = None, duration: str = None, details: str = None):
        """Send deployment notification to Slack."""

        if status.lower() not in ['success', 'failure']:
            raise PluginError("Status must be 'success' or 'failure'")

        # Build deployment message
        color = "good" if status.lower() == 'success' else "danger"
        emoji = "✅" if status.lower() == 'success' else "❌"

        fields = [
            {"title": "Service", "value": service, "short": True},
            {"title": "Environment", "value": environment, "short": True}
        ]

        if version:
            fields.append({"title": "Version", "value": version, "short": True})

        if duration:
            fields.append({"title": "Duration", "value": duration, "short": True})

        attachment = {
            "color": color,
            "title": f"{emoji} Deployment {status.title()}",
            "fields": fields,
            "footer": "System Control",
            "ts": int(datetime.now().timestamp())
        }

        if details:
            attachment["text"] = details

        # Determine target channel
        config = self.get_config("slack", {})
        channel_mappings = config.get("channel_mappings", {})

        if status.lower() == 'failure':
            channel = channel_mappings.get("deployment_failure", config.get("default_channel"))
        else:
            channel = channel_mappings.get("deployment_success", config.get("default_channel"))

        self.send_message(
            channel=channel,
            text=f"Deployment {status} for {service}",
            attachments=[attachment]
        )

        self.success(f"Deployment notification sent to Slack")

    # Event handlers
    def setup_event_handlers(self):
        """Set up event handlers for system events."""
        event_bus = self.get_service("events")

        # Register event handlers
        event_handlers = [
            ("deployment.completed", self.on_deployment_completed),
            ("service.health_changed", self.on_health_changed),
            ("alert.triggered", self.on_alert_triggered),
            ("system.error", self.on_system_error)
        ]

        for event_name, handler in event_handlers:
            event_bus.subscribe(event_name, handler)

    @event_handler("deployment.completed")
    def on_deployment_completed(self, event):
        """Handle deployment completion events."""
        config = self.get_config("slack", {})

        # Check if deployment notifications are enabled
        if not config.get("notification_settings", {}).get("deployment_success", True):
            return

        data = event.data
        service = data.get("service")
        environment = data.get("environment")
        success = data.get("success", False)
        version = data.get("version")
        duration = data.get("duration")

        status = "success" if success else "failure"

        self.deployment_notification(
            service=service,
            environment=environment,
            status=status,
            version=version,
            duration=f"{duration}s" if duration else None
        )

    @event_handler("service.health_changed")
    def on_health_changed(self, event):
        """Handle service health change events."""
        config = self.get_config("slack", {})

        if not config.get("notification_settings", {}).get("health_alerts", True):
            return

        data = event.data
        service = data.get("service")
        environment = data.get("environment")
        old_status = data.get("old_status")
        new_status = data.get("new_status")

        # Only alert on status changes to unhealthy
        if new_status == "unhealthy" and old_status != "unhealthy":
            self.send_health_alert(service, environment, new_status)
        elif new_status == "healthy" and old_status == "unhealthy":
            self.send_recovery_notification(service, environment)

    @event_handler("alert.triggered")
    def on_alert_triggered(self, event):
        """Handle generic alert events."""
        data = event.data

        self.send_alert(
            title=data.get("title", "System Alert"),
            message=data.get("message"),
            severity=data.get("severity", "warning"),
            environment=data.get("environment"),
            service=data.get("service")
        )

    # Notification methods
    def send_notification(self, message: str, title: str = None, severity: str = "info",
                         channel: str = None, **kwargs):
        """Send notification via Slack (called by notification service)."""

        color_map = {
            "info": "good",
            "success": "good",
            "warning": "warning",
            "error": "danger",
            "critical": "danger"
        }

        attachment = {
            "color": color_map.get(severity.lower(), "good"),
            "title": title or "System Notification",
            "text": message,
            "footer": "System Control",
            "ts": int(datetime.now().timestamp())
        }

        # Add fields from kwargs
        if kwargs:
            fields = []
            for key, value in kwargs.items():
                if key not in ['channel', 'attachments']:
                    fields.append({
                        "title": key.title().replace('_', ' '),
                        "value": str(value),
                        "short": True
                    })

            if fields:
                attachment["fields"] = fields

        self.send_message(
            channel=channel,
            text=message,
            attachments=[attachment]
        )

    def send_message(self, channel: str = None, text: str = None,
                    attachments: List[Dict] = None, **kwargs):
        """Send message to Slack."""

        config = self.get_config("slack", {})
        target_channel = channel or config.get("default_channel", "#general")

        if self.slack_client:
            # Use Slack Web API
            self.slack_client.send_message(
                channel=target_channel,
                text=text,
                attachments=attachments,
                **kwargs
            )
        elif self.webhook_url:
            # Use webhook
            payload = {
                "channel": target_channel,
                "text": text
            }

            if attachments:
                payload["attachments"] = attachments

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
        else:
            raise PluginError("No Slack webhook URL or bot token configured")

    def send_health_alert(self, service: str, environment: str, status: str):
        """Send service health alert."""

        emoji_map = {
            "healthy": "✅",
            "unhealthy": "❌",
            "degraded": "⚠️"
        }

        color_map = {
            "healthy": "good",
            "unhealthy": "danger",
            "degraded": "warning"
        }

        emoji = emoji_map.get(status, "❓")
        color = color_map.get(status, "warning")

        attachment = {
            "color": color,
            "title": f"{emoji} Service Health Alert",
            "fields": [
                {"title": "Service", "value": service, "short": True},
                {"title": "Environment", "value": environment, "short": True},
                {"title": "Status", "value": status.title(), "short": True}
            ],
            "footer": "System Control Health Monitor",
            "ts": int(datetime.now().timestamp())
        }

        # Get health-specific channel
        config = self.get_config("slack", {})
        channel_mappings = config.get("channel_mappings", {})
        channel = channel_mappings.get("health_alerts", config.get("default_channel"))

        self.send_message(
            channel=channel,
            text=f"Service {service} is {status} in {environment}",
            attachments=[attachment]
        )

    def send_recovery_notification(self, service: str, environment: str):
        """Send service recovery notification."""

        attachment = {
            "color": "good",
            "title": "✅ Service Recovered",
            "text": f"Service {service} in {environment} has recovered and is now healthy",
            "fields": [
                {"title": "Service", "value": service, "short": True},
                {"title": "Environment", "value": environment, "short": True}
            ],
            "footer": "System Control Health Monitor",
            "ts": int(datetime.now().timestamp())
        }

        config = self.get_config("slack", {})
        channel_mappings = config.get("channel_mappings", {})
        channel = channel_mappings.get("recovery_alerts", config.get("default_channel"))

        self.send_message(
            channel=channel,
            text=f"Service {service} recovered in {environment}",
            attachments=[attachment]
        )

    def send_alert(self, title: str, message: str, severity: str = "warning",
                   environment: str = None, service: str = None):
        """Send generic alert."""

        color_map = {
            "info": "good",
            "warning": "warning",
            "error": "danger",
            "critical": "danger"
        }

        fields = []
        if environment:
            fields.append({"title": "Environment", "value": environment, "short": True})
        if service:
            fields.append({"title": "Service", "value": service, "short": True})

        attachment = {
            "color": color_map.get(severity.lower(), "warning"),
            "title": title,
            "text": message,
            "fields": fields,
            "footer": "System Control Alerts",
            "ts": int(datetime.now().timestamp())
        }

        config = self.get_config("slack", {})
        channel_mappings = config.get("channel_mappings", {})
        channel = channel_mappings.get(f"{severity}_alerts", config.get("default_channel"))

        self.send_message(
            channel=channel,
            text=message,
            attachments=[attachment]
        )

    def cleanup(self):
        """Cleanup plugin resources."""
        # Unregister from notification service
        try:
            notification_service = self.get_service("notifications")
            notification_service.unregister_channel("slack")
        except:
            pass

        self.info("Slack integration cleaned up")

class SlackClient:
    """Slack Web API client."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"

    def send_message(self, channel: str, text: str = None,
                    attachments: List[Dict] = None, **kwargs):
        """Send message using Slack Web API."""

        payload = {
            "channel": channel,
            "text": text or ""
        }

        if attachments:
            payload["attachments"] = json.dumps(attachments)

        # Add any additional kwargs
        payload.update(kwargs)

        response = requests.post(
            f"{self.base_url}/chat.postMessage",
            headers={
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Slack API error: {result.get('error')}")

# Plugin registration
plugin = SlackIntegrationPlugin()
```

## Service Plugin Example

### Database Connection Pool Plugin

```python
# plugins/database_pool/plugin.py
from system_control.plugin import ServicePlugin
from system_control.services import BaseService
from system_control.decorators import command, option, argument
from system_control.exceptions import PluginError
import asyncio
import asyncpg
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

@dataclass
class ConnectionStats:
    """Connection pool statistics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_connections: int
    total_queries: int
    avg_query_time: float
    last_reset: float

class DatabaseConnectionPool(BaseService):
    """Advanced database connection pool service."""

    def __init__(self, config: Dict):
        super().__init__()

        self.config = config
        self.pools: Dict[str, asyncpg.Pool] = {}
        self.stats: Dict[str, ConnectionStats] = {}
        self._monitoring_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the connection pool service."""
        await self.initialize_pools()

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_pools())

        self.info("Database connection pool service started")

    async def stop(self):
        """Stop the connection pool service."""

        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Close all pools
        for pool_name, pool in self.pools.items():
            await pool.close()
            self.info(f"Closed connection pool: {pool_name}")

        self.pools.clear()
        self.stats.clear()

        self.info("Database connection pool service stopped")

    async def initialize_pools(self):
        """Initialize database connection pools."""

        databases = self.config.get("databases", {})

        for db_name, db_config in databases.items():
            try:
                pool = await asyncpg.create_pool(
                    host=db_config["host"],
                    port=db_config.get("port", 5432),
                    database=db_config["database"],
                    user=db_config["user"],
                    password=db_config["password"],
                    min_size=db_config.get("min_connections", 1),
                    max_size=db_config.get("max_connections", 10),
                    command_timeout=db_config.get("command_timeout", 30),
                    server_settings=db_config.get("server_settings", {})
                )

                self.pools[db_name] = pool
                self.stats[db_name] = ConnectionStats(
                    total_connections=0,
                    active_connections=0,
                    idle_connections=0,
                    waiting_connections=0,
                    total_queries=0,
                    avg_query_time=0.0,
                    last_reset=time.time()
                )

                self.info(f"Initialized connection pool for database: {db_name}")

            except Exception as e:
                self.error(f"Failed to initialize pool for {db_name}: {e}")
                raise

    async def get_pool(self, database: str = "default") -> asyncpg.Pool:
        """Get connection pool for database."""

        if database not in self.pools:
            raise PluginError(f"Database pool '{database}' not found")

        return self.pools[database]

    @asynccontextmanager
    async def get_connection(self, database: str = "default"):
        """Get database connection with automatic cleanup."""

        pool = await self.get_pool(database)

        async with pool.acquire() as connection:
            yield connection

    async def execute_query(self, query: str, *args, database: str = "default", timeout: Optional[float] = None):
        """Execute query with timing and error handling."""

        start_time = time.time()

        try:
            async with self.get_connection(database) as conn:
                result = await conn.fetchval(query, *args, timeout=timeout)

            # Update statistics
            query_time = time.time() - start_time
            self._update_stats(database, query_time)

            return result

        except Exception as e:
            query_time = time.time() - start_time
            self.error(f"Query failed after {query_time:.3f}s: {e}")
            raise

    async def execute_many(self, query: str, args_list: List, database: str = "default", timeout: Optional[float] = None):
        """Execute query with multiple parameter sets."""

        start_time = time.time()

        try:
            async with self.get_connection(database) as conn:
                result = await conn.executemany(query, args_list, timeout=timeout)

            query_time = time.time() - start_time
            self._update_stats(database, query_time, len(args_list))

            return result

        except Exception as e:
            query_time = time.time() - start_time
            self.error(f"Bulk query failed after {query_time:.3f}s: {e}")
            raise

    async def get_pool_stats(self, database: str = "default") -> ConnectionStats:
        """Get connection pool statistics."""

        if database not in self.pools:
            raise PluginError(f"Database pool '{database}' not found")

        pool = self.pools[database]
        stats = self.stats[database]

        # Update real-time stats
        stats.total_connections = pool.get_size()
        stats.active_connections = pool.get_size() - pool.get_idle_size()
        stats.idle_connections = pool.get_idle_size()

        return stats

    async def health_check(self, database: str = "default") -> bool:
        """Check database connection health."""

        try:
            result = await self.execute_query("SELECT 1", database=database, timeout=5.0)
            return result == 1

        except Exception as e:
            self.error(f"Database health check failed for {database}: {e}")
            return False

    def _update_stats(self, database: str, query_time: float, query_count: int = 1):
        """Update query statistics."""

        stats = self.stats[database]

        # Update query count and average time
        total_time = stats.avg_query_time * stats.total_queries
        stats.total_queries += query_count
        stats.avg_query_time = (total_time + query_time) / stats.total_queries

    async def _monitor_pools(self):
        """Background task to monitor pool health."""

        while True:
            try:
                for db_name in self.pools.keys():
                    # Check pool health
                    if not await self.health_check(db_name):
                        self.warning(f"Database {db_name} health check failed")

                    # Log pool statistics
                    stats = await self.get_pool_stats(db_name)
                    self.debug(f"Pool {db_name}: {stats.active_connections}/{stats.total_connections} active")

                # Wait before next check
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error(f"Pool monitoring error: {e}")
                await asyncio.sleep(60)

class DatabasePoolPlugin(ServicePlugin):
    """Database connection pool plugin."""

    name = "database-pool"
    version = "1.0.0"
    description = "Advanced database connection pool management"
    service_class = DatabaseConnectionPool

    def get_config_schema(self) -> Dict:
        """Return configuration schema."""
        return {
            "database_pool": {
                "databases": {
                    "default": {
                        "host": "localhost",
                        "port": 5432,
                        "database": "myapp",
                        "user": "myapp",
                        "password": "secret",
                        "min_connections": 1,
                        "max_connections": 10,
                        "command_timeout": 30
                    }
                }
            }
        }

    @command("db-stats")
    @option("--database", default="default", help="Database name")
    @option("--format", default="table", help="Output format (table, json)")
    def show_database_stats(self, database: str = "default", format: str = "table"):
        """Show database connection pool statistics."""

        try:
            pool_service = self.get_service_instance()

            # Get stats (this is sync context, so we need to handle async)
            import asyncio
            stats = asyncio.run(pool_service.get_pool_stats(database))

            if format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(stats), indent=2))
            else:
                from rich.table import Table
                from rich.console import Console

                console = Console()
                table = Table(title=f"Database Pool Stats - {database}")

                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Total Connections", str(stats.total_connections))
                table.add_row("Active Connections", str(stats.active_connections))
                table.add_row("Idle Connections", str(stats.idle_connections))
                table.add_row("Waiting Connections", str(stats.waiting_connections))
                table.add_row("Total Queries", str(stats.total_queries))
                table.add_row("Avg Query Time", f"{stats.avg_query_time:.3f}s")

                console.print(table)

        except Exception as e:
            raise PluginError(f"Failed to get database stats: {e}")

    @command("db-health")
    @option("--database", default="default", help="Database name")
    def check_database_health(self, database: str = "default"):
        """Check database connection health."""

        try:
            pool_service = self.get_service_instance()

            import asyncio
            is_healthy = asyncio.run(pool_service.health_check(database))

            if is_healthy:
                self.success(f"Database {database} is healthy")
            else:
                self.error(f"Database {database} health check failed")

        except Exception as e:
            raise PluginError(f"Health check failed: {e}")

    @command("db-query")
    @argument("query", help="SQL query to execute")
    @option("--database", default="default", help="Database name")
    @option("--timeout", type=float, help="Query timeout in seconds")
    def execute_database_query(self, query: str, database: str = "default", timeout: Optional[float] = None):
        """Execute database query."""

        try:
            pool_service = self.get_service_instance()

            import asyncio
            result = asyncio.run(pool_service.execute_query(query, database=database, timeout=timeout))

            if result is not None:
                print(result)
            else:
                self.success("Query executed successfully")

        except Exception as e:
            raise PluginError(f"Query execution failed: {e}")

# Plugin registration
plugin = DatabasePoolPlugin()
```

## Monitoring Plugin Example

### Custom Metrics Plugin

```python
# plugins/custom_metrics/plugin.py
from system_control.plugin import CommandPlugin
from system_control.decorators import command, option, argument
from system_control.monitoring import MetricCollector, MetricRegistry
from system_control.exceptions import PluginError
import psutil
import requests
import time
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class MetricDefinition:
    """Custom metric definition."""
    name: str
    description: str
    metric_type: str  # counter, gauge, histogram, summary
    labels: List[str]
    collection_interval: int
    enabled: bool = True

class CustomMetricsCollector(MetricCollector):
    """Custom metrics collector."""

    def __init__(self, plugin):
        self.plugin = plugin
        self.config = plugin.get_config("custom_metrics", {})
        self.metric_registry = MetricRegistry()
        self.last_collection = {}

        # Register custom metrics
        self.register_metrics()

    def register_metrics(self):
        """Register custom metrics with the registry."""

        metrics = self.config.get("metrics", {})

        for metric_name, metric_config in metrics.items():
            metric_def = MetricDefinition(
                name=metric_name,
                description=metric_config.get("description", ""),
                metric_type=metric_config.get("type", "gauge"),
                labels=metric_config.get("labels", []),
                collection_interval=metric_config.get("interval", 60),
                enabled=metric_config.get("enabled", True)
            )

            if metric_def.enabled:
                self.metric_registry.register_metric(
                    name=metric_name,
                    metric_type=metric_def.metric_type,
                    description=metric_def.description,
                    labels=metric_def.labels
                )

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all custom metrics."""

        current_time = time.time()
        collected_metrics = {}

        metrics = self.config.get("metrics", {})

        for metric_name, metric_config in metrics.items():
            if not metric_config.get("enabled", True):
                continue

            interval = metric_config.get("interval", 60)
            last_collected = self.last_collection.get(metric_name, 0)

            # Check if it's time to collect this metric
            if current_time - last_collected < interval:
                continue

            try:
                metric_value = self.collect_single_metric(metric_name, metric_config)

                if metric_value is not None:
                    collected_metrics[metric_name] = metric_value
                    self.last_collection[metric_name] = current_time

            except Exception as e:
                self.plugin.error(f"Failed to collect metric {metric_name}: {e}")

        return collected_metrics

    def collect_single_metric(self, metric_name: str, metric_config: Dict) -> Any:
        """Collect a single metric based on its configuration."""

        collection_method = metric_config.get("collection_method")

        if collection_method == "system":
            return self.collect_system_metric(metric_config)
        elif collection_method == "http":
            return self.collect_http_metric(metric_config)
        elif collection_method == "command":
            return self.collect_command_metric(metric_config)
        elif collection_method == "custom":
            return self.collect_custom_metric(metric_config)
        else:
            raise ValueError(f"Unknown collection method: {collection_method}")

    def collect_system_metric(self, config: Dict) -> float:
        """Collect system-based metrics."""

        metric_source = config.get("source")

        if metric_source == "cpu_percent":
            return psutil.cpu_percent(interval=1)
        elif metric_source == "memory_percent":
            return psutil.virtual_memory().percent
        elif metric_source == "disk_usage":
            path = config.get("path", "/")
            return psutil.disk_usage(path).percent
        elif metric_source == "network_io":
            stats = psutil.net_io_counters()
            return getattr(stats, config.get("field", "bytes_sent"))
        elif metric_source == "process_count":
            return len(psutil.pids())
        else:
            raise ValueError(f"Unknown system metric source: {metric_source}")

    def collect_http_metric(self, config: Dict) -> float:
        """Collect metrics from HTTP endpoints."""

        url = config.get("url")
        if not url:
            raise ValueError("HTTP metric requires 'url' parameter")

        timeout = config.get("timeout", 10)
        headers = config.get("headers", {})
        auth = config.get("auth")

        try:
            response = requests.get(url, timeout=timeout, headers=headers, auth=auth)
            response.raise_for_status()

            response_type = config.get("response_type", "json")

            if response_type == "json":
                data = response.json()
                json_path = config.get("json_path", "")

                # Navigate JSON path
                for key in json_path.split("."):
                    if key:
                        data = data[key]

                return float(data)

            elif response_type == "text":
                return float(response.text.strip())
            elif response_type == "status_code":
                return float(response.status_code)
            elif response_type == "response_time":
                return response.elapsed.total_seconds()
            else:
                raise ValueError(f"Unknown response type: {response_type}")

        except requests.RequestException as e:
            raise Exception(f"HTTP request failed: {e}")

    def collect_command_metric(self, config: Dict) -> float:
        """Collect metrics from shell commands."""

        import subprocess

        command = config.get("command")
        if not command:
            raise ValueError("Command metric requires 'command' parameter")

        timeout = config.get("timeout", 30)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                raise Exception(f"Command failed with exit code {result.returncode}: {result.stderr}")

            output_type = config.get("output_type", "numeric")

            if output_type == "numeric":
                return float(result.stdout.strip())
            elif output_type == "exit_code":
                return float(result.returncode)
            elif output_type == "line_count":
                return float(len(result.stdout.splitlines()))
            else:
                raise ValueError(f"Unknown output type: {output_type}")

        except subprocess.TimeoutExpired:
            raise Exception(f"Command timed out after {timeout} seconds")

    def collect_custom_metric(self, config: Dict) -> float:
        """Collect custom application metrics."""

        # This would typically interface with your application's metrics
        # For example, getting metrics from a service or database

        metric_source = config.get("source")

        if metric_source == "database_connections":
            # Example: get active database connections
            db_service = self.plugin.get_service("database")
            return db_service.get_active_connections()

        elif metric_source == "queue_size":
            # Example: get message queue size
            queue_service = self.plugin.get_service("message_queue")
            queue_name = config.get("queue_name", "default")
            return queue_service.get_queue_size(queue_name)

        elif metric_source == "cache_hit_rate":
            # Example: get cache hit rate
            cache_service = self.plugin.get_service("cache")
            return cache_service.get_hit_rate()

        else:
            raise ValueError(f"Unknown custom metric source: {metric_source}")

class CustomMetricsPlugin(CommandPlugin):
    """Custom metrics collection and monitoring plugin."""

    name = "custom-metrics"
    version = "1.0.0"
    description = "Custom metrics collection and monitoring"

    def initialize(self):
        """Initialize custom metrics plugin."""

        # Create and register metrics collector
        self.collector = CustomMetricsCollector(self)

        # Register with monitoring service
        monitoring_service = self.get_service("monitoring")
        monitoring_service.register_collector("custom", self.collector)

        self.info("Custom metrics plugin initialized")

    @command("metrics-list")
    @option("--enabled-only", is_flag=True, help="Show only enabled metrics")
    def list_custom_metrics(self, enabled_only: bool = False):
        """List all custom metrics."""

        from rich.table import Table
        from rich.console import Console

        console = Console()
        table = Table(title="Custom Metrics")

        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Interval", justify="center")
        table.add_column("Enabled", justify="center")
        table.add_column("Description")

        metrics = self.get_config("custom_metrics", {}).get("metrics", {})

        for metric_name, metric_config in metrics.items():
            enabled = metric_config.get("enabled", True)

            if enabled_only and not enabled:
                continue

            table.add_row(
                metric_name,
                metric_config.get("type", "gauge"),
                f"{metric_config.get('interval', 60)}s",
                "✅" if enabled else "❌",
                metric_config.get("description", "")
            )

        console.print(table)

    @command("metrics-collect")
    @argument("metric_name", required=False, help="Specific metric to collect")
    @option("--format", default="table", help="Output format (table, json)")
    def collect_metrics_now(self, metric_name: str = None, format: str = "table"):
        """Collect metrics immediately."""

        try:
            if metric_name:
                # Collect specific metric
                metrics = self.get_config("custom_metrics", {}).get("metrics", {})

                if metric_name not in metrics:
                    raise PluginError(f"Metric '{metric_name}' not found")

                metric_config = metrics[metric_name]
                value = self.collector.collect_single_metric(metric_name, metric_config)

                if format == "json":
                    import json
                    print(json.dumps({metric_name: value}, indent=2))
                else:
                    self.success(f"{metric_name}: {value}")
            else:
                # Collect all metrics
                collected = self.collector.collect_metrics()

                if format == "json":
                    import json
                    print(json.dumps(collected, indent=2))
                else:
                    from rich.table import Table
                    from rich.console import Console

                    console = Console()
                    table = Table(title="Collected Metrics")

                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    table.add_column("Timestamp")

                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    for name, value in collected.items():
                        table.add_row(name, str(value), current_time)

                    console.print(table)

        except Exception as e:
            raise PluginError(f"Failed to collect metrics: {e}")

    @command("metrics-enable")
    @argument("metric_name", help="Metric name to enable")
    def enable_metric(self, metric_name: str):
        """Enable a custom metric."""

        config = self.get_config("custom_metrics", {})
        metrics = config.get("metrics", {})

        if metric_name not in metrics:
            raise PluginError(f"Metric '{metric_name}' not found")

        metrics[metric_name]["enabled"] = True

        # Update configuration (this would typically persist to config file)
        self.update_config("custom_metrics", config)

        self.success(f"Enabled metric: {metric_name}")

    @command("metrics-disable")
    @argument("metric_name", help="Metric name to disable")
    def disable_metric(self, metric_name: str):
        """Disable a custom metric."""

        config = self.get_config("custom_metrics", {})
        metrics = config.get("metrics", {})

        if metric_name not in metrics:
            raise PluginError(f"Metric '{metric_name}' not found")

        metrics[metric_name]["enabled"] = False

        # Update configuration
        self.update_config("custom_metrics", config)

        self.success(f"Disabled metric: {metric_name}")

    @command("metrics-test")
    @argument("metric_name", help="Metric name to test")
    def test_metric_collection(self, metric_name: str):
        """Test metric collection for debugging."""

        metrics = self.get_config("custom_metrics", {}).get("metrics", {})

        if metric_name not in metrics:
            raise PluginError(f"Metric '{metric_name}' not found")

        metric_config = metrics[metric_name]

        try:
            self.info(f"Testing metric collection for: {metric_name}")
            self.info(f"Configuration: {metric_config}")

            start_time = time.time()
            value = self.collector.collect_single_metric(metric_name, metric_config)
            collection_time = time.time() - start_time

            self.success(f"Metric collected successfully!")
            self.info(f"Value: {value}")
            self.info(f"Collection time: {collection_time:.3f}s")

        except Exception as e:
            self.error(f"Metric collection test failed: {e}")
            raise PluginError(f"Test failed: {e}")

    def cleanup(self):
        """Cleanup plugin resources."""

        try:
            monitoring_service = self.get_service("monitoring")
            monitoring_service.unregister_collector("custom")
        except:
            pass

        self.info("Custom metrics plugin cleaned up")

# Plugin registration
plugin = CustomMetricsPlugin()
```

These plugin examples demonstrate:

1. **Command Plugin**: Service management with rich CLI commands
2. **Integration Plugin**: Slack integration with event handling and notifications
3. **Service Plugin**: Database connection pooling with async operations
4. **Monitoring Plugin**: Custom metrics collection with multiple data sources

Each example shows different aspects of plugin development including configuration management,
error handling, rich output formatting, async operations, event handling, and service
integration.
