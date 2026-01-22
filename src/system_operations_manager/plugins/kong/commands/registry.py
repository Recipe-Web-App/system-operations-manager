"""CLI commands for Kong Service Registry management.

This module provides commands for managing the local service registry
and deploying services to Kong.

Commands:
- list: List all registered services
- show: Show details for a single service
- add: Add a new service to the registry
- remove: Remove a service from the registry
- import: Import services from a YAML file
- deploy: Deploy services to Kong
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.panel import Panel
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.service_registry import (
    DeploymentResult,
    ServiceAlreadyExistsError,
    ServiceDeployResult,
    ServiceDeploySummary,
    ServiceNotFoundError,
    ServiceProtocol,
    ServiceRegistryEntry,
)
from system_operations_manager.integrations.konnect.client import KonnectClient
from system_operations_manager.integrations.konnect.config import KonnectConfig
from system_operations_manager.integrations.konnect.exceptions import KonnectConfigError
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.openapi_sync_manager import OpenAPISyncManager
    from system_operations_manager.services.kong.registry_manager import RegistryManager
    from system_operations_manager.services.kong.service_manager import ServiceManager


def register_registry_commands(
    app: typer.Typer,
    get_registry_manager: Callable[[], RegistryManager],
    get_service_manager: Callable[[], ServiceManager],
    get_openapi_sync_manager: Callable[[], OpenAPISyncManager],
) -> None:
    """Register service registry commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_registry_manager: Factory function that returns a RegistryManager.
        get_service_manager: Factory function that returns a ServiceManager.
        get_openapi_sync_manager: Factory function that returns an OpenAPISyncManager.
    """
    registry_app = typer.Typer(
        name="registry",
        help="Service registry management - manage and deploy services from local config",
        no_args_is_help=True,
    )

    @registry_app.command("list")
    def list_services(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all services in the registry.

        Shows all services configured in ~/.config/ops/kong/services.yaml

        Examples:
            ops kong registry list
            ops kong registry list --output json
            ops kong registry list --output yaml
        """
        manager = get_registry_manager()
        registry = manager.load()

        if not registry.services:
            console.print("[yellow]No services in registry[/yellow]")
            console.print(f"\n[dim]Registry location: {manager.config_path}[/dim]")
            console.print(
                "[dim]Add services with: ops kong registry add <name> --host <host>[/dim]"
            )
            return

        # Sort services by name
        sorted_services = sorted(registry.services, key=lambda s: s.name)

        if output == OutputFormat.TABLE:
            table = Table(title="Service Registry")
            table.add_column("Name", style="cyan")
            table.add_column("Host")
            table.add_column("Port")
            table.add_column("Protocol")
            table.add_column("OpenAPI Spec", style="dim")

            for service in sorted_services:
                spec_display = Path(service.openapi_spec).name if service.openapi_spec else "-"
                table.add_row(
                    service.name,
                    service.host,
                    str(service.port),
                    service.protocol,
                    spec_display,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(registry.services)} services[/dim]")
            console.print(f"[dim]Registry: {manager.config_path}[/dim]")
        else:
            formatter = get_formatter(output, console)
            data = {
                "services": [s.model_dump(exclude_none=True) for s in sorted_services],
                "total": len(sorted_services),
                "registry_path": str(manager.config_path),
            }
            formatter.format_dict(data, title="Service Registry")

    @registry_app.command("show")
    def show_service(
        name: Annotated[str, typer.Argument(help="Service name")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show details for a single service.

        Examples:
            ops kong registry show auth-service
            ops kong registry show auth-service --output json
        """
        manager = get_registry_manager()
        service = manager.get_service(name)

        if service is None:
            console.print(f"[red]Error:[/red] Service '{name}' not found in registry")
            raise typer.Exit(1)

        if output == OutputFormat.TABLE:
            panel_content = f"""[cyan]Name:[/cyan] {service.name}
[cyan]Host:[/cyan] {service.host}
[cyan]Port:[/cyan] {service.port}
[cyan]Protocol:[/cyan] {service.protocol}
[cyan]Enabled:[/cyan] {service.enabled}"""

            if service.path:
                panel_content += f"\n[cyan]Path:[/cyan] {service.path}"
            if service.tags:
                panel_content += f"\n[cyan]Tags:[/cyan] {', '.join(service.tags)}"
            if service.openapi_spec:
                panel_content += f"\n[cyan]OpenAPI Spec:[/cyan] {service.openapi_spec}"
            if service.path_prefix:
                panel_content += f"\n[cyan]Path Prefix:[/cyan] {service.path_prefix}"

            console.print(Panel(panel_content, title=f"Service: {name}"))
        else:
            formatter = get_formatter(output, console)
            formatter.format_dict(service.model_dump(exclude_none=True), title=f"Service: {name}")

    @registry_app.command("add")
    def add_service(
        name: Annotated[str, typer.Argument(help="Service name")],
        host: Annotated[str, typer.Option("--host", "-h", help="Upstream host")],
        port: Annotated[int, typer.Option("--port", "-p", help="Upstream port")] = 80,
        protocol: Annotated[
            str, typer.Option("--protocol", help="Protocol (http/https/grpc/grpcs)")
        ] = "http",
        path: Annotated[str | None, typer.Option("--path", help="Path prefix")] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated)"),
        ] = None,
        openapi_spec: Annotated[
            str | None,
            typer.Option("--openapi-spec", "--spec", help="Path to OpenAPI spec file"),
        ] = None,
        path_prefix: Annotated[
            str | None,
            typer.Option("--path-prefix", help="Route path prefix for OpenAPI sync"),
        ] = None,
        strip_path: Annotated[
            bool,
            typer.Option("--strip-path/--no-strip-path", help="Strip path when proxying"),
        ] = False,
    ) -> None:
        """Add a service to the registry.

        Examples:
            ops kong registry add auth-service --host auth.local --port 8080
            ops kong registry add api --host api.local --tag prod --tag api
            ops kong registry add users --host users.local --openapi-spec ./openapi.yaml
        """
        try:
            entry = ServiceRegistryEntry(
                name=name,
                host=host,
                port=port,
                protocol=cast(ServiceProtocol, protocol),
                path=path,
                tags=tags,
                openapi_spec=openapi_spec,
                path_prefix=path_prefix,
                strip_path=strip_path,
            )
        except PydanticValidationError as e:
            console.print("[red]Error:[/red] Invalid service configuration")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                console.print(f"  {field}: {error['msg']}")
            raise typer.Exit(1) from None

        manager = get_registry_manager()
        try:
            manager.add_service(entry)
            console.print(f"[green]Added service '{name}' to registry[/green]")
            console.print(f"[dim]Registry: {manager.config_path}[/dim]")
        except ServiceAlreadyExistsError:
            console.print(f"[red]Error:[/red] Service '{name}' already exists in registry")
            console.print("[dim]Use 'ops kong registry edit' to modify it[/dim]")
            raise typer.Exit(1) from None

    @registry_app.command("edit")
    def edit_service(
        name: Annotated[str, typer.Argument(help="Service name to edit")],
        host: Annotated[str | None, typer.Option("--host", "-h", help="Upstream host")] = None,
        port: Annotated[int | None, typer.Option("--port", "-p", help="Upstream port")] = None,
        protocol: Annotated[
            str | None, typer.Option("--protocol", help="Protocol (http/https/grpc/grpcs)")
        ] = None,
        path: Annotated[str | None, typer.Option("--path", help="Path prefix")] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated, replaces existing)"),
        ] = None,
        openapi_spec: Annotated[
            str | None,
            typer.Option("--openapi-spec", "--spec", help="Path to OpenAPI spec file"),
        ] = None,
        path_prefix: Annotated[
            str | None,
            typer.Option("--path-prefix", help="Route path prefix for OpenAPI sync"),
        ] = None,
        strip_path: Annotated[
            bool | None,
            typer.Option("--strip-path/--no-strip-path", help="Strip path when proxying"),
        ] = None,
    ) -> None:
        """Edit an existing service in the registry.

        Only specified fields will be updated; others remain unchanged.

        Examples:
            ops kong registry edit auth-service --port 9090
            ops kong registry edit auth-service --host new-host.local --port 8080
            ops kong registry edit auth-service --no-strip-path
            ops kong registry edit auth-service --tag prod --tag api
        """
        manager = get_registry_manager()
        existing = manager.get_service(name)

        if existing is None:
            console.print(f"[red]Error:[/red] Service '{name}' not found in registry")
            raise typer.Exit(1)

        # Build updated entry, only changing fields that were specified
        updated_data = existing.model_dump()

        if host is not None:
            updated_data["host"] = host
        if port is not None:
            updated_data["port"] = port
        if protocol is not None:
            updated_data["protocol"] = protocol
        if path is not None:
            updated_data["path"] = path
        if tags is not None:
            updated_data["tags"] = tags
        if openapi_spec is not None:
            updated_data["openapi_spec"] = openapi_spec
        if path_prefix is not None:
            updated_data["path_prefix"] = path_prefix
        if strip_path is not None:
            updated_data["strip_path"] = strip_path

        try:
            updated_entry = ServiceRegistryEntry(**updated_data)
            manager.update_service(updated_entry)
            console.print(f"[green]Updated service '{name}' in registry[/green]")
        except PydanticValidationError as e:
            console.print("[red]Error:[/red] Invalid service configuration")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                console.print(f"  {field}: {error['msg']}")
            raise typer.Exit(1) from None

    @registry_app.command("remove")
    def remove_service(
        name: Annotated[str, typer.Argument(help="Service name")],
        force: ForceOption = False,
    ) -> None:
        """Remove a service from the registry.

        This only removes from the local registry, not from Kong.

        Examples:
            ops kong registry remove auth-service
            ops kong registry remove auth-service --force
        """
        manager = get_registry_manager()

        if not force and not typer.confirm(
            f"Remove service '{name}' from registry?", default=False
        ):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

        try:
            manager.remove_service(name)
            console.print(f"[green]Removed service '{name}' from registry[/green]")
        except ServiceNotFoundError:
            console.print(f"[red]Error:[/red] Service '{name}' not found in registry")
            raise typer.Exit(1) from None

    @registry_app.command("import")
    def import_services(
        file: Annotated[
            Path,
            typer.Argument(help="YAML file to import", exists=True, readable=True),
        ],
    ) -> None:
        """Import services from a YAML file.

        Merges services into the existing registry. Existing services with
        the same name will be updated.

        File format:
            services:
              - name: auth-service
                host: auth.local
                port: 8080

        Examples:
            ops kong registry import services.yaml
        """
        manager = get_registry_manager()
        try:
            count = manager.import_from_file(file)
            console.print(f"[green]Imported {count} service(s) from {file.name}[/green]")
            console.print(f"[dim]Registry: {manager.config_path}[/dim]")
        except PydanticValidationError as e:
            console.print("[red]Error:[/red] Invalid file format")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                console.print(f"  {field}: {error['msg']}")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to import: {e}")
            raise typer.Exit(1) from None

    @registry_app.command("deploy")
    def deploy_services(
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Preview changes without applying"),
        ] = False,
        skip_routes: Annotated[
            bool,
            typer.Option("--skip-routes", help="Skip OpenAPI route synchronization"),
        ] = False,
        service: Annotated[
            str | None,
            typer.Option("--service", "-s", help="Deploy only this service"),
        ] = None,
        confirm: Annotated[
            bool,
            typer.Option("--confirm/--no-confirm", help="Require confirmation"),
        ] = True,
        gateway_only: Annotated[
            bool,
            typer.Option("--gateway-only", help="Deploy to Kong Gateway only, skip Konnect"),
        ] = False,
        control_plane: Annotated[
            str | None,
            typer.Option("--control-plane", "-cp", help="Konnect control plane name or ID"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Deploy services from registry to Kong Gateway and Konnect.

        By default, deploys to both Kong Gateway and the configured Konnect
        control plane. Use --gateway-only to skip Konnect synchronization.

        Examples:
            ops kong registry deploy --dry-run
            ops kong registry deploy
            ops kong registry deploy --gateway-only
            ops kong registry deploy --control-plane production
            ops kong registry deploy --skip-routes
            ops kong registry deploy --service auth-service
            ops kong registry deploy --no-confirm
        """
        registry_manager = get_registry_manager()
        service_manager = get_service_manager()
        openapi_manager = get_openapi_sync_manager()

        registry = registry_manager.load()
        if not registry.services:
            console.print("[yellow]No services in registry to deploy[/yellow]")
            raise typer.Exit(0)

        service_names = [service] if service else None

        if service and registry.get_service(service) is None:
            console.print(f"[red]Error:[/red] Service '{service}' not found in registry")
            raise typer.Exit(1)

        # Setup Konnect client if not gateway_only
        konnect_client: KonnectClient | None = None
        control_plane_id: str | None = None
        konnect_cp_name: str | None = None

        if not gateway_only:
            try:
                konnect_config = KonnectConfig.load()
                konnect_client = KonnectClient(konnect_config)

                # Resolve control plane
                cp_identifier = control_plane or konnect_config.default_control_plane
                if cp_identifier:
                    cp = konnect_client.find_control_plane(cp_identifier)
                    control_plane_id = cp.id
                    konnect_cp_name = cp.name
                else:
                    console.print(
                        "[yellow]Warning:[/yellow] No control plane configured. "
                        "Deploying to Gateway only.\n"
                        "[dim]Set default_control_plane in ~/.config/ops/konnect.yaml "
                        "or use --control-plane[/dim]"
                    )
            except KonnectConfigError:
                console.print(
                    "[yellow]Warning:[/yellow] Konnect not configured. "
                    "Deploying to Gateway only.\n"
                    "[dim]Run 'ops kong konnect login' to configure Konnect[/dim]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not connect to Konnect: {e}\n"
                    "[dim]Deploying to Gateway only.[/dim]"
                )

        try:
            # Calculate diff
            console.print("[dim]Calculating changes...[/dim]\n")
            summary = registry_manager.calculate_diff(service_manager, service_names)

            if not summary.has_changes:
                console.print("[green]All services are in sync - no changes needed[/green]")
                raise typer.Exit(0)

            # Display diff
            _display_deploy_summary(summary, output)

            # Show deployment targets
            console.print("\n[bold]Deployment targets:[/bold]")
            console.print("  • Kong Gateway (Admin API)")
            if konnect_client and control_plane_id:
                console.print(f"  • Konnect (control-plane: {konnect_cp_name})")
            elif gateway_only:
                console.print("  • [dim]Konnect: skipped (--gateway-only)[/dim]")
            else:
                console.print("  • [dim]Konnect: skipped (not configured)[/dim]")

            # Check for OpenAPI specs
            services_with_specs = sum(
                1
                for s in registry.services
                if s.has_openapi_spec and (not service_names or s.name in service_names)
            )
            if services_with_specs > 0 and not skip_routes:
                console.print(
                    f"\n[dim]{services_with_specs} service(s) have OpenAPI specs - "
                    f"routes will be synced after service creation[/dim]"
                )

            # Handle dry run
            if dry_run:
                console.print("\n[yellow]Dry run - no changes applied[/yellow]")
                raise typer.Exit(0)

            # Confirm
            if confirm and not typer.confirm("\nApply these changes?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            # Deploy
            console.print("\n[dim]Deploying services...[/dim]")
            deployment_result = registry_manager.deploy(
                service_manager,
                openapi_manager,
                skip_routes=skip_routes,
                service_names=service_names,
                konnect_client=konnect_client,
                control_plane_id=control_plane_id,
                gateway_only=gateway_only or konnect_client is None,
            )

            # Display results
            _display_deployment_results(deployment_result, konnect_cp_name, output)

        except KongAPIError as e:
            handle_kong_error(e)
        finally:
            if konnect_client:
                konnect_client.close()

    app.add_typer(registry_app, name="registry")


def _display_deploy_summary(summary: ServiceDeploySummary, output: OutputFormat) -> None:
    """Display deployment preview summary."""
    if output != OutputFormat.TABLE:
        formatter = get_formatter(output, console)
        formatter.format_dict(summary.model_dump(), title="Deploy Preview")
        return

    # Summary panel
    panel_text = (
        f"Total: {summary.total_services}  "
        f"Create: [green]{summary.creates}[/green]  "
        f"Update: [yellow]{summary.updates}[/yellow]  "
        f"Unchanged: [dim]{summary.unchanged}[/dim]"
    )
    console.print(Panel(panel_text, title="Service Deployment Preview"))

    # Creates table
    creates = [d for d in summary.diffs if d.operation == "create"]
    if creates:
        table = Table(title="[green]Services to Create[/green]")
        table.add_column("Service Name", style="cyan")
        table.add_column("Host")
        table.add_column("Port")
        table.add_column("Protocol")

        for diff in creates:
            if diff.desired:
                table.add_row(
                    diff.service_name,
                    diff.desired.get("host", "-"),
                    str(diff.desired.get("port", 80)),
                    diff.desired.get("protocol", "http"),
                )
        console.print(table)

    # Updates table
    updates = [d for d in summary.diffs if d.operation == "update"]
    if updates:
        table = Table(title="[yellow]Services to Update[/yellow]")
        table.add_column("Service Name", style="cyan")
        table.add_column("Changes")

        for diff in updates:
            changes_str = ", ".join(
                f"{k}: {v[0]} -> {v[1]}" for k, v in (diff.changes or {}).items()
            )
            table.add_row(diff.service_name, changes_str)
        console.print(table)


def _display_deploy_results(
    results: list[ServiceDeployResult],
    output: OutputFormat,
) -> None:
    """Display deployment results."""

    if output != OutputFormat.TABLE:
        formatter = get_formatter(output, console)
        formatter.format_dict(
            {"results": [r.model_dump() for r in results]},
            title="Deploy Results",
        )
        return

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    if failed:
        console.print(
            f"\n[yellow]Deployment completed with errors: "
            f"{len(successful)} succeeded, {len(failed)} failed[/yellow]"
        )
        table = Table(title="[red]Failed Deployments[/red]")
        table.add_column("Service", style="cyan")
        table.add_column("Status")
        table.add_column("Error", style="red")

        for r in failed:
            table.add_row(r.service_name, r.service_status, r.error or "Unknown")
        console.print(table)
        raise typer.Exit(1)
    else:
        # Success summary
        created = sum(1 for r in results if r.service_status == "created")
        updated = sum(1 for r in results if r.service_status == "updated")
        unchanged = sum(1 for r in results if r.service_status == "unchanged")
        routes_synced = sum(r.routes_synced for r in results)

        console.print("\n[green]Deployment successful![/green]")
        console.print(f"  Services: {created} created, {updated} updated, {unchanged} unchanged")
        if routes_synced > 0:
            console.print(f"  Routes synced: {routes_synced}")


def _display_deployment_results(
    result: DeploymentResult,
    konnect_cp_name: str | None,
    output: OutputFormat,
) -> None:
    """Display deployment results for both Gateway and Konnect."""

    if output != OutputFormat.TABLE:
        formatter = get_formatter(output, console)
        data = {
            "gateway": [r.model_dump() for r in result.gateway],
            "konnect": [r.model_dump() for r in result.konnect] if result.konnect else None,
            "konnect_skipped": result.konnect_skipped,
            "konnect_error": result.konnect_error,
        }
        formatter.format_dict(data, title="Deployment Results")
        return

    # Gateway results
    console.print("\n[bold cyan]Gateway Deployment:[/bold cyan]")
    _display_target_results(result.gateway, "Gateway")

    # Konnect results
    if result.konnect_skipped:
        console.print("\n[dim]Konnect: skipped (--gateway-only)[/dim]")
    elif result.konnect_error:
        console.print(f"\n[red]Konnect Error:[/red] {result.konnect_error}")
    elif result.konnect:
        console.print(f"\n[bold cyan]Konnect Deployment ({konnect_cp_name}):[/bold cyan]")
        _display_target_results(result.konnect, "Konnect")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    gw_summary = result.gateway_summary
    console.print(
        f"  Gateway: {len(result.gateway)} services "
        f"({gw_summary['created']} created, {gw_summary['updated']} updated, "
        f"{gw_summary['unchanged']} unchanged, {gw_summary['failed']} failed)"
    )

    if result.konnect:
        kn_summary = result.konnect_summary
        if kn_summary:
            console.print(
                f"  Konnect: {len(result.konnect)} services "
                f"({kn_summary['created']} created, {kn_summary['updated']} updated, "
                f"{kn_summary['unchanged']} unchanged, {kn_summary['failed']} failed)"
            )

    # Check for any failures
    gateway_failed = any(not r.success for r in result.gateway)
    konnect_failed = result.konnect and any(not r.success for r in result.konnect)

    if gateway_failed or konnect_failed or result.konnect_error:
        console.print("\n[yellow]Deployment completed with errors[/yellow]")
        raise typer.Exit(1)
    else:
        console.print("\n[green]Deployment successful![/green]")


def _display_target_results(results: list[ServiceDeployResult], target: str) -> None:
    """Display results for a single deployment target."""
    table = Table()
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Routes")
    table.add_column("Error", style="red")

    for r in results:
        status_style = {
            "created": "[green]created[/green]",
            "updated": "[blue]updated[/blue]",
            "unchanged": "[dim]unchanged[/dim]",
            "failed": "[red]failed[/red]",
        }.get(r.service_status, r.service_status)

        routes_display = ""
        if r.routes_status == "synced":
            routes_display = f"[green]{r.routes_synced} synced[/green]"
        elif r.routes_status == "skipped":
            routes_display = "[dim]skipped[/dim]"
        elif r.routes_status == "failed":
            routes_display = "[red]failed[/red]"
        elif r.routes_status == "no_spec":
            routes_display = "[dim]-[/dim]"

        table.add_row(
            r.service_name,
            status_style,
            routes_display,
            r.error or "",
        )

    console.print(table)
