"""Unified query service for multi-source Kong entity management.

This service queries both Kong Gateway (data plane) and Konnect (control plane)
and returns unified results with source tracking and drift detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.enterprise import Vault
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    UnifiedEntityList,
    merge_entities,
)
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream

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
        gateway_certificate_manager: Gateway CertificateManager instance (optional).
        gateway_sni_manager: Gateway SNIManager instance (optional).
        gateway_ca_certificate_manager: Gateway CACertificateManager instance (optional).
        gateway_key_set_manager: Gateway KeySetManager instance (optional).
        gateway_key_manager: Gateway KeyManager instance (optional).
        gateway_vault_manager: Gateway VaultManager instance (optional).
        konnect_service_manager: Konnect ServiceManager (None if not configured).
        konnect_route_manager: Konnect RouteManager (None if not configured).
        konnect_consumer_manager: Konnect ConsumerManager (None if not configured).
        konnect_plugin_manager: Konnect PluginManager (None if not configured).
        konnect_upstream_manager: Konnect UpstreamManager (None if not configured).
        konnect_certificate_manager: Konnect CertificateManager (None if not configured).
        konnect_sni_manager: Konnect SNIManager (None if not configured).
        konnect_ca_certificate_manager: Konnect CACertificateManager (None if not configured).
        konnect_key_set_manager: Konnect KeySetManager (None if not configured).
        konnect_key_manager: Konnect KeyManager (None if not configured).
        konnect_vault_manager: Konnect VaultManager (None if not configured).
    """

    def __init__(
        self,
        *,
        gateway_service_manager: ServiceManager,
        gateway_route_manager: RouteManager,
        gateway_consumer_manager: ConsumerManager,
        gateway_plugin_manager: KongPluginManager,
        gateway_upstream_manager: UpstreamManager,
        gateway_certificate_manager: CertificateManager | None = None,
        gateway_sni_manager: SNIManager | None = None,
        gateway_ca_certificate_manager: CACertificateManager | None = None,
        gateway_key_set_manager: KeySetManager | None = None,
        gateway_key_manager: KeyManager | None = None,
        gateway_vault_manager: VaultManager | None = None,
        konnect_service_manager: KonnectServiceManager | None = None,
        konnect_route_manager: KonnectRouteManager | None = None,
        konnect_consumer_manager: KonnectConsumerManager | None = None,
        konnect_plugin_manager: KonnectPluginManager | None = None,
        konnect_upstream_manager: KonnectUpstreamManager | None = None,
        konnect_certificate_manager: KonnectCertificateManager | None = None,
        konnect_sni_manager: KonnectSNIManager | None = None,
        konnect_ca_certificate_manager: KonnectCACertificateManager | None = None,
        konnect_key_set_manager: KonnectKeySetManager | None = None,
        konnect_key_manager: KonnectKeyManager | None = None,
        konnect_vault_manager: KonnectVaultManager | None = None,
    ) -> None:
        # Gateway managers
        self._gateway_services = gateway_service_manager
        self._gateway_routes = gateway_route_manager
        self._gateway_consumers = gateway_consumer_manager
        self._gateway_plugins = gateway_plugin_manager
        self._gateway_upstreams = gateway_upstream_manager
        self._gateway_certificates = gateway_certificate_manager
        self._gateway_snis = gateway_sni_manager
        self._gateway_ca_certificates = gateway_ca_certificate_manager
        self._gateway_key_sets = gateway_key_set_manager
        self._gateway_keys = gateway_key_manager
        self._gateway_vaults = gateway_vault_manager

        # Konnect managers (optional)
        self._konnect_services = konnect_service_manager
        self._konnect_routes = konnect_route_manager
        self._konnect_consumers = konnect_consumer_manager
        self._konnect_plugins = konnect_plugin_manager
        self._konnect_upstreams = konnect_upstream_manager
        self._konnect_certificates = konnect_certificate_manager
        self._konnect_snis = konnect_sni_manager
        self._konnect_ca_certificates = konnect_ca_certificate_manager
        self._konnect_key_sets = konnect_key_set_manager
        self._konnect_keys = konnect_key_manager
        self._konnect_vaults = konnect_vault_manager

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
    # Certificate Queries
    # -------------------------------------------------------------------------

    def list_certificates(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Certificate]:
        """List certificates from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of certificates with source information.
        """
        # Fetch from Gateway
        gateway_certs: list[Certificate] = []
        if self._gateway_certificates:
            gateway_certs = self._fetch_all_gateway_certificates(tags=tags)

        # Fetch from Konnect if configured
        konnect_certs: list[Certificate] = []
        if self._konnect_certificates:
            konnect_certs = self._fetch_all_konnect_certificates(tags=tags)

        return merge_entities(gateway_certs, konnect_certs, key_field="id")

    def _fetch_all_gateway_certificates(
        self, *, tags: list[str] | None = None
    ) -> list[Certificate]:
        """Fetch all certificates from Gateway with pagination."""
        if not self._gateway_certificates:
            return []

        certificates: list[Certificate] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_certificates.list(tags=tags, offset=offset)
            certificates.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return certificates

    def _fetch_all_konnect_certificates(
        self, *, tags: list[str] | None = None
    ) -> list[Certificate]:
        """Fetch all certificates from Konnect with pagination."""
        if not self._konnect_certificates:
            return []

        certificates: list[Certificate] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_certificates.list(tags=tags, offset=offset)
            certificates.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return certificates

    # -------------------------------------------------------------------------
    # SNI Queries
    # -------------------------------------------------------------------------

    def list_snis(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[SNI]:
        """List SNIs from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of SNIs with source information.
        """
        # Fetch from Gateway
        gateway_snis: list[SNI] = []
        if self._gateway_snis:
            gateway_snis = self._fetch_all_gateway_snis(tags=tags)

        # Fetch from Konnect if configured
        konnect_snis: list[SNI] = []
        if self._konnect_snis:
            konnect_snis = self._fetch_all_konnect_snis(tags=tags)

        return merge_entities(gateway_snis, konnect_snis, key_field="name")

    def _fetch_all_gateway_snis(self, *, tags: list[str] | None = None) -> list[SNI]:
        """Fetch all SNIs from Gateway with pagination."""
        if not self._gateway_snis:
            return []

        snis: list[SNI] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_snis.list(tags=tags, offset=offset)
            snis.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return snis

    def _fetch_all_konnect_snis(self, *, tags: list[str] | None = None) -> list[SNI]:
        """Fetch all SNIs from Konnect with pagination."""
        if not self._konnect_snis:
            return []

        snis: list[SNI] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_snis.list(tags=tags, offset=offset)
            snis.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return snis

    # -------------------------------------------------------------------------
    # CA Certificate Queries
    # -------------------------------------------------------------------------

    def list_ca_certificates(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[CACertificate]:
        """List CA certificates from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of CA certificates with source information.
        """
        # Fetch from Gateway
        gateway_ca_certs: list[CACertificate] = []
        if self._gateway_ca_certificates:
            gateway_ca_certs = self._fetch_all_gateway_ca_certificates(tags=tags)

        # Fetch from Konnect if configured
        konnect_ca_certs: list[CACertificate] = []
        if self._konnect_ca_certificates:
            konnect_ca_certs = self._fetch_all_konnect_ca_certificates(tags=tags)

        return merge_entities(gateway_ca_certs, konnect_ca_certs, key_field="id")

    def _fetch_all_gateway_ca_certificates(
        self, *, tags: list[str] | None = None
    ) -> list[CACertificate]:
        """Fetch all CA certificates from Gateway with pagination."""
        if not self._gateway_ca_certificates:
            return []

        ca_certs: list[CACertificate] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_ca_certificates.list(tags=tags, offset=offset)
            ca_certs.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return ca_certs

    def _fetch_all_konnect_ca_certificates(
        self, *, tags: list[str] | None = None
    ) -> list[CACertificate]:
        """Fetch all CA certificates from Konnect with pagination."""
        if not self._konnect_ca_certificates:
            return []

        ca_certs: list[CACertificate] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_ca_certificates.list(tags=tags, offset=offset)
            ca_certs.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return ca_certs

    # -------------------------------------------------------------------------
    # Key Set Queries
    # -------------------------------------------------------------------------

    def list_key_sets(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[KeySet]:
        """List key sets from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of key sets with source information.
        """
        # Fetch from Gateway
        gateway_key_sets: list[KeySet] = []
        if self._gateway_key_sets:
            gateway_key_sets = self._fetch_all_gateway_key_sets(tags=tags)

        # Fetch from Konnect if configured
        konnect_key_sets: list[KeySet] = []
        if self._konnect_key_sets:
            konnect_key_sets = self._fetch_all_konnect_key_sets(tags=tags)

        return merge_entities(gateway_key_sets, konnect_key_sets, key_field="name")

    def _fetch_all_gateway_key_sets(self, *, tags: list[str] | None = None) -> list[KeySet]:
        """Fetch all key sets from Gateway with pagination."""
        if not self._gateway_key_sets:
            return []

        key_sets: list[KeySet] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_key_sets.list(tags=tags, offset=offset)
            key_sets.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return key_sets

    def _fetch_all_konnect_key_sets(self, *, tags: list[str] | None = None) -> list[KeySet]:
        """Fetch all key sets from Konnect with pagination."""
        if not self._konnect_key_sets:
            return []

        key_sets: list[KeySet] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_key_sets.list(tags=tags, offset=offset)
            key_sets.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return key_sets

    # -------------------------------------------------------------------------
    # Key Queries
    # -------------------------------------------------------------------------

    def list_keys(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Key]:
        """List keys from both Gateway and Konnect.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of keys with source information.
        """
        # Fetch from Gateway
        gateway_keys: list[Key] = []
        if self._gateway_keys:
            gateway_keys = self._fetch_all_gateway_keys(tags=tags)

        # Fetch from Konnect if configured
        konnect_keys: list[Key] = []
        if self._konnect_keys:
            konnect_keys = self._fetch_all_konnect_keys(tags=tags)

        return merge_entities(gateway_keys, konnect_keys, key_field="kid")

    def _fetch_all_gateway_keys(self, *, tags: list[str] | None = None) -> list[Key]:
        """Fetch all keys from Gateway with pagination."""
        if not self._gateway_keys:
            return []

        keys: list[Key] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_keys.list(tags=tags, offset=offset)
            keys.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return keys

    def _fetch_all_konnect_keys(self, *, tags: list[str] | None = None) -> list[Key]:
        """Fetch all keys from Konnect with pagination."""
        if not self._konnect_keys:
            return []

        keys: list[Key] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_keys.list(tags=tags, offset=offset)
            keys.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return keys

    # -------------------------------------------------------------------------
    # Vault Queries
    # -------------------------------------------------------------------------

    def list_vaults(
        self,
        *,
        tags: list[str] | None = None,
    ) -> UnifiedEntityList[Vault]:
        """List vaults from both Gateway and Konnect.

        Note: Vaults are an Enterprise feature.

        Args:
            tags: Filter by tags.

        Returns:
            Unified list of vaults with source information.
        """
        # Fetch from Gateway
        gateway_vaults: list[Vault] = []
        if self._gateway_vaults:
            gateway_vaults = self._fetch_all_gateway_vaults(tags=tags)

        # Fetch from Konnect if configured
        konnect_vaults: list[Vault] = []
        if self._konnect_vaults:
            konnect_vaults = self._fetch_all_konnect_vaults(tags=tags)

        return merge_entities(gateway_vaults, konnect_vaults, key_field="name")

    def _fetch_all_gateway_vaults(self, *, tags: list[str] | None = None) -> list[Vault]:
        """Fetch all vaults from Gateway with pagination."""
        if not self._gateway_vaults:
            return []

        vaults: list[Vault] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._gateway_vaults.list(tags=tags, offset=offset)
            vaults.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return vaults

    def _fetch_all_konnect_vaults(self, *, tags: list[str] | None = None) -> list[Vault]:
        """Fetch all vaults from Konnect with pagination."""
        if not self._konnect_vaults:
            return []

        vaults: list[Vault] = []
        offset: str | None = None

        while True:
            batch, next_offset = self._konnect_vaults.list(tags=tags, offset=offset)
            vaults.extend(batch)
            if not next_offset:
                break
            offset = next_offset

        return vaults

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
            elif entity_type == "certificates":
                summary[entity_type] = extract_stats(self.list_certificates())
            elif entity_type == "snis":
                summary[entity_type] = extract_stats(self.list_snis())
            elif entity_type == "ca_certificates":
                summary[entity_type] = extract_stats(self.list_ca_certificates())
            elif entity_type == "key_sets":
                summary[entity_type] = extract_stats(self.list_key_sets())
            elif entity_type == "keys":
                summary[entity_type] = extract_stats(self.list_keys())
            elif entity_type == "vaults":
                summary[entity_type] = extract_stats(self.list_vaults())

        return summary
