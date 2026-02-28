"""Unit tests for request and response transformer commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.traffic.transformers import (
    _parse_key_value_pairs,
    register_transformer_commands,
)


class TestTransformerCommands:
    """Tests for request and response transformer CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with transformer commands."""
        app = typer.Typer()
        register_transformer_commands(app, lambda: mock_plugin_manager)
        return app


class TestRequestTransformerEnable(TestTransformerCommands):
    """Tests for request-transformer enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(
            app, ["request-transformer", "enable", "--add-header", "X-Custom:value"]
        )

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_at_least_one_transformation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without any transformation option."""
        result = cli_runner.invoke(app, ["request-transformer", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "transformation" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_add_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["headers"] == ["X-Custom:value"]

    @pytest.mark.unit
    def test_enable_with_multiple_add_headers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support multiple --add-header options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Header1:value1",
                "--add-header",
                "X-Header2:value2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        headers = call_kwargs[1]["config"]["add"]["headers"]
        assert "X-Header1:value1" in headers
        assert "X-Header2:value2" in headers

    @pytest.mark.unit
    def test_enable_with_remove_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass remove header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-header",
                "X-Internal",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["headers"] == ["X-Internal"]

    @pytest.mark.unit
    def test_enable_with_rename_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass rename header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--rename-header",
                "Authorization:X-Auth",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["rename"]["headers"] == ["Authorization:X-Auth"]

    @pytest.mark.unit
    def test_enable_with_invalid_header_format(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should reject invalid header format."""
        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "InvalidFormat",
            ],
        )

        assert result.exit_code == 1
        assert "format" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass querystring options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-querystring",
                "api_version:v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["querystring"] == ["api_version:v2"]

    @pytest.mark.unit
    def test_enable_with_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass body options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-body",
                "source:internal",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["body"] == ["source:internal"]

    @pytest.mark.unit
    def test_enable_with_mixed_operations(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support mixed add/remove/rename operations."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
                "--remove-header",
                "X-Internal",
                "--rename-header",
                "Auth:X-Auth",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["add"]["headers"] == ["X-Custom:value"]
        assert config["remove"]["headers"] == ["X-Internal"]
        assert config["rename"]["headers"] == ["Auth:X-Auth"]

    @pytest.mark.unit
    def test_enable_with_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should work with route scope."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--route",
                "my-route",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

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
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestRequestTransformerGet(TestTransformerCommands):
    """Tests for request-transformer get command."""

    @pytest.mark.unit
    def test_get_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """get should fail without --service or --route."""
        result = cli_runner.invoke(app, ["request-transformer", "get"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["request-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no request transformer" in result.stdout.lower()


class TestRequestTransformerDisable(TestTransformerCommands):
    """Tests for request-transformer disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "request-transformer",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "service-123", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestResponseTransformerEnable(TestTransformerCommands):
    """Tests for response-transformer enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(
            app, ["response-transformer", "enable", "--add-header", "X-Custom:value"]
        )

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_at_least_one_transformation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without any transformation option."""
        result = cli_runner.invoke(app, ["response-transformer", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "transformation" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_add_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Response-Time:100ms",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["headers"] == ["X-Response-Time:100ms"]

    @pytest.mark.unit
    def test_enable_with_remove_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass remove header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-header",
                "Server",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["headers"] == ["Server"]

    @pytest.mark.unit
    def test_enable_with_add_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add json to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-json",
                "api_version:v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["json"] == ["api_version:v2"]

    @pytest.mark.unit
    def test_enable_with_mixed_operations(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support mixed header and json operations."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "Cache-Control:no-cache",
                "--remove-header",
                "X-Powered-By",
                "--add-json",
                "status:success",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["add"]["headers"] == ["Cache-Control:no-cache"]
        assert config["add"]["json"] == ["status:success"]
        assert config["remove"]["headers"] == ["X-Powered-By"]


class TestResponseTransformerGet(TestTransformerCommands):
    """Tests for response-transformer get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["response-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no response transformer" in result.stdout.lower()


class TestResponseTransformerDisable(TestTransformerCommands):
    """Tests for response-transformer disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "response-transformer",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "service-123", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestParseKeyValuePairs:
    """Tests for _parse_key_value_pairs helper function."""

    @pytest.mark.unit
    def test_returns_empty_list_for_none(self) -> None:
        """_parse_key_value_pairs should return [] when items is None (line 49)."""
        result = _parse_key_value_pairs(None)

        assert result == []

    @pytest.mark.unit
    def test_returns_empty_list_for_empty_list(self) -> None:
        """_parse_key_value_pairs should return [] when items is empty (line 49)."""
        result = _parse_key_value_pairs([])

        assert result == []

    @pytest.mark.unit
    def test_raises_exit_for_invalid_format(self) -> None:
        """_parse_key_value_pairs should raise typer.Exit for items missing colon (line 57)."""
        with pytest.raises(typer.Exit):
            _parse_key_value_pairs(["BadFormat"])

    @pytest.mark.unit
    def test_returns_valid_pairs(self) -> None:
        """_parse_key_value_pairs should return valid key:value items unchanged."""
        result = _parse_key_value_pairs(["key:value", "another:pair"])

        assert result == ["key:value", "another:pair"]


class TestRequestTransformerBuildConfig:
    """Tests for _build_transformer_config paths via CLI (lines 102-139)."""

    @pytest.fixture
    def app(self, mock_plugin_manager: MagicMock) -> typer.Typer:
        """Create a test app with transformer commands."""
        app = typer.Typer()
        register_transformer_commands(app, lambda: mock_plugin_manager)
        return app

    @pytest.mark.unit
    def test_enable_with_remove_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include remove querystring in config (line 102)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-querystring",
                "debug",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["querystring"] == ["debug"]

    @pytest.mark.unit
    def test_enable_with_remove_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include remove body in config (line 104)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-body",
                "sensitive_field",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["body"] == ["sensitive_field"]

    @pytest.mark.unit
    def test_enable_with_rename_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include rename querystring in config (line 113)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--rename-querystring",
                "old_param:new_param",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["rename"]["querystring"] == ["old_param:new_param"]

    @pytest.mark.unit
    def test_enable_with_rename_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include rename body in config (line 115)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--rename-body",
                "old_field:new_field",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["rename"]["body"] == ["old_field:new_field"]

    @pytest.mark.unit
    def test_enable_with_replace_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include replace header in config (line 122)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--replace-header",
                "X-Env:prod",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["replace"]["headers"] == ["X-Env:prod"]

    @pytest.mark.unit
    def test_enable_with_replace_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include replace querystring in config (line 124)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--replace-querystring",
                "version:v3",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["replace"]["querystring"] == ["version:v3"]

    @pytest.mark.unit
    def test_enable_with_replace_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include replace body in config (lines 126, 128)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--replace-body",
                "field:new_value",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["replace"]["body"] == ["field:new_value"]

    @pytest.mark.unit
    def test_enable_with_append_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include append header in config (line 133)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--append-header",
                "X-Tag:extra",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["append"]["headers"] == ["X-Tag:extra"]

    @pytest.mark.unit
    def test_enable_with_append_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include append querystring in config (line 135)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--append-querystring",
                "trace:1",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["append"]["querystring"] == ["trace:1"]

    @pytest.mark.unit
    def test_enable_with_append_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include append body in config (lines 137, 139)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--append-body",
                "tag:extra",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["append"]["body"] == ["tag:extra"]


class TestRequestTransformerGetFound(TestTransformerCommands):
    """Tests for request-transformer get command when plugin exists (lines 359-363)."""

    @pytest.mark.unit
    def test_get_found_formats_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should call formatter when plugin is found (lines 359-360)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-42",
            "name": "request-transformer",
            "service": {"id": "svc-1", "name": "my-api"},
            "config": {"add": {"headers": ["X-Custom:value"]}},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["request-transformer", "get", "--service", "svc-1"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_found_with_route_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should display plugin data when found by route scope."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-99",
            "name": "request-transformer",
            "route": {"id": "route-7", "name": "my-route"},
            "config": {"remove": {"headers": ["X-Internal"]}},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["request-transformer", "get", "--route", "route-7"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_handles_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should handle KongAPIError gracefully (line 363)."""
        mock_plugin_manager.list.side_effect = KongAPIError("Connection refused", status_code=503)

        result = cli_runner.invoke(app, ["request-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestRequestTransformerDisableExtended(TestTransformerCommands):
    """Extended tests for request-transformer disable command (lines 386-412)."""

    @pytest.mark.unit
    def test_disable_not_found_for_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should show not-found message and exit 0 when plugin missing (lines 386-390)."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "missing-svc"],
        )

        assert result.exit_code == 0
        assert "no request transformer" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_not_found_for_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should show not-found message for route scope (lines 386-390)."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--route", "missing-route"],
        )

        assert result.exit_code == 0
        assert "no request transformer" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_missing_plugin_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should fail when plugin data has no id field (lines 394-395)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "name": "request-transformer",
            "service": {"id": "svc-1", "name": "my-api"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "svc-1", "--force"],
        )

        assert result.exit_code == 1
        assert "plugin id" in result.stdout.lower() or "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancel_on_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should abort when user declines confirmation (lines 403-404)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "request-transformer",
            "service": {"id": "svc-1", "name": "my-api"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "svc-1"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_handles_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should handle KongAPIError gracefully (lines 411-412)."""
        mock_plugin_manager.list.side_effect = KongAPIError("Upstream error", status_code=502)

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "svc-1", "--force"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestResponseTransformerEnableExtended(TestTransformerCommands):
    """Extended tests for response-transformer enable covering more config paths (lines 527-574)."""

    @pytest.mark.unit
    def test_enable_with_remove_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include remove json in config (line 527)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-json",
                "debug_field",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["json"] == ["debug_field"]

    @pytest.mark.unit
    def test_enable_with_rename_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include rename header in config (lines 534, 536)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--rename-header",
                "X-Old:X-New",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["rename"]["headers"] == ["X-Old:X-New"]

    @pytest.mark.unit
    def test_enable_with_replace_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include replace header in config (lines 541, 545)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--replace-header",
                "Content-Type:application/json",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["replace"]["headers"] == ["Content-Type:application/json"]

    @pytest.mark.unit
    def test_enable_with_replace_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include replace json in config (lines 543, 545)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--replace-json",
                "status:ok",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["replace"]["json"] == ["status:ok"]

    @pytest.mark.unit
    def test_enable_with_append_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include append header in config (lines 550, 554)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--append-header",
                "X-Powered-By:MyAPI",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["append"]["headers"] == ["X-Powered-By:MyAPI"]

    @pytest.mark.unit
    def test_enable_with_append_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should include append json in config (lines 552, 554)."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--append-json",
                "meta:extra",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["append"]["json"] == ["meta:extra"]

    @pytest.mark.unit
    def test_enable_with_route_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should work with route scope for response transformer."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--route",
                "my-route",
                "--add-header",
                "X-Route:yes",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_handles_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should handle KongAPIError gracefully (lines 573-574)."""
        mock_plugin_manager.enable.side_effect = KongAPIError("Plugin conflict", status_code=409)

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:val",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestResponseTransformerGetExtended(TestTransformerCommands):
    """Extended tests for response-transformer get command (lines 605-609)."""

    @pytest.mark.unit
    def test_get_found_formats_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should call formatter when plugin is found (lines 605-606)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-55",
            "name": "response-transformer",
            "service": {"id": "svc-55", "name": "my-api"},
            "config": {"add": {"headers": ["X-Response-Time:50ms"]}},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["response-transformer", "get", "--service", "svc-55"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_found_with_route_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should display plugin data when found by route scope."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-77",
            "name": "response-transformer",
            "route": {"id": "route-77", "name": "my-route"},
            "config": {"remove": {"headers": ["Server"]}},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["response-transformer", "get", "--route", "route-77"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_handles_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should handle KongAPIError gracefully (line 609)."""
        mock_plugin_manager.list.side_effect = KongAPIError("Gateway timeout", status_code=504)

        result = cli_runner.invoke(app, ["response-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """get should fail without --service or --route."""
        result = cli_runner.invoke(app, ["response-transformer", "get"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()


class TestResponseTransformerDisableExtended(TestTransformerCommands):
    """Extended tests for response-transformer disable command (lines 634-660)."""

    @pytest.mark.unit
    def test_disable_not_found_for_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should show not-found message and exit 0 when plugin missing (lines 634-638)."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "missing-svc"],
        )

        assert result.exit_code == 0
        assert "no response transformer" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_not_found_for_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should show not-found message for route scope (lines 634-638)."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--route", "missing-route"],
        )

        assert result.exit_code == 0
        assert "no response transformer" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_missing_plugin_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should fail when plugin data has no id field (lines 642-643)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "name": "response-transformer",
            "service": {"id": "svc-1", "name": "my-api"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "svc-1", "--force"],
        )

        assert result.exit_code == 1
        assert "plugin id" in result.stdout.lower() or "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancel_on_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should abort when user declines confirmation (lines 651-652)."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "response-transformer",
            "service": {"id": "svc-1", "name": "my-api"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "svc-1"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_handles_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should handle KongAPIError gracefully (lines 659-660)."""
        mock_plugin_manager.list.side_effect = KongAPIError("Service unavailable", status_code=503)

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "svc-1", "--force"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_route_scope_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should work with route scope and --force flag."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-rt-1",
            "name": "response-transformer",
            "route": {"id": "route-abc", "name": "my-route"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--route", "route-abc", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-rt-1")
