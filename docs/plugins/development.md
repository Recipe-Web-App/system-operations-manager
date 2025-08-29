# Plugin Development

Comprehensive guide for developing custom plugins for the system control framework,
including APIs, best practices, and testing strategies.

## Overview

Plugin development features:

- **Simple API**: Clean, well-documented plugin interface
- **Hot Reloading**: Develop and test without restarts
- **Type Safety**: Full TypeScript-style type hints support
- **Rich Integration**: Access all system components
- **Testing Framework**: Comprehensive testing utilities
- **Packaging**: Standard Python packaging for distribution

## Quick Start

### Plugin Structure

```python
# plugins/my_plugin.py
from system_control.plugin import Plugin, CommandPlugin, ConfigPlugin
from system_control.decorators import command, option, argument
from rich.console import Console

class MyPlugin(CommandPlugin):
    """Example custom plugin."""

    name = "my-plugin"
    version = "1.0.0"
    description = "My awesome plugin"

    def initialize(self):
        """Initialize plugin resources."""
        self.console = Console()
        self.config = self.get_config("my-plugin", {})

    @command("hello")
    @argument("name", help="Name to greet")
    @option("--loud", is_flag=True, help="Shout the greeting")
    def hello_command(self, name: str, loud: bool = False):
        """Say hello to someone."""
        greeting = f"Hello, {name}!"

        if loud:
            greeting = greeting.upper()

        self.console.print(greeting, style="bold green")

    def cleanup(self):
        """Cleanup plugin resources."""
        pass

# Plugin registration
plugin = MyPlugin()
```

### Registration

```python
# __init__.py in plugin directory
from .my_plugin import plugin

__all__ = ["plugin"]
```

## Plugin Types

### Command Plugins

Add new CLI commands to the system.

```python
from system_control.plugin import CommandPlugin
from system_control.decorators import command, group, option, argument

class DeploymentPlugin(CommandPlugin):
    name = "advanced-deploy"

    @group("deploy")
    def deploy_group(self):
        """Advanced deployment commands."""
        pass

    @deploy_group.command("canary")
    @argument("service", help="Service to deploy")
    @option("--percentage", type=int, default=10, help="Canary percentage")
    def canary_deploy(self, service: str, percentage: int):
        """Deploy using canary strategy."""

        # Validate percentage
        if not 1 <= percentage <= 100:
            self.error("Percentage must be between 1 and 100")
            return

        # Get deployment manager
        deployer = self.get_service("deployment")

        # Execute canary deployment
        with self.progress("Canary deployment") as progress:
            task = progress.add_task(f"Deploying {service}", total=100)

            result = deployer.deploy_canary(
                service=service,
                percentage=percentage,
                progress_callback=lambda p: progress.update(task, completed=p)
            )

        if result.success:
            self.success(f"Canary deployment successful: {service}")
        else:
            self.error(f"Deployment failed: {result.error}")
```

### Configuration Plugins

Extend configuration management and validation.

```python
from system_control.plugin import ConfigPlugin
from system_control.config import ConfigSchema
from marshmallow import fields, validate

class DatabaseConfigPlugin(ConfigPlugin):
    name = "database-config"

    def get_schema_extensions(self) -> dict:
        """Return schema extensions."""
        return {
            "database": {
                "host": fields.Str(required=True),
                "port": fields.Int(validate=validate.Range(1, 65535)),
                "name": fields.Str(required=True),
                "ssl": fields.Bool(default=True),
                "pool_size": fields.Int(default=10),
                "timeout": fields.Int(default=30)
            }
        }

    def validate_config(self, config: dict) -> list:
        """Custom validation logic."""
        errors = []

        db_config = config.get("database", {})

        # Custom validation: SSL required for production
        if config.get("environment") == "production" and not db_config.get("ssl"):
            errors.append("SSL is required for production database connections")

        return errors

    def transform_config(self, config: dict) -> dict:
        """Transform configuration values."""
        if "database" in config:
            # Add computed connection string
            db = config["database"]
            config["database"]["connection_string"] = (
                f"postgresql://{db['host']}:{db['port']}/{db['name']}"
            )

        return config
```

### Service Plugins

Extend system services with new functionality.

