"""Unit tests for Kong Developer Portal commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError, KongNotFoundError
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


class TestPortalStatusCommandErrors:
    """Tests for KongAPIError handling in portal status command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_status_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """status should handle KongAPIError gracefully."""
        mock_portal_manager.get_status.side_effect = KongAPIError(
            "Portal service unavailable", status_code=503
        )

        result = cli_runner.invoke(app, ["portal", "status"])

        assert result.exit_code == 1


class TestPortalSpecListCommandErrors:
    """Tests for KongAPIError handling in portal specs list command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_list_specs_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should handle KongAPIError gracefully."""
        mock_portal_manager.list_specs.side_effect = KongAPIError(
            "Failed to list specs", status_code=500
        )

        result = cli_runner.invoke(app, ["portal", "specs", "list"])

        assert result.exit_code == 1


class TestPortalSpecGetCommandContents:
    """Tests for spec get command contents display branch."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_get_spec_with_contents_short(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get --contents should display spec contents when shorter than 2000 chars."""
        spec_mock: Any = MagicMock()
        spec_mock.name = "users-api"
        spec_mock.contents = "openapi: 3.0.0\ninfo:\n  title: Users API"
        spec_mock.model_dump.return_value = {
            "name": "users-api",
            "path": "specs/users.yaml",
            "contents": spec_mock.contents,
        }
        mock_portal_manager.get_spec.return_value = spec_mock

        result = cli_runner.invoke(
            app, ["portal", "specs", "get", "specs/users.yaml", "--contents"]
        )

        assert result.exit_code == 0
        assert "Contents" in result.output
        assert "openapi: 3.0.0" in result.output

    @pytest.mark.unit
    def test_get_spec_with_contents_truncated(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get --contents should truncate contents longer than 2000 chars."""
        long_contents = "x" * 2500
        spec_mock: Any = MagicMock()
        spec_mock.name = "users-api"
        spec_mock.contents = long_contents
        spec_mock.model_dump.return_value = {
            "name": "users-api",
            "path": "specs/users.yaml",
            "contents": long_contents,
        }
        mock_portal_manager.get_spec.return_value = spec_mock

        result = cli_runner.invoke(
            app, ["portal", "specs", "get", "specs/users.yaml", "--contents"]
        )

        assert result.exit_code == 0
        assert "truncated" in result.output

    @pytest.mark.unit
    def test_get_spec_without_contents_flag(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get without --contents should not display spec contents section."""
        result = cli_runner.invoke(app, ["portal", "specs", "get", "specs/users.yaml"])

        assert result.exit_code == 0
        assert "Contents" not in result.output


class TestPortalSpecPublishCommandErrors:
    """Tests for KongAPIError handling in portal specs publish command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_publish_spec_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """publish should handle KongAPIError gracefully."""
        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0")
        mock_portal_manager.publish_spec.side_effect = KongAPIError(
            "Failed to publish spec", status_code=422
        )

        result = cli_runner.invoke(app, ["portal", "specs", "publish", str(spec_file)])

        assert result.exit_code == 1


class TestPortalSpecUpdateCommand:
    """Tests for portal specs update command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_update_spec_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """update should error when spec file does not exist."""
        result = cli_runner.invoke(
            app,
            ["portal", "specs", "update", "specs/users.yaml", "/nonexistent/api.yaml"],
        )

        assert result.exit_code == 1
        assert "File not found" in result.output

    @pytest.mark.unit
    def test_update_spec_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """update should update an existing specification."""
        spec_file = tmp_path / "users.yaml"
        spec_file.write_text("openapi: 3.0.0\ninfo:\n  title: Updated Users API")

        result = cli_runner.invoke(
            app, ["portal", "specs", "update", "specs/users.yaml", str(spec_file)]
        )

        assert result.exit_code == 0
        assert "updated" in result.output
        mock_portal_manager.update_spec.assert_called_once_with(
            "specs/users.yaml", "openapi: 3.0.0\ninfo:\n  title: Updated Users API"
        )

    @pytest.mark.unit
    def test_update_spec_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """update should handle KongAPIError gracefully."""
        spec_file = tmp_path / "users.yaml"
        spec_file.write_text("openapi: 3.0.0")
        mock_portal_manager.update_spec.side_effect = KongAPIError(
            "Spec not found", status_code=404
        )

        result = cli_runner.invoke(
            app, ["portal", "specs", "update", "specs/users.yaml", str(spec_file)]
        )

        assert result.exit_code == 1


class TestPortalSpecDeleteCommandErrors:
    """Tests for KongAPIError handling in portal specs delete command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_delete_spec_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should handle KongAPIError gracefully."""
        mock_portal_manager.delete_spec.side_effect = KongAPIError(
            "Failed to delete spec", status_code=500
        )

        result = cli_runner.invoke(
            app, ["portal", "specs", "delete", "specs/users.yaml", "--force"]
        )

        assert result.exit_code == 1


class TestPortalDeveloperListCommandErrors:
    """Tests for empty result and KongAPIError handling in developer list command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_list_developers_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should display no-developers message when result is empty."""
        mock_portal_manager.list_developers.return_value = ([], None)

        result = cli_runner.invoke(app, ["portal", "developers", "list"])

        assert result.exit_code == 0
        assert "No developers found" in result.output

    @pytest.mark.unit
    def test_list_developers_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """list should handle KongAPIError gracefully."""
        mock_portal_manager.list_developers.side_effect = KongAPIError(
            "Failed to list developers", status_code=500
        )

        result = cli_runner.invoke(app, ["portal", "developers", "list"])

        assert result.exit_code == 1


class TestPortalDeveloperGetCommand:
    """Tests for portal developer get command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_get_developer_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get should display developer details."""
        result = cli_runner.invoke(app, ["portal", "developers", "get", "alice@example.com"])

        assert result.exit_code == 0
        mock_portal_manager.get_developer.assert_called_once_with("alice@example.com")

    @pytest.mark.unit
    def test_get_developer_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """get should handle KongAPIError when developer does not exist."""
        mock_portal_manager.get_developer.side_effect = KongAPIError(
            "Developer not found", status_code=404
        )

        result = cli_runner.invoke(app, ["portal", "developers", "get", "unknown@example.com"])

        assert result.exit_code == 1


class TestPortalDeveloperApproveCommandErrors:
    """Tests for KongAPIError handling in developer approve command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_approve_developer_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """approve should handle KongAPIError gracefully."""
        mock_portal_manager.approve_developer.side_effect = KongAPIError(
            "Developer not found", status_code=404
        )

        result = cli_runner.invoke(app, ["portal", "developers", "approve", "unknown@example.com"])

        assert result.exit_code == 1


class TestPortalDeveloperRejectCommandExtended:
    """Tests for cancel path and KongAPIError in developer reject command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_reject_developer_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """reject should cancel when user declines confirmation."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "reject", "bob@example.com"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_portal_manager.reject_developer.assert_not_called()

    @pytest.mark.unit
    def test_reject_developer_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """reject should handle KongAPIError gracefully."""
        mock_portal_manager.reject_developer.side_effect = KongAPIError(
            "Developer not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["portal", "developers", "reject", "unknown@example.com", "--force"],
        )

        assert result.exit_code == 1


class TestPortalDeveloperRevokeCommandExtended:
    """Tests for cancel path and KongAPIError in developer revoke command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_revoke_developer_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """revoke should cancel when user declines confirmation."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "revoke", "alice@example.com"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_portal_manager.revoke_developer.assert_not_called()

    @pytest.mark.unit
    def test_revoke_developer_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """revoke should handle KongAPIError gracefully."""
        mock_portal_manager.revoke_developer.side_effect = KongAPIError(
            "Developer not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["portal", "developers", "revoke", "unknown@example.com", "--force"],
        )

        assert result.exit_code == 1


class TestPortalDeveloperDeleteCommandExtended:
    """Tests for cancel path and KongAPIError in developer delete command."""

    @pytest.fixture
    def app(self, get_portal_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with portal commands."""
        return create_enterprise_app(register_portal_commands, get_portal_manager)

    @pytest.mark.unit
    def test_delete_developer_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should cancel when user declines confirmation."""
        result = cli_runner.invoke(
            app, ["portal", "developers", "delete", "alice@example.com"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_portal_manager.delete_developer.assert_not_called()

    @pytest.mark.unit
    def test_delete_developer_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_portal_manager: MagicMock,
    ) -> None:
        """delete should handle KongAPIError gracefully."""
        mock_portal_manager.delete_developer.side_effect = KongAPIError(
            "Developer not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["portal", "developers", "delete", "unknown@example.com", "--force"],
        )

        assert result.exit_code == 1
