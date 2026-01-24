"""CLI commands for Kong/Konnect sync status and synchronization.

This module provides commands for checking sync status between
Kong Gateway (data plane) and Konnect (control plane):
- status: Show drift report between Gateway and Konnect
- push: Push Gateway configuration to Konnect
- pull: Pull Konnect configuration to Gateway
- history: View sync operation history
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
    confirm_action,
    console,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
    SyncSummary,
    parse_since,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.certificate_manager import (
        CACertificateManager,
        CertificateManager,
        SNIManager,
    )
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.key_manager import KeyManager, KeySetManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.service_manager import ServiceManager
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService
    from system_operations_manager.services.kong.upstream_manager import UpstreamManager
    from system_operations_manager.services.kong.vault_manager import VaultManager
    from system_operations_manager.services.konnect.certificate_manager import (
        KonnectCACertificateManager,
        KonnectCertificateManager,
        KonnectSNIManager,
    )
    from system_operations_manager.services.konnect.consumer_manager import (
        KonnectConsumerManager,
    )
    from system_operations_manager.services.konnect.key_manager import (
        KonnectKeyManager,
        KonnectKeySetManager,
    )
    from system_operations_manager.services.konnect.plugin_manager import (
        KonnectPluginManager,
    )
    from system_operations_manager.services.konnect.route_manager import (
        KonnectRouteManager,
    )
    from system_operations_manager.services.konnect.service_manager import (
        KonnectServiceManager,
    )
    from system_operations_manager.services.konnect.upstream_manager import (
        KonnectUpstreamManager,
    )
    from system_operations_manager.services.konnect.vault_manager import (
        KonnectVaultManager,
    )


def _display_sync_status_table(
    summary: dict[str, dict[str, int]],
    entity_types: list[str],
    unified_service: UnifiedQueryService,
) -> None:
    """Display sync status as a formatted table."""
    from system_operations_manager.cli.output import Table
    from system_operations_manager.integrations.kong.models.unified import (
        UnifiedEntityList,
    )

    console.print("\n[bold]Sync Status Report[/bold]")
    console.print("=" * 50)

    # Summary table
    table = Table(title="Entity Sync Summary", show_header=True)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Gateway Only", justify="right", style="blue")
    table.add_column("Konnect Only", justify="right", style="green")
    table.add_column("Synced", justify="right", style="green")
    table.add_column("With Drift", justify="right", style="yellow")

    totals = {
        "total": 0,
        "gateway_only": 0,
        "konnect_only": 0,
        "synced": 0,
        "drift": 0,
    }

    for etype in entity_types:
        if etype not in summary:
            continue
        stats = summary[etype]
        table.add_row(
            etype.capitalize(),
            str(stats["total"]),
            str(stats["gateway_only"]) if stats["gateway_only"] > 0 else "-",
            str(stats["konnect_only"]) if stats["konnect_only"] > 0 else "-",
            str(stats["synced"]) if stats["synced"] > 0 else "-",
            str(stats["drift"]) if stats["drift"] > 0 else "-",
        )
        totals["total"] += stats["total"]
        totals["gateway_only"] += stats["gateway_only"]
        totals["konnect_only"] += stats["konnect_only"]
        totals["synced"] += stats["synced"]
        totals["drift"] += stats["drift"]

    # Add totals row
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{totals['total']}[/bold]",
        f"[bold blue]{totals['gateway_only']}[/bold blue]" if totals["gateway_only"] > 0 else "-",
        f"[bold green]{totals['konnect_only']}[/bold green]" if totals["konnect_only"] > 0 else "-",
        f"[bold green]{totals['synced']}[/bold green]" if totals["synced"] > 0 else "-",
        f"[bold yellow]{totals['drift']}[/bold yellow]" if totals["drift"] > 0 else "-",
    )

    console.print(table)

    def _get_entities(etype: str) -> UnifiedEntityList[Any]:
        """Get entities for a given type."""
        if etype == "services":
            return unified_service.list_services()
        elif etype == "routes":
            return unified_service.list_routes()
        elif etype == "consumers":
            return unified_service.list_consumers()
        elif etype == "plugins":
            return unified_service.list_plugins()
        elif etype == "upstreams":
            return unified_service.list_upstreams()
        elif etype == "certificates":
            return unified_service.list_certificates()
        elif etype == "snis":
            return unified_service.list_snis()
        elif etype == "ca_certificates":
            return unified_service.list_ca_certificates()
        elif etype == "key_sets":
            return unified_service.list_key_sets()
        elif etype == "keys":
            return unified_service.list_keys()
        elif etype == "vaults":
            return unified_service.list_vaults()
        else:
            return UnifiedEntityList(entities=[])

    # Show detailed drift info if any
    if totals["drift"] > 0:
        console.print("\n[bold yellow]Entities with Configuration Drift:[/bold yellow]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["drift"] == 0:
                continue

            entities = _get_entities(etype)
            drifted = entities.with_drift
            if drifted:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in drifted:
                    name = unified_entity.identifier
                    drift_fields = unified_entity.drift_fields or []
                    console.print(f"    - {name}: [yellow]{', '.join(drift_fields)}[/yellow]")

    # Show gateway-only entities
    if totals["gateway_only"] > 0:
        console.print("\n[bold blue]Entities only in Gateway (not in Konnect):[/bold blue]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["gateway_only"] == 0:
                continue

            entities = _get_entities(etype)
            gateway_only = entities.gateway_only
            if gateway_only:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in gateway_only[:5]:  # Limit to 5
                    console.print(f"    - {unified_entity.identifier}")
                if len(gateway_only) > 5:
                    console.print(f"    [dim]... and {len(gateway_only) - 5} more[/dim]")

    # Show konnect-only entities
    if totals["konnect_only"] > 0:
        console.print("\n[bold green]Entities only in Konnect (not in Gateway):[/bold green]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["konnect_only"] == 0:
                continue

            entities = _get_entities(etype)
            konnect_only = entities.konnect_only
            if konnect_only:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in konnect_only[:5]:  # Limit to 5
                    console.print(f"    - {unified_entity.identifier}")
                if len(konnect_only) > 5:
                    console.print(f"    [dim]... and {len(konnect_only) - 5} more[/dim]")

    console.print()


def _push_entity_type(
    entity_type: str,
    unified_service: UnifiedQueryService,
    konnect_managers: dict[str, Any],
    dry_run: bool,
    audit_service: SyncAuditService | None = None,
    sync_id: str | None = None,
) -> tuple[int, int, int]:
    """Push entities of a specific type to Konnect.

    Args:
        entity_type: Type of entity (services, routes, etc.)
        unified_service: UnifiedQueryService instance
        konnect_managers: Dict mapping entity type to Konnect manager
        dry_run: If True, show what would be pushed without changes
        audit_service: Optional audit service for logging operations
        sync_id: Optional sync operation ID for grouping audit entries

    Returns:
        Tuple of (created_count, updated_count, error_count)
    """
    from system_operations_manager.integrations.kong.models.unified import (
        UnifiedEntityList,
    )

    # Get unified list for this entity type
    entities: UnifiedEntityList[Any]
    if entity_type == "services":
        entities = unified_service.list_services()
    elif entity_type == "routes":
        entities = unified_service.list_routes()
    elif entity_type == "consumers":
        entities = unified_service.list_consumers()
    elif entity_type == "plugins":
        entities = unified_service.list_plugins()
    elif entity_type == "upstreams":
        entities = unified_service.list_upstreams()
    elif entity_type == "certificates":
        entities = unified_service.list_certificates()
    elif entity_type == "snis":
        entities = unified_service.list_snis()
    elif entity_type == "ca_certificates":
        entities = unified_service.list_ca_certificates()
    elif entity_type == "key_sets":
        entities = unified_service.list_key_sets()
    elif entity_type == "keys":
        entities = unified_service.list_keys()
    elif entity_type == "vaults":
        entities = unified_service.list_vaults()
    else:
        return 0, 0, 0

    manager = konnect_managers.get(entity_type)
    if manager is None:
        console.print(f"  [yellow]Skipping {entity_type} (manager not available)[/yellow]")
        return 0, 0, 0

    created, updated, errors = 0, 0, 0

    # Create entities that only exist in Gateway
    for unified in entities.gateway_only:
        entity = unified.gateway_entity
        if entity is None:
            continue

        if dry_run:
            console.print(f"  [cyan]Would create:[/cyan] {unified.identifier}")
            created += 1
            # Record audit entry
            if audit_service and sync_id:
                audit_service.record(
                    SyncAuditEntry(
                        sync_id=sync_id,
                        timestamp=datetime.now(UTC).isoformat(),
                        operation="push",
                        dry_run=True,
                        entity_type=entity_type,
                        entity_id=unified.gateway_id,
                        entity_name=unified.identifier,
                        action="create",
                        source="gateway",
                        target="konnect",
                        status="would_create",
                    )
                )
        else:
            try:
                result = manager.create(entity)
                console.print(f"  [green]Created:[/green] {unified.identifier}")
                created += 1
                # Record audit entry
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="push",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.gateway_id,
                            entity_name=unified.identifier,
                            action="create",
                            source="gateway",
                            target="konnect",
                            status="success",
                            after_state=result.model_dump()
                            if hasattr(result, "model_dump")
                            else None,
                        )
                    )
            except Exception as e:
                console.print(f"  [red]Failed to create:[/red] {unified.identifier} - {e}")
                errors += 1
                # Record error in audit
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="push",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.gateway_id,
                            entity_name=unified.identifier,
                            action="create",
                            source="gateway",
                            target="konnect",
                            status="failed",
                            error=str(e),
                        )
                    )

    # Update entities with drift
    for unified in entities.with_drift:
        entity = unified.gateway_entity
        konnect_id = unified.konnect_id
        if entity is None or konnect_id is None:
            continue

        drift_fields = unified.drift_fields or []

        if dry_run:
            console.print(f"  [cyan]Would update:[/cyan] {unified.identifier}")
            if drift_fields:
                console.print(f"    [dim]Drift fields: {', '.join(drift_fields)}[/dim]")
            updated += 1
            # Record audit entry
            if audit_service and sync_id:
                audit_service.record(
                    SyncAuditEntry(
                        sync_id=sync_id,
                        timestamp=datetime.now(UTC).isoformat(),
                        operation="push",
                        dry_run=True,
                        entity_type=entity_type,
                        entity_id=unified.gateway_id,
                        entity_name=unified.identifier,
                        action="update",
                        source="gateway",
                        target="konnect",
                        status="would_update",
                        drift_fields=drift_fields if drift_fields else None,
                        before_state=unified.konnect_entity.model_dump()
                        if unified.konnect_entity and hasattr(unified.konnect_entity, "model_dump")
                        else None,
                    )
                )
        else:
            try:
                result = manager.update(konnect_id, entity)
                console.print(f"  [green]Updated:[/green] {unified.identifier}")
                updated += 1
                # Record audit entry
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="push",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.gateway_id,
                            entity_name=unified.identifier,
                            action="update",
                            source="gateway",
                            target="konnect",
                            status="success",
                            drift_fields=drift_fields if drift_fields else None,
                            before_state=unified.konnect_entity.model_dump()
                            if unified.konnect_entity
                            and hasattr(unified.konnect_entity, "model_dump")
                            else None,
                            after_state=result.model_dump()
                            if hasattr(result, "model_dump")
                            else None,
                        )
                    )
            except Exception as e:
                console.print(f"  [red]Failed to update:[/red] {unified.identifier} - {e}")
                errors += 1
                # Record error in audit
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="push",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.gateway_id,
                            entity_name=unified.identifier,
                            action="update",
                            source="gateway",
                            target="konnect",
                            status="failed",
                            error=str(e),
                            drift_fields=drift_fields if drift_fields else None,
                        )
                    )

    return created, updated, errors


def _pull_entity_type(
    entity_type: str,
    unified_service: UnifiedQueryService,
    gateway_managers: dict[str, Any],
    dry_run: bool,
    with_drift: bool = False,
    audit_service: SyncAuditService | None = None,
    sync_id: str | None = None,
) -> tuple[int, int, int]:
    """Pull entities of a specific type from Konnect to Gateway.

    Args:
        entity_type: Type of entity (services, routes, etc.)
        unified_service: UnifiedQueryService instance
        gateway_managers: Dict mapping entity type to Gateway manager
        dry_run: If True, show what would be pulled without changes
        with_drift: If True, also update entities with drift (Gateway to match Konnect)
        audit_service: Optional audit service for logging operations
        sync_id: Optional sync operation ID for grouping audit entries

    Returns:
        Tuple of (created_count, updated_count, error_count)
    """
    from system_operations_manager.integrations.kong.models.unified import (
        UnifiedEntityList,
    )

    # Get unified list for this entity type
    entities: UnifiedEntityList[Any]
    if entity_type == "services":
        entities = unified_service.list_services()
    elif entity_type == "routes":
        entities = unified_service.list_routes()
    elif entity_type == "consumers":
        entities = unified_service.list_consumers()
    elif entity_type == "plugins":
        entities = unified_service.list_plugins()
    elif entity_type == "upstreams":
        entities = unified_service.list_upstreams()
    elif entity_type == "certificates":
        entities = unified_service.list_certificates()
    elif entity_type == "snis":
        entities = unified_service.list_snis()
    elif entity_type == "ca_certificates":
        entities = unified_service.list_ca_certificates()
    elif entity_type == "key_sets":
        entities = unified_service.list_key_sets()
    elif entity_type == "keys":
        entities = unified_service.list_keys()
    elif entity_type == "vaults":
        entities = unified_service.list_vaults()
    else:
        return 0, 0, 0

    manager = gateway_managers.get(entity_type)
    if manager is None:
        console.print(f"  [yellow]Skipping {entity_type} (manager not available)[/yellow]")
        return 0, 0, 0

    created, updated, errors = 0, 0, 0

    # Create entities that only exist in Konnect
    for unified in entities.konnect_only:
        entity = unified.konnect_entity
        if entity is None:
            continue

        if dry_run:
            console.print(f"  [cyan]Would create:[/cyan] {unified.identifier}")
            created += 1
            # Record audit entry
            if audit_service and sync_id:
                audit_service.record(
                    SyncAuditEntry(
                        sync_id=sync_id,
                        timestamp=datetime.now(UTC).isoformat(),
                        operation="pull",
                        dry_run=True,
                        entity_type=entity_type,
                        entity_id=unified.konnect_id,
                        entity_name=unified.identifier,
                        action="create",
                        source="konnect",
                        target="gateway",
                        status="would_create",
                    )
                )
        else:
            try:
                result = manager.create(entity)
                console.print(f"  [green]Created:[/green] {unified.identifier}")
                created += 1
                # Record audit entry
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="pull",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.konnect_id,
                            entity_name=unified.identifier,
                            action="create",
                            source="konnect",
                            target="gateway",
                            status="success",
                            after_state=result.model_dump()
                            if hasattr(result, "model_dump")
                            else None,
                        )
                    )
            except Exception as e:
                console.print(f"  [red]Failed to create:[/red] {unified.identifier} - {e}")
                errors += 1
                # Record error in audit
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="pull",
                            dry_run=False,
                            entity_type=entity_type,
                            entity_id=unified.konnect_id,
                            entity_name=unified.identifier,
                            action="create",
                            source="konnect",
                            target="gateway",
                            status="failed",
                            error=str(e),
                        )
                    )

    # Update entities with drift (if requested)
    if with_drift:
        for unified in entities.with_drift:
            entity = unified.konnect_entity  # Use Konnect version as source
            gateway_id = unified.gateway_id
            if entity is None or gateway_id is None:
                continue

            drift_fields = unified.drift_fields or []

            if dry_run:
                console.print(f"  [cyan]Would update:[/cyan] {unified.identifier}")
                if drift_fields:
                    console.print(f"    [dim]Drift fields: {', '.join(drift_fields)}[/dim]")
                updated += 1
                # Record audit entry
                if audit_service and sync_id:
                    audit_service.record(
                        SyncAuditEntry(
                            sync_id=sync_id,
                            timestamp=datetime.now(UTC).isoformat(),
                            operation="pull",
                            dry_run=True,
                            entity_type=entity_type,
                            entity_id=unified.konnect_id,
                            entity_name=unified.identifier,
                            action="update",
                            source="konnect",
                            target="gateway",
                            status="would_update",
                            drift_fields=drift_fields if drift_fields else None,
                            before_state=unified.gateway_entity.model_dump()
                            if unified.gateway_entity
                            and hasattr(unified.gateway_entity, "model_dump")
                            else None,
                        )
                    )
            else:
                try:
                    result = manager.update(gateway_id, entity)
                    console.print(f"  [green]Updated:[/green] {unified.identifier}")
                    updated += 1
                    # Record audit entry
                    if audit_service and sync_id:
                        audit_service.record(
                            SyncAuditEntry(
                                sync_id=sync_id,
                                timestamp=datetime.now(UTC).isoformat(),
                                operation="pull",
                                dry_run=False,
                                entity_type=entity_type,
                                entity_id=unified.konnect_id,
                                entity_name=unified.identifier,
                                action="update",
                                source="konnect",
                                target="gateway",
                                status="success",
                                drift_fields=drift_fields if drift_fields else None,
                                before_state=unified.gateway_entity.model_dump()
                                if unified.gateway_entity
                                and hasattr(unified.gateway_entity, "model_dump")
                                else None,
                                after_state=result.model_dump()
                                if hasattr(result, "model_dump")
                                else None,
                            )
                        )
                except Exception as e:
                    console.print(f"  [red]Failed to update:[/red] {unified.identifier} - {e}")
                    errors += 1
                    # Record error in audit
                    if audit_service and sync_id:
                        audit_service.record(
                            SyncAuditEntry(
                                sync_id=sync_id,
                                timestamp=datetime.now(UTC).isoformat(),
                                operation="pull",
                                dry_run=False,
                                entity_type=entity_type,
                                entity_id=unified.konnect_id,
                                entity_name=unified.identifier,
                                action="update",
                                source="konnect",
                                target="gateway",
                                status="failed",
                                error=str(e),
                                drift_fields=drift_fields if drift_fields else None,
                            )
                        )

    return created, updated, errors


def _push_targets_for_upstreams(
    unified_service: UnifiedQueryService,
    upstreams: list[str],
    konnect_upstream_manager: Any,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Push targets for the given upstreams from Gateway to Konnect.

    Args:
        unified_service: UnifiedQueryService instance.
        upstreams: List of upstream names to sync targets for.
        konnect_upstream_manager: Konnect UpstreamManager instance.
        dry_run: If True, show what would be pushed without changes.

    Returns:
        Tuple of (created_count, updated_count, error_count).
    """
    created, updated, errors = 0, 0, 0

    for upstream_name in upstreams:
        try:
            targets = unified_service.list_targets_for_upstream(upstream_name)
        except Exception as e:
            console.print(f"  [yellow]Could not fetch targets for {upstream_name}: {e}[/yellow]")
            continue

        # Create targets that only exist in Gateway
        for unified in targets.gateway_only:
            target = unified.gateway_entity
            if target is None:
                continue

            if dry_run:
                console.print(
                    f"  [cyan]Would create target:[/cyan] {target.target} -> {upstream_name}"
                )
                created += 1
            else:
                try:
                    konnect_upstream_manager.add_target(upstream_name, target)
                    console.print(
                        f"  [green]Created target:[/green] {target.target} -> {upstream_name}"
                    )
                    created += 1
                except Exception as e:
                    console.print(f"  [red]Failed to create target:[/red] {target.target} - {e}")
                    errors += 1

        # Note: Target updates are not supported (targets are immutable, recreate to change)

    return created, updated, errors


