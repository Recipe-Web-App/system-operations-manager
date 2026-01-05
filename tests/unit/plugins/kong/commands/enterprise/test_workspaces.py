"""Unit tests for Kong workspace commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.plugins.kong.commands.enterprise.workspaces import (
    register_workspace_commands,
)

from .conftest import create_enterprise_app


class TestWorkspaceListCommand:
    """Tests for workspace list command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_list_workspaces_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """list should display workspaces in table format."""
        result = cli_runner.invoke(app, ["workspaces", "list"])

        assert result.exit_code == 0
        assert "default" in result.output
        assert "production" in result.output
        mock_workspace_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_list_workspaces_with_limit(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """list should pass limit parameter."""
        result = cli_runner.invoke(app, ["workspaces", "list", "--limit", "10"])

        assert result.exit_code == 0
        mock_workspace_manager.list.assert_called_once_with(limit=10)

    @pytest.mark.unit
    def test_list_workspaces_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """list should handle empty results."""
        mock_workspace_manager.list.return_value = ([], None)

        result = cli_runner.invoke(app, ["workspaces", "list"])

        assert result.exit_code == 0
        assert "No workspaces found" in result.output

    @pytest.mark.unit
    def test_list_workspaces_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """list should output JSON when requested."""
        result = cli_runner.invoke(app, ["workspaces", "list", "--output", "json"])

        assert result.exit_code == 0


class TestWorkspaceGetCommand:
    """Tests for workspace get command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_get_workspace_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """get should display workspace details."""
        result = cli_runner.invoke(app, ["workspaces", "get", "default"])

        assert result.exit_code == 0
        assert "default" in result.output
        mock_workspace_manager.get.assert_called_once_with("default")

    @pytest.mark.unit
    def test_get_workspace_with_entity_counts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """get should display entity counts."""
        result = cli_runner.invoke(app, ["workspaces", "get", "default"])

        assert result.exit_code == 0
        mock_workspace_manager.get_entities_count.assert_called_once_with("default")

    @pytest.mark.unit
    def test_get_workspace_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """get should handle not found error."""
        mock_workspace_manager.get.side_effect = KongNotFoundError(
            resource_type="workspace", resource_id="nonexistent"
        )

        result = cli_runner.invoke(app, ["workspaces", "get", "nonexistent"])

        assert result.exit_code == 1


class TestWorkspaceCreateCommand:
    """Tests for workspace create command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_create_workspace_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """create should create workspace."""
        result = cli_runner.invoke(app, ["workspaces", "create", "staging"])

        assert result.exit_code == 0
        assert "created successfully" in result.output
        mock_workspace_manager.create_with_config.assert_called_once()

    @pytest.mark.unit
    def test_create_workspace_with_comment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """create should pass comment option."""
        result = cli_runner.invoke(
            app, ["workspaces", "create", "staging", "--comment", "Staging environment"]
        )

        assert result.exit_code == 0
        mock_workspace_manager.create_with_config.assert_called_once_with(
            "staging", comment="Staging environment", portal_enabled=False
        )

    @pytest.mark.unit
    def test_create_workspace_with_portal(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """create should enable portal when requested."""
        result = cli_runner.invoke(app, ["workspaces", "create", "staging", "--portal"])

        assert result.exit_code == 0
        mock_workspace_manager.create_with_config.assert_called_once_with(
            "staging", comment=None, portal_enabled=True
        )


class TestWorkspaceUseCommand:
    """Tests for workspace use command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_use_workspace_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """use should switch workspace context."""
        result = cli_runner.invoke(app, ["workspaces", "use", "production"])

        assert result.exit_code == 0
        assert "Switched to workspace" in result.output
        mock_workspace_manager.switch_context.assert_called_once_with("production")

    @pytest.mark.unit
    def test_use_workspace_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """use should handle not found error."""
        mock_workspace_manager.switch_context.side_effect = KongNotFoundError(
            resource_type="workspace", resource_id="nonexistent"
        )

        result = cli_runner.invoke(app, ["workspaces", "use", "nonexistent"])

        assert result.exit_code == 1


class TestWorkspaceCurrentCommand:
    """Tests for workspace current command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_current_workspace_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """current should display current workspace."""
        result = cli_runner.invoke(app, ["workspaces", "current"])

        assert result.exit_code == 0
        assert "Current workspace" in result.output
        mock_workspace_manager.get_current.assert_called_once()


class TestWorkspaceDeleteCommand:
    """Tests for workspace delete command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_delete_workspace_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(app, ["workspaces", "delete", "staging", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_workspace_manager.delete.assert_called_once_with("staging")

    @pytest.mark.unit
    def test_delete_workspace_with_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """delete should prompt for confirmation."""
        result = cli_runner.invoke(app, ["workspaces", "delete", "staging"], input="y\n")

        assert result.exit_code == 0
        mock_workspace_manager.delete.assert_called_once()

    @pytest.mark.unit
    def test_delete_workspace_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """delete should cancel when user declines."""
        result = cli_runner.invoke(app, ["workspaces", "delete", "staging"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_workspace_manager.delete.assert_not_called()


class TestWorkspaceUpdateCommand:
    """Tests for workspace update command."""

    @pytest.fixture
    def app(self, get_workspace_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with workspace commands."""
        return create_enterprise_app(register_workspace_commands, get_workspace_manager)

    @pytest.mark.unit
    def test_update_workspace_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workspace_manager: MagicMock,
    ) -> None:
        """update should update workspace."""
        result = cli_runner.invoke(
            app, ["workspaces", "update", "default", "--comment", "New description"]
        )

        assert result.exit_code == 0
        assert "updated" in result.output
        mock_workspace_manager.update.assert_called_once()
