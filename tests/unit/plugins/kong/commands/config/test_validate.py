"""Unit tests for config validate command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.config import (
    ConfigValidationError,
    ConfigValidationResult,
)
from system_operations_manager.plugins.kong.commands.config.validate import (
    register_validate_command,
)


class TestValidateCommand:
    """Tests for config validate command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with validate command."""
        app = typer.Typer()
        register_validate_command(app, lambda: mock_config_manager)
        return app

    def _write_config(self, path: Path, config: dict[str, Any]) -> None:
        """Write config to YAML file."""
        path.write_text(yaml.dump(config))

    @pytest.mark.unit
    def test_validate_valid_config(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """validate should succeed for valid configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "valid" in result.stdout.lower()
            mock_config_manager.validate_config.assert_called_once()

    @pytest.mark.unit
    def test_validate_shows_summary(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """validate should show entity count summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "services" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """validate should fail when file doesn't exist."""
        result = cli_runner.invoke(app, ["/nonexistent/kong.yaml"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_invalid_yaml_syntax(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """validate should fail for invalid YAML syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            config_path.write_text("invalid: yaml: syntax: [")

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "yaml" in result.stdout.lower() or "syntax" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_invalid_json_syntax(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """validate should fail for invalid JSON syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.json"
            config_path.write_text('{"invalid": json}')

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "json" in result.stdout.lower() or "syntax" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_empty_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """validate should fail for empty configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            config_path.write_text("")

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "empty" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_with_errors(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_validation_errors: ConfigValidationResult,
    ) -> None:
        """validate should display errors when config is invalid."""
        mock_config_manager.validate_config.return_value = sample_validation_errors

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()
            assert "unknown service" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_with_warnings(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """validate should display warnings."""
        mock_config_manager.validate_config.return_value = ConfigValidationResult(
            valid=True,
            errors=[],
            warnings=[
                ConfigValidationError(
                    path="plugins[0]",
                    message="Plugin has no scope - will be global",
                    entity_type="plugin",
                    entity_name="rate-limiting",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "warning" in result.stdout.lower()

    @pytest.mark.unit
    def test_validate_handles_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """validate should handle KongAPIError gracefully."""
        mock_config_manager.validate_config.side_effect = KongAPIError(
            "Connection failed", status_code=500
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()
