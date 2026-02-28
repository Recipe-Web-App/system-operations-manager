"""Unit tests for Kong Plugins CLI commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.unified import (
    UnifiedEntityList,
)
from system_operations_manager.plugins.kong.commands.plugins import (
    register_plugin_commands,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(name: str = "rate-limiting", plugin_id: str = "plugin-id-123") -> MagicMock:
    m = MagicMock()
    m.name = name
    m.id = plugin_id
    return m


def _make_available_plugin(version: str = "1.0.0", priority: int = 100) -> MagicMock:
    m = MagicMock()
    m.version = version
    m.priority = priority
    m.model_dump.return_value = {"version": version, "priority": priority}
    return m


def _make_schema(fields: list[dict[str, Any]] | None = None) -> MagicMock:
    m = MagicMock()
    m.fields = [{"config": {"type": "record"}}] if fields is None else fields
    return m


# ---------------------------------------------------------------------------
# Common app fixtures
# ---------------------------------------------------------------------------


class PluginsCommandsBase:
    """Base class providing shared app fixtures."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_unified_query_service: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> typer.Typer:
        a = typer.Typer()
        register_plugin_commands(
            a,
            lambda: mock_plugin_manager,
            lambda: mock_unified_query_service,
            lambda: mock_dual_write_service,
        )
        return a

    @pytest.fixture
    def gateway_only_app(self, mock_plugin_manager: MagicMock) -> typer.Typer:
        a = typer.Typer()
        register_plugin_commands(a, lambda: mock_plugin_manager)
        return a


# ===========================================================================
# plugins list
# ===========================================================================


