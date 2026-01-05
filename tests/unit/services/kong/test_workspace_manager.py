"""Unit tests for Kong WorkspaceManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.workspace_manager import WorkspaceManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> WorkspaceManager:
    """Create a WorkspaceManager with mocked client."""
    return WorkspaceManager(mock_client)


class TestWorkspaceManagerInit:
    """Tests for WorkspaceManager initialization."""

    @pytest.mark.unit
    def test_workspace_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = WorkspaceManager(mock_client)

        assert manager._client is mock_client
        assert manager._current_workspace == "default"


class TestWorkspaceManagerCurrentWorkspace:
    """Tests for current workspace property."""

    @pytest.mark.unit
    def test_current_workspace_default(self, manager: WorkspaceManager) -> None:
        """Current workspace should default to 'default'."""
        assert manager.current_workspace == "default"


class TestWorkspaceManagerSwitchContext:
    """Tests for switch_context method."""

    @pytest.mark.unit
    def test_switch_context_success(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """switch_context should update current workspace."""
        mock_client.get.return_value = {"id": "ws-1", "name": "production"}

        workspace = manager.switch_context("production")

        assert workspace.name == "production"
        assert manager.current_workspace == "production"

    @pytest.mark.unit
    def test_switch_context_not_found(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """switch_context should raise error for non-existent workspace."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="workspace", resource_id="nonexistent"
        )

        with pytest.raises(KongNotFoundError):
            manager.switch_context("nonexistent")

        # Current workspace should not change
        assert manager.current_workspace == "default"


class TestWorkspaceManagerGetCurrent:
    """Tests for get_current method."""

    @pytest.mark.unit
    def test_get_current_success(self, manager: WorkspaceManager, mock_client: MagicMock) -> None:
        """get_current should return current workspace entity."""
        mock_client.get.return_value = {"id": "ws-1", "name": "default"}

        workspace = manager.get_current()

        assert workspace.name == "default"
        mock_client.get.assert_called_once_with("workspaces/default")


class TestWorkspaceManagerGetEntitiesCount:
    """Tests for get_entities_count method."""

    @pytest.mark.unit
    def test_get_entities_count_success(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """get_entities_count should return entity counts."""
        mock_client.get.return_value = {
            "counts": {
                "services": 5,
                "routes": 10,
                "consumers": 3,
                "plugins": 7,
                "upstreams": 2,
            }
        }

        counts = manager.get_entities_count("production")

        assert counts["services"] == 5
        assert counts["routes"] == 10
        assert counts["consumers"] == 3
        assert counts["plugins"] == 7
        assert counts["upstreams"] == 2

    @pytest.mark.unit
    def test_get_entities_count_unavailable(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """get_entities_count should return empty dict on error."""
        mock_client.get.side_effect = Exception("Meta endpoint not available")

        counts = manager.get_entities_count("production")

        assert counts == {}


class TestWorkspaceManagerCreateWithConfig:
    """Tests for create_with_config method."""

    @pytest.mark.unit
    def test_create_with_config_basic(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """create_with_config should create workspace with basic config."""
        mock_client.post.return_value = {"id": "ws-new", "name": "staging"}

        _workspace = manager.create_with_config("staging", comment="Staging environment")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "workspaces"
        assert call_args[1]["json"]["name"] == "staging"

    @pytest.mark.unit
    def test_create_with_config_portal_enabled(
        self, manager: WorkspaceManager, mock_client: MagicMock
    ) -> None:
        """create_with_config should enable portal when requested."""
        mock_client.post.return_value = {
            "id": "ws-new",
            "name": "portal-ws",
            "config": {"portal": True},
        }

        _workspace = manager.create_with_config("portal-ws", portal_enabled=True)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["name"] == "portal-ws"


class TestWorkspaceManagerCRUD:
    """Tests for CRUD operations inherited from BaseEntityManager."""

    @pytest.mark.unit
    def test_list_workspaces(self, manager: WorkspaceManager, mock_client: MagicMock) -> None:
        """list should return workspaces."""
        mock_client.get.return_value = {
            "data": [
                {"id": "ws-1", "name": "default"},
                {"id": "ws-2", "name": "production"},
            ]
        }

        workspaces, _offset = manager.list()

        assert len(workspaces) == 2
        assert workspaces[0].name == "default"

    @pytest.mark.unit
    def test_get_workspace(self, manager: WorkspaceManager, mock_client: MagicMock) -> None:
        """get should return workspace by name."""
        mock_client.get.return_value = {"id": "ws-1", "name": "production"}

        workspace = manager.get("production")

        assert workspace.name == "production"

    @pytest.mark.unit
    def test_delete_workspace(self, manager: WorkspaceManager, mock_client: MagicMock) -> None:
        """delete should remove workspace."""
        manager.delete("staging")

        mock_client.delete.assert_called_once_with("workspaces/staging")

    @pytest.mark.unit
    def test_update_workspace(self, manager: WorkspaceManager, mock_client: MagicMock) -> None:
        """update should modify workspace."""
        from system_operations_manager.integrations.kong.models.enterprise import (
            Workspace,
        )

        mock_client.patch.return_value = {
            "id": "ws-1",
            "name": "staging",
            "comment": "Updated comment",
        }

        updated = manager.update("staging", Workspace(name="staging", comment="Updated comment"))

        assert updated.comment == "Updated comment"