def _pull_targets_for_upstreams(
    unified_service: UnifiedQueryService,
    upstreams: list[str],
    gateway_upstream_manager: Any,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Pull targets for the given upstreams from Konnect to Gateway.

    Args:
        unified_service: UnifiedQueryService instance.
        upstreams: List of upstream names to sync targets for.
        gateway_upstream_manager: Gateway UpstreamManager instance.
        dry_run: If True, show what would be pulled without changes.

    Returns:
        Tuple of (created_count, updated_count, error_count).
    """
    created, updated, errors = 0, 0, 0

    for upstream_name in upstreams:
        try:
            targets = unified_service.list_targets_for_upstream(upstream_name)
        except Exception as e:
            console.print(f"  [yellow]Could not fetch targets for {upstream_name}: {e}[/yellow]")
            continue

        # Create targets that only exist in Konnect
        for unified in targets.konnect_only:
            target = unified.konnect_entity
            if target is None:
                continue

            if dry_run:
                console.print(
                    f"  [cyan]Would create target:[/cyan] {target.target} -> {upstream_name}"
                )
                created += 1
            else:
                try:
                    gateway_upstream_manager.add_target(
                        upstream_name,
                        target=target.target,
                        weight=target.weight,
                        tags=getattr(target, "tags", None),
                    )
                    console.print(
                        f"  [green]Created target:[/green] {target.target} -> {upstream_name}"
                    )
                    created += 1
                except Exception as e:
                    console.print(f"  [red]Failed to create target:[/red] {target.target} - {e}")
                    errors += 1

    return created, updated, errors


def register_sync_commands(
    app: typer.Typer,
    get_unified_query_service: Callable[[], UnifiedQueryService | None],
    get_konnect_service_manager: Callable[[], KonnectServiceManager | None] | None = None,
    get_konnect_route_manager: Callable[[], KonnectRouteManager | None] | None = None,
    get_konnect_consumer_manager: Callable[[], KonnectConsumerManager | None] | None = None,
    get_konnect_plugin_manager: Callable[[], KonnectPluginManager | None] | None = None,
    get_konnect_upstream_manager: Callable[[], KonnectUpstreamManager | None] | None = None,
    get_konnect_certificate_manager: Callable[[], KonnectCertificateManager | None] | None = None,
    get_konnect_sni_manager: Callable[[], KonnectSNIManager | None] | None = None,
    get_konnect_ca_certificate_manager: Callable[[], KonnectCACertificateManager | None]
    | None = None,
    get_konnect_key_set_manager: Callable[[], KonnectKeySetManager | None] | None = None,
    get_konnect_key_manager: Callable[[], KonnectKeyManager | None] | None = None,
    get_konnect_vault_manager: Callable[[], KonnectVaultManager | None] | None = None,
    # Gateway manager factories (for sync pull)
    get_gateway_service_manager: Callable[[], ServiceManager] | None = None,
    get_gateway_route_manager: Callable[[], RouteManager] | None = None,
    get_gateway_consumer_manager: Callable[[], ConsumerManager] | None = None,
    get_gateway_plugin_manager: Callable[[], KongPluginManager] | None = None,
    get_gateway_upstream_manager: Callable[[], UpstreamManager] | None = None,
    get_gateway_certificate_manager: Callable[[], CertificateManager] | None = None,
    get_gateway_sni_manager: Callable[[], SNIManager] | None = None,
    get_gateway_ca_certificate_manager: Callable[[], CACertificateManager] | None = None,
    get_gateway_key_set_manager: Callable[[], KeySetManager] | None = None,
    get_gateway_key_manager: Callable[[], KeyManager] | None = None,
    get_gateway_vault_manager: Callable[[], VaultManager] | None = None,
) -> None:
    """Register sync commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_unified_query_service: Factory function that returns a UnifiedQueryService.
        get_konnect_service_manager: Factory for Konnect service manager.
        get_konnect_route_manager: Factory for Konnect route manager.
        get_konnect_consumer_manager: Factory for Konnect consumer manager.
        get_konnect_plugin_manager: Factory for Konnect plugin manager.
        get_konnect_upstream_manager: Factory for Konnect upstream manager.
        get_konnect_certificate_manager: Factory for Konnect certificate manager.
        get_konnect_sni_manager: Factory for Konnect SNI manager.
        get_konnect_ca_certificate_manager: Factory for Konnect CA certificate manager.
        get_konnect_key_set_manager: Factory for Konnect key set manager.
        get_konnect_key_manager: Factory for Konnect key manager.
        get_konnect_vault_manager: Factory for Konnect vault manager.
        get_gateway_service_manager: Factory for Gateway service manager (for pull).
        get_gateway_route_manager: Factory for Gateway route manager (for pull).
        get_gateway_consumer_manager: Factory for Gateway consumer manager (for pull).
        get_gateway_plugin_manager: Factory for Gateway plugin manager (for pull).
        get_gateway_upstream_manager: Factory for Gateway upstream manager (for pull).
        get_gateway_certificate_manager: Factory for Gateway certificate manager (for pull).
        get_gateway_sni_manager: Factory for Gateway SNI manager (for pull).
        get_gateway_ca_certificate_manager: Factory for Gateway CA certificate manager (for pull).
        get_gateway_key_set_manager: Factory for Gateway key set manager (for pull).
        get_gateway_key_manager: Factory for Gateway key manager (for pull).
        get_gateway_vault_manager: Factory for Gateway vault manager (for pull).
    """
    sync_app = typer.Typer(
        name="sync",
        help="Sync and drift detection between Gateway and Konnect",
        no_args_is_help=True,
    )

    @sync_app.command("status")
    def sync_status(
        entity_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                "-t",
                help="Entity type to check (services, routes, consumers, plugins, upstreams)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show drift between Gateway and Konnect.

        Displays:
        - Entities only in Gateway (not synced to Konnect)
        - Entities only in Konnect (not in Gateway)
        - Entities in both with configuration drift
        - Fully synced entities

        Examples:
            ops kong sync status
            ops kong sync status --type services
            ops kong sync status --output json
        """
        unified_service = get_unified_query_service()

        if unified_service is None:
            console.print(
                "[yellow]Konnect not configured.[/yellow] "
                "Configure Konnect in ops.yaml to use sync status."
            )
            console.print("\nExample configuration:")
            console.print("[dim]konnect:[/dim]")
            console.print("[dim]  api_key: ${KONNECT_API_KEY}[/dim]")
            console.print("[dim]  default_control_plane: my-control-plane[/dim]")
            raise typer.Exit(1)

        formatter = get_formatter(output, console)

        # Determine which entity types to check
        if entity_type:
            valid_types = [
                "services",
                "routes",
                "consumers",
                "plugins",
                "upstreams",
                "certificates",
                "snis",
                "ca_certificates",
                "key_sets",
                "keys",
                "vaults",
            ]
            if entity_type not in valid_types:
                console.print(
                    f"[red]Invalid entity type:[/red] {entity_type}\n"
                    f"Valid types: {', '.join(valid_types)}"
                )
                raise typer.Exit(1)
            entity_types = [entity_type]
        else:
            entity_types = [
                "services",
                "routes",
                "consumers",
                "plugins",
                "upstreams",
                "certificates",
                "snis",
                "ca_certificates",
                "key_sets",
                "keys",
                "vaults",
            ]

        # Get sync summary
        summary = unified_service.get_sync_summary(entity_types)

        if output == OutputFormat.TABLE:
            _display_sync_status_table(summary, entity_types, unified_service)
        else:
            formatter.format_dict(summary, title="Sync Status")

    @sync_app.command("push")
    def sync_push(
        entity_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                "-t",
                help="Entity type to push (services, routes, consumers, plugins, upstreams)",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-n",
                help="Show what would be pushed without making changes",
            ),
        ] = False,
        include_targets: Annotated[
            bool,
            typer.Option(
                "--include-targets",
                help="Also sync targets when syncing upstreams",
            ),
        ] = False,
        force: ForceOption = False,
    ) -> None:
        """Push Gateway configuration to Konnect.

        Syncs entities that are:
        - Only in Gateway (creates in Konnect)
        - In both with drift (updates Konnect to match Gateway)

        Examples:
            ops kong sync push                     # Push all entity types
            ops kong sync push --type services     # Push only services
            ops kong sync push --dry-run           # Preview changes
            ops kong sync push --force             # Skip confirmation
        """
        unified_service = get_unified_query_service()

        if unified_service is None:
            console.print(
                "[yellow]Konnect not configured.[/yellow] "
                "Configure Konnect in ops.yaml to use sync push."
            )
            console.print("\nExample configuration:")
            console.print("[dim]konnect:[/dim]")
            console.print("[dim]  api_key: ${KONNECT_API_KEY}[/dim]")
            console.print("[dim]  default_control_plane: my-control-plane[/dim]")
            raise typer.Exit(1)

        # Determine which entity types to push
        valid_types = [
            "services",
            "routes",
            "consumers",
            "plugins",
            "upstreams",
            "certificates",
            "snis",
            "ca_certificates",
            "key_sets",
            "keys",
            "vaults",
        ]
        if entity_type:
            if entity_type not in valid_types:
                console.print(
                    f"[red]Invalid entity type:[/red] {entity_type}\n"
                    f"Valid types: {', '.join(valid_types)}"
                )
                raise typer.Exit(1)
            entity_types_to_push = [entity_type]
        else:
            entity_types_to_push = valid_types

        # Build Konnect managers dict
        konnect_managers: dict[str, Any] = {}
        if get_konnect_service_manager:
            konnect_managers["services"] = get_konnect_service_manager()
        if get_konnect_route_manager:
            konnect_managers["routes"] = get_konnect_route_manager()
        if get_konnect_consumer_manager:
            konnect_managers["consumers"] = get_konnect_consumer_manager()
        if get_konnect_plugin_manager:
            konnect_managers["plugins"] = get_konnect_plugin_manager()
        if get_konnect_upstream_manager:
            konnect_managers["upstreams"] = get_konnect_upstream_manager()
        if get_konnect_certificate_manager:
            konnect_managers["certificates"] = get_konnect_certificate_manager()
        if get_konnect_sni_manager:
            konnect_managers["snis"] = get_konnect_sni_manager()
        if get_konnect_ca_certificate_manager:
            konnect_managers["ca_certificates"] = get_konnect_ca_certificate_manager()
        if get_konnect_key_set_manager:
            konnect_managers["key_sets"] = get_konnect_key_set_manager()
        if get_konnect_key_manager:
            konnect_managers["keys"] = get_konnect_key_manager()
        if get_konnect_vault_manager:
            konnect_managers["vaults"] = get_konnect_vault_manager()

        if not konnect_managers:
            console.print("[yellow]No Konnect managers available.[/yellow]")
            raise typer.Exit(1)

        # Get preview of changes
        summary = unified_service.get_sync_summary(entity_types_to_push)
        total_to_create = sum(s["gateway_only"] for s in summary.values())
        total_to_update = sum(s["drift"] for s in summary.values())

        if total_to_create == 0 and total_to_update == 0:
            console.print("\n[green]Nothing to push.[/green] Gateway and Konnect are in sync.")
            raise typer.Exit(0)

        # Show preview header
        if dry_run:
            console.print("\n[bold cyan]Sync Preview (dry run)[/bold cyan]")
        else:
            console.print("\n[bold]Pushing Gateway -> Konnect[/bold]")

        # Confirmation for non-dry-run
        if not dry_run and not force:
            console.print(
                f"\nThis will create {total_to_create} and update {total_to_update} entities."
            )
            if not confirm_action("push these changes to Konnect"):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Initialize audit service
        audit_service = SyncAuditService()
        sync_id = audit_service.start_sync("push", dry_run)

        # Push each entity type
        total_created = 0
        total_updated = 0
        total_errors = 0

        for etype in entity_types_to_push:
            stats = summary.get(etype, {})
            to_create = stats.get("gateway_only", 0)
            to_update = stats.get("drift", 0)

            if to_create == 0 and to_update == 0:
                continue

            console.print(f"\n[cyan]{etype.capitalize()}:[/cyan]")
            created, updated, errors = _push_entity_type(
                etype,
                unified_service,
                konnect_managers,
                dry_run,
                audit_service=audit_service,
                sync_id=sync_id,
            )
            total_created += created
            total_updated += updated
            total_errors += errors

        # Push targets for upstreams if requested
        if include_targets and "upstreams" in entity_types_to_push:
            konnect_upstream_mgr = konnect_managers.get("upstreams")
            if konnect_upstream_mgr:
                # Get all upstream names
                upstreams = unified_service.list_upstreams()
                upstream_names = [u.identifier for u in upstreams.entities]
                if upstream_names:
                    console.print("\n[cyan]Targets:[/cyan]")
                    created, updated, errors = _push_targets_for_upstreams(
                        unified_service, upstream_names, konnect_upstream_mgr, dry_run
                    )
                    total_created += created
                    total_updated += updated
                    total_errors += errors

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        if dry_run:
            console.print(f"  Would create: {total_created} entity(s)")
            console.print(f"  Would update: {total_updated} entity(s)")
        else:
            console.print(f"  Created: {total_created} entity(s)")
            console.print(f"  Updated: {total_updated} entity(s)")
            if total_errors > 0:
                console.print(f"  [red]Errors: {total_errors}[/red]")
            else:
                console.print("\n[green]✓ Sync complete[/green]")

    @sync_app.command("pull")
    def sync_pull(
        entity_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                "-t",
                help="Entity type to pull (services, routes, consumers, plugins, upstreams)",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-n",
                help="Show what would be pulled without making changes",
            ),
        ] = False,
        with_drift: Annotated[
            bool,
            typer.Option(
                "--with-drift",
                help="Also update entities with drift (Gateway to match Konnect)",
            ),
        ] = False,
        include_targets: Annotated[
            bool,
            typer.Option(
                "--include-targets",
                help="Also sync targets when syncing upstreams",
            ),
        ] = False,
        force: ForceOption = False,
    ) -> None:
        """Pull Konnect configuration to Gateway.

        Syncs entities that are:
        - Only in Konnect (creates in Gateway)
        - Optionally: in both with drift (updates Gateway to match Konnect)

        Note: This command pulls from Konnect (control plane) to Gateway (data plane).
        Use with caution as it modifies your Gateway configuration.

        Examples:
            ops kong sync pull                     # Pull all entity types
            ops kong sync pull --type services     # Pull only services
            ops kong sync pull --dry-run           # Preview changes
            ops kong sync pull --with-drift        # Also sync drifted entities
            ops kong sync pull --force             # Skip confirmation
        """
        unified_service = get_unified_query_service()

        if unified_service is None:
            console.print(
                "[yellow]Konnect not configured.[/yellow] "
                "Configure Konnect in ops.yaml to use sync pull."
            )
            console.print("\nExample configuration:")
            console.print("[dim]konnect:[/dim]")
            console.print("[dim]  api_key: ${KONNECT_API_KEY}[/dim]")
            console.print("[dim]  default_control_plane: my-control-plane[/dim]")
            raise typer.Exit(1)

        # Determine which entity types to pull
        valid_types = [
            "services",
            "routes",
            "consumers",
            "plugins",
            "upstreams",
            "certificates",
            "snis",
            "ca_certificates",
            "key_sets",
            "keys",
            "vaults",
        ]
        if entity_type:
            if entity_type not in valid_types:
                console.print(
                    f"[red]Invalid entity type:[/red] {entity_type}\n"
                    f"Valid types: {', '.join(valid_types)}"
                )
                raise typer.Exit(1)
            entity_types_to_pull = [entity_type]
        else:
            # Process in dependency order: services first, then routes, etc.
            entity_types_to_pull = [
                "services",
                "upstreams",
                "consumers",
                "routes",
                "plugins",
                "ca_certificates",
                "certificates",
                "snis",
                "key_sets",
                "keys",
                "vaults",
            ]

        # Build Gateway managers dict
        gateway_managers: dict[str, Any] = {}
        if get_gateway_service_manager:
            gateway_managers["services"] = get_gateway_service_manager()
        if get_gateway_route_manager:
            gateway_managers["routes"] = get_gateway_route_manager()
        if get_gateway_consumer_manager:
            gateway_managers["consumers"] = get_gateway_consumer_manager()
        if get_gateway_plugin_manager:
            gateway_managers["plugins"] = get_gateway_plugin_manager()
        if get_gateway_upstream_manager:
            gateway_managers["upstreams"] = get_gateway_upstream_manager()
        if get_gateway_certificate_manager:
            gateway_managers["certificates"] = get_gateway_certificate_manager()
        if get_gateway_sni_manager:
            gateway_managers["snis"] = get_gateway_sni_manager()
        if get_gateway_ca_certificate_manager:
            gateway_managers["ca_certificates"] = get_gateway_ca_certificate_manager()
        if get_gateway_key_set_manager:
            gateway_managers["key_sets"] = get_gateway_key_set_manager()
        if get_gateway_key_manager:
            gateway_managers["keys"] = get_gateway_key_manager()
        if get_gateway_vault_manager:
            gateway_managers["vaults"] = get_gateway_vault_manager()

        if not gateway_managers:
            console.print("[yellow]No Gateway managers available.[/yellow]")
            raise typer.Exit(1)

        # Get preview of changes
        summary = unified_service.get_sync_summary(entity_types_to_pull)
        total_to_create = sum(s["konnect_only"] for s in summary.values())
        total_to_update = sum(s["drift"] for s in summary.values()) if with_drift else 0

        if total_to_create == 0 and total_to_update == 0:
            console.print("\n[green]Nothing to pull.[/green] Gateway and Konnect are in sync.")
            if not with_drift:
                drift_count = sum(s["drift"] for s in summary.values())
                if drift_count > 0:
                    console.print(
                        f"[dim]({drift_count} entities with drift - use --with-drift to sync)[/dim]"
                    )
            raise typer.Exit(0)

        # Show preview header
        if dry_run:
            console.print("\n[bold cyan]Sync Preview (dry run)[/bold cyan]")
        else:
            console.print("\n[bold]Pulling Konnect -> Gateway[/bold]")

        # Confirmation for non-dry-run
        if not dry_run and not force:
            msg = f"This will create {total_to_create}"
            if with_drift:
                msg += f" and update {total_to_update}"
            msg += " entities in Gateway."
            console.print(f"\n{msg}")
            if not confirm_action("pull these changes from Konnect"):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Initialize audit service
        audit_service = SyncAuditService()
        sync_id = audit_service.start_sync("pull", dry_run)

        # Pull each entity type
        total_created = 0
        total_updated = 0
        total_errors = 0

        for etype in entity_types_to_pull:
            stats = summary.get(etype, {})
            to_create = stats.get("konnect_only", 0)
            to_update = stats.get("drift", 0) if with_drift else 0

            if to_create == 0 and to_update == 0:
                continue

            console.print(f"\n[cyan]{etype.capitalize()}:[/cyan]")
            created, updated, errors = _pull_entity_type(
                etype,
                unified_service,
                gateway_managers,
                dry_run,
                with_drift,
                audit_service=audit_service,
                sync_id=sync_id,
            )
            total_created += created
            total_updated += updated
            total_errors += errors

        # Pull targets for upstreams if requested
        if include_targets and "upstreams" in entity_types_to_pull:
            gateway_upstream_mgr = gateway_managers.get("upstreams")
            if gateway_upstream_mgr:
                # Get all upstream names
                upstreams = unified_service.list_upstreams()
                upstream_names = [u.identifier for u in upstreams.entities]
                if upstream_names:
                    console.print("\n[cyan]Targets:[/cyan]")
                    created, updated, errors = _pull_targets_for_upstreams(
                        unified_service, upstream_names, gateway_upstream_mgr, dry_run
                    )
                    total_created += created
                    total_updated += updated
                    total_errors += errors

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        if dry_run:
            console.print(f"  Would create: {total_created} entity(s)")
            if with_drift:
                console.print(f"  Would update: {total_updated} entity(s)")
        else:
            console.print(f"  Created: {total_created} entity(s)")
            if with_drift:
                console.print(f"  Updated: {total_updated} entity(s)")
            if total_errors > 0:
                console.print(f"  [red]Errors: {total_errors}[/red]")
            else:
                console.print("\n[green]✓ Sync complete[/green]")

    @sync_app.command("history")
    def sync_history(
        sync_id: Annotated[
            str | None,
            typer.Option(
                "--sync-id",
                "-s",
                help="Show details for a specific sync operation",
            ),
        ] = None,
        entity_type: Annotated[
            str | None,
            typer.Option(
                "--entity-type",
                "-t",
                help="Filter by entity type (services, routes, etc.)",
            ),
        ] = None,
        entity_name: Annotated[
            str | None,
            typer.Option(
                "--entity-name",
                "-e",
                help="Filter by entity name (requires --entity-type)",
            ),
        ] = None,
        limit: Annotated[
            int,
            typer.Option(
                "--limit",
                "-l",
                help="Maximum number of results to show",
            ),
        ] = 20,
        since: Annotated[
            str | None,
            typer.Option(
                "--since",
                help="Show syncs since time (e.g., '7d', '24h', '2026-01-15')",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show sync operation history.

        View the history of sync operations between Gateway and Konnect.
        Each sync operation is tracked with details about what was created,
        updated, or failed.

        Examples:
            ops kong sync history                     # Recent syncs
            ops kong sync history --sync-id <id>     # Details of specific sync
            ops kong sync history --since 7d         # Last 7 days
            ops kong sync history --entity-type services --entity-name api-svc
            ops kong sync history --output json      # JSON format
        """
        from rich.table import Table

        from system_operations_manager.services.kong.sync_audit import (
            SyncAuditService,
        )

        audit_service = SyncAuditService()

        # Parse since parameter
        since_dt = None
        if since:
            try:
                since_dt = parse_since(since)
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        # Show entity history if entity_type and entity_name provided
        if entity_type and entity_name:
            entries = audit_service.get_entity_history(entity_type, entity_name, limit)

            if not entries:
                console.print(
                    f"[yellow]No sync history found for {entity_type}/{entity_name}[/yellow]"
                )
                raise typer.Exit(0)

            if output == OutputFormat.JSON:
                import json

                data = [e.model_dump() for e in entries]
                console.print(json.dumps(data, indent=2, default=str))
                raise typer.Exit(0)

            # Table output for entity history
            console.print(f"\n[bold]Sync History for {entity_type}/{entity_name}[/bold]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Timestamp")
            table.add_column("Operation")
            table.add_column("Action")
            table.add_column("Status")
            table.add_column("Details")

            for entry in entries:
                # Format timestamp
                try:
                    ts = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
                    ts_str = ts.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    ts_str = entry.timestamp[:16]

                details = ""
                if entry.drift_fields:
                    details = f"drift: {', '.join(entry.drift_fields)}"
                if entry.error:
                    details = entry.error[:40]

                status_style = {
                    "success": "green",
                    "failed": "red",
                    "would_create": "cyan",
                    "would_update": "cyan",
                }.get(entry.status, "")

                table.add_row(
                    ts_str,
                    entry.operation,
                    entry.action,
                    f"[{status_style}]{entry.status}[/{status_style}]"
                    if status_style
                    else entry.status,
                    details,
                )

            console.print(table)
            raise typer.Exit(0)

        # Show specific sync details
        if sync_id:
            entries = audit_service.get_sync_details(sync_id)

            if not entries:
                console.print(f"[yellow]No sync found with ID: {sync_id}[/yellow]")
                raise typer.Exit(1)

            if output == OutputFormat.JSON:
                import json

                data = [e.model_dump() for e in entries]
                console.print(json.dumps(data, indent=2, default=str))
                raise typer.Exit(0)

            # Table output for sync details
            first = entries[0]
            direction = "Gateway → Konnect" if first.operation == "push" else "Konnect → Gateway"

            console.print(f"\n[bold]Sync Operation: {sync_id[:12]}...[/bold]")
            console.print(f"Timestamp: {first.timestamp}")
            console.print(f"Operation: {first.operation} ({direction})")
            console.print(f"Dry Run: {'Yes' if first.dry_run else 'No'}")

            console.print("\n[bold]Operations:[/bold]")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Entity Type")
            table.add_column("Name")
            table.add_column("Action")
            table.add_column("Status")
            table.add_column("Details")

            created = updated = errors = 0
            for entry in entries:
                details = ""
                if entry.drift_fields:
                    details = f"drift: {', '.join(entry.drift_fields)}"
                if entry.error:
                    details = entry.error[:40]

                status_style = {
                    "success": "green",
                    "failed": "red",
                    "would_create": "cyan",
                    "would_update": "cyan",
                }.get(entry.status, "")

                table.add_row(
                    entry.entity_type,
                    entry.entity_name,
                    entry.action,
                    f"[{status_style}]{entry.status}[/{status_style}]"
                    if status_style
                    else entry.status,
                    details,
                )

                if entry.status in ("success", "would_create") and entry.action == "create":
                    created += 1
                elif entry.status in ("success", "would_update") and entry.action == "update":
                    updated += 1
                elif entry.status == "failed":
                    errors += 1

            console.print(table)
            console.print(
                f"\n[dim]Summary: {created} created, {updated} updated, {errors} errors[/dim]"
            )
            raise typer.Exit(0)

        # List recent syncs
        syncs: list[SyncSummary] = audit_service.list_syncs(limit=limit, since=since_dt)

        if not syncs:
            console.print("[yellow]No sync operations found.[/yellow]")
            if since:
                console.print(f"[dim](Filtered by --since {since})[/dim]")
            raise typer.Exit(0)

        if output == OutputFormat.JSON:
            import json

            data = [s.model_dump() for s in syncs]
            console.print(json.dumps(data, indent=2, default=str))
            raise typer.Exit(0)

        # Table output
        console.print("\n[bold]Recent Sync Operations[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Sync ID")
        table.add_column("Timestamp")
        table.add_column("Operation")
        table.add_column("Dry Run")
        table.add_column("Created")
        table.add_column("Updated")
        table.add_column("Errors")

        for sync in syncs:
            # Format timestamp to relative time
            try:
                ts = datetime.fromisoformat(sync.timestamp.replace("Z", "+00:00"))
                now = datetime.now(UTC)
                delta = now - ts
                if delta.days > 0:
                    ts_str = f"{delta.days}d ago"
                elif delta.seconds >= 3600:
                    ts_str = f"{delta.seconds // 3600}h ago"
                elif delta.seconds >= 60:
                    ts_str = f"{delta.seconds // 60}m ago"
                else:
                    ts_str = "just now"
            except Exception:
                ts_str = sync.timestamp[:16]

            errors_str = str(sync.errors)
            if sync.errors > 0:
                errors_str = f"[red]{sync.errors}[/red]"

            table.add_row(
                sync.sync_id[:12] + "...",
                ts_str,
                sync.operation,
                "Yes" if sync.dry_run else "No",
                str(sync.created),
                str(sync.updated),
                errors_str,
            )

        console.print(table)
        console.print("\n[dim]Use 'ops kong sync history --sync-id <id>' for details[/dim]")

    app.add_typer(sync_app, name="sync")
