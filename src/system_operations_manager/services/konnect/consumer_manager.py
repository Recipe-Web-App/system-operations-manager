"""Konnect Consumer Manager for control plane consumer operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectConsumerManager:
    """Manager for Konnect Control Plane consumer operations.

    Provides CRUD operations for consumers via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's ConsumerManager
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
    ) -> tuple[list[Consumer], str | None]:
        """List all consumers in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of consumers to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of consumers, next offset for pagination).
        """
        return self._client.list_consumers(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, username_or_id: str) -> Consumer:
        """Get a consumer by username or ID.

        Args:
            username_or_id: Consumer username or ID.

        Returns:
            Consumer details.

        Raises:
            KonnectNotFoundError: If consumer not found.
        """
        return self._client.get_consumer(self._control_plane_id, username_or_id)

    def exists(self, username_or_id: str) -> bool:
        """Check if a consumer exists.

        Args:
            username_or_id: Consumer username or ID.

        Returns:
            True if the consumer exists, False otherwise.
        """
        try:
            self._client.get_consumer(self._control_plane_id, username_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, consumer: Consumer) -> Consumer:
        """Create a new consumer.

        Args:
            consumer: Consumer to create.

        Returns:
            Created consumer with ID and timestamps.
        """
        return self._client.create_consumer(self._control_plane_id, consumer)

    def update(self, username_or_id: str, consumer: Consumer) -> Consumer:
        """Update an existing consumer.

        Args:
            username_or_id: Consumer username or ID to update.
            consumer: Updated consumer data.

        Returns:
            Updated consumer.
        """
        return self._client.update_consumer(self._control_plane_id, username_or_id, consumer)

    def delete(self, username_or_id: str) -> None:
        """Delete a consumer.

        Args:
            username_or_id: Consumer username or ID to delete.
        """
        self._client.delete_consumer(self._control_plane_id, username_or_id)
