"""Unit tests for config diff command."""

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
    ConfigDiff,
    ConfigDiffSummary,
)
from system_operations_manager.plugins.kong.commands.config.diff import (
    register_diff_command,
)


class TestDiffCommand:
    """Tests for config diff command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with diff command."""
        app = typer.Typer()
        register_diff_command(app, lambda: mock_config_manager)
        return app

    def _write_config(self, path: Path, config: dict[str, Any]) -> None:
        """Write config to YAML file."""
        path.write_text(yaml.dump(config))

    @pytest.mark.unit
    def test_diff_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff should show message when no changes needed."""
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

    @pytest.mark.unit
    def test_diff_with_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """diff should show change summary."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "services" in result.stdout.lower()
            assert "3" in result.stdout  # total changes

    @pytest.mark.unit
    def test_diff_verbose_shows_field_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff --verbose should show field-level changes."""
        mock_config_manager.diff_config.return_value = ConfigDiffSummary(
            total_changes=1,
            creates={},
            updates={"routes": 1},
            deletes={},
            diffs=[
                ConfigDiff(
                    entity_type="routes",
                    operation="update",
                    id_or_name="test-route",
                    current={"paths": ["/old"]},
                    desired={"paths": ["/new"]},
                    changes={"paths": (["/old"], ["/new"])},
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path), "--verbose"])

            assert result.exit_code == 0
            assert "update" in result.stdout.lower()
            assert "paths" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail when file doesn't exist."""
        result = cli_runner.invoke(app, ["/nonexistent/kong.yaml"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_invalid_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail for invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            config_path.write_text("invalid: yaml: [")

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1

    @pytest.mark.unit
    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """diff --output json should produce JSON output."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path), "--output", "json"])

            assert result.exit_code == 0
            # JSON output should contain the key fields
            assert "total_changes" in result.stdout or "creates" in result.stdout

    @pytest.mark.unit
    def test_diff_handles_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff should handle KongAPIError gracefully."""
        mock_config_manager.diff_config.side_effect = KongAPIError(
            "Connection failed", status_code=500
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()
