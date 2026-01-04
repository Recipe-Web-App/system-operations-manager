"""Unit tests for config apply command."""

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
    ApplyOperation,
    ConfigDiffSummary,
    ConfigValidationResult,
)
from system_operations_manager.plugins.kong.commands.config.apply import (
    register_apply_command,
)


class TestApplyCommand:
    """Tests for config apply command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with apply command."""
        app = typer.Typer()
        register_apply_command(app, lambda: mock_config_manager)
        return app

    def _write_config(self, path: Path, config: dict[str, Any]) -> None:
        """Write config to YAML file."""
        path.write_text(yaml.dump(config))

    @pytest.mark.unit
    def test_apply_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """apply should exit when no changes needed."""
        mock_config_manager.diff_config.return_value = ConfigDiffSummary(
            total_changes=0,
            creates={},
            updates={},
            deletes={},
            diffs=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "no changes" in result.stdout.lower() or "in sync" in result.stdout.lower()
            mock_config_manager.apply_config.assert_not_called()

    @pytest.mark.unit
    def test_apply_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply --dry-run should show changes without applying."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path), "--dry-run"])

            assert result.exit_code == 0
            assert "dry run" in result.stdout.lower()
            mock_config_manager.apply_config.assert_not_called()

    @pytest.mark.unit
    def test_apply_shows_change_summary(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply should show change summary before applying."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            # Use --no-confirm and input to skip confirmation
            result = cli_runner.invoke(
                app,
                [str(config_path), "--no-confirm"],
            )

            assert result.exit_code == 0
            assert "changes" in result.stdout.lower()

    @pytest.mark.unit
    def test_apply_with_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply should require confirmation by default."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes
        mock_config_manager.apply_config.return_value = [
            ApplyOperation(
                operation="create",
                entity_type="services",
                id_or_name="new-service",
                result="success",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            # Confirm with "y"
            result = cli_runner.invoke(
                app,
                [str(config_path)],
                input="y\n",
            )

            assert result.exit_code == 0
            mock_config_manager.apply_config.assert_called_once()

    @pytest.mark.unit
    def test_apply_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply should exit when user declines confirmation."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            # Decline with "n"
            result = cli_runner.invoke(
                app,
                [str(config_path)],
                input="n\n",
            )

            assert result.exit_code == 0
            assert "cancelled" in result.stdout.lower()
            mock_config_manager.apply_config.assert_not_called()

    @pytest.mark.unit
    def test_apply_successful(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply should report successful operations."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes
        mock_config_manager.apply_config.return_value = [
            ApplyOperation(
                operation="create",
                entity_type="services",
                id_or_name="new-service",
                result="success",
            ),
            ApplyOperation(
                operation="update",
                entity_type="routes",
                id_or_name="existing-route",
                result="success",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(
                app,
                [str(config_path), "--no-confirm"],
            )

            assert result.exit_code == 0
            assert "success" in result.stdout.lower()

    @pytest.mark.unit
    def test_apply_with_failures(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """apply should report failed operations."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes
        mock_config_manager.apply_config.return_value = [
            ApplyOperation(
                operation="create",
                entity_type="services",
                id_or_name="new-service",
                result="success",
            ),
            ApplyOperation(
                operation="update",
                entity_type="routes",
                id_or_name="existing-route",
                result="failed",
                error="Permission denied",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(
                app,
                [str(config_path), "--no-confirm"],
            )

            assert result.exit_code == 1
            assert "failed" in result.stdout.lower()
            assert "permission denied" in result.stdout.lower()

    @pytest.mark.unit
    def test_apply_validation_fails(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """apply should fail when validation fails."""
        mock_config_manager.validate_config.return_value = ConfigValidationResult(
            valid=False,
            errors=[],
            warnings=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "validation" in result.stdout.lower()

    @pytest.mark.unit
    def test_apply_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """apply should fail when file doesn't exist."""
        result = cli_runner.invoke(app, ["/nonexistent/kong.yaml"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_apply_handles_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """apply should handle KongAPIError gracefully."""
        mock_config_manager.validate_config.side_effect = KongAPIError(
            "Connection failed", status_code=500
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()
