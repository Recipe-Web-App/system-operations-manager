"""Request and response transformer commands for Kong Gateway.

Provides CLI commands for configuring request and response transformation
using Kong's request-transformer and response-transformer plugins.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.traffic.base import (
    ForceOption,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    find_plugin_for_scope,
    get_formatter,
    handle_kong_error,
    validate_scope,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager

# Kong plugin names
REQUEST_TRANSFORMER_PLUGIN = "request-transformer"
RESPONSE_TRANSFORMER_PLUGIN = "response-transformer"


def _parse_key_value_pairs(items: list[str] | None) -> list[str]:
    """Parse and validate key:value pairs.

    Args:
        items: List of key:value strings.

    Returns:
        Validated list of key:value strings.

    Raises:
        typer.Exit: If format is invalid.
    """
    if not items:
        return []

    result = []
    for item in items:
        if ":" not in item:
            console.print(
                f"[red]Error:[/red] Invalid format '{item}'. Expected 'key:value' format."
            )
            raise typer.Exit(1)
        result.append(item)
    return result


def _build_transformer_config(
    add_headers: list[str] | None,
    remove_headers: list[str] | None,
    rename_headers: list[str] | None,
    replace_headers: list[str] | None,
    append_headers: list[str] | None,
    add_querystring: list[str] | None,
    remove_querystring: list[str] | None,
    rename_querystring: list[str] | None,
    replace_querystring: list[str] | None,
    append_querystring: list[str] | None,
    add_body: list[str] | None,
    remove_body: list[str] | None,
    rename_body: list[str] | None,
    replace_body: list[str] | None,
    append_body: list[str] | None,
) -> dict[str, Any]:
    """Build transformer plugin configuration from CLI options.

    Returns:
        Plugin configuration dictionary.
    """
    config: dict[str, Any] = {}

    # Add operations
    add_config: dict[str, list[str]] = {}
    if add_headers:
        add_config["headers"] = _parse_key_value_pairs(add_headers)
    if add_querystring:
        add_config["querystring"] = _parse_key_value_pairs(add_querystring)
    if add_body:
        add_config["body"] = _parse_key_value_pairs(add_body)
    if add_config:
        config["add"] = add_config

    # Remove operations
    remove_config: dict[str, list[str]] = {}
    if remove_headers:
        remove_config["headers"] = remove_headers
    if remove_querystring:
        remove_config["querystring"] = remove_querystring
    if remove_body:
        remove_config["body"] = remove_body
    if remove_config:
        config["remove"] = remove_config

    # Rename operations
    rename_config: dict[str, list[str]] = {}
    if rename_headers:
        rename_config["headers"] = _parse_key_value_pairs(rename_headers)
    if rename_querystring:
        rename_config["querystring"] = _parse_key_value_pairs(rename_querystring)
    if rename_body:
        rename_config["body"] = _parse_key_value_pairs(rename_body)
    if rename_config:
        config["rename"] = rename_config

    # Replace operations
    replace_config: dict[str, list[str]] = {}
    if replace_headers:
        replace_config["headers"] = _parse_key_value_pairs(replace_headers)
    if replace_querystring:
        replace_config["querystring"] = _parse_key_value_pairs(replace_querystring)
    if replace_body:
        replace_config["body"] = _parse_key_value_pairs(replace_body)
    if replace_config:
        config["replace"] = replace_config

    # Append operations
    append_config: dict[str, list[str]] = {}
    if append_headers:
        append_config["headers"] = _parse_key_value_pairs(append_headers)
    if append_querystring:
        append_config["querystring"] = _parse_key_value_pairs(append_querystring)
    if append_body:
        append_config["body"] = _parse_key_value_pairs(append_body)
    if append_config:
        config["append"] = append_config

    return config


def register_transformer_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register request and response transformer subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    _register_request_transformer_commands(app, get_plugin_manager)
    _register_response_transformer_commands(app, get_plugin_manager)


def _register_request_transformer_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register request transformer subcommands."""
    request_transformer_app = typer.Typer(
        name="request-transformer",
        help="Request transformation configuration",
        no_args_is_help=True,
    )

    @request_transformer_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        add_header: Annotated[
            list[str] | None,
            typer.Option(
                "--add-header",
                help="Add header (format: 'name:value', can be repeated)",
            ),
        ] = None,
        remove_header: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-header",
                help="Remove header by name (can be repeated)",
            ),
        ] = None,
        rename_header: Annotated[
            list[str] | None,
            typer.Option(
                "--rename-header",
                help="Rename header (format: 'old:new', can be repeated)",
            ),
        ] = None,
        replace_header: Annotated[
            list[str] | None,
            typer.Option(
                "--replace-header",
                help="Replace header value (format: 'name:value', can be repeated)",
            ),
        ] = None,
        append_header: Annotated[
            list[str] | None,
            typer.Option(
                "--append-header",
                help="Append to header (format: 'name:value', can be repeated)",
            ),
        ] = None,
        add_querystring: Annotated[
            list[str] | None,
            typer.Option(
                "--add-querystring",
                help="Add querystring param (format: 'name:value', can be repeated)",
            ),
        ] = None,
        remove_querystring: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-querystring",
                help="Remove querystring param by name (can be repeated)",
            ),
        ] = None,
        rename_querystring: Annotated[
            list[str] | None,
            typer.Option(
                "--rename-querystring",
                help="Rename querystring param (format: 'old:new', can be repeated)",
            ),
        ] = None,
        replace_querystring: Annotated[
            list[str] | None,
            typer.Option(
                "--replace-querystring",
                help="Replace querystring value (format: 'name:value', can be repeated)",
            ),
        ] = None,
        append_querystring: Annotated[
            list[str] | None,
            typer.Option(
                "--append-querystring",
                help="Append to querystring (format: 'name:value', can be repeated)",
            ),
        ] = None,
        add_body: Annotated[
            list[str] | None,
            typer.Option(
                "--add-body",
                help="Add body param (format: 'name:value', can be repeated)",
            ),
        ] = None,
        remove_body: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-body",
                help="Remove body param by name (can be repeated)",
            ),
        ] = None,
        rename_body: Annotated[
            list[str] | None,
            typer.Option(
                "--rename-body",
                help="Rename body param (format: 'old:new', can be repeated)",
            ),
        ] = None,
        replace_body: Annotated[
            list[str] | None,
            typer.Option(
                "--replace-body",
                help="Replace body value (format: 'name:value', can be repeated)",
            ),
        ] = None,
        append_body: Annotated[
            list[str] | None,
            typer.Option(
                "--append-body",
                help="Append to body (format: 'name:value', can be repeated)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable request transformation on a service or route.

        Transform incoming requests by adding, removing, renaming, replacing,
        or appending headers, querystring parameters, and body fields.

        Examples:
            ops kong traffic request-transformer enable --service my-api --add-header "X-Custom:value"
            ops kong traffic request-transformer enable --service my-api \\
                --add-header "X-Request-Id:$(uuid)" --remove-header "X-Internal-Header"
            ops kong traffic request-transformer enable --route my-route \\
                --rename-header "Authorization:X-Auth" --add-querystring "api_version:v2"
        """
        validate_scope(service, route)

        config = _build_transformer_config(
            add_headers=add_header,
            remove_headers=remove_header,
            rename_headers=rename_header,
            replace_headers=replace_header,
            append_headers=append_header,
            add_querystring=add_querystring,
            remove_querystring=remove_querystring,
            rename_querystring=rename_querystring,
            replace_querystring=replace_querystring,
            append_querystring=append_querystring,
            add_body=add_body,
            remove_body=remove_body,
            rename_body=rename_body,
            replace_body=replace_body,
            append_body=append_body,
        )

        if not config:
            console.print("[red]Error:[/red] At least one transformation option is required")
            raise typer.Exit(1)

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                REQUEST_TRANSFORMER_PLUGIN,
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Request transformer enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Request Transformer Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @request_transformer_app.command("get")
    def get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get request transformer configuration for a service or route.

        Shows the current request transformer plugin configuration if one exists.

        Examples:
            ops kong traffic request-transformer get --service my-api
            ops kong traffic request-transformer get --route my-route --output json
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, REQUEST_TRANSFORMER_PLUGIN, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No request transformer plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Request Transformer Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @request_transformer_app.command("disable")
    def disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable request transformation on a service or route.

        Removes the request transformer plugin from the specified scope.

        Examples:
            ops kong traffic request-transformer disable --service my-api
            ops kong traffic request-transformer disable --route my-route --force
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, REQUEST_TRANSFORMER_PLUGIN, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No request transformer plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id or not isinstance(plugin_id, str):
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope_desc = f"service '{service}'" if service else f"route '{route}'"

            if not force and not typer.confirm(
                f"Are you sure you want to disable request transformation on {scope_desc}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(
                f"[green]Request transformer disabled successfully on {scope_desc}[/green]"
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(request_transformer_app, name="request-transformer")


def _register_response_transformer_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register response transformer subcommands."""
    response_transformer_app = typer.Typer(
        name="response-transformer",
        help="Response transformation configuration",
        no_args_is_help=True,
    )

    @response_transformer_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        add_header: Annotated[
            list[str] | None,
            typer.Option(
                "--add-header",
                help="Add response header (format: 'name:value', can be repeated)",
            ),
        ] = None,
        remove_header: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-header",
                help="Remove response header by name (can be repeated)",
            ),
        ] = None,
        rename_header: Annotated[
            list[str] | None,
            typer.Option(
                "--rename-header",
                help="Rename response header (format: 'old:new', can be repeated)",
            ),
        ] = None,
        replace_header: Annotated[
            list[str] | None,
            typer.Option(
                "--replace-header",
                help="Replace response header value (format: 'name:value', can be repeated)",
            ),
        ] = None,
        append_header: Annotated[
            list[str] | None,
            typer.Option(
                "--append-header",
                help="Append to response header (format: 'name:value', can be repeated)",
            ),
        ] = None,
        add_json: Annotated[
            list[str] | None,
            typer.Option(
                "--add-json",
                help="Add JSON field to response body (format: 'key:value', can be repeated)",
            ),
        ] = None,
        remove_json: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-json",
                help="Remove JSON field from response body (can be repeated)",
            ),
        ] = None,
        replace_json: Annotated[
            list[str] | None,
            typer.Option(
                "--replace-json",
                help="Replace JSON field value (format: 'key:value', can be repeated)",
            ),
        ] = None,
        append_json: Annotated[
            list[str] | None,
            typer.Option(
                "--append-json",
                help="Append to JSON field (format: 'key:value', can be repeated)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable response transformation on a service or route.

        Transform outgoing responses by adding, removing, renaming, replacing,
        or appending headers and JSON body fields.

        Examples:
            ops kong traffic response-transformer enable --service my-api --add-header "X-Response-Time:100ms"
            ops kong traffic response-transformer enable --service my-api \\
                --remove-header "Server" --remove-header "X-Powered-By"
            ops kong traffic response-transformer enable --route my-route \\
                --add-json "api_version:v2" --add-header "Cache-Control:no-cache"
        """
        validate_scope(service, route)

        config: dict[str, Any] = {}

        # Add operations
        add_config: dict[str, list[str]] = {}
        if add_header:
            add_config["headers"] = _parse_key_value_pairs(add_header)
        if add_json:
            add_config["json"] = _parse_key_value_pairs(add_json)
        if add_config:
            config["add"] = add_config

        # Remove operations
        remove_config: dict[str, list[str]] = {}
        if remove_header:
            remove_config["headers"] = remove_header
        if remove_json:
            remove_config["json"] = remove_json
        if remove_config:
            config["remove"] = remove_config

        # Rename operations
        rename_config: dict[str, list[str]] = {}
        if rename_header:
            rename_config["headers"] = _parse_key_value_pairs(rename_header)
        if rename_config:
            config["rename"] = rename_config

        # Replace operations
        replace_config: dict[str, list[str]] = {}
        if replace_header:
            replace_config["headers"] = _parse_key_value_pairs(replace_header)
        if replace_json:
            replace_config["json"] = _parse_key_value_pairs(replace_json)
        if replace_config:
            config["replace"] = replace_config

        # Append operations
        append_config: dict[str, list[str]] = {}
        if append_header:
            append_config["headers"] = _parse_key_value_pairs(append_header)
        if append_json:
            append_config["json"] = _parse_key_value_pairs(append_json)
        if append_config:
            config["append"] = append_config

        if not config:
            console.print("[red]Error:[/red] At least one transformation option is required")
            raise typer.Exit(1)

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                RESPONSE_TRANSFORMER_PLUGIN,
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Response transformer enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Response Transformer Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @response_transformer_app.command("get")
    def get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get response transformer configuration for a service or route.

        Shows the current response transformer plugin configuration if one exists.

        Examples:
            ops kong traffic response-transformer get --service my-api
            ops kong traffic response-transformer get --route my-route --output json
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(
                manager, RESPONSE_TRANSFORMER_PLUGIN, service, route
            )

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No response transformer plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Response Transformer Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @response_transformer_app.command("disable")
    def disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable response transformation on a service or route.

        Removes the response transformer plugin from the specified scope.

        Examples:
            ops kong traffic response-transformer disable --service my-api
            ops kong traffic response-transformer disable --route my-route --force
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(
                manager, RESPONSE_TRANSFORMER_PLUGIN, service, route
            )

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No response transformer plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id or not isinstance(plugin_id, str):
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope_desc = f"service '{service}'" if service else f"route '{route}'"

            if not force and not typer.confirm(
                f"Are you sure you want to disable response transformation on {scope_desc}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(
                f"[green]Response transformer disabled successfully on {scope_desc}[/green]"
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(response_transformer_app, name="response-transformer")