```python
from system_control.plugin import ServicePlugin
from system_control.services import BaseService

class CacheService(BaseService):
    """Redis cache service integration."""

    def __init__(self, config: dict):
        super().__init__()
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6379)
        self.client = None

    async def start(self):
        """Start cache service."""
        import redis.asyncio as redis
        self.client = redis.Redis(host=self.host, port=self.port)
        await self.client.ping()

    async def stop(self):
        """Stop cache service."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> str:
        """Get value from cache."""
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache."""
        await self.client.setex(key, ttl, value)

class CachePlugin(ServicePlugin):
    name = "cache"
    service_class = CacheService

    def get_config_schema(self) -> dict:
        return {
            "cache": {
                "host": fields.Str(default="localhost"),
                "port": fields.Int(default=6379),
                "enabled": fields.Bool(default=True)
            }
        }
```

### Integration Plugins

Connect with external systems and tools.

```python
from system_control.plugin import IntegrationPlugin
from system_control.monitoring import MetricCollector

class DatadogPlugin(IntegrationPlugin):
    name = "datadog"

    def initialize(self):
        """Initialize Datadog integration."""
        config = self.get_config("datadog")

        self.api_key = config.get("api_key")
        self.app_key = config.get("app_key")
        self.tags = config.get("tags", [])

        if not self.api_key:
            self.warning("Datadog API key not configured")
            return

        # Initialize Datadog client
        import datadog
        datadog.initialize(api_key=self.api_key, app_key=self.app_key)

        # Register metric collector
        self.register_metric_collector(DatadogMetricCollector(self))

    def send_metric(self, name: str, value: float, tags: list = None):
        """Send metric to Datadog."""
        import datadog

        all_tags = self.tags + (tags or [])
        datadog.api.Metric.send(
            metric=name,
            points=[(time.time(), value)],
            tags=all_tags
        )

    def send_event(self, title: str, text: str, alert_type: str = "info"):
        """Send event to Datadog."""
        import datadog

        datadog.api.Event.create(
            title=title,
            text=text,
            alert_type=alert_type,
            tags=self.tags
        )

class DatadogMetricCollector(MetricCollector):
    def __init__(self, plugin):
        self.plugin = plugin

    def collect_metrics(self) -> dict:
        """Collect system metrics for Datadog."""
        import psutil

        return {
            "system.cpu_percent": psutil.cpu_percent(),
            "system.memory_percent": psutil.virtual_memory().percent,
            "system.disk_percent": psutil.disk_usage('/').percent
        }

    def send_metrics(self, metrics: dict):
        """Send collected metrics."""
        for name, value in metrics.items():
            self.plugin.send_metric(name, value)
```

## Plugin API Reference

### Base Plugin Class

```python
class Plugin:
    """Base plugin class."""

    # Plugin metadata
    name: str = None
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str = ""

    # Dependencies
    requires: List[str] = []
    conflicts: List[str] = []

    def initialize(self):
        """Initialize plugin (called on load)."""
        pass

    def cleanup(self):
        """Cleanup plugin (called on unload)."""
        pass

    # Service access
    def get_service(self, name: str) -> BaseService:
        """Get system service by name."""
        pass

    def get_config(self, key: str, default=None) -> dict:
        """Get configuration values."""
        pass

    # Logging
    def log(self, message: str, level: str = "info"):
        """Log message."""
        pass

    def debug(self, message: str):
        """Log debug message."""
        pass

    def info(self, message: str):
        """Log info message."""
        pass

    def warning(self, message: str):
        """Log warning message."""
        pass

    def error(self, message: str):
        """Log error message."""
        pass

    # UI helpers
    def success(self, message: str):
        """Display success message."""
        pass

    def progress(self, description: str):
        """Create progress bar context."""
        pass

    def confirm(self, message: str) -> bool:
        """Ask for confirmation."""
        pass

    def prompt(self, message: str, default: str = None) -> str:
        """Prompt for input."""
        pass
```

### Command Decorators

