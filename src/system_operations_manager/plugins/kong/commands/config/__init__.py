"""Declarative configuration commands for Kong Gateway.

This module provides commands for managing Kong's declarative configuration:
- export: Export current state to YAML/JSON file
- validate: Validate configuration file
- diff: Show differences between file and current state
- apply: Apply configuration file to Kong
- generate: Interactive wizard to create configuration
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from system_operations_manager.services.kong.config_manager import ConfigManager


def register_config_commands(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register declarative config commands with the Kong app.

    Args:
        app: Parent Typer app to register commands with.
        get_config_manager: Factory function returning ConfigManager instance.
    """
    from system_operations_manager.plugins.kong.commands.config.apply import (
        register_apply_command,
    )
    from system_operations_manager.plugins.kong.commands.config.diff import (
        register_diff_command,
    )
    from system_operations_manager.plugins.kong.commands.config.export import (
        register_export_command,
    )
    from system_operations_manager.plugins.kong.commands.config.generate import (
        register_generate_command,
    )
    from system_operations_manager.plugins.kong.commands.config.validate import (
        register_validate_command,
    )

    config_app = typer.Typer(
        name="config",
        help="Declarative configuration management (export, validate, diff, apply)",
        no_args_is_help=True,
    )

    register_export_command(config_app, get_config_manager)
    register_validate_command(config_app, get_config_manager)
    register_diff_command(config_app, get_config_manager)
    register_apply_command(config_app, get_config_manager)
    register_generate_command(config_app, get_config_manager)

    app.add_typer(config_app, name="config")
