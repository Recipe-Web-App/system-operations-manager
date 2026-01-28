"""Observability commands for Kong Gateway.

Provides CLI commands for logging, metrics, health checks, and distributed tracing:
- logs: HTTP, file, syslog, TCP logging configuration
- metrics: Prometheus metrics viewing and configuration
- health: Upstream health monitoring
- tracing: OpenTelemetry and Zipkin configuration
- External queries: Prometheus, Elasticsearch/Loki, Jaeger/Zipkin
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from system_operations_manager.services.kong.observability_manager import (
        ObservabilityManager,
    )
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager
    from system_operations_manager.services.kong.upstream_manager import UpstreamManager
    from system_operations_manager.services.observability import (
        LogsManager,
        MetricsManager,
        TracingManager,
    )


def register_observability_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_upstream_manager: Callable[[], UpstreamManager],
    get_observability_manager: Callable[[], ObservabilityManager],
    get_metrics_manager: Callable[[], MetricsManager | None] | None = None,
    get_logs_manager: Callable[[], LogsManager | None] | None = None,
    get_tracing_manager: Callable[[], TracingManager | None] | None = None,
) -> None:
    """Register all observability commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_upstream_manager: Factory function that returns an UpstreamManager instance.
        get_observability_manager: Factory function that returns an ObservabilityManager.
        get_metrics_manager: Optional factory for external Prometheus metrics manager.
        get_logs_manager: Optional factory for external log manager (ES/Loki).
        get_tracing_manager: Optional factory for external tracing manager (Jaeger/Zipkin).
    """
    # Import command registration functions
    from system_operations_manager.plugins.kong.commands.observability.health import (
        register_health_commands,
    )
    from system_operations_manager.plugins.kong.commands.observability.logs import (
        register_logs_commands,
    )
    from system_operations_manager.plugins.kong.commands.observability.metrics import (
        register_metrics_commands,
    )
    from system_operations_manager.plugins.kong.commands.observability.tracing import (
        register_tracing_commands,
    )

    # Create observability sub-app
    observability_app = typer.Typer(
        name="observability",
        help="Observability commands (logging, metrics, health, tracing)",
        no_args_is_help=True,
    )

    # Register all command groups
    register_logs_commands(observability_app, get_plugin_manager)
    register_metrics_commands(observability_app, get_plugin_manager, get_observability_manager)
    register_health_commands(observability_app, get_upstream_manager, get_observability_manager)
    register_tracing_commands(observability_app, get_plugin_manager)

    # Register external observability backend commands if configured
    if get_metrics_manager is not None:
        from system_operations_manager.plugins.kong.commands.observability.external import (
            register_external_metrics_commands,
        )

        register_external_metrics_commands(observability_app, get_metrics_manager)

    if get_logs_manager is not None:
        from system_operations_manager.plugins.kong.commands.observability.external import (
            register_external_logs_commands,
        )

        register_external_logs_commands(observability_app, get_logs_manager)

    if get_tracing_manager is not None:
        from system_operations_manager.plugins.kong.commands.observability.external import (
            register_external_tracing_commands,
        )

        register_external_tracing_commands(observability_app, get_tracing_manager)

    # Add observability sub-app to main app
    app.add_typer(observability_app, name="observability")