```python
from system_control.decorators import (
    command, group, option, argument,
    pass_context, pass_config, pass_services
)

# Basic command
@command("deploy")
@argument("service", help="Service to deploy")
def deploy_service(service: str):
    """Deploy a service."""
    pass

# Command with options
@command("scale")
@argument("service", help="Service to scale")
@option("--replicas", type=int, required=True, help="Number of replicas")
@option("--timeout", type=int, default=300, help="Timeout in seconds")
def scale_service(service: str, replicas: int, timeout: int):
    """Scale a service."""
    pass

# Command group
@group("database")
def db_commands():
    """Database management commands."""
    pass

@db_commands.command("backup")
@option("--compress", is_flag=True, help="Compress backup")
def backup_database(compress: bool):
    """Create database backup."""
    pass

# Context injection
@command("status")
@pass_context
@pass_config
@pass_services
def show_status(ctx, config, services):
    """Show system status."""
    pass
```

### Configuration Integration

```python
from system_control.config import ConfigValidator
from marshmallow import Schema, fields, validate

class PluginConfigSchema(Schema):
    """Plugin configuration schema."""

    api_key = fields.Str(required=True)
    endpoint = fields.Url()
    timeout = fields.Int(validate=validate.Range(1, 300))
    retries = fields.Int(default=3)

    class Meta:
        unknown = "EXCLUDE"

class MyPlugin(ConfigPlugin):
    def get_schema_extensions(self) -> dict:
        return {
            "my_plugin": PluginConfigSchema()
        }

    def validate_config(self, config: dict) -> list:
        errors = []

        plugin_config = config.get("my_plugin", {})

        # Custom validation logic
        if plugin_config.get("retries", 0) > 5:
            errors.append("Retries should not exceed 5")

        return errors
```

## Testing Plugins

### Test Structure

```python
# tests/test_my_plugin.py
import pytest
from unittest.mock import Mock, patch
from system_control.testing import PluginTestCase
from plugins.my_plugin import MyPlugin

class TestMyPlugin(PluginTestCase):
    plugin_class = MyPlugin

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.plugin = self.create_plugin({
            "my_plugin": {
                "api_key": "test-key",
                "endpoint": "https://api.example.com"
            }
        })

    def test_plugin_initialization(self):
        """Test plugin initializes correctly."""
        self.plugin.initialize()

        self.assertEqual(self.plugin.api_key, "test-key")
        self.assertEqual(self.plugin.endpoint, "https://api.example.com")

    def test_hello_command(self):
        """Test hello command."""
        result = self.invoke_command("hello", ["Alice"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hello, Alice!", result.output)

    def test_hello_command_loud(self):
        """Test hello command with --loud flag."""
        result = self.invoke_command("hello", ["Bob", "--loud"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("HELLO, BOB!", result.output)

    @patch('plugins.my_plugin.external_api_call')
    def test_api_integration(self, mock_api):
        """Test external API integration."""
        mock_api.return_value = {"status": "success"}

        result = self.plugin.call_external_api()

        self.assertEqual(result["status"], "success")
        mock_api.assert_called_once()
```

### Mock Services

```python
from system_control.testing import MockService

class TestServiceIntegration(PluginTestCase):
    def setUp(self):
        super().setUp()

        # Mock deployment service
        self.mock_deployer = MockService("deployment")
        self.mock_deployer.deploy_canary.return_value = Mock(
            success=True,
            error=None
        )

        self.register_mock_service("deployment", self.mock_deployer)

    def test_canary_deployment(self):
        """Test canary deployment command."""
        result = self.invoke_command("deploy", ["canary", "api", "--percentage", "20"])

        self.assertEqual(result.exit_code, 0)
        self.mock_deployer.deploy_canary.assert_called_once_with(
            service="api",
            percentage=20,
            progress_callback=unittest.mock.ANY
        )
```

### Integration Testing

```python
import pytest
from system_control.testing import SystemTestCase

class TestPluginIntegration(SystemTestCase):
    """Test plugin integration with full system."""

    @pytest.mark.integration
    def test_full_deployment_workflow(self):
        """Test complete deployment workflow."""
        # Load plugin
        self.load_plugin("deployment_plugin")

        # Test deployment
        result = self.run_command([
            "deploy", "canary", "test-service",
            "--percentage", "10",
            "--env", "staging"
        ])

        self.assertEqual(result.exit_code, 0)

        # Verify service was deployed
        status = self.get_service_status("test-service", "staging")
        self.assertEqual(status.deployment_type, "canary")
        self.assertEqual(status.canary_percentage, 10)
```

