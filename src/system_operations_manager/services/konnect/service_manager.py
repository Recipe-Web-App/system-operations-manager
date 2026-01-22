"""Konnect Service Manager for control plane service operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectServiceManager:
    """Manager for Konnect Control Plane service operations.

    Provides CRUD operations for services via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's ServiceManager
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
    ) -> tuple[list[Service], str | None]:
        """List all services in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of services to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of services, next offset for pagination).
        """
        return self._client.list_services(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> Service:
        """Get a service by name or ID.

        Args:
            name_or_id: Service name or ID.

        Returns:
            Service details.

        Raises:
            KonnectNotFoundError: If service not found.
        """
        return self._client.get_service(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if a service exists.

        Args:
            name_or_id: Service name or ID.

        Returns:
            True if the service exists, False otherwise.
        """
        try:
            self._client.get_service(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, service: Service) -> Service:
        """Create a new service.

        Args:
            service: Service to create.

        Returns:
            Created service with ID and timestamps.
        """
        return self._client.create_service(self._control_plane_id, service)

    def update(self, name_or_id: str, service: Service) -> Service:
        """Update an existing service.

        Args:
            name_or_id: Service name or ID to update.
            service: Updated service data.

        Returns:
            Updated service.
        """
        return self._client.update_service(self._control_plane_id, name_or_id, service)

    def delete(self, name_or_id: str) -> None:
        """Delete a service.

        Args:
            name_or_id: Service name or ID to delete.
        """
        self._client.delete_service(self._control_plane_id, name_or_id)
