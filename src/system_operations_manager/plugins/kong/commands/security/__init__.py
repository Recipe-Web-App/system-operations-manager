"""Security commands for Kong Gateway.

Provides CLI commands for authentication, authorization, and security plugins:
- key-auth: API key authentication
- jwt: JSON Web Token authentication
- oauth2: OAuth 2.0 authentication
- acl: Access Control Lists
- ip-restriction: IP-based access control
- cors: Cross-Origin Resource Sharing
- mtls: Mutual TLS authentication
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_security_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register all security commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    # Import command registration functions
    from system_operations_manager.plugins.kong.commands.security.acl import (
        register_acl_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.cors import (
        register_cors_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.ip_restriction import (
        register_ip_restriction_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.jwt import (
        register_jwt_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.key_auth import (
        register_key_auth_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.mtls import (
        register_mtls_commands,
    )
    from system_operations_manager.plugins.kong.commands.security.oauth2 import (
        register_oauth2_commands,
    )

    # Create security sub-app
    security_app = typer.Typer(
        name="security",
        help="Security and authentication commands",
        no_args_is_help=True,
    )

    # Register all security command groups
    register_key_auth_commands(security_app, get_plugin_manager, get_consumer_manager)
    register_jwt_commands(security_app, get_plugin_manager, get_consumer_manager)
    register_oauth2_commands(security_app, get_plugin_manager, get_consumer_manager)
    register_acl_commands(security_app, get_plugin_manager, get_consumer_manager)
    register_ip_restriction_commands(security_app, get_plugin_manager)
    register_cors_commands(security_app, get_plugin_manager)
    register_mtls_commands(security_app, get_plugin_manager, get_consumer_manager)

    # Add security sub-app to main app
    app.add_typer(security_app, name="security")