## Best Practices

### Plugin Design

```python
# Good: Clear separation of concerns
class MonitoringPlugin(CommandPlugin):
    name = "monitoring"

    def initialize(self):
        """Initialize monitoring components."""
        self.metrics = self.get_service("metrics")
        self.alerting = self.get_service("alerting")

    @command("alert")
    def create_alert(self):
        """Create alert - delegates to service."""
        return self.alerting.create_alert()

    @command("metrics")
    def show_metrics(self):
        """Show metrics - delegates to service."""
        return self.metrics.get_current_metrics()

# Avoid: Too much logic in plugin
class BadPlugin(CommandPlugin):
    @command("complex-operation")
    def complex_operation(self):
        """Bad: Too much logic in command method."""
        # 100+ lines of complex logic here
        pass
```

### Error Handling

```python
from system_control.exceptions import PluginError, ConfigurationError

class MyPlugin(CommandPlugin):
    @command("risky-operation")
    def risky_operation(self):
        """Operation that might fail."""
        try:
            # Risky operation
            result = self.external_service.dangerous_call()

        except ExternalServiceError as e:
            # Convert to plugin error
            raise PluginError(f"External service failed: {e}") from e

        except Exception as e:
            # Log unexpected errors
            self.error(f"Unexpected error: {e}")
            raise PluginError("Operation failed unexpectedly") from e

        return result

    def validate_prerequisites(self):
        """Validate plugin can run."""
        config = self.get_config("my_plugin")

        if not config.get("api_key"):
            raise ConfigurationError("API key is required")

        if not self.external_service.is_available():
            raise PluginError("External service is not available")
```

### Configuration Management

```python
from system_control.config import get_config_value

class ConfigurablePlugin(CommandPlugin):
    def get_setting(self, key: str, default=None):
        """Get plugin setting with fallbacks."""
        # Try plugin-specific config first
        value = get_config_value(f"plugins.{self.name}.{key}", default)

        # Fall back to global config
        if value is default:
            value = get_config_value(f"global.{key}", default)

        return value

    def validate_config(self):
        """Validate plugin configuration."""
        required_settings = ["api_key", "endpoint"]

        for setting in required_settings:
            if not self.get_setting(setting):
                self.error(f"Required setting missing: {setting}")
                return False

        return True

    def initialize(self):
        """Initialize with validation."""
        if not self.validate_config():
            raise ConfigurationError("Plugin configuration is invalid")

        super().initialize()
```

## Advanced Features

### Hot Reloading

```python
class ReloadablePlugin(CommandPlugin):
    """Plugin that supports hot reloading."""

    def __init__(self):
        super().__init__()
        self.reload_count = 0

    def initialize(self):
        """Initialize plugin resources."""
        self.reload_count += 1
        self.info(f"Plugin loaded (reload #{self.reload_count})")

        # Set up file watchers for config changes
        self.setup_config_watchers()

    def setup_config_watchers(self):
        """Watch for configuration changes."""
        config_files = [
            "config/plugin.yaml",
            "config/environments.yaml"
        ]

        for file_path in config_files:
            self.watch_file(file_path, self.on_config_change)

    def on_config_change(self, file_path: str):
        """Handle configuration file changes."""
        self.info(f"Config file changed: {file_path}")

        # Reload configuration
        self.reload_config()

        # Trigger plugin reload
        self.request_reload()

    def cleanup(self):
        """Clean up resources before reload."""
        self.info("Cleaning up plugin resources")

        # Close connections, clear caches, etc.
        if hasattr(self, 'connection'):
            self.connection.close()

        super().cleanup()
```

### Async Operations

```python
import asyncio
from system_control.plugin import AsyncCommandPlugin

class AsyncPlugin(AsyncCommandPlugin):
    """Plugin with async command support."""

    @command("async-deploy")
    @argument("services", nargs=-1, help="Services to deploy")
    async def async_deploy(self, services: List[str]):
        """Deploy multiple services concurrently."""

        async def deploy_service(service_name: str):
            """Deploy single service."""
            deployer = await self.get_service_async("deployment")

            with self.progress(f"Deploying {service_name}") as progress:
                result = await deployer.deploy_async(
                    service=service_name,
                    progress_callback=progress.update
                )

            return service_name, result

        # Deploy all services concurrently
        tasks = [deploy_service(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for service, result in results:
            if isinstance(result, Exception):
                self.error(f"Failed to deploy {service}: {result}")
            else:
                self.success(f"Successfully deployed {service}")
```

