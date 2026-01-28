"""Unit tests for ACL security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.acl import (
    register_acl_commands,
)


class TestACLCommands:
    """Tests for ACL CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with ACL commands."""
        app = typer.Typer()
        register_acl_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_consumer_manager,
        )
        return app


class TestACLEnable(TestACLCommands):
    """Tests for ACL enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["acl", "enable", "--allow", "admin"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_allow_or_deny(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --allow or --deny."""
        result = cli_runner.invoke(app, ["acl", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "allow" in result.stdout.lower() or "deny" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_rejects_both_allow_and_deny(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail when both --allow and --deny are specified."""
        result = cli_runner.invoke(
            app,
            [
                "acl",
                "enable",
                "--service",
                "my-api",
                "--allow",
                "admin",
                "--deny",
                "blocked",
            ],
        )

        assert result.exit_code == 1
        assert "both" in result.stdout.lower() or "cannot" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_allow_groups(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass allow groups to plugin manager."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="acl",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "acl",
                "enable",
                "--service",
                "my-api",
                "--allow",
                "admin",
                "--allow",
                "premium",
            ],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        allow_groups = call_kwargs[1]["config"]["allow"]
        assert "admin" in allow_groups
        assert "premium" in allow_groups

    @pytest.mark.unit
    def test_enable_with_deny_groups(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass deny groups to plugin manager."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="acl",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "acl",
                "enable",
                "--route",
                "my-route",
                "--deny",
                "blocked-users",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["deny"] == ["blocked-users"]
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_with_hide_groups_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass hide_groups_header flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="acl",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "acl",
                "enable",
                "--service",
                "my-api",
                "--allow",
                "admin",
                "--hide-groups-header",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["hide_groups_header"] is True

    @pytest.mark.unit
    def test_enable_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin configuration error",
            status_code=400,
        )

        result = cli_runner.invoke(
            app,
            ["acl", "enable", "--service", "my-api", "--allow", "admin"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestACLAddGroup(TestACLCommands):
    """Tests for ACL add-group command."""

    @pytest.mark.unit
    def test_add_group_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-group should add consumer to group."""
        result = cli_runner.invoke(
            app,
            ["acl", "add-group", "my-user", "admin-group"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.add_to_acl_group.assert_called_once_with(
            "my-user", "admin-group", None
        )

    @pytest.mark.unit
    def test_add_group_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-group should pass tags."""
        result = cli_runner.invoke(
            app,
            [
                "acl",
                "add-group",
                "my-user",
                "premium-users",
                "--tag",
                "production",
                "--tag",
                "tier1",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_to_acl_group.call_args
        tags = call_args[0][2]
        assert "production" in tags
        assert "tier1" in tags

    @pytest.mark.unit
    def test_add_group_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-group should handle KongAPIError gracefully."""
        mock_consumer_manager.add_to_acl_group.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["acl", "add-group", "nonexistent", "admin"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestACLRemoveGroup(TestACLCommands):
    """Tests for ACL remove-group command."""

    @pytest.mark.unit
    def test_remove_group_with_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """remove-group should prompt for confirmation."""
        result = cli_runner.invoke(
            app,
            ["acl", "remove-group", "my-user", "acl-123"],
            input="y\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.remove_from_acl_group.assert_called_once_with("my-user", "acl-123")

    @pytest.mark.unit
    def test_remove_group_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """remove-group should not delete when cancelled."""
        result = cli_runner.invoke(
            app,
            ["acl", "remove-group", "my-user", "acl-123"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.remove_from_acl_group.assert_not_called()

    @pytest.mark.unit
    def test_remove_group_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """remove-group --force should skip confirmation."""
        result = cli_runner.invoke(
            app,
            ["acl", "remove-group", "my-user", "acl-123", "--force"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.remove_from_acl_group.assert_called_once_with("my-user", "acl-123")

    @pytest.mark.unit
    def test_remove_group_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """remove-group should handle KongAPIError gracefully."""
        mock_consumer_manager.remove_from_acl_group.side_effect = KongAPIError(
            "ACL entry not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["acl", "remove-group", "my-user", "acl-123", "--force"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestACLListGroups(TestACLCommands):
    """Tests for ACL list-groups command."""

    @pytest.mark.unit
    def test_list_groups_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-groups should list ACL groups."""
        result = cli_runner.invoke(
            app,
            ["acl", "list-groups", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_acl_groups.assert_called_once_with("my-user")

    @pytest.mark.unit
    def test_list_groups_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-groups should support JSON output."""
        result = cli_runner.invoke(
            app,
            ["acl", "list-groups", "my-user", "--output", "json"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_list_groups_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-groups should handle KongAPIError gracefully."""
        mock_consumer_manager.list_acl_groups.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["acl", "list-groups", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
