"""Unit tests for config generate command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.plugins.kong.commands.config.generate import (
    _configure_plugins,
    _configure_routes,
    _configure_services,
    register_generate_command,
)


class TestGenerateCommand:
    """Tests for config generate command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with generate command."""
        app = typer.Typer()
        register_generate_command(app, lambda: mock_config_manager)
        return app

    @pytest.mark.unit
    def test_generate_creates_yaml_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should create a valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            # Simulate user input for minimal config
            user_input = "\n".join(
                [
                    "my-service",  # Service name
                    "httpbin.org",  # Upstream host
                    "80",  # Port
                    "http",  # Protocol
                    "",  # No base path
                    "n",  # No custom timeouts
                    "n",  # No more services
                    "my-service-route",  # Route name
                    "/api",  # Paths
                    "n",  # No host matching
                    "n",  # No method restriction
                    "y",  # Strip path
                    "n",  # No more routes
                    "n",  # No plugins
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            assert output_path.exists()

            # Verify valid YAML
            content = yaml.safe_load(output_path.read_text())
            assert "_format_version" in content
            assert "services" in content
            assert len(content["services"]) == 1
            assert content["services"][0]["name"] == "my-service"

    @pytest.mark.unit
    def test_generate_with_multiple_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should support multiple services."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            # Simulate user input for two services
            user_input = "\n".join(
                [
                    # Service 1
                    "api-1",
                    "api1.example.com",
                    "8001",
                    "http",
                    "",
                    "n",  # No timeouts
                    "y",  # Add another service
                    # Service 2
                    "api-2",
                    "api2.example.com",
                    "8002",
                    "https",
                    "/v2",  # With base path
                    "n",  # No timeouts
                    "n",  # No more services
                    # Routes for service 1
                    "api-1-route",
                    "/v1",
                    "n",  # No host
                    "n",  # No methods
                    "y",  # Strip path
                    "n",  # No more routes
                    # Routes for service 2
                    "api-2-route",
                    "/v2",
                    "n",
                    "n",
                    "y",
                    "n",
                    # Plugins
                    "n",
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            assert len(content["services"]) == 2
            assert len(content["routes"]) == 2

    @pytest.mark.unit
    def test_generate_with_rate_limiting_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should support rate limiting plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    # Minimal service
                    "my-service",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",
                    "n",
                    # Minimal route
                    "my-route",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    # Plugins
                    "y",  # Add plugins
                    "y",  # Add rate limiting
                    "my-service",  # Apply to service
                    "100",  # Requests per minute
                    "local",  # Policy
                    "n",  # No key auth
                    "n",  # No CORS
                    "n",  # No custom headers
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            assert len(content["plugins"]) == 1
            assert content["plugins"][0]["name"] == "rate-limiting"
            assert content["plugins"][0]["config"]["minute"] == 100

    @pytest.mark.unit
    def test_generate_with_cors_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should support CORS plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    # Minimal service
                    "my-service",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",
                    "n",
                    # Minimal route
                    "my-route",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    # Plugins
                    "y",  # Add plugins
                    "n",  # No rate limiting
                    "n",  # No key auth
                    "y",  # Add CORS
                    "(global)",  # Apply globally
                    "*",  # Allow all origins
                    "n",  # No custom headers
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            assert len(content["plugins"]) == 1
            assert content["plugins"][0]["name"] == "cors"
            assert "*" in content["plugins"][0]["config"]["origins"]

    @pytest.mark.unit
    def test_generate_keyboard_interrupt(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should handle Ctrl+C gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            # Simulate Ctrl+C by providing incomplete input
            # The CLI should handle this gracefully
            result = cli_runner.invoke(
                app,
                [str(output_path)],
                input="",  # Empty input triggers EOF
            )

            # Should exit without error (exit code 0 or 1 depending on implementation)
            # File should not exist if cancelled early
            assert result.exit_code in (0, 1)

    @pytest.mark.unit
    def test_generate_shows_summary(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should show configuration summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    "my-service",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",
                    "n",
                    "my-route",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    "n",  # No plugins
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            assert "summary" in result.stdout.lower()
            assert "services" in result.stdout.lower()
            assert "routes" in result.stdout.lower()

    @pytest.mark.unit
    def test_generate_shows_next_steps(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """generate should show next steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    "my-service",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",
                    "n",
                    "my-route",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    "n",
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            assert "next steps" in result.stdout.lower()
            assert "validate" in result.stdout.lower()
            assert "apply" in result.stdout.lower()


