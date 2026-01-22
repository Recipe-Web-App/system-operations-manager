"""Konnect Upstream Manager for control plane upstream operations."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.upstream import Target, Upstream
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectUpstreamManager:
    """Manager for Konnect Control Plane upstream operations.

    Provides CRUD operations for upstreams and targets via the Konnect
    Control Plane Admin API. Designed to have a similar interface to
    Kong's UpstreamManager for consistency.

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

    # -------------------------------------------------------------------------
    # Upstream Operations
    # -------------------------------------------------------------------------

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Upstream], str | None]:
        """List all upstreams in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of upstreams to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of upstreams, next offset for pagination).
        """
        return self._client.list_upstreams(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> Upstream:
        """Get an upstream by name or ID.

        Args:
            name_or_id: Upstream name or ID.

        Returns:
            Upstream details.

        Raises:
            KonnectNotFoundError: If upstream not found.
        """
        return self._client.get_upstream(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if an upstream exists.

        Args:
            name_or_id: Upstream name or ID.

        Returns:
            True if the upstream exists, False otherwise.
        """
        try:
            self._client.get_upstream(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, upstream: Upstream) -> Upstream:
        """Create a new upstream.

        Args:
            upstream: Upstream to create.

        Returns:
            Created upstream with ID and timestamps.
        """
        return self._client.create_upstream(self._control_plane_id, upstream)

    def update(self, name_or_id: str, upstream: Upstream) -> Upstream:
        """Update an existing upstream.

        Args:
            name_or_id: Upstream name or ID to update.
            upstream: Updated upstream data.

        Returns:
            Updated upstream.
        """
        return self._client.update_upstream(self._control_plane_id, name_or_id, upstream)

    def delete(self, name_or_id: str) -> None:
        """Delete an upstream.

        Args:
            name_or_id: Upstream name or ID to delete.
        """
        self._client.delete_upstream(self._control_plane_id, name_or_id)

    # -------------------------------------------------------------------------
    # Target Operations
    # -------------------------------------------------------------------------

    def list_targets(
        self,
        upstream_name_or_id: str,
        *,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[builtins.list[Target], str | None]:
        """List all targets for an upstream.

        Args:
            upstream_name_or_id: Upstream name or ID.
            limit: Maximum number of targets to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of targets, next offset for pagination).
        """
        return self._client.list_targets(
            self._control_plane_id,
            upstream_name_or_id,
            limit=limit,
            offset=offset,
        )

    def add_target(self, upstream_name_or_id: str, target: Target) -> Target:
        """Add a target to an upstream.

        Args:
            upstream_name_or_id: Upstream name or ID.
            target: Target to add.

        Returns:
            Created target with ID and timestamps.
        """
        return self._client.create_target(self._control_plane_id, upstream_name_or_id, target)

    def delete_target(self, upstream_name_or_id: str, target_id: str) -> None:
        """Delete a target from an upstream.

        Args:
            upstream_name_or_id: Upstream name or ID.
            target_id: Target ID to delete.
        """
        self._client.delete_target(self._control_plane_id, upstream_name_or_id, target_id)
