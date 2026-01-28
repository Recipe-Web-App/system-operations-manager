"""Konnect Plugin Manager for control plane plugin operations."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectPluginManager:
    """Manager for Konnect Control Plane plugin operations.

    Provides CRUD operations for plugins via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's PluginManager
    for consistency.

    Args:
        client: Konnect API client.
        control_plane_id: Control plane ID to operate on.
    """

    def __init__(self, client: KonnectClient, control_plane_id: str) -> None:
        self._client = client
        self._control_plane_id = control_plane_id

    @property
    def control_plane_id(self) -> str:
        """Get the control plane ID."""
        return self._control_plane_id

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[KongPluginEntity], str | None]:
        """List all plugins in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of plugins to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of plugins, next offset for pagination).
        """
        return self._client.list_plugins(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def list_by_service(
        self,
        service_name_or_id: str,
        *,
        tags: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[builtins.list[KongPluginEntity], str | None]:
        """List plugins scoped to a specific service.

        Args:
            service_name_or_id: Service name or ID to filter by.
            tags: Filter by tags.
            limit: Maximum number of plugins to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of plugins, next offset for pagination).
        """
        return self._client.list_plugins(
            self._control_plane_id,
            service_name_or_id=service_name_or_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def list_by_route(
        self,
        route_name_or_id: str,
        *,
        tags: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[builtins.list[KongPluginEntity], str | None]:
        """List plugins scoped to a specific route.

        Args:
            route_name_or_id: Route name or ID to filter by.
            tags: Filter by tags.
            limit: Maximum number of plugins to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of plugins, next offset for pagination).
        """
        return self._client.list_plugins(
            self._control_plane_id,
            route_name_or_id=route_name_or_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def list_by_consumer(
        self,
        consumer_name_or_id: str,
        *,
        tags: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[builtins.list[KongPluginEntity], str | None]:
        """List plugins scoped to a specific consumer.

        Args:
            consumer_name_or_id: Consumer username or ID to filter by.
            tags: Filter by tags.
            limit: Maximum number of plugins to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of plugins, next offset for pagination).
        """
        return self._client.list_plugins(
            self._control_plane_id,
            consumer_name_or_id=consumer_name_or_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, plugin_id: str) -> KongPluginEntity:
        """Get a plugin by ID.

        Args:
            plugin_id: Plugin ID.

        Returns:
            Plugin details.

        Raises:
            KonnectNotFoundError: If plugin not found.
        """
        return self._client.get_plugin(self._control_plane_id, plugin_id)

    def exists(self, plugin_id: str) -> bool:
        """Check if a plugin exists.

        Args:
            plugin_id: Plugin ID.

        Returns:
            True if the plugin exists, False otherwise.
        """
        try:
            self._client.get_plugin(self._control_plane_id, plugin_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, plugin: KongPluginEntity) -> KongPluginEntity:
        """Create a new plugin.

        The plugin's scope (service, route, consumer) should be set on the
        plugin entity's `service`, `route`, and `consumer` fields.

        Args:
            plugin: Plugin to create.

        Returns:
            Created plugin with ID and timestamps.
        """
        return self._client.create_plugin(self._control_plane_id, plugin)

    def update(self, plugin_id: str, plugin: KongPluginEntity) -> KongPluginEntity:
        """Update an existing plugin.

        Args:
            plugin_id: Plugin ID to update.
            plugin: Updated plugin data.

        Returns:
            Updated plugin.
        """
        return self._client.update_plugin(
            self._control_plane_id,
            plugin_id,
            plugin,
        )

    def delete(self, plugin_id: str) -> None:
        """Delete a plugin.

        Args:
            plugin_id: Plugin ID to delete.
        """
        self._client.delete_plugin(self._control_plane_id, plugin_id)