class TestGenerateKeyboardInterrupt:
    """Tests for KeyboardInterrupt handling in config_generate (lines 108-109)."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with generate command."""
        app = typer.Typer()
        register_generate_command(app, lambda: mock_config_manager)
        return app

    @pytest.mark.unit
    def test_keyboard_interrupt_in_configure_services_exits_cleanly(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """KeyboardInterrupt during service configuration should exit with code 0."""
        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate._configure_services",
                side_effect=KeyboardInterrupt,
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            output_path = Path(tmpdir) / "kong.yaml"
            result = cli_runner.invoke(app, [str(output_path)], input="")

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_keyboard_interrupt_prints_cancellation_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """KeyboardInterrupt should print 'Generation cancelled' message."""
        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate._configure_services",
                side_effect=KeyboardInterrupt,
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            output_path = Path(tmpdir) / "kong.yaml"
            result = cli_runner.invoke(app, [str(output_path)], input="")

        assert "cancelled" in result.stdout.lower()

    @pytest.mark.unit
    def test_keyboard_interrupt_during_route_configuration(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """KeyboardInterrupt during route configuration should also exit with code 0."""
        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate._configure_services"
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate._configure_routes",
                side_effect=KeyboardInterrupt,
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            output_path = Path(tmpdir) / "kong.yaml"
            result = cli_runner.invoke(app, [str(output_path)], input="")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()


class TestConfigureServicesPathNormalization:
    """Tests for _configure_services path-prefix logic (line 158)."""

    @pytest.mark.unit
    def test_service_path_without_leading_slash_is_normalized(self) -> None:
        """A base path without a leading slash should be prefixed with '/' (line 158)."""
        config: Any = {"services": []}

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Sequence: service_name, host, protocol, path, then add-another
            mock_prompt.side_effect = ["svc", "localhost", "http", "api"]
            mock_int_prompt.return_value = 8080
            # Configure custom timeouts? -> False; Add another service? -> False
            mock_confirm.side_effect = [False, False]

            _configure_services(config)

        assert config["services"][0]["path"] == "/api"

    @pytest.mark.unit
    def test_service_path_with_leading_slash_is_unchanged(self) -> None:
        """A base path that already starts with '/' should not be double-prefixed."""
        config: Any = {"services": []}

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_prompt.side_effect = ["svc", "localhost", "http", "/already"]
            mock_int_prompt.return_value = 8080
            mock_confirm.side_effect = [False, False]

            _configure_services(config)

        assert config["services"][0]["path"] == "/already"

    @pytest.mark.unit
    def test_empty_path_is_omitted_from_service(self) -> None:
        """An empty base path response should not add a 'path' key to the service."""
        config: Any = {"services": []}

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_prompt.side_effect = ["svc", "localhost", "http", ""]
            mock_int_prompt.return_value = 8080
            mock_confirm.side_effect = [False, False]

            _configure_services(config)

        assert "path" not in config["services"][0]


class TestConfigureServicesCustomTimeouts:
    """Tests for _configure_services custom timeout block (lines 163-171)."""

    @pytest.mark.unit
    def test_custom_timeouts_are_stored_on_service(self) -> None:
        """When the user opts into custom timeouts the three fields should be recorded."""
        config: Any = {"services": []}

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Prompt sequence: service_name, host, protocol, path
            mock_prompt.side_effect = ["svc", "localhost", "http", ""]
            # IntPrompt sequence: port, connect_timeout, write_timeout, read_timeout
            mock_int_prompt.side_effect = [8080, 5000, 6000, 7000]
            # Confirm sequence: Configure custom timeouts? -> True; Add another? -> False
            mock_confirm.side_effect = [True, False]

            _configure_services(config)

        service = config["services"][0]
        assert service["connect_timeout"] == 5000
        assert service["write_timeout"] == 6000
        assert service["read_timeout"] == 7000

    @pytest.mark.unit
    def test_default_timeouts_not_set_when_declined(self) -> None:
        """When the user skips custom timeouts the timeout keys must be absent."""
        config: Any = {"services": []}

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_prompt.side_effect = ["svc", "localhost", "http", ""]
            mock_int_prompt.return_value = 8080
            mock_confirm.side_effect = [False, False]

            _configure_services(config)

        service = config["services"][0]
        assert "connect_timeout" not in service
        assert "write_timeout" not in service
        assert "read_timeout" not in service


class TestConfigureRoutesHostAndMethodMatching:
    """Tests for route host matching (lines 224-229) and method restriction (lines 233-239)."""

    def _make_config_with_service(self, name: str = "svc") -> Any:
        """Return a config dict pre-populated with one service."""
        return {
            "services": [{"name": name}],
            "routes": [],
        }

    @pytest.mark.unit
    def test_host_matching_added_to_route(self) -> None:
        """When the user enables host matching the 'hosts' key should appear on the route."""
        config: Any = self._make_config_with_service()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Prompt sequence: route_name, paths, hosts_input
            mock_prompt.side_effect = ["r1", "/api", "example.com,api.example.com"]
            # Confirm: Add host matching? -> True; Restrict methods? -> False;
            #          Strip path? -> False; Add another route? -> False
            mock_confirm.side_effect = [True, False, False, False]

            _configure_routes(config)

        assert config["routes"][0]["hosts"] == ["example.com", "api.example.com"]

    @pytest.mark.unit
    def test_empty_host_input_omits_hosts_key(self) -> None:
        """If the host input resolves to an empty list the 'hosts' key must be absent."""
        config: Any = self._make_config_with_service()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Prompt sequence: route_name, paths, hosts_input (blank → stripped to [])
            mock_prompt.side_effect = ["r1", "/api", "   "]
            # Add host matching? -> True; Restrict methods? -> False;
            # Strip path? -> False; Add another? -> False
            mock_confirm.side_effect = [True, False, False, False]

            _configure_routes(config)

        assert "hosts" not in config["routes"][0]

    @pytest.mark.unit
    def test_method_restriction_added_to_route(self) -> None:
        """When the user enables method restriction the 'methods' key should be uppercased."""
        config: Any = self._make_config_with_service()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Prompt sequence: route_name, paths, methods_input
            mock_prompt.side_effect = ["r1", "/api", "get,post"]
            # Add host matching? -> False; Restrict methods? -> True;
            # Strip path? -> False; Add another? -> False
            mock_confirm.side_effect = [False, True, False, False]

            _configure_routes(config)

        assert config["routes"][0]["methods"] == ["GET", "POST"]

    @pytest.mark.unit
    def test_empty_method_input_omits_methods_key(self) -> None:
        """If the method input resolves to an empty list the 'methods' key must be absent."""
        config: Any = self._make_config_with_service()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Prompt sequence: route_name, paths, methods_input (whitespace only)
            mock_prompt.side_effect = ["r1", "/api", "  "]
            # Add host matching? -> False; Restrict methods? -> True;
            # Strip path? -> False; Add another? -> False
            mock_confirm.side_effect = [False, True, False, False]

            _configure_routes(config)

        assert "methods" not in config["routes"][0]

    @pytest.mark.unit
    def test_route_path_without_leading_slash_is_normalised(self) -> None:
        """Paths that lack a leading '/' should be prefixed during route configuration."""
        config: Any = self._make_config_with_service()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Path provided without leading slash
            mock_prompt.side_effect = ["r1", "noslash"]
            # Add host matching? -> False; Restrict methods? -> False;
            # Strip path? -> False; Add another? -> False
            mock_confirm.side_effect = [False, False, False, False]

            _configure_routes(config)

        assert config["routes"][0]["paths"] == ["/noslash"]


class TestConfigurePluginsKeyAuth:
    """Tests for key-auth plugin section (lines 305-336)."""

    def _make_config(self, service_name: str = "svc") -> Any:
        return {
            "services": [{"name": service_name}],
            "plugins": [],
        }

    @pytest.mark.unit
    def test_key_auth_plugin_added_with_custom_key_names(self) -> None:
        """Key-auth plugin should record provided key names and hide_credentials flag."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.IntPrompt.ask"
            ) as mock_int_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Add plugins? -> True; Add rate limiting? -> False;
            # Add key auth? -> True; Add CORS? -> False; Add custom headers? -> False
            mock_confirm.side_effect = [True, False, True, False, False, False]
            # Prompt: apply-to-service, key_names_input; hide_creds via Confirm
            mock_prompt.side_effect = ["svc", "x-api-key,apikey"]
            mock_int_prompt.return_value = 100
            # Confirm index 3 is hide_creds -> True (already counted above at index 2
            # for key-auth; the sequence is: add-plugins, rate-limit, key-auth, hide-creds,
            # cors, custom-headers)
            mock_confirm.side_effect = [True, False, True, True, False, False]

            _configure_plugins(config)

        assert len(config["plugins"]) == 1
        plugin = config["plugins"][0]
        assert plugin["name"] == "key-auth"
        assert plugin["config"]["key_names"] == ["x-api-key", "apikey"]
        assert plugin["config"]["hide_credentials"] is True

    @pytest.mark.unit
    def test_key_auth_plugin_scoped_to_service(self) -> None:
        """Key-auth plugin with a specific service should include the service reference."""
        config: Any = self._make_config("my-svc")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, True, False, False, False]
            mock_prompt.side_effect = ["my-svc", "apikey"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert plugin["service"] == {"name": "my-svc"}

    @pytest.mark.unit
    def test_key_auth_plugin_global_scope_omits_service_key(self) -> None:
        """When the user selects '(global)' no 'service' key should appear on the plugin."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, True, False, False, False]
            mock_prompt.side_effect = ["(global)", "apikey"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert "service" not in plugin

    @pytest.mark.unit
    def test_key_auth_via_cli_integration(
        self,
        cli_runner: CliRunner,
        mock_config_manager: MagicMock,
    ) -> None:
        """Full CLI invocation should produce a key-auth plugin in the YAML output."""
        app = typer.Typer()
        register_generate_command(app, lambda: mock_config_manager)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    # Service
                    "my-service",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",  # No custom timeouts
                    "n",  # No more services
                    # Route
                    "my-route",
                    "/api",
                    "n",  # No host matching
                    "n",  # No method restriction
                    "y",  # Strip path
                    "n",  # No more routes
                    # Plugins
                    "y",  # Add plugins
                    "n",  # No rate limiting
                    "y",  # Add key auth
                    "my-service",  # Apply to service
                    "apikey,api-key",  # Key names
                    "y",  # Hide credentials
                    "n",  # No CORS
                    "n",  # No custom headers
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            plugin_names = [p["name"] for p in content["plugins"]]
            assert "key-auth" in plugin_names


class TestConfigurePluginsCorsNonWildcard:
    """Tests for CORS plugin with non-wildcard origins (line 355) and service scope (line 369)."""

    def _make_config(self, service_name: str = "svc") -> Any:
        return {
            "services": [{"name": service_name}],
            "plugins": [],
        }

    @pytest.mark.unit
    def test_cors_non_wildcard_origins_parsed_from_csv(self) -> None:
        """Comma-separated origins should be split into a list (line 355)."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Add plugins, rate-limit, key-auth, cors, custom-headers
            mock_confirm.side_effect = [True, False, False, True, False]
            # Prompt: service choice, origins input
            mock_prompt.side_effect = ["(global)", "https://a.example.com, https://b.example.com"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert plugin["name"] == "cors"
        assert "https://a.example.com" in plugin["config"]["origins"]
        assert "https://b.example.com" in plugin["config"]["origins"]
        assert len(plugin["config"]["origins"]) == 2

    @pytest.mark.unit
    def test_cors_plugin_scoped_to_service(self) -> None:
        """CORS plugin applied to a specific service should include the service ref (line 369)."""
        config: Any = self._make_config("api-svc")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, False, True, False]
            mock_prompt.side_effect = ["api-svc", "*"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert plugin["service"] == {"name": "api-svc"}

    @pytest.mark.unit
    def test_cors_plugin_global_omits_service_key(self) -> None:
        """CORS plugin with '(global)' scope must not carry a 'service' key."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, False, True, False]
            mock_prompt.side_effect = ["(global)", "*"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert "service" not in plugin

    @pytest.mark.unit
    def test_cors_via_cli_with_explicit_origins(
        self,
        cli_runner: CliRunner,
        mock_config_manager: MagicMock,
    ) -> None:
        """Full CLI run should persist explicit CORS origins into the YAML file."""
        app = typer.Typer()
        register_generate_command(app, lambda: mock_config_manager)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    # Service
                    "svc",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",  # No timeouts
                    "n",  # No more services
                    # Route
                    "rt",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    # Plugins
                    "y",  # Add plugins
                    "n",  # No rate limiting
                    "n",  # No key auth
                    "y",  # Add CORS
                    "svc",  # Apply to service
                    "https://front.example.com",  # Explicit origin (non-wildcard)
                    "n",  # No custom headers
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            cors_plugins = [p for p in content["plugins"] if p["name"] == "cors"]
            assert len(cors_plugins) == 1
            assert "https://front.example.com" in cors_plugins[0]["config"]["origins"]


class TestConfigurePluginsRequestTransformer:
    """Tests for request-transformer (custom headers) plugin (lines 376-409)."""

    def _make_config(self, service_name: str = "svc") -> Any:
        return {
            "services": [{"name": service_name}],
            "plugins": [],
        }

    @pytest.mark.unit
    def test_request_transformer_added_with_valid_headers(self) -> None:
        """Valid 'name:value' headers should produce a request-transformer plugin."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            # Add plugins, rate-limit, key-auth, cors, custom-headers
            mock_confirm.side_effect = [True, False, False, False, True]
            # service choice, headers input
            mock_prompt.side_effect = ["(global)", "X-Tenant-Id:acme, X-Version:2"]

            _configure_plugins(config)

        assert len(config["plugins"]) == 1
        plugin = config["plugins"][0]
        assert plugin["name"] == "request-transformer"
        assert "X-Tenant-Id:acme" in plugin["config"]["add"]["headers"]
        assert "X-Version:2" in plugin["config"]["add"]["headers"]

    @pytest.mark.unit
    def test_request_transformer_scoped_to_service(self) -> None:
        """When a specific service is chosen the plugin must reference it (line 405-406)."""
        config: Any = self._make_config("backend")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, False, False, True]
            mock_prompt.side_effect = ["backend", "X-App:v1"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert plugin["service"] == {"name": "backend"}

    @pytest.mark.unit
    def test_request_transformer_global_scope_omits_service_key(self) -> None:
        """When '(global)' is chosen no 'service' key should appear on the plugin."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, False, False, True]
            mock_prompt.side_effect = ["(global)", "X-App:v1"]

            _configure_plugins(config)

        plugin = config["plugins"][0]
        assert "service" not in plugin

    @pytest.mark.unit
    def test_request_transformer_skipped_when_no_valid_headers(self) -> None:
        """If the headers input contains no 'name:value' pairs the plugin must not be added."""
        config: Any = self._make_config()

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Prompt.ask"
            ) as mock_prompt,
            patch(
                "system_operations_manager.plugins.kong.commands.config.generate.Confirm.ask"
            ) as mock_confirm,
        ):
            mock_confirm.side_effect = [True, False, False, False, True]
            # Headers input with no colon separator -> add_headers remains []
            mock_prompt.side_effect = ["(global)", "no-colon-here"]

            _configure_plugins(config)

        assert len(config["plugins"]) == 0

    @pytest.mark.unit
    def test_request_transformer_via_cli_integration(
        self,
        cli_runner: CliRunner,
        mock_config_manager: MagicMock,
    ) -> None:
        """Full CLI invocation should persist custom headers into the YAML output."""
        app = typer.Typer()
        register_generate_command(app, lambda: mock_config_manager)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            user_input = "\n".join(
                [
                    # Service
                    "svc",
                    "localhost",
                    "8080",
                    "http",
                    "",
                    "n",  # No timeouts
                    "n",  # No more services
                    # Route
                    "rt",
                    "/api",
                    "n",
                    "n",
                    "y",
                    "n",
                    # Plugins
                    "y",  # Add plugins
                    "n",  # No rate limiting
                    "n",  # No key auth
                    "n",  # No CORS
                    "y",  # Add custom headers
                    "(global)",  # Global scope
                    "X-Request-Source:ops-cli",  # Header
                ]
            )

            result = cli_runner.invoke(app, [str(output_path)], input=user_input)

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            transformer_plugins = [
                p for p in content["plugins"] if p["name"] == "request-transformer"
            ]
            assert len(transformer_plugins) == 1
            assert "X-Request-Source:ops-cli" in transformer_plugins[0]["config"]["add"]["headers"]
