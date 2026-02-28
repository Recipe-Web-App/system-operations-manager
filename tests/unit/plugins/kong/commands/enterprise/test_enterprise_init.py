"""Unit tests for Kong enterprise commands __init__ module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kong.commands.enterprise import (
    register_enterprise_commands,
)


class TestRegisterEnterpriseCommands:
    """Tests for register_enterprise_commands() function."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_workspace_manager(self) -> MagicMock:
        """Create a mock WorkspaceManager."""
        return MagicMock()

    @pytest.fixture
    def mock_rbac_manager(self) -> MagicMock:
        """Create a mock RBACManager."""
        return MagicMock()

    @pytest.fixture
    def mock_vault_manager(self) -> MagicMock:
        """Create a mock VaultManager."""
        return MagicMock()

    @pytest.fixture
    def mock_portal_manager(self) -> MagicMock:
        """Create a mock PortalManager."""
        return MagicMock()

    @pytest.fixture
    def app(
        self,
        mock_workspace_manager: MagicMock,
        mock_rbac_manager: MagicMock,
        mock_vault_manager: MagicMock,
        mock_portal_manager: MagicMock,
    ) -> typer.Typer:
        """Create a Typer app with enterprise commands registered."""
        root_app = typer.Typer()
        register_enterprise_commands(
            root_app,
            get_workspace_manager=lambda: mock_workspace_manager,
            get_rbac_manager=lambda: mock_rbac_manager,
            get_vault_manager=lambda: mock_vault_manager,
            get_portal_manager=lambda: mock_portal_manager,
        )
        return root_app

    @pytest.mark.unit
    def test_register_enterprise_commands_creates_enterprise_subapp(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """register_enterprise_commands should add an 'enterprise' sub-app to the root app."""
        result = cli_runner.invoke(app, ["enterprise", "--help"])

        assert result.exit_code == 0
        assert "enterprise" in result.output.lower()

    @pytest.mark.unit
    def test_register_enterprise_commands_includes_workspace_group(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """register_enterprise_commands should expose workspace commands."""
        result = cli_runner.invoke(app, ["enterprise", "--help"])

        assert result.exit_code == 0
        assert "workspace" in result.output.lower()

    @pytest.mark.unit
    def test_register_enterprise_commands_includes_rbac_group(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """register_enterprise_commands should expose rbac commands."""
        result = cli_runner.invoke(app, ["enterprise", "--help"])

        assert result.exit_code == 0
        assert "rbac" in result.output.lower()

    @pytest.mark.unit
    def test_register_enterprise_commands_includes_vaults_group(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """register_enterprise_commands should expose vault commands."""
        result = cli_runner.invoke(app, ["enterprise", "--help"])

        assert result.exit_code == 0
        assert "vault" in result.output.lower()

    @pytest.mark.unit
    def test_register_enterprise_commands_includes_portal_group(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """register_enterprise_commands should expose portal commands."""
        result = cli_runner.invoke(app, ["enterprise", "--help"])

        assert result.exit_code == 0
        assert "portal" in result.output.lower()

    @pytest.mark.unit
    def test_register_enterprise_commands_rbac_roles_accessible(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """register_enterprise_commands should wire rbac roles commands correctly."""
        mock_rbac_manager.list_roles.return_value = ([], None)

        result = cli_runner.invoke(app, ["enterprise", "rbac", "roles", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_roles.assert_called_once()

    @pytest.mark.unit
    def test_register_enterprise_commands_vaults_accessible(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """register_enterprise_commands should wire vault commands correctly."""
        mock_vault_manager.list.return_value = ([], None)

        result = cli_runner.invoke(app, ["enterprise", "vaults", "list"])

        assert result.exit_code == 0
        mock_vault_manager.list.assert_called_once()
