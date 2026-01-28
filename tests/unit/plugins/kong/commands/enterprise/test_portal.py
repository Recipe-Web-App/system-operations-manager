"""Unit tests for Kong Developer Portal commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.enterprise import DevPortalStatus
from system_operations_manager.plugins.kong.commands.enterprise.portal import (
    register_portal_commands,
)

from .conftest import create_enterprise_app


class TestPortalStatusCommand:
    """Tests for portal status command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_status_enabled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """status should display enabled portal status."""
        result = cli_runner.invoke(app, ["portal", "status"])

        assert result.exit_code == 0
        assert "Enabled" in result.output
        mock_portal_manager.get_status.assert_called_once()

    @pytest.mark.unit
    def test_status_disabled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """status should display disabled portal status."""
        mock_portal_manager.get_status.return_value = DevPortalStatus(enabled=False)

        result = cli_runner.invoke(app, ["portal", "status"])

        assert result.exit_code == 0
        assert "Disabled" in result.output


class TestPortalSpecListCommand:
    """Tests for portal spec list command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_list_specs_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should display specifications."""
        result = cli_runner.invoke(app, ["portal", "specs", "list"])

        assert result.exit_code == 0
        assert "users-api" in result.output
        mock_portal_manager.list_specs.assert_called_once()

    @pytest.mark.unit
    def test_list_specs_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should handle empty results."""
        mock_portal_manager.list_specs.return_value = ([], None)

        result = cli_runner.invoke(app, ["portal", "specs", "list"])

        assert result.exit_code == 0
        assert "No specifications published" in result.output


class TestPortalSpecGetCommand:
    """Tests for portal spec get command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_get_spec_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get should display spec details."""
        result = cli_runner.invoke(app, ["portal", "specs", "get", "specs/users.yaml"])

        assert result.exit_code == 0
        mock_portal_manager.get_spec.assert_called_once_with("specs/users.yaml")

    @pytest.mark.unit
    def test_get_spec_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get should handle not found error."""
        mock_portal_manager.get_spec.side_effect = KongNotFoundError(
            resource_type="file", resource_id="specs/nonexistent.yaml"
        )

        result = cli_runner.invoke(app, ["portal", "specs", "get", "specs/nonexistent.yaml"])

        assert result.exit_code == 1


class TestPortalSpecPublishCommand:
    """Tests for portal spec publish command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_publish_spec_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """publish should publish new spec."""
        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0")

        result = cli_runner.invoke(app, ["portal", "specs", "publish", str(spec_file)])

        assert result.exit_code == 0
        assert "published" in result.output
        mock_portal_manager.publish_spec.assert_called_once()

    @pytest.mark.unit
    def test_publish_spec_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """publish should error on missing file."""
        result = cli_runner.invoke(app, ["portal", "specs", "publish", "/nonexistent/api.yaml"])

        assert result.exit_code == 1
        assert "File not found" in result.output


class TestPortalSpecDeleteCommand:
    """Tests for portal spec delete command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_delete_spec_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(
            app, ["portal", "specs", "delete", "specs/users.yaml", "--force"]
        )

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_portal_manager.delete_spec.assert_called_once()

    @pytest.mark.unit
    def test_delete_spec_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should cancel when user declines."""
        result = cli_runner.invoke(
            app, ["portal", "specs", "delete", "specs/users.yaml"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestPortalDeveloperListCommand:
    """Tests for portal developer list command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_list_developers_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should display developers."""
        result = cli_runner.invoke(app, ["portal", "developers", "list"])

        assert result.exit_code == 0
        assert "alice@example.com" in result.output
        mock_portal_manager.list_developers.assert_called_once()

    @pytest.mark.unit
    def test_list_developers_filter_by_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should filter by status."""
        result = cli_runner.invoke(app, ["portal", "developers", "list", "--status", "pending"])

        assert result.exit_code == 0
        mock_portal_manager.list_developers.assert_called_once()


class TestPortalDeveloperApproveCommand:
    """Tests for portal developer approve command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_approve_developer_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """approve should approve pending developer."""
        result = cli_runner.invoke(app, ["portal", "developers", "approve", "bob@example.com"])

        assert result.exit_code == 0
        assert "approved" in result.output
        mock_portal_manager.approve_developer.assert_called_once_with("bob@example.com")


class TestPortalDeveloperRejectCommand:
    """Tests for portal developer reject command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_reject_developer_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """reject should skip confirmation with --force."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "reject", "bob@example.com", "--force"]
        )

        assert result.exit_code == 0
        assert "rejected" in result.output
        mock_portal_manager.reject_developer.assert_called_once()


class TestPortalDeveloperRevokeCommand:
    """Tests for portal developer revoke command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_revoke_developer_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """revoke should skip confirmation with --force."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "revoke", "alice@example.com", "--force"]
        )

        assert result.exit_code == 0
        assert "revoked" in result.output
        mock_portal_manager.revoke_developer.assert_called_once()


class TestPortalDeveloperDeleteCommand:
    """Tests for portal developer delete command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_delete_developer_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "delete", "alice@example.com", "--force"]
        )

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_portal_manager.delete_developer.assert_called_once()
