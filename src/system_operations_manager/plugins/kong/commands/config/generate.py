"""Generate command for Kong declarative configuration.

This module provides the `config generate` command with an interactive wizard
to help users create Kong declarative configuration files.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import yaml
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from system_operations_manager.plugins.kong.commands.base import console

if TYPE_CHECKING:
    from system_operations_manager.services.kong.config_manager import ConfigManager


def register_generate_command(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register the config generate command.

    Args:
        app: Typer app to register the command with.
        get_config_manager: Factory function returning ConfigManager (unused here).
    """

    @app.command("generate")
    def config_generate(
        file: Annotated[
            Path,
            typer.Argument(help="Output file path (.yaml, .yml, or .json)"),
        ],
    ) -> None:
        """Interactive wizard to generate a Kong config file.

        Guides you through creating a complete Kong configuration including:
        - Service definitions (upstream backends)
        - Route configurations (path/host matching)
        - Optional plugins (rate limiting, authentication, etc.)

        The generated file can be validated with 'config validate' and
        applied with 'config apply'.

        Examples:
            ops kong config generate my-api.yaml
            ops kong config generate services.yml
        """
        console.print(
            Panel(
                "[bold cyan]Kong Configuration Generator[/bold cyan]\n\n"
                "This wizard will help you create a declarative configuration file.\n"
                "Press Ctrl+C at any time to cancel.",
                title="Welcome",
            )
        )
        console.print()

        config: dict[str, Any] = {
            "_format_version": "3.0",
            "services": [],
            "routes": [],
            "plugins": [],
        }

        try:
            # Service configuration
            _configure_services(config)

            # Route configuration
            _configure_routes(config)

            # Optional plugins
            _configure_plugins(config)

            # Write file
            content = yaml.dump(
                config,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            file.write_text(content)

            console.print(f"\n[green]Configuration written to {file}[/green]\n")

            # Show summary
            console.print("[bold]Configuration Summary:[/bold]")
            console.print(f"  Services: {len(config['services'])}")
            console.print(f"  Routes:   {len(config['routes'])}")
            console.print(f"  Plugins:  {len(config['plugins'])}")

            # Next steps
            console.print("\n[bold]Next Steps:[/bold]")
            console.print(f"  1. Review:   [cyan]cat {file}[/cyan]")
            console.print(f"  2. Validate: [cyan]ops kong config validate {file}[/cyan]")
            console.print(f"  3. Preview:  [cyan]ops kong config diff {file}[/cyan]")
            console.print(f"  4. Apply:    [cyan]ops kong config apply {file}[/cyan]")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Generation cancelled[/yellow]")
            raise typer.Exit(0) from None


def _configure_services(config: dict[str, Any]) -> None:
    """Configure services interactively.

    Args:
        config: Configuration dictionary to update.
    """
    console.print("[bold cyan]1. Service Configuration[/bold cyan]\n")
    console.print("A service represents an upstream API or backend that Kong will proxy to.\n")

    while True:
        service_name = Prompt.ask(
            "Service name",
            default="my-service",
        )

        host = Prompt.ask(
            "Upstream host",
            default="localhost",
        )

        port = IntPrompt.ask(
            "Upstream port",
            default=8080,
        )

        protocol = Prompt.ask(
            "Protocol",
            choices=["http", "https", "grpc", "grpcs"],
            default="http",
        )

        # Optional path
        path = Prompt.ask(
            "Base path (optional, press Enter to skip)",
            default="",
        )

        service: dict[str, Any] = {
            "name": service_name,
            "host": host,
            "port": port,
            "protocol": protocol,
        }

        if path:
            if not path.startswith("/"):
                path = "/" + path
            service["path"] = path

        # Optional timeouts
        if Confirm.ask("Configure custom timeouts?", default=False):
            service["connect_timeout"] = IntPrompt.ask(
                "Connect timeout (ms)",
                default=60000,
            )
            service["write_timeout"] = IntPrompt.ask(
                "Write timeout (ms)",
                default=60000,
            )
            service["read_timeout"] = IntPrompt.ask(
                "Read timeout (ms)",
                default=60000,
            )

        config["services"].append(service)
        console.print(f"\n[green]Service '{service_name}' added.[/green]\n")

        if not Confirm.ask("Add another service?", default=False):
            break

    console.print()


def _configure_routes(config: dict[str, Any]) -> None:
    """Configure routes interactively.

    Args:
        config: Configuration dictionary to update.
    """
    console.print("[bold cyan]2. Route Configuration[/bold cyan]\n")
    console.print("Routes define how requests are matched and sent to services.\n")

    # Get service names for selection
    service_names = [s["name"] for s in config["services"]]

    for service_name in service_names:
        console.print(f"\nConfiguring routes for service '[cyan]{service_name}[/cyan]':")

        while True:
            route_name = Prompt.ask(
                "Route name",
                default=f"{service_name}-route",
            )

            # Path matching
            paths_input = Prompt.ask(
                "Path(s) to match (comma-separated)",
                default="/api",
            )
            paths = [p.strip() for p in paths_input.split(",") if p.strip()]

            # Ensure paths start with /
            paths = [p if p.startswith("/") else f"/{p}" for p in paths]

            route: dict[str, Any] = {
                "name": route_name,
                "paths": paths,
                "service": {"name": service_name},
            }

            # Optional host matching
            if Confirm.ask("Add host matching?", default=False):
                hosts_input = Prompt.ask(
                    "Host(s) to match (comma-separated)",
                )
                hosts = [h.strip() for h in hosts_input.split(",") if h.strip()]
                if hosts:
                    route["hosts"] = hosts

            # Optional method matching
            if Confirm.ask("Restrict to specific HTTP methods?", default=False):
                methods_input = Prompt.ask(
                    "Methods (comma-separated)",
                    default="GET,POST",
                )
                methods = [m.strip().upper() for m in methods_input.split(",") if m.strip()]
                if methods:
                    route["methods"] = methods

            # Strip path option
            if Confirm.ask("Strip the matched path from upstream request?", default=True):
                route["strip_path"] = True

            config["routes"].append(route)
            console.print(f"\n[green]Route '{route_name}' added.[/green]")

            if not Confirm.ask("Add another route for this service?", default=False):
                break

    console.print()


def _configure_plugins(config: dict[str, Any]) -> None:
    """Configure plugins interactively.

    Args:
        config: Configuration dictionary to update.
    """
    console.print("[bold cyan]3. Plugin Configuration[/bold cyan]\n")
    console.print("Plugins add functionality like rate limiting, authentication, and more.\n")

    if not Confirm.ask("Add plugins?", default=True):
        return

    service_names = [s["name"] for s in config["services"]]

    # Rate limiting
    if Confirm.ask("Add rate limiting?", default=False):
        console.print("\n[dim]Rate limiting restricts how many requests can be made.[/dim]")

        service = Prompt.ask(
            "Apply to service",
            choices=[*service_names, "(global)"],
            default=service_names[0] if service_names else "(global)",
        )

        minute_limit = IntPrompt.ask(
            "Requests per minute",
            default=100,
        )

        policy = Prompt.ask(
            "Rate limit policy",
            choices=["local", "cluster", "redis"],
            default="local",
        )

        plugin: dict[str, Any] = {
            "name": "rate-limiting",
            "config": {
                "minute": minute_limit,
                "policy": policy,
            },
        }

        if service != "(global)":
            plugin["service"] = {"name": service}

        config["plugins"].append(plugin)
        console.print("[green]Rate limiting plugin added.[/green]\n")

    # Key authentication
    if Confirm.ask("Add API key authentication?", default=False):
        console.print("\n[dim]API key auth requires clients to provide an API key.[/dim]")

        service = Prompt.ask(
            "Apply to service",
            choices=[*service_names, "(global)"],
            default=service_names[0] if service_names else "(global)",
        )

        key_names_input = Prompt.ask(
            "Header/query param names for API key (comma-separated)",
            default="apikey,api-key",
        )
        key_names = [k.strip() for k in key_names_input.split(",") if k.strip()]

        hide_creds = Confirm.ask(
            "Hide credentials from upstream?",
            default=True,
        )

        plugin = {
            "name": "key-auth",
            "config": {
                "key_names": key_names,
                "hide_credentials": hide_creds,
            },
        }

        if service != "(global)":
            plugin["service"] = {"name": service}

        config["plugins"].append(plugin)
        console.print("[green]Key authentication plugin added.[/green]\n")

    # CORS
    if Confirm.ask("Add CORS support?", default=False):
        console.print("\n[dim]CORS allows cross-origin requests from browsers.[/dim]")

        service = Prompt.ask(
            "Apply to service",
            choices=[*service_names, "(global)"],
            default=service_names[0] if service_names else "(global)",
        )

        origins_input = Prompt.ask(
            "Allowed origins (comma-separated, or * for all)",
            default="*",
        )
        if origins_input == "*":
            origins = ["*"]
        else:
            origins = [o.strip() for o in origins_input.split(",") if o.strip()]

        plugin = {
            "name": "cors",
            "config": {
                "origins": origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "headers": ["Accept", "Authorization", "Content-Type"],
                "credentials": True,
                "max_age": 3600,
            },
        }

        if service != "(global)":
            plugin["service"] = {"name": service}

        config["plugins"].append(plugin)
        console.print("[green]CORS plugin added.[/green]\n")

    # Request transformer (headers)
    if Confirm.ask("Add custom request headers?", default=False):
        console.print("\n[dim]Add headers that will be sent to the upstream service.[/dim]")

        service = Prompt.ask(
            "Apply to service",
            choices=[*service_names, "(global)"],
            default=service_names[0] if service_names else "(global)",
        )

        headers_input = Prompt.ask(
            "Headers to add (format: name:value, comma-separated)",
            default="X-Custom-Header:my-value",
        )

        add_headers = []
        for h in headers_input.split(","):
            h = h.strip()
            if ":" in h:
                add_headers.append(h)

        if add_headers:
            plugin = {
                "name": "request-transformer",
                "config": {
                    "add": {
                        "headers": add_headers,
                    },
                },
            }

            if service != "(global)":
                plugin["service"] = {"name": service}

            config["plugins"].append(plugin)
            console.print("[green]Request transformer plugin added.[/green]\n")

    console.print()
