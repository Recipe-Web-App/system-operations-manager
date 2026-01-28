"""Unit tests for config export command."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.config.export import (
    register_export_command,
)


class TestExportCommand:
    """Tests for config export command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with export command."""
        app = typer.Typer()
        register_export_command(app, lambda: mock_config_manager)
        return app

    @pytest.mark.unit
    def test_export_creates_yaml_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should create a valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path)])

            assert result.exit_code == 0
            assert output_path.exists()
            mock_config_manager.export_state.assert_called_once()

            # Verify valid YAML
            content = yaml.safe_load(output_path.read_text())
            assert "_format_version" in content
            assert "services" in content

    @pytest.mark.unit
    def test_export_creates_json_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should create a valid JSON file when --format json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.json"

            result = cli_runner.invoke(app, [str(output_path), "--format", "json"])

            assert result.exit_code == 0
            assert output_path.exists()

            # Verify valid JSON
            content = json.loads(output_path.read_text())
            assert "_format_version" in content

    @pytest.mark.unit
    def test_export_auto_detects_json_extension(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should auto-detect JSON format from .json extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.json"

            result = cli_runner.invoke(app, [str(output_path)])

            assert result.exit_code == 0
            # Should be valid JSON
            content = json.loads(output_path.read_text())
            assert "_format_version" in content

    @pytest.mark.unit
    def test_export_with_only_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should pass --only filter to manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(
                app,
                [str(output_path), "--only", "services", "--only", "routes"],
            )

            assert result.exit_code == 0
            call_kwargs = mock_config_manager.export_state.call_args
            assert call_kwargs[1]["only"] == ["services", "routes"]

    @pytest.mark.unit
    def test_export_with_invalid_only_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """export should reject invalid --only values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path), "--only", "invalid-type"])

            assert result.exit_code == 1
            assert "invalid" in result.stdout.lower()

    @pytest.mark.unit
    def test_export_with_include_credentials(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should pass --include-credentials flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path), "--include-credentials"])

            assert result.exit_code == 0
            call_kwargs = mock_config_manager.export_state.call_args
            assert call_kwargs[1]["include_credentials"] is True
            assert "warning" in result.stdout.lower()

    @pytest.mark.unit
    def test_export_includes_metadata(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should include metadata in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path)])

            assert result.exit_code == 0
            content = yaml.safe_load(output_path.read_text())
            assert "_metadata" in content
            assert "exported_at" in content["_metadata"]

    @pytest.mark.unit
    def test_export_displays_summary(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should display entity count summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path)])

            assert result.exit_code == 0
            assert "services" in result.stdout.lower()
            assert "routes" in result.stdout.lower()

    @pytest.mark.unit
    def test_export_handles_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """export should handle KongAPIError gracefully."""
        mock_config_manager.export_state.side_effect = KongAPIError(
            "Connection failed", status_code=500
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "kong.yaml"

            result = cli_runner.invoke(app, [str(output_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()