@pytest.mark.unit
class TestListPlugins(PluginsCommandsBase):
    """Tests for the 'plugins list' command."""

    def test_list_with_unified_query(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_plugins.return_value = unified_result

        result = cli_runner.invoke(app, ["plugins", "list"])

        assert result.exit_code == 0
        mock_unified_query_service.list_plugins.assert_called_once()

    def test_list_with_source_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_plugins.return_value = unified_result

        result = cli_runner.invoke(app, ["plugins", "list", "--source", "gateway"])

        assert result.exit_code == 0

    def test_list_with_compare(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_plugins.return_value = unified_result

        result = cli_runner.invoke(app, ["plugins", "list", "--compare"])

        assert result.exit_code == 0

    def test_list_unified_failure_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_unified_query_service.list_plugins.side_effect = RuntimeError("unavailable")
        mock_plugin_manager.list.return_value = ([_make_plugin()], None)

        result = cli_runner.invoke(app, ["plugins", "list"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once()

    def test_list_konnect_source_without_unified(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(gateway_only_app, ["plugins", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()

    def test_list_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list.return_value = ([_make_plugin()], None)

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once()

    def test_list_by_service(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_by_service.return_value = [_make_plugin()]

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list", "--service", "my-svc"])

        assert result.exit_code == 0
        mock_plugin_manager.list_by_service.assert_called_once_with("my-svc")

    def test_list_by_route(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_by_route.return_value = [_make_plugin()]

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list", "--route", "my-route"])

        assert result.exit_code == 0
        mock_plugin_manager.list_by_route.assert_called_once_with("my-route")

    def test_list_by_consumer(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_by_consumer.return_value = [_make_plugin()]

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list", "--consumer", "my-user"])

        assert result.exit_code == 0
        mock_plugin_manager.list_by_consumer.assert_called_once_with("my-user")

    def test_list_with_name_filter_gateway(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        rl = _make_plugin("rate-limiting")
        ka = _make_plugin("key-auth")
        mock_plugin_manager.list.return_value = ([rl, ka], None)

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list", "--name", "rate-limiting"])

        assert result.exit_code == 0

    def test_list_with_pagination(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list.return_value = ([_make_plugin()], "next-page")

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list"])

        assert result.exit_code == 0
        assert "next-page" in result.stdout

    def test_list_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list.side_effect = KongAPIError("fail", status_code=503)

        result = cli_runner.invoke(gateway_only_app, ["plugins", "list"])

        assert result.exit_code == 1


# ===========================================================================
# plugins available
# ===========================================================================


@pytest.mark.unit
class TestListAvailablePlugins(PluginsCommandsBase):
    """Tests for the 'plugins available' command."""

    def test_available_table_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_available.return_value = {
            "rate-limiting": _make_available_plugin("2.0.0", 901),
            "key-auth": _make_available_plugin("1.5.0", 1003),
        }

        result = cli_runner.invoke(app, ["plugins", "available"])

        assert result.exit_code == 0
        assert "2" in result.stdout  # Total count

    def test_available_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_available.return_value = {
            "rate-limiting": _make_available_plugin(),
        }

        result = cli_runner.invoke(app, ["plugins", "available", "--output", "json"])

        assert result.exit_code == 0

    def test_available_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.list_available.side_effect = KongAPIError("fail", status_code=503)

        result = cli_runner.invoke(app, ["plugins", "available"])

        assert result.exit_code == 1


# ===========================================================================
# plugins get
# ===========================================================================


@pytest.mark.unit
class TestGetPlugin(PluginsCommandsBase):
    """Tests for the 'plugins get' command."""

    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.return_value = _make_plugin()

        result = cli_runner.invoke(app, ["plugins", "get", "plugin-id-123"])

        assert result.exit_code == 0
        mock_plugin_manager.get.assert_called_once_with("plugin-id-123")

    def test_get_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["plugins", "get", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# plugins enable
# ===========================================================================


@pytest.mark.unit
class TestEnablePlugin(PluginsCommandsBase):
    """Tests for the 'plugins enable' command."""

    def test_enable_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(app, ["plugins", "enable", "key-auth", "--service", "my-svc"])

        assert result.exit_code == 0
        assert "enabled" in result.stdout.lower()

    def test_enable_with_config(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("rate-limiting")

        result = cli_runner.invoke(
            app,
            [
                "plugins",
                "enable",
                "rate-limiting",
                "--service",
                "my-svc",
                "--config",
                "minute=100",
                "--config",
                "hour=5000",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["minute"] == 100

    def test_enable_with_config_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("acl")

        result = cli_runner.invoke(
            app,
            [
                "plugins",
                "enable",
                "acl",
                "--service",
                "my-svc",
                "--config-json",
                '{"allow": ["admin"]}',
            ],
        )

        assert result.exit_code == 0

    def test_enable_invalid_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(
            app,
            ["plugins", "enable", "key-auth", "--config-json", "not-json"],
        )

        assert result.exit_code == 1

    def test_enable_data_plane_only(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(app, ["plugins", "enable", "key-auth", "--data-plane-only"])

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_enable_with_route_and_consumer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(
            app,
            [
                "plugins",
                "enable",
                "key-auth",
                "--route",
                "my-route",
                "--consumer",
                "my-user",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"
        assert call_kwargs[1]["consumer"] == "my-user"

    def test_enable_with_instance_name_and_protocols(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(
            app,
            [
                "plugins",
                "enable",
                "key-auth",
                "--instance-name",
                "my-instance",
                "--protocol",
                "http",
                "--protocol",
                "https",
            ],
        )

        assert result.exit_code == 0

    def test_enable_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.enable.side_effect = KongAPIError("bad request", status_code=400)

        result = cli_runner.invoke(app, ["plugins", "enable", "bad-plugin"])

        assert result.exit_code == 1


# ===========================================================================
# plugins update
# ===========================================================================


@pytest.mark.unit
class TestUpdatePlugin(PluginsCommandsBase):
    """Tests for the 'plugins update' command."""

    def test_update_config(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.update_config.return_value = _make_plugin("rate-limiting")

        result = cli_runner.invoke(
            app, ["plugins", "update", "plugin-123", "--config", "minute=200"]
        )

        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()
        mock_plugin_manager.update_config.assert_called_once()

    def test_update_toggle_enabled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.toggle.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(app, ["plugins", "update", "plugin-123", "--disabled"])

        assert result.exit_code == 0
        mock_plugin_manager.toggle.assert_called_once_with("plugin-123", False)

    def test_update_config_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.update_config.return_value = _make_plugin("rate-limiting")

        result = cli_runner.invoke(
            app,
            ["plugins", "update", "plugin-123", "--config-json", '{"minute": 500}'],
        )

        assert result.exit_code == 0

    def test_update_invalid_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(
            app, ["plugins", "update", "plugin-123", "--config-json", "not-json"]
        )

        assert result.exit_code == 1

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["plugins", "update", "plugin-123"])

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_update_data_plane_only(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.update_config.return_value = _make_plugin("rate-limiting")

        result = cli_runner.invoke(
            app,
            ["plugins", "update", "plugin-123", "--config", "minute=200", "--data-plane-only"],
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_update_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.update_config.side_effect = KongAPIError("fail", status_code=400)

        result = cli_runner.invoke(app, ["plugins", "update", "ghost", "--config", "minute=200"])

        assert result.exit_code == 1


# ===========================================================================
# plugins disable
# ===========================================================================


@pytest.mark.unit
class TestDisablePlugin(PluginsCommandsBase):
    """Tests for the 'plugins disable' command."""

    def test_disable_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(app, ["plugins", "disable", "plugin-123", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-123")
        assert "disabled" in result.stdout.lower()

    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(app, ["plugins", "disable", "plugin-123"], input="n\n")

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_disable_data_plane_only(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.return_value = _make_plugin("key-auth")

        result = cli_runner.invoke(
            app, ["plugins", "disable", "plugin-123", "--force", "--data-plane-only"]
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_disable_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["plugins", "disable", "ghost", "--force"])

        assert result.exit_code == 1


# ===========================================================================
# plugins schema
# ===========================================================================


@pytest.mark.unit
class TestShowPluginSchema(PluginsCommandsBase):
    """Tests for the 'plugins schema' command."""

    def test_schema_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get_schema.return_value = _make_schema()

        result = cli_runner.invoke(app, ["plugins", "schema", "rate-limiting"])

        assert result.exit_code == 0
        mock_plugin_manager.get_schema.assert_called_once_with("rate-limiting")

    def test_schema_no_fields(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get_schema.return_value = _make_schema(fields=[])

        result = cli_runner.invoke(app, ["plugins", "schema", "custom-plugin"])

        assert result.exit_code == 0
        assert "no schema" in result.stdout.lower()

    def test_schema_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        mock_plugin_manager.get_schema.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["plugins", "schema", "ghost-plugin"])

        assert result.exit_code == 1
