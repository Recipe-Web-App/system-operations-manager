"""Unit tests for IP restriction security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.ip_restriction import (
    register_ip_restriction_commands,
)


class TestIPRestrictionCommands:
    """Tests for IP restriction CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with IP restriction commands."""
        app = typer.Typer()
        register_ip_restriction_commands(app, lambda: mock_plugin_manager)
        return app

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["ip-restriction", "enable", "--allow", "10.0.0.0/8"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_allow_or_deny(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --allow or --deny."""
        result = cli_runner.invoke(app, ["ip-restriction", "enable", "--service", "my-api"])

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
                "ip-restriction",
                "enable",
                "--service",
                "my-api",
                "--allow",
                "10.0.0.0/8",
                "--deny",
                "192.168.1.0/24",
            ],
        )

        assert result.exit_code == 1
        assert "both" in result.stdout.lower() or "cannot" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_allow_ips(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass allow list to plugin manager."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="ip-restriction",
            enabled=True,
            config={"allow": ["10.0.0.0/8"]},
        )

        result = cli_runner.invoke(
            app,
            ["ip-restriction", "enable", "--service", "my-api", "--allow", "10.0.0.0/8"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["allow"] == ["10.0.0.0/8"]

    @pytest.mark.unit
    def test_enable_with_multiple_allow_ips(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support multiple --allow flags."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="ip-restriction",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "ip-restriction",
                "enable",
                "--service",
                "my-api",
                "--allow",
                "10.0.0.0/8",
                "--allow",
                "192.168.1.0/24",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert "10.0.0.0/8" in call_kwargs[1]["config"]["allow"]
        assert "192.168.1.0/24" in call_kwargs[1]["config"]["allow"]

    @pytest.mark.unit
    def test_enable_with_deny_ips(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass deny list to plugin manager."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="ip-restriction",
            enabled=True,
            config={"deny": ["203.0.113.0/24"]},
        )

        result = cli_runner.invoke(
            app,
            ["ip-restriction", "enable", "--route", "admin-route", "--deny", "203.0.113.0/24"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["deny"] == ["203.0.113.0/24"]
        assert call_kwargs[1]["route"] == "admin-route"

    @pytest.mark.unit
    def test_enable_with_custom_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass custom status code to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="ip-restriction",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "ip-restriction",
                "enable",
                "--service",
                "my-api",
                "--deny",
                "0.0.0.0/0",
                "--status",
                "401",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["status"] == 401

    @pytest.mark.unit
    def test_enable_with_custom_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass custom message to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="ip-restriction",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "ip-restriction",
                "enable",
                "--service",
                "my-api",
                "--deny",
                "0.0.0.0/0",
                "--message",
                "Access denied from your IP",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["message"] == "Access denied from your IP"

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
            ["ip-restriction", "enable", "--service", "my-api", "--allow", "10.0.0.0/8"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
