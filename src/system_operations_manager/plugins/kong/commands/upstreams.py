"""CLI commands for Kong Upstreams and Targets.

This module provides commands for managing Kong Upstream entities
and their targets:
- list: List all upstreams
- get: Get upstream details
- create: Create a new upstream
- update: Update an existing upstream
- delete: Delete an upstream
- health: Show upstream health status
- targets list/add/delete: Manage upstream targets
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.upstream import Upstream
from system_operations_manager.plugins.kong.commands.base import (
    DataPlaneOnlyOption,
    ForceOption,
    LimitOption,
    OffsetOption,
    OutputOption,
    TagsOption,
    confirm_delete,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.dual_write import DualWriteService
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService
    from system_operations_manager.services.kong.upstream_manager import UpstreamManager


# Column definitions for listings
UPSTREAM_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("algorithm", "Algorithm"),
    ("slots", "Slots"),
    ("hash_on", "Hash On"),
]

TARGET_COLUMNS = [
    ("id", "ID"),
    ("target", "Target"),
    ("weight", "Weight"),
    ("tags", "Tags"),
]


def register_upstream_commands(
    app: typer.Typer,
    get_manager: Callable[[], UpstreamManager],
    get_unified_query_service: Callable[[], UnifiedQueryService | None] | None = None,
    get_dual_write_service: Callable[[], DualWriteService[Any]] | None = None,
) -> None:
    """Register upstream commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns an UpstreamManager instance.
        get_unified_query_service: Optional factory that returns a UnifiedQueryService
            for querying both Gateway and Konnect.
        get_dual_write_service: Optional factory that returns a DualWriteService
            for writing to both Gateway and Konnect.
    """
    upstreams_app = typer.Typer(
        name="upstreams",
        help="Manage Kong Upstreams and load balancing",
        no_args_is_help=True,
    )

    # =========================================================================
    # Upstream CRUD Commands
    # =========================================================================

    @upstreams_app.command("list")
    def list_upstreams(
        output: OutputOption = OutputFormat.TABLE,
        tags: TagsOption = None,
        limit: LimitOption = None,
        offset: OffsetOption = None,
        source: Annotated[
            str | None,
            typer.Option(
                "--source",
                "-S",
                help="Filter by source: gateway, konnect (only when Konnect is configured)",
            ),
        ] = None,
        compare: Annotated[
            bool,
            typer.Option(
                "--compare",
                help="Show drift details between Gateway and Konnect",
            ),
        ] = False,
    ) -> None:
        """List all upstreams.

        When Konnect is configured, shows upstreams from both Gateway and Konnect
        with a Source column indicating where each upstream exists.

        Examples:
            ops kong upstreams list
            ops kong upstreams list --tag production
            ops kong upstreams list --output json
            ops kong upstreams list --source gateway
            ops kong upstreams list --compare
        """
        formatter = get_formatter(output, console)

        # Try unified query first if available
        unified_service = get_unified_query_service() if get_unified_query_service else None

        if unified_service is not None:
            try:
                results = unified_service.list_upstreams(tags=tags)

                # Filter by source if specified
                if source:
                    results = results.filter_by_source(source)

                formatter.format_unified_list(
                    results,
                    UPSTREAM_COLUMNS,
                    title="Kong Upstreams",
                    show_drift=compare,
                )
                return
            except Exception as e:
                # Fall back to gateway-only if unified query fails
                console.print(
                    f"[dim]Note: Unified query unavailable ({e}), showing gateway only[/dim]\n"
                )

        # Fall back to gateway-only query
        if source == "konnect":
            console.print(
                "[yellow]Konnect not configured. Use 'ops kong konnect login' to configure.[/yellow]"
            )
            raise typer.Exit(1)

        try:
            manager = get_manager()
            upstreams, next_offset = manager.list(tags=tags, limit=limit, offset=offset)

            formatter.format_list(upstreams, UPSTREAM_COLUMNS, title="Kong Upstreams")

            if next_offset:
                console.print(f"\n[dim]More results available. Use --offset {next_offset}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @upstreams_app.command("get")
    def get_upstream(
        name_or_id: Annotated[str, typer.Argument(help="Upstream name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get an upstream by name or ID.

        Examples:
            ops kong upstreams get my-upstream
            ops kong upstreams get my-upstream --output json
        """
        try:
            manager = get_manager()
            upstream = manager.get(name_or_id)

            formatter = get_formatter(output, console)
            title = f"Upstream: {upstream.name}"
            formatter.format_entity(upstream, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @upstreams_app.command("create")
    def create_upstream(
        name: Annotated[
            str,
            typer.Argument(help="Upstream name (virtual hostname)"),
        ],
        algorithm: Annotated[
            str,
            typer.Option(
                "--algorithm",
                "-a",
                help="Load balancing algorithm: round-robin, consistent-hashing, least-connections, latency",
            ),
        ] = "round-robin",
        slots: Annotated[
            int | None,
            typer.Option("--slots", help="Hash ring slots (10-65536)"),
        ] = None,
        hash_on: Annotated[
            str | None,
            typer.Option(
                "--hash-on",
                help="Hash input: none, consumer, ip, header, cookie, path, query_arg, uri_capture",
            ),
        ] = None,
        hash_on_header: Annotated[
            str | None,
            typer.Option("--hash-on-header", help="Header name for hash_on=header"),
        ] = None,
        hash_on_cookie: Annotated[
            str | None,
            typer.Option("--hash-on-cookie", help="Cookie name for hash_on=cookie"),
        ] = None,
        hash_on_query_arg: Annotated[
            str | None,
            typer.Option("--hash-on-query-arg", help="Query arg for hash_on=query_arg"),
        ] = None,
        host_header: Annotated[
            str | None,
            typer.Option("--host-header", help="Override host header sent to targets"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new upstream.

        By default, creates the upstream in both Gateway and Konnect (if configured).

        Examples:
            ops kong upstreams create my-upstream
            ops kong upstreams create my-upstream --algorithm least-connections
            ops kong upstreams create my-upstream --algorithm consistent-hashing --hash-on ip
            ops kong upstreams create my-upstream --data-plane-only
        """
        try:
            # Build upstream data, only including non-None values
            upstream_data: dict[str, Any] = {"name": name}
            if algorithm is not None:
                upstream_data["algorithm"] = algorithm
            if slots is not None:
                upstream_data["slots"] = slots
            if hash_on is not None:
                upstream_data["hash_on"] = hash_on
            if hash_on_header is not None:
                upstream_data["hash_on_header"] = hash_on_header
            if hash_on_cookie is not None:
                upstream_data["hash_on_cookie"] = hash_on_cookie
            if hash_on_query_arg is not None:
                upstream_data["hash_on_query_arg"] = hash_on_query_arg
            if host_header is not None:
                upstream_data["host_header"] = host_header
            if tags is not None:
                upstream_data["tags"] = tags

            upstream = Upstream(**upstream_data)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.create(upstream, data_plane_only=data_plane_only)

                formatter = get_formatter(output, console)
                console.print("[green]Upstream created successfully[/green]\n")
                formatter.format_entity(
                    result.gateway_result, title=f"Upstream: {result.gateway_result.name}"
                )

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                created = manager.create(upstream)

                formatter = get_formatter(output, console)
                console.print("[green]Upstream created successfully[/green]\n")
                formatter.format_entity(created, title=f"Upstream: {created.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @upstreams_app.command("update")
    def update_upstream(
        name_or_id: Annotated[str, typer.Argument(help="Upstream name or ID to update")],
        algorithm: Annotated[
            str | None,
            typer.Option("--algorithm", "-a", help="Load balancing algorithm"),
        ] = None,
        slots: Annotated[
            int | None,
            typer.Option("--slots", help="Hash ring slots"),
        ] = None,
        hash_on: Annotated[
            str | None,
            typer.Option("--hash-on", help="Hash input"),
        ] = None,
        hash_on_header: Annotated[
            str | None,
            typer.Option("--hash-on-header", help="Header for hashing"),
        ] = None,
        hash_on_cookie: Annotated[
            str | None,
            typer.Option("--hash-on-cookie", help="Cookie for hashing"),
        ] = None,
        host_header: Annotated[
            str | None,
            typer.Option("--host-header", help="Host header override"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (replaces existing)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing upstream.

        Only specified fields will be updated. By default, updates the upstream
        in both Gateway and Konnect (if configured).

        Examples:
            ops kong upstreams update my-upstream --algorithm least-connections
            ops kong upstreams update my-upstream --slots 20000
            ops kong upstreams update my-upstream --algorithm round-robin --data-plane-only
        """
        # Build update data
        update_data: dict[str, Any] = {"name": name_or_id}  # Name required for model
        if algorithm is not None:
            update_data["algorithm"] = algorithm
        if slots is not None:
            update_data["slots"] = slots
        if hash_on is not None:
            update_data["hash_on"] = hash_on
        if hash_on_header is not None:
            update_data["hash_on_header"] = hash_on_header
        if hash_on_cookie is not None:
            update_data["hash_on_cookie"] = hash_on_cookie
        if host_header is not None:
            update_data["host_header"] = host_header
        if tags is not None:
            update_data["tags"] = tags

        if len(update_data) <= 1:  # Only name
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            upstream = Upstream(**update_data)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.update(name_or_id, upstream, data_plane_only=data_plane_only)

                formatter = get_formatter(output, console)
                console.print("[green]Upstream updated successfully[/green]\n")
                formatter.format_entity(
                    result.gateway_result, title=f"Upstream: {result.gateway_result.name}"
                )

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                updated = manager.update(name_or_id, upstream)

                formatter = get_formatter(output, console)
                console.print("[green]Upstream updated successfully[/green]\n")
                formatter.format_entity(updated, title=f"Upstream: {updated.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @upstreams_app.command("delete")
    def delete_upstream(
        name_or_id: Annotated[str, typer.Argument(help="Upstream name or ID to delete")],
        force: ForceOption = False,
        data_plane_only: DataPlaneOnlyOption = False,
    ) -> None:
        """Delete an upstream.

        This will also delete all associated targets. By default, deletes from
        both Gateway and Konnect (if configured).

        Examples:
            ops kong upstreams delete my-upstream
            ops kong upstreams delete my-upstream --force
            ops kong upstreams delete my-upstream --data-plane-only
        """
        try:
            manager = get_manager()

            # Verify upstream exists
            upstream = manager.get(name_or_id)

            if not force and not confirm_delete("upstream", upstream.name):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.delete(name_or_id, data_plane_only=data_plane_only)

                console.print(f"[green]Upstream '{upstream.name}' deleted successfully[/green]")

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("[green]✓ Deleted from Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"[yellow]⚠ Konnect delete failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("[dim]Konnect delete skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager.delete(name_or_id)
                console.print(f"[green]Upstream '{upstream.name}' deleted successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @upstreams_app.command("health")
    def show_upstream_health(
        name_or_id: Annotated[str, typer.Argument(help="Upstream name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show health status for an upstream and its targets.

        Examples:
            ops kong upstreams health my-upstream
            ops kong upstreams health my-upstream --output json
        """
        try:
            manager = get_manager()
            health = manager.get_health(name_or_id)

            formatter = get_formatter(output, console)

            # Show overall health
            health_status = health.health or "UNKNOWN"
            if health_status == "HEALTHY":
                status_display = "[green]HEALTHY[/green]"
            elif health_status == "UNHEALTHY":
                status_display = "[red]UNHEALTHY[/red]"
            else:
                status_display = f"[yellow]{health_status}[/yellow]"

            console.print(f"\nUpstream: {name_or_id}")
            console.print(f"Overall Health: {status_display}\n")

            # Show detailed data if available
            if health.data:
                formatter.format_dict({"targets": health.data}, title="Health Details")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Target Management Commands
    # =========================================================================

    targets_app = typer.Typer(
        name="targets",
        help="Manage upstream targets",
        no_args_is_help=True,
    )

    @targets_app.command("list")
    def list_targets(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        output: OutputOption = OutputFormat.TABLE,
        limit: LimitOption = None,
        offset: OffsetOption = None,
    ) -> None:
        """List all targets for an upstream.

        Examples:
            ops kong upstreams targets list my-upstream
            ops kong upstreams targets list my-upstream --output json
        """
        try:
            manager = get_manager()
            targets, next_offset = manager.list_targets(upstream, limit=limit, offset=offset)

            formatter = get_formatter(output, console)
            formatter.format_list(
                targets,
                TARGET_COLUMNS,
                title=f"Targets for Upstream: {upstream}",
            )

            if next_offset:
                console.print(f"\n[dim]More results available. Use --offset {next_offset}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @targets_app.command("add")
    def add_target(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        target: Annotated[str, typer.Argument(help="Target address (host:port or host)")],
        weight: Annotated[
            int,
            typer.Option("--weight", "-w", help="Load balancing weight (0-65535)"),
        ] = 100,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Add a target to an upstream.

        Examples:
            ops kong upstreams targets add my-upstream api.example.com:8080
            ops kong upstreams targets add my-upstream api.example.com:8080 --weight 50
            ops kong upstreams targets add my-upstream api.example.com --weight 0  # disabled
        """
        try:
            manager = get_manager()
            created = manager.add_target(upstream, target, weight, tags)

            formatter = get_formatter(output, console)
            console.print("[green]Target added successfully[/green]\n")
            formatter.format_entity(created, title="Target")

        except KongAPIError as e:
            handle_kong_error(e)

    @targets_app.command("update")
    def update_target(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        target_id: Annotated[str, typer.Argument(help="Target ID or address")],
        weight: Annotated[
            int | None,
            typer.Option("--weight", "-w", help="New weight"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (replaces existing)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a target's weight or tags.

        Examples:
            ops kong upstreams targets update my-upstream abc-123 --weight 50
            ops kong upstreams targets update my-upstream api.example.com:8080 --weight 0
        """
        if weight is None and tags is None:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            manager = get_manager()
            updated = manager.update_target(upstream, target_id, weight, tags)

            formatter = get_formatter(output, console)
            console.print("[green]Target updated successfully[/green]\n")
            formatter.format_entity(updated, title="Target")

        except KongAPIError as e:
            handle_kong_error(e)

    @targets_app.command("delete")
    def delete_target(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        target_id: Annotated[str, typer.Argument(help="Target ID or address to delete")],
        force: ForceOption = False,
    ) -> None:
        """Delete a target from an upstream.

        Examples:
            ops kong upstreams targets delete my-upstream abc-123
            ops kong upstreams targets delete my-upstream api.example.com:8080 --force
        """
        try:
            manager = get_manager()

            if not force and not confirm_delete("target", target_id):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.delete_target(upstream, target_id)
            console.print(f"[green]Target '{target_id}' deleted successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @targets_app.command("healthy")
    def mark_target_healthy(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        target_id: Annotated[str, typer.Argument(help="Target ID or address")],
    ) -> None:
        """Manually mark a target as healthy.

        This overrides active/passive health check results.

        Examples:
            ops kong upstreams targets healthy my-upstream api.example.com:8080
        """
        try:
            manager = get_manager()
            manager.set_target_healthy(upstream, target_id)
            console.print(f"[green]Target '{target_id}' marked as healthy[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @targets_app.command("unhealthy")
    def mark_target_unhealthy(
        upstream: Annotated[str, typer.Argument(help="Upstream name or ID")],
        target_id: Annotated[str, typer.Argument(help="Target ID or address")],
    ) -> None:
        """Manually mark a target as unhealthy.

        This overrides active/passive health check results.

        Examples:
            ops kong upstreams targets unhealthy my-upstream api.example.com:8080
        """
        try:
            manager = get_manager()
            manager.set_target_unhealthy(upstream, target_id)
            console.print(f"[yellow]Target '{target_id}' marked as unhealthy[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    upstreams_app.add_typer(targets_app, name="targets")

    app.add_typer(upstreams_app, name="upstreams")
