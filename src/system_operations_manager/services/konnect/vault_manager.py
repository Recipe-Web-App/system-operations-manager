"""Konnect Vault Manager for control plane vault operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.enterprise import Vault
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectVaultManager:
    """Manager for Konnect Control Plane vault operations.

    Provides CRUD operations for vaults via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's VaultManager
    for consistency.

    Note: Vaults are an Enterprise feature.

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
    ) -> tuple[list[Vault], str | None]:
        """List all vaults in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of vaults to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of vaults, next offset for pagination).
        """
        return self._client.list_vaults(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> Vault:
        """Get a vault by name, prefix, or ID.

        Args:
            name_or_id: Vault name, prefix, or ID.

        Returns:
            Vault details.

        Raises:
            KonnectNotFoundError: If vault not found.
        """
        return self._client.get_vault(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if a vault exists.

        Args:
            name_or_id: Vault name, prefix, or ID.

        Returns:
            True if the vault exists, False otherwise.
        """
        try:
            self._client.get_vault(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, vault: Vault) -> Vault:
        """Create a new vault.

        Args:
            vault: Vault to create.

        Returns:
            Created vault with ID and timestamps.
        """
        return self._client.create_vault(self._control_plane_id, vault)

    def update(self, name_or_id: str, vault: Vault) -> Vault:
        """Update an existing vault.

        Args:
            name_or_id: Vault name, prefix, or ID to update.
            vault: Updated vault data.

        Returns:
            Updated vault.
        """
        return self._client.update_vault(self._control_plane_id, name_or_id, vault)

    def delete(self, name_or_id: str) -> None:
        """Delete a vault.

        Args:
            name_or_id: Vault name, prefix, or ID to delete.
        """
        self._client.delete_vault(self._control_plane_id, name_or_id)
