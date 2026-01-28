"""Export command for Kong declarative configuration.

This module provides the `config export` command to export current Kong
state to a declarative configuration file in YAML or JSON format.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.base import console, handle_kong_error

if TYPE_CHECKING:
    from system_operations_manager.services.kong.config_manager import ConfigManager


def register_export_command(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register the config export command.

    Args:
        app: Typer app to register the command with.
        get_config_manager: Factory function returning ConfigManager.
    """

    @app.command("export")
    def config_export(
        file: Annotated[
            Path,
            typer.Argument(help="Output file path (.yaml, .yml, or .json)"),
        ],
        only: Annotated[
            list[str] | None,
            typer.Option(
                "--only",
                "-o",
                help="Entity types to export (can be repeated): services, routes, upstreams, consumers, plugins",
            ),
        ] = None,
        include_credentials: Annotated[
            bool,
            typer.Option(
                "--include-credentials",
                help="Include consumer credentials (sensitive data!)",
            ),
        ] = False,
        format: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Output format: yaml or json (auto-detected from file extension if not specified)",
            ),
        ] = "",
    ) -> None:
        """Export current Kong state to a declarative config file.

        Exports services, routes, upstreams, consumers, and plugins from Kong
        into a YAML or JSON file that can be used for backup, version control,
        or applying to other Kong instances.

        Examples:
            ops kong config export kong.yaml
            ops kong config export kong.json --format json
            ops kong config export services.yaml --only services --only routes
            ops kong config export full.yaml --include-credentials
        """
        # Validate --only options
        valid_types = {"services", "routes", "upstreams", "consumers", "plugins"}
        if only:
            invalid = set(only) - valid_types
            if invalid:
                console.print(f"[red]Error:[/red] Invalid entity types: {', '.join(invalid)}")
                console.print(f"  Valid types: {', '.join(sorted(valid_types))}")
                raise typer.Exit(1)

        # Warn about credentials
        if include_credentials:
            console.print(
                "[yellow]Warning:[/yellow] Including credentials in export. "
                "This file will contain sensitive data!"
            )

        try:
            manager = get_config_manager()
            config = manager.export_state(
                only=only,
                include_credentials=include_credentials,
            )

            # Prepare output data
            output_data = config.model_dump(by_alias=True, exclude_none=True)

            # Add metadata
            output_data["_metadata"] = {
                "exported_at": datetime.now(UTC).isoformat(),
                "exported_by": "ops kong config export",
            }

            # Determine format from extension or --format flag
            use_json = format.lower() == "json" if format else file.suffix.lower() == ".json"

            # Write file
            if use_json:
                content = json.dumps(output_data, indent=2, default=str)
            else:
                # For YAML, use custom representer to handle None and empty lists
                content = yaml.dump(
                    output_data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

            file.write_text(content)

            # Display summary
            console.print(f"\n[green]Configuration exported to {file}[/green]\n")
            console.print("  [cyan]Entity counts:[/cyan]")
            console.print(f"    Services:  {len(config.services)}")
            console.print(f"    Routes:    {len(config.routes)}")
            console.print(f"    Upstreams: {len(config.upstreams)}")
            console.print(f"    Consumers: {len(config.consumers)}")
            console.print(f"    Plugins:   {len(config.plugins)}")

            total = (
                len(config.services)
                + len(config.routes)
                + len(config.upstreams)
                + len(config.consumers)
                + len(config.plugins)
            )
            console.print(f"\n  [bold]Total entities:[/bold] {total}")

        except KongAPIError as e:
            handle_kong_error(e)
