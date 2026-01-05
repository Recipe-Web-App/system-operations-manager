"""Integration tests for WorkspaceManager (Enterprise)."""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.workspace_manager import WorkspaceManager
from tests.integration.plugins.kong.conftest import skip_enterprise

pytestmark = [
    pytest.mark.integration,
    pytest.mark.kong,
    pytest.mark.kong_enterprise,
    skip_enterprise,
]


class TestWorkspaceManagerList:
    """Test workspace listing operations."""

    def test_list_workspaces_includes_default(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """list should include default workspace."""
        workspaces, _ = workspace_manager.list()

        assert len(workspaces) >= 1
        assert any(ws.name == "default" for ws in workspaces)

    def test_list_with_pagination(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """list should support pagination."""
        workspaces, _ = workspace_manager.list(limit=10)

        assert isinstance(workspaces, list)


class TestWorkspaceManagerGet:
    """Test workspace retrieval operations."""

    def test_get_default_workspace(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """get should retrieve default workspace."""
        workspace = workspace_manager.get("default")

        # Kong GET response may not include 'name' field, verify by id presence
        assert workspace is not None
        assert workspace.id is not None

    def test_exists_returns_true_for_default(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """exists should return True for default workspace."""
        assert workspace_manager.exists("default") is True

    def test_exists_returns_false_for_nonexistent(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """exists should return False for nonexistent workspace."""
        assert workspace_manager.exists("nonexistent-workspace") is False


class TestWorkspaceManagerCount:
    """Test workspace count operations."""

    def test_count_workspaces(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """count should return at least 1 (default workspace)."""
        count = workspace_manager.count()

        assert count >= 1
