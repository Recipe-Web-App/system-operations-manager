"""Kong Gateway plugin implementation.

This plugin provides integration with Kong Gateway's Admin API for:
- API Management: Services, routes, consumers, upstreams
- Traffic Control: Rate limiting, request transformation
- Security: Authentication, ACLs, IP restrictions
- Observability: Logging, metrics, health checks
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
import typer
from rich.console import Console
from rich.table import Table

from system_operations_manager.core.plugins.base import Plugin, hookimpl
from system_operations_manager.integrations.kong.client import KongAdminClient
from system_operations_manager.integrations.kong.config import KongPluginConfig
from system_operations_manager.integrations.kong.exceptions import KongAPIError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()
console = Console()


class KongPlugin(Plugin):
    """Kong Gateway integration plugin.

    Provides CLI commands and API access to Kong Gateway via the Admin API.
    """

    name = "kong"
    version = "0.1.0"
    description = "Kong Gateway API management and traffic control"

    def __init__(self) -> None:
        """Initialize Kong plugin."""
        super().__init__()
        self._client: KongAdminClient | None = None
        self._plugin_config: KongPluginConfig | None = None

    def on_initialize(self) -> None:
        """Initialize Kong plugin with configuration.

        Parses the plugin configuration and creates the Kong Admin API client.
        Environment variables can override configuration file values.
        """
        try:
            # Parse configuration with environment variable overrides
            config_dict = self._config or {}
            self._plugin_config = KongPluginConfig.from_env(config_dict)

            # Create HTTP client
            self._client = KongAdminClient(
                connection_config=self._plugin_config.connection,
                auth_config=self._plugin_config.auth,
            )

            logger.info(
                "Kong plugin initialized",
                base_url=self._plugin_config.connection.base_url,
                auth_type=self._plugin_config.auth.type,
            )
        except Exception as e:
            logger.error("Failed to initialize Kong plugin", error=str(e))
            raise

    @hookimpl
    def register_commands(self, app: typer.Typer) -> None:
        """Register Kong commands with the CLI.

        Creates a 'kong' subcommand group with all entity management commands:
        - status/info: Node status and configuration
        - services: Service management
        - routes: Route management
        - consumers: Consumer and credential management
        - upstreams: Upstream and target management
        - plugins: Plugin management
        """
        # Create Kong sub-app
        kong_app = typer.Typer(
            name="kong",
            help="Kong Gateway management commands",
            no_args_is_help=True,
        )

        # Register status commands (existing)
        self._register_status_commands(kong_app)

        # Register entity commands
        self._register_entity_commands(kong_app)

        # Add Kong sub-app to main app
        app.add_typer(kong_app, name="kong")

        logger.debug("Kong commands registered")

    def _register_entity_commands(self, app: typer.Typer) -> None:
        """Register all entity management commands."""
        # Import command registration functions
        from system_operations_manager.plugins.kong.commands.consumers import (
            register_consumer_commands,
        )
        from system_operations_manager.plugins.kong.commands.observability import (
            register_observability_commands,
        )
        from system_operations_manager.plugins.kong.commands.plugins import (
            register_plugin_commands,
        )
        from system_operations_manager.plugins.kong.commands.routes import (
            register_route_commands,
        )
        from system_operations_manager.plugins.kong.commands.security import (
            register_security_commands,
        )
        from system_operations_manager.plugins.kong.commands.services import (
            register_service_commands,
        )
        from system_operations_manager.plugins.kong.commands.traffic import (
            register_traffic_commands,
        )
        from system_operations_manager.plugins.kong.commands.upstreams import (
            register_upstream_commands,
        )

        # Import managers
        from system_operations_manager.services.kong import (
            ConsumerManager,
            KongPluginManager,
            ObservabilityManager,
            RouteManager,
            ServiceManager,
            UpstreamManager,
        )

        # Create manager factory functions that use the current client
        def get_service_manager() -> ServiceManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return ServiceManager(self._client)

        def get_route_manager() -> RouteManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return RouteManager(self._client)

        def get_consumer_manager() -> ConsumerManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return ConsumerManager(self._client)

        def get_upstream_manager() -> UpstreamManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return UpstreamManager(self._client)

        def get_plugin_manager() -> KongPluginManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return KongPluginManager(self._client)

        def get_observability_manager() -> ObservabilityManager:
            if not self._client:
                raise RuntimeError("Kong client not initialized")
            return ObservabilityManager(self._client)

        # Register all command groups
        register_service_commands(app, get_service_manager)
        register_route_commands(app, get_route_manager)
        register_consumer_commands(app, get_consumer_manager)
        register_upstream_commands(app, get_upstream_manager)
        register_plugin_commands(app, get_plugin_manager)

        # Register security commands
        register_security_commands(app, get_plugin_manager, get_consumer_manager)

        # Register traffic commands
        register_traffic_commands(app, get_plugin_manager)

        # Register observability commands
        register_observability_commands(
            app,
            get_plugin_manager,
            get_upstream_manager,
            get_observability_manager,
        )

    def _register_status_commands(self, app: typer.Typer) -> None:
        """Register status and info commands."""
        from system_operations_manager.plugins.kong.commands.base import (
            OutputOption,
            handle_kong_error,
        )
        from system_operations_manager.plugins.kong.formatters import (
            OutputFormat,
            get_formatter,
        )

        client = self._client
        plugin_config = self._plugin_config

        @app.command()
        def status(
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Show additional details"),
            output: OutputOption = OutputFormat.TABLE,
        ) -> None:
            """Show Kong node status and connectivity.

            Examples:
                ops kong status
                ops kong status --verbose
                ops kong status --output json
            """
            if not client:
                console.print("[red]Error:[/red] Kong plugin not configured")
                raise typer.Exit(1)

            try:
                status_data = client.get_status()
                info_data = client.get_info()

                # Detect edition
                plugins = info_data.get("plugins", {}).get("available_on_server", {})
                edition = "Enterprise" if "openid-connect" in plugins else "OSS"

                # Database status
                db_status = status_data.get("database", {})
                db_reachable = db_status.get("reachable", False)

                # Build data dictionary
                data = {
                    "node": info_data.get("hostname", "unknown"),
                    "version": info_data.get("version", "unknown"),
                    "edition": edition,
                    "database": "connected" if db_reachable else "disconnected",
                }

                if verbose:
                    data["lua_version"] = info_data.get("lua_version", "unknown")
                    data["tagline"] = info_data.get("tagline", "")
                    memory = status_data.get("memory", {})
                    if lua_shared := memory.get("lua_shared_dicts", {}):
                        workers = lua_shared.get("kong", {})
                        if allocated := workers.get("allocated_slabs"):
                            data["memory_kong"] = allocated

                if output == OutputFormat.TABLE:
                    table = Table(title="Kong Gateway Status")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")

                    table.add_row("Node", data["node"])
                    table.add_row("Version", data["version"])
                    table.add_row("Edition", data["edition"])
                    table.add_row(
                        "Database",
                        "[green]Connected[/green]" if db_reachable else "[red]Disconnected[/red]",
                    )

                    if verbose:
                        table.add_row("Lua Version", data.get("lua_version", "-"))
                        if data.get("memory_kong"):
                            table.add_row("Memory (Kong)", data["memory_kong"])

                    console.print(table)
                else:
                    formatter = get_formatter(output, console)
                    formatter.format_dict(data, title="Kong Gateway Status")

            except KongAPIError as e:
                handle_kong_error(e)

        @app.command()
        def info(
            output: OutputOption = OutputFormat.TABLE,
        ) -> None:
            """Show detailed Kong configuration and features.

            Examples:
                ops kong info
                ops kong info --output json
                ops kong info --output yaml
            """
            if not client:
                console.print("[red]Error:[/red] Kong plugin not configured")
                raise typer.Exit(1)

            try:
                info_data = client.get_info()

                # Plugin info
                plugins = info_data.get("plugins", {})
                available = plugins.get("available_on_server", {})
                enabled = plugins.get("enabled_in_cluster", [])

                # Build data dictionary
                data = {
                    "admin_api": (plugin_config.connection.base_url if plugin_config else "N/A"),
                    "version": info_data.get("version", "unknown"),
                    "hostname": info_data.get("hostname", "unknown"),
                    "lua_version": info_data.get("lua_version", "unknown"),
                    "plugins_available": len(available),
                    "plugins_enabled": len(enabled),
                    "enabled_plugins": sorted(enabled),
                }

                if output == OutputFormat.TABLE:
                    table = Table(title="Kong Configuration")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")

                    table.add_row("Admin API", data["admin_api"])
                    table.add_row("Version", data["version"])
                    table.add_row("Hostname", data["hostname"])
                    table.add_row("Lua Version", data["lua_version"])
                    table.add_row("Plugins Available", str(data["plugins_available"]))
                    table.add_row("Plugins Enabled", str(data["plugins_enabled"]))

                    console.print(table)

                    # List enabled plugins
                    if enabled:
                        plugin_table = Table(title="Enabled Plugins")
                        plugin_table.add_column("Plugin", style="cyan")
                        for plugin_name in sorted(enabled):
                            plugin_table.add_row(plugin_name)
                        console.print(plugin_table)
                else:
                    formatter = get_formatter(output, console)
                    formatter.format_dict(data, title="Kong Configuration")

            except KongAPIError as e:
                handle_kong_error(e)

    @hookimpl
    def cleanup(self) -> None:
        """Cleanup Kong plugin resources."""
        if self._client:
            self._client.close()
            self._client = None
        super().cleanup()
        logger.debug("Kong plugin cleaned up")

    @property
    def client(self) -> KongAdminClient | None:
        """Get the Kong Admin API client.

        Returns:
            The initialized KongAdminClient, or None if not initialized.
        """
        return self._client

    @property
    def plugin_config(self) -> KongPluginConfig | None:
        """Get the Kong plugin configuration.

        Returns:
            The parsed KongPluginConfig, or None if not initialized.
        """
        return self._plugin_config
