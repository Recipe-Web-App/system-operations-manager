"""Konnect Key Managers for control plane key operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectKeySetManager:
    """Manager for Konnect Control Plane key set operations.

    Provides CRUD operations for key sets via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's KeySetManager
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
    ) -> tuple[list[KeySet], str | None]:
        """List all key sets in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of key sets to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of key sets, next offset for pagination).
        """
        return self._client.list_key_sets(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> KeySet:
        """Get a key set by name or ID.

        Args:
            name_or_id: Key set name or ID.

        Returns:
            Key set details.

        Raises:
            KonnectNotFoundError: If key set not found.
        """
        return self._client.get_key_set(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if a key set exists.

        Args:
            name_or_id: Key set name or ID.

        Returns:
            True if the key set exists, False otherwise.
        """
        try:
            self._client.get_key_set(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, key_set: KeySet) -> KeySet:
        """Create a new key set.

        Args:
            key_set: Key set to create.

        Returns:
            Created key set with ID and timestamps.
        """
        return self._client.create_key_set(self._control_plane_id, key_set)

    def update(self, name_or_id: str, key_set: KeySet) -> KeySet:
        """Update an existing key set.

        Args:
            name_or_id: Key set name or ID to update.
            key_set: Updated key set data.

        Returns:
            Updated key set.
        """
        return self._client.update_key_set(self._control_plane_id, name_or_id, key_set)

    def delete(self, name_or_id: str) -> None:
        """Delete a key set.

        Args:
            name_or_id: Key set name or ID to delete.
        """
        self._client.delete_key_set(self._control_plane_id, name_or_id)


class KonnectKeyManager:
    """Manager for Konnect Control Plane key operations.

    Provides CRUD operations for cryptographic keys via the Konnect Control
    Plane Admin API. Designed to have a similar interface to Kong's KeyManager
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
    ) -> tuple[list[Key], str | None]:
        """List all keys in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of keys to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of keys, next offset for pagination).
        """
        return self._client.list_keys(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> Key:
        """Get a key by name or ID.

        Args:
            name_or_id: Key name or ID.

        Returns:
            Key details.

        Raises:
            KonnectNotFoundError: If key not found.
        """
        return self._client.get_key(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if a key exists.

        Args:
            name_or_id: Key name or ID.

        Returns:
            True if the key exists, False otherwise.
        """
        try:
            self._client.get_key(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, key: Key) -> Key:
        """Create a new key.

        Args:
            key: Key to create.

        Returns:
            Created key with ID and timestamps.
        """
        return self._client.create_key(self._control_plane_id, key)

    def update(self, name_or_id: str, key: Key) -> Key:
        """Update an existing key.

        Args:
            name_or_id: Key name or ID to update.
            key: Updated key data.

        Returns:
            Updated key.
        """
        return self._client.update_key(self._control_plane_id, name_or_id, key)

    def delete(self, name_or_id: str) -> None:
        """Delete a key.

        Args:
            name_or_id: Key name or ID to delete.
        """
        self._client.delete_key(self._control_plane_id, name_or_id)
