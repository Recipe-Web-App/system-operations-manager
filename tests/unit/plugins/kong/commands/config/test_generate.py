"""Unit tests for config generate command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.plugins.kong.commands.config.generate import (
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
