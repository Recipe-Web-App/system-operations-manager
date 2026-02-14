"""Unit tests for Kubernetes manifest validate command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.manifests import (
    register_manifest_commands,
)
from system_operations_manager.services.kubernetes.manifest_manager import (
    ValidationResult,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidateCommand:
    """Tests for the ``manifests validate`` command."""

    @pytest.fixture
    def app(self, get_manifest_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with manifest commands."""
        app = typer.Typer()
        register_manifest_commands(app, get_manifest_manager)
        return app

    def test_validate_all_valid(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """validate should succeed when all manifests are valid."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]

        result = cli_runner.invoke(app, ["manifests", "validate", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()
        mock_manifest_manager.load_manifests.assert_called_once()
        mock_manifest_manager.validate_manifests.assert_called_once()

    def test_validate_with_errors(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_fail: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """validate should exit 1 when manifests have errors."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_fail]

        result = cli_runner.invoke(app, ["manifests", "validate", str(tmp_manifest_file)])

        assert result.exit_code == 1
        assert "invalid" in result.output.lower()

    def test_validate_no_manifests(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        tmp_manifest_file: Path,
    ) -> None:
        """validate should handle empty manifest list gracefully."""
        mock_manifest_manager.load_manifests.return_value = []

        result = cli_runner.invoke(app, ["manifests", "validate", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "no manifests" in result.output.lower()

    def test_validate_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """validate should support JSON output."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]

        result = cli_runner.invoke(
            app, ["manifests", "validate", str(tmp_manifest_file), "--output", "json"]
        )

        assert result.exit_code == 0
