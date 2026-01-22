"""Konnect Route Manager for control plane route operations."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectRouteManager:
    """Manager for Konnect Control Plane route operations.

    Provides CRUD operations for routes via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's RouteManager
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
    ) -> tuple[list[Route], str | None]:
        """List all routes in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of routes to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of routes, next offset for pagination).
        """
        return self._client.list_routes(
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
    ) -> tuple[builtins.list[Route], str | None]:
        """List routes for a specific service.

        Args:
            service_name_or_id: Service name or ID to filter by.
            tags: Filter by tags.
            limit: Maximum number of routes to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of routes, next offset for pagination).
        """
        return self._client.list_routes(
            self._control_plane_id,
            service_name_or_id=service_name_or_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, route_id_or_name: str) -> Route:
        """Get a route by name or ID.

        Args:
            route_id_or_name: Route name or ID.

        Returns:
            Route details.

        Raises:
            KonnectNotFoundError: If route not found.
        """
        return self._client.get_route(self._control_plane_id, route_id_or_name)

    def exists(self, route_id_or_name: str) -> bool:
        """Check if a route exists.

        Args:
            route_id_or_name: Route name or ID.

        Returns:
            True if the route exists, False otherwise.
        """
        try:
            self._client.get_route(self._control_plane_id, route_id_or_name)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, route: Route, service_name_or_id: str | None = None) -> Route:
        """Create a new route.

        Args:
            route: Route to create.
            service_name_or_id: Service to attach route to (optional).

        Returns:
            Created route with ID and timestamps.
        """
        return self._client.create_route(
            self._control_plane_id,
            route,
            service_name_or_id=service_name_or_id,
        )

    def update(self, route_id_or_name: str, route: Route) -> Route:
        """Update an existing route.

        Args:
            route_id_or_name: Route name or ID to update.
            route: Updated route data.

        Returns:
            Updated route.
        """
        return self._client.update_route(
            self._control_plane_id,
            route_id_or_name,
            route,
        )

    def delete(self, route_id_or_name: str) -> None:
        """Delete a route.

        Args:
            route_id_or_name: Route name or ID to delete.
        """
        self._client.delete_route(self._control_plane_id, route_id_or_name)
