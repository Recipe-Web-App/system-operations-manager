"""Unified query service for multi-source Kong entity management.

This service queries both Kong Gateway (data plane) and Konnect (control plane)
and returns unified results with source tracking and drift detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    UnifiedEntityList,
    merge_entities,
)
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.service_manager import ServiceManager
    from system_operations_manager.services.kong.upstream_manager import UpstreamManager
    from system_operations_manager.services.konnect.consumer_manager import (
        KonnectConsumerManager,
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

logger = structlog.get_logger()


class UnifiedQueryService:
    """Service for querying entities from both Gateway and Konnect.

    This service provides a unified interface for querying Kong entities
    from both the Gateway (data plane) and Konnect (control plane). Results
    are merged and annotated with source information and drift detection.

    Args:
        gateway_service_manager: Gateway ServiceManager instance.
        gateway_route_manager: Gateway RouteManager instance.
        gateway_consumer_manager: Gateway ConsumerManager instance.
        gateway_plugin_manager: Gateway PluginManager instance.
        gateway_upstream_manager: Gateway UpstreamManager instance.
        konnect_service_manager: Konnect ServiceManager (None if not configured).
        konnect_route_manager: Konnect RouteManager (None if not configured).
        konnect_consumer_manager: Konnect ConsumerManager (None if not configured).
        konnect_plugin_manager: Konnect PluginManager (None if not configured).
        konnect_upstream_manager: Konnect UpstreamManager (None if not configured).
    """

    def __init__(
        self,
        *,
        gateway_service_manager: ServiceManager,
        gateway_route_manager: RouteManager,
        gateway_consumer_manager: ConsumerManager,
        gateway_plugin_manager: KongPluginManager,
        gateway_upstream_manager: UpstreamManager,
        konnect_service_manager: KonnectServiceManager | None = None,
        konnect_route_manager: KonnectRouteManager | None = None,
        konnect_consumer_manager: KonnectConsumerManager | None = None,
        konnect_plugin_manager: KonnectPluginManager | None = None,
        konnect_upstream_manager: KonnectUpstreamManager | None = None,
    ) -> None:
        # Gateway managers
        self._gateway_services = gateway_service_manager
        self._gateway_routes = gateway_route_manager
        self._gateway_consumers = gateway_consumer_manager
        self._gateway_plugins = gateway_plugin_manager
        self._gateway_upstreams = gateway_upstream_manager

        # Konnect managers (optional)
        self._konnect_services = konnect_service_manager
        self._konnect_routes = konnect_route_manager
        self._konnect_consumers = konnect_consumer_manager
        self._konnect_plugins = konnect_plugin_manager
        self._konnect_upstreams = konnect_upstream_manager

    @property
    def konnect_configured(self) -> bool:
        """Check if Konnect is configured."""
        return self._konnect_services is not None

    # -------------------------------------------------------------------------
    # Service Queries
    # -------------------------------------------------------------------------

    def list_services(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Service]:
        """List services from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of services with source information.
        """
        # Fetch from Gateway
        gateway_services = self._fetch_all_gateway_services(tags=tags)

        # Fetch from Konnect if configured
        konnect_services: list[Service] = []
        if self._konnect_services:
            konnect_services = self._fetch_all_konnect_services(tags=tags)

        return merge_entities(gateway_services, konnect_services, key_field="name")

    def _fetch_all_gateway_services(self, *, tags: list[str] | None = None) -> list[Service]:
        """Fetch all services from Gateway with pagination."""
        services: list[Service] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_services.list(tags=tags, offset=offset)
            services.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return services

    def _fetch_all_konnect_services(self, *, tags: list[str] | None = None) -> list[Service]:
        """Fetch all services from Konnect with pagination."""
        if not self._konnect_services:
            return []

        services: list[Service] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_services.list(tags=tags, offset=offset)
            services.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return services

    # -------------------------------------------------------------------------
    # Route Queries
    # -------------------------------------------------------------------------

    def list_routes(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
    ) -> UnifiedEntityList[Route]:
        """List routes from both Gateway and Konnect.

        Args:
            tags: Filter by tags.
            service_name_or_id: Filter by service.

        Returns:
            Unified list of routes with source information.
        """
        # Fetch from Gateway
        gateway_routes = self._fetch_all_gateway_routes(
            tags=tags, service_name_or_id=service_name_or_id
        )

        # Fetch from Konnect if configured
        konnect_routes: list[Route] = []
        if self._konnect_routes:
            konnect_routes = self._fetch_all_konnect_routes(
                tags=tags, service_name_or_id=service_name_or_id
            )

        return merge_entities(gateway_routes, konnect_routes, key_field="name")

    def _fetch_all_gateway_routes(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
    ) -> list[Route]:
        """Fetch all routes from Gateway with pagination."""
        routes: list[Route] = []
        offset: str | None = None

        while True:
            if service_name_or_id:
                batch, next_offset = self._gateway_routes.list_by_service(
                    service_name_or_id, tags=tags, offset=offset
                )
            else:
                batch, next_offset = self._gateway_routes.list(tags=tags, offset=offset)
            routes.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return routes

    def _fetch_all_konnect_routes(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
    ) -> list[Route]:
        """Fetch all routes from Konnect with pagination."""
        if not self._konnect_routes:
            return []

        routes: list[Route] = []
        offset: str | None = None

        while True:
            if service_name_or_id:
                batch, next_offset = self._konnect_routes.list_by_service(
                    service_name_or_id, tags=tags, offset=offset
                )
            else:
                batch, next_offset = self._konnect_routes.list(tags=tags, offset=offset)
            routes.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return routes

    # -------------------------------------------------------------------------
    # Consumer Queries
    # -------------------------------------------------------------------------

    def list_consumers(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Consumer]:
        """List consumers from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of consumers with source information.
        """
        # Fetch from Gateway
        gateway_consumers = self._fetch_all_gateway_consumers(tags=tags)

        # Fetch from Konnect if configured
        konnect_consumers: list[Consumer] = []
        if self._konnect_consumers:
            konnect_consumers = self._fetch_all_konnect_consumers(tags=tags)

        # Use username as key for consumers
        return merge_entities(gateway_consumers, konnect_consumers, key_field="username")

    def _fetch_all_gateway_consumers(self, *, tags: list[str] | None = None) -> list[Consumer]:
        """Fetch all consumers from Gateway with pagination."""
        consumers: list[Consumer] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_consumers.list(tags=tags, offset=offset)
            consumers.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return consumers

    def _fetch_all_konnect_consumers(self, *, tags: list[str] | None = None) -> list[Consumer]:
        """Fetch all consumers from Konnect with pagination."""
        if not self._konnect_consumers:
            return []

        consumers: list[Consumer] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_consumers.list(tags=tags, offset=offset)
            consumers.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return consumers

    # -------------------------------------------------------------------------
    # Plugin Queries
    # -------------------------------------------------------------------------

    def list_plugins(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
        route_name_or_id: str | None = None,
        consumer_name_or_id: str | None = None,
    ) -> UnifiedEntityList[KongPluginEntity]:
        """List plugins from both Gateway and Konnect.

        Args:
            tags: Filter by tags.
            service_name_or_id: Filter by service scope.
            route_name_or_id: Filter by route scope.
            consumer_name_or_id: Filter by consumer scope.

        Returns:
            Unified list of plugins with source information.
        """
        # Fetch from Gateway
        gateway_plugins = self._fetch_all_gateway_plugins(
            tags=tags,
            service_name_or_id=service_name_or_id,
            route_name_or_id=route_name_or_id,
            consumer_name_or_id=consumer_name_or_id,
        )

        # Fetch from Konnect if configured
        konnect_plugins: list[KongPluginEntity] = []
        if self._konnect_plugins:
            konnect_plugins = self._fetch_all_konnect_plugins(
                tags=tags,
                service_name_or_id=service_name_or_id,
                route_name_or_id=route_name_or_id,
                consumer_name_or_id=consumer_name_or_id,
            )

        # Use instance_name or name+scope as key for plugins
        return self._merge_plugins(gateway_plugins, konnect_plugins)

    def _fetch_all_gateway_plugins(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
        route_name_or_id: str | None = None,
        consumer_name_or_id: str | None = None,
    ) -> list[KongPluginEntity]:
        """Fetch all plugins from Gateway with pagination."""
        plugins: list[KongPluginEntity] = []
        offset: str | None = None

        while True:
            # Gateway plugin manager may have different filtering API
            batch, next_offset = self._gateway_plugins.list(tags=tags, offset=offset)
            plugins.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        # Filter by scope if specified
        if service_name_or_id:
            plugins = [
                p
                for p in plugins
                if (p.service and p.service.id == service_name_or_id)
                or (p.service and getattr(p.service, "name", None) == service_name_or_id)
            ]
        if route_name_or_id:
            plugins = [
                p
                for p in plugins
                if (p.route and p.route.id == route_name_or_id)
                or (p.route and getattr(p.route, "name", None) == route_name_or_id)
            ]
        if consumer_name_or_id:
            plugins = [
                p
                for p in plugins
                if (p.consumer and p.consumer.id == consumer_name_or_id)
                or (p.consumer and getattr(p.consumer, "name", None) == consumer_name_or_id)
            ]

        return plugins

    def _fetch_all_konnect_plugins(
        self,
        *,
        tags: list[str] | None = None,
        service_name_or_id: str | None = None,
        route_name_or_id: str | None = None,
        consumer_name_or_id: str | None = None,
    ) -> list[KongPluginEntity]:
        """Fetch all plugins from Konnect with pagination."""
        if not self._konnect_plugins:
            return []

        plugins: list[KongPluginEntity] = []
        offset: str | None = None

        # Use filtered list if scope is specified
        while True:
            if service_name_or_id:
                batch, next_offset = self._konnect_plugins.list_by_service(
                    service_name_or_id, tags=tags, offset=offset
                )
            elif route_name_or_id:
                batch, next_offset = self._konnect_plugins.list_by_route(
                    route_name_or_id, tags=tags, offset=offset
                )
            elif consumer_name_or_id:
                batch, next_offset = self._konnect_plugins.list_by_consumer(
                    consumer_name_or_id, tags=tags, offset=offset
                )
            else:
                batch, next_offset = self._konnect_plugins.list(tags=tags, offset=offset)
            plugins.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return plugins

    def _merge_plugins(
        self,
        gateway_plugins: list[KongPluginEntity],
        konnect_plugins: list[KongPluginEntity],
    ) -> UnifiedEntityList[KongPluginEntity]:
        """Merge plugins using instance_name or generated key."""

        def plugin_key(plugin: KongPluginEntity) -> str:
            """Generate a unique key for a plugin."""
            if plugin.instance_name:
                return plugin.instance_name

            # Build key from name + scope
            parts = [plugin.name]
            if plugin.service:
                parts.append(f"svc:{plugin.service.id or 'unknown'}")
            if plugin.route:
                parts.append(f"rt:{plugin.route.id or 'unknown'}")
            if plugin.consumer:
                parts.append(f"con:{plugin.consumer.id or 'unknown'}")
            return "|".join(parts)

        # Index by key
        gateway_by_key = {plugin_key(p): p for p in gateway_plugins}
        konnect_by_key = {plugin_key(p): p for p in konnect_plugins}

        # Get all unique keys
        all_keys = sorted(set(gateway_by_key.keys()) | set(konnect_by_key.keys()))

        # Create unified entries
        from system_operations_manager.integrations.kong.models.unified import (
            EntitySource,
            UnifiedEntity,
            detect_drift,
        )

        unified: list[UnifiedEntity[Any]] = []
        for key in all_keys:
            gw = gateway_by_key.get(key)
            kn = konnect_by_key.get(key)

            if gw and kn:
                has_drift, drift_fields = detect_drift(gw, kn)
                unified.append(
                    UnifiedEntity(
                        entity=gw,
                        source=EntitySource.BOTH,
                        gateway_id=gw.id,
                        konnect_id=kn.id,
                        has_drift=has_drift,
                        drift_fields=drift_fields if drift_fields else None,
                        gateway_entity=gw,
                        konnect_entity=kn,
                    )
                )
            elif gw:
                unified.append(
                    UnifiedEntity(
                        entity=gw,
                        source=EntitySource.GATEWAY,
                        gateway_id=gw.id,
                        gateway_entity=gw,
                    )
                )
            elif kn:
                unified.append(
                    UnifiedEntity(
                        entity=kn,
                        source=EntitySource.KONNECT,
                        konnect_id=kn.id,
                        konnect_entity=kn,
                    )
                )

        return UnifiedEntityList(entities=unified)

    # -------------------------------------------------------------------------
    # Upstream Queries
    # -------------------------------------------------------------------------

    def list_upstreams(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Upstream]:
        """List upstreams from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of upstreams with source information.
        """
        # Fetch from Gateway
        gateway_upstreams = self._fetch_all_gateway_upstreams(tags=tags)

        # Fetch from Konnect if configured
        konnect_upstreams: list[Upstream] = []
        if self._konnect_upstreams:
            konnect_upstreams = self._fetch_all_konnect_upstreams(tags=tags)

        return merge_entities(gateway_upstreams, konnect_upstreams, key_field="name")

    def _fetch_all_gateway_upstreams(self, *, tags: list[str] | None = None) -> list[Upstream]:
        """Fetch all upstreams from Gateway with pagination."""
        upstreams: list[Upstream] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_upstreams.list(tags=tags, offset=offset)
            upstreams.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return upstreams

    def _fetch_all_konnect_upstreams(self, *, tags: list[str] | None = None) -> list[Upstream]:
        """Fetch all upstreams from Konnect with pagination."""
        if not self._konnect_upstreams:
            return []

        upstreams: list[Upstream] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_upstreams.list(tags=tags, offset=offset)
            upstreams.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return upstreams

    def list_targets_for_upstream(
        self,
        upstream_name_or_id: str,
    ) -> UnifiedEntityList[Target]:
        """List and merge targets from Gateway and Konnect for an upstream.

        Args:
            upstream_name_or_id: Upstream name or ID.

        Returns:
            Unified list of targets with source information.
        """
        # Fetch from Gateway
        gateway_targets = self._fetch_all_gateway_targets(upstream_name_or_id)

        # Fetch from Konnect if configured
        konnect_targets: list[Target] = []
        if self._konnect_upstreams:
            konnect_targets = self._fetch_all_konnect_targets(upstream_name_or_id)

        return merge_entities(gateway_targets, konnect_targets, key_field="target")

    def _fetch_all_gateway_targets(
        self,
        upstream_name_or_id: str,
    ) -> list[Target]:
        """Fetch all targets from Gateway for an upstream with pagination."""
        targets: list[Target] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_upstreams.list_targets(
                upstream_name_or_id,
                offset=offset,
            )
            targets.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return targets

    def _fetch_all_konnect_targets(
        self,
        upstream_name_or_id: str,
    ) -> list[Target]:
        """Fetch all targets from Konnect for an upstream with pagination."""
        if not self._konnect_upstreams:
            return []

        targets: list[Target] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_upstreams.list_targets(
                upstream_name_or_id,
                offset=offset,
            )
            targets.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return targets

    # -------------------------------------------------------------------------
    # Summary Methods
    # -------------------------------------------------------------------------

    def get_sync_summary(
        self,
        entity_types: list[str] | None = None,
    ) -> dict[str, dict[str, int]]:
        """Get a summary of sync status across entity types.

        Args:
            entity_types: Entity types to check. Defaults to all types.

        Returns:
            Dict mapping entity type to sync statistics:
            {
                "services": {
                    "gateway_only": 2,
                    "konnect_only": 1,
                    "synced": 10,
                    "drift": 3,
                    "total": 16
                },
                ...
            }
        """
        if entity_types is None:
            entity_types = ["services", "routes", "consumers", "plugins", "upstreams"]

        summary: dict[str, dict[str, int]] = {}

        def extract_stats(entities: UnifiedEntityList[Any]) -> dict[str, int]:
            return {
                "gateway_only": entities.gateway_only_count,
                "konnect_only": entities.konnect_only_count,
                "synced": entities.synced_count,
                "drift": entities.drift_count,
                "total": len(entities),
            }

        for entity_type in entity_types:
            if entity_type == "services":
                summary[entity_type] = extract_stats(self.list_services())
            elif entity_type == "routes":
                summary[entity_type] = extract_stats(self.list_routes())
            elif entity_type == "consumers":
                summary[entity_type] = extract_stats(self.list_consumers())
            elif entity_type == "plugins":
                summary[entity_type] = extract_stats(self.list_plugins())
            elif entity_type == "upstreams":
                summary[entity_type] = extract_stats(self.list_upstreams())

        return summary
