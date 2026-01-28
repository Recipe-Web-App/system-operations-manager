"""Kong Enterprise workspace manager.

This module provides the service layer for managing Kong Enterprise workspaces,
enabling multi-tenancy through isolated configuration environments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.enterprise import Workspace
from system_operations_manager.services.kong.base import BaseEntityManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

logger = structlog.get_logger()


class WorkspaceManager(BaseEntityManager[Workspace]):
    """Manager for Kong Enterprise workspaces.

    Workspaces provide multi-tenancy by isolating Kong configurations.
    Each workspace contains its own services, routes, consumers, and plugins.

    Example:
        >>> manager = WorkspaceManager(client)
        >>> workspaces, _ = manager.list()
        >>> for ws in workspaces:
        ...     print(f"{ws.name}: {ws.comment}")
    """

    _endpoint = "workspaces"
    _entity_name = "workspace"
    _model_class = Workspace

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the workspace manager.

        Args:
            client: Kong Admin API client instance.
        """
        super().__init__(client)
        self._current_workspace: str = "default"

    @property
    def current_workspace(self) -> str:
        """Get the current workspace context."""
        return self._current_workspace

    def switch_context(self, workspace_name: str) -> Workspace:
        """Switch the current workspace context.

        This updates the client's base URL to use the specified workspace.

        Args:
            workspace_name: Name of the workspace to switch to.

        Returns:
            The workspace that was switched to.

        Raises:
            KongNotFoundError: If workspace doesn't exist.
        """
        # Verify workspace exists
        workspace = self.get(workspace_name)

        self._current_workspace = workspace_name
        self._log.info("switched_workspace", workspace=workspace_name)

        return workspace

    def get_current(self) -> Workspace:
        """Get the current workspace entity.

        Returns:
            The current workspace entity.

        Raises:
            KongNotFoundError: If current workspace doesn't exist.
        """
        return self.get(self._current_workspace)

    def get_entities_count(self, workspace_name: str) -> dict[str, int]:
        """Get count of entities in a workspace.

        Args:
            workspace_name: Name of the workspace.

        Returns:
            Dictionary with entity type counts.
        """
        meta_endpoint = f"workspaces/{workspace_name}/meta"
        try:
            response = self._client.get(meta_endpoint)
            counts = response.get("counts", {})
            return {
                "services": counts.get("services", 0),
                "routes": counts.get("routes", 0),
                "consumers": counts.get("consumers", 0),
                "plugins": counts.get("plugins", 0),
                "upstreams": counts.get("upstreams", 0),
            }
        except Exception:
            self._log.debug("workspace_meta_unavailable", workspace=workspace_name)
            return {}

    def create_with_config(
        self,
        name: str,
        comment: str | None = None,
        *,
        portal_enabled: bool = False,
    ) -> Workspace:
        """Create a workspace with configuration.

        Args:
            name: Unique workspace name.
            comment: Optional description.
            portal_enabled: Whether to enable Developer Portal.

        Returns:
            The created workspace.
        """
        from system_operations_manager.integrations.kong.models.enterprise import (
            WorkspaceConfig,
        )

        config = WorkspaceConfig(portal=portal_enabled) if portal_enabled else None
        workspace = Workspace(name=name, comment=comment, config=config)
        return self.create(workspace)
