"""Traffic control commands for Kong Gateway.

Provides CLI commands for traffic management plugins:
- rate-limit: Rate limiting and throttling
- request-size: Request payload size limiting
- request-transformer: Request header/body transformation
- response-transformer: Response header/body transformation
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_traffic_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register all traffic control commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    # Import command registration functions
    from system_operations_manager.plugins.kong.commands.traffic.rate_limit import (
        register_rate_limit_commands,
    )
    from system_operations_manager.plugins.kong.commands.traffic.request_size import (
        register_request_size_commands,
    )
    from system_operations_manager.plugins.kong.commands.traffic.transformers import (
        register_transformer_commands,
    )

    # Create traffic sub-app
    traffic_app = typer.Typer(
        name="traffic",
        help="Traffic control commands",
        no_args_is_help=True,
    )

    # Register all traffic command groups
    register_rate_limit_commands(traffic_app, get_plugin_manager)
    register_request_size_commands(traffic_app, get_plugin_manager)
    register_transformer_commands(traffic_app, get_plugin_manager)

    # Add traffic sub-app to main app
    app.add_typer(traffic_app, name="traffic")