### Plugin Communication

```python
from system_control.events import EventBus, event_handler

class CommunicatingPlugin(CommandPlugin):
    """Plugin that communicates via events."""

    def initialize(self):
        """Initialize event handlers."""
        self.event_bus = self.get_service("events")

        # Register event handlers
        self.event_bus.subscribe("deployment.started", self.on_deployment_started)
        self.event_bus.subscribe("service.health_changed", self.on_health_changed)

    @event_handler("deployment.completed")
    def on_deployment_completed(self, event):
        """Handle deployment completion."""
        service = event.data["service"]
        success = event.data["success"]

        if success:
            # Trigger post-deployment actions
            self.event_bus.publish("monitoring.update_targets", {
                "service": service,
                "action": "add"
            })
        else:
            # Handle deployment failure
            self.event_bus.publish("alerting.send_alert", {
                "type": "deployment_failed",
                "service": service,
                "severity": "critical"
            })

    @command("trigger-event")
    @argument("event_name", help="Event to trigger")
    @option("--data", help="Event data (JSON)")
    def trigger_event(self, event_name: str, data: str = None):
        """Trigger custom event."""
        event_data = {}

        if data:
            import json
            event_data = json.loads(data)

        self.event_bus.publish(event_name, event_data)
        self.success(f"Triggered event: {event_name}")
```

## Packaging and Distribution

### Plugin Metadata

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="system-control-my-plugin",
    version="1.0.0",
    description="My awesome System Control plugin",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/your-username/system-control-my-plugin",

    packages=find_packages(),
    python_requires=">=3.8",

    install_requires=[
        "system-control>=2.0.0",
        "requests>=2.25.0",
        "pydantic>=1.8.0"
    ],

    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.0.0",
            "flake8>=3.9.0"
        ]
    },

    entry_points={
        "system_control.plugins": [
            "my-plugin = my_plugin:plugin"
        ]
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10"
    ]
)
```

### Plugin Registry

```yaml
# plugin-registry.yaml
name: "my-awesome-plugin"
version: "1.0.0"
description: "Plugin for awesome functionality"
author: "Your Name <your.email@example.com>"
homepage: "https://github.com/your-username/system-control-my-plugin"
license: "MIT"

compatibility:
  system_control: ">=2.0.0,<3.0.0"
  python: ">=3.8"

dependencies:
  required:
    - "requests>=2.25.0"
    - "pydantic>=1.8.0"
  optional:
    monitoring:
      - "prometheus-client>=0.11.0"
    development:
      - "pytest>=6.0.0"

installation:
  pip: "system-control-my-plugin"
  conda: "conda-forge/system-control-my-plugin"

configuration:
  required_settings:
    - "api_key"
    - "endpoint"
  optional_settings:
    - "timeout"
    - "retries"

commands:
  - name: "my-command"
    description: "My custom command"
    usage: "sysctl my-command [OPTIONS]"

  - name: "hello"
    description: "Say hello"
    usage: "sysctl hello NAME [OPTIONS]"

services:
  - name: "my-service"
    description: "My custom service"

events:
  publishes:
    - "my-plugin.action_completed"
    - "my-plugin.error_occurred"
  subscribes:
    - "system.startup"
    - "deployment.completed"
```

## Troubleshooting

### Common Issues

```python
# Debug plugin loading
import logging
logging.getLogger("system_control.plugins").setLevel(logging.DEBUG)

# Check plugin status
sysctl plugins status my-plugin

# Reload plugin
sysctl plugins reload my-plugin

# Validate plugin
sysctl plugins validate my-plugin

# Plugin dependency issues
sysctl plugins check-deps my-plugin
```

### Development Tools

```bash
# Plugin development commands
sysctl dev plugin create my-plugin
sysctl dev plugin validate my-plugin
sysctl dev plugin test my-plugin
sysctl dev plugin package my-plugin

# Hot reload during development
sysctl dev plugin watch my-plugin

# Debug plugin execution
sysctl --debug my-plugin-command
```
