"""Unit tests for Kubernetes manifest diff command."""

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
from system_operations_manager.services.kubernetes.manifest_manager import DiffResult


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDiffCommand:
    """Tests for the ``manifests diff`` command."""

    @pytest.fixture
    def app(self, get_manifest_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with manifest commands."""
        app = typer.Typer()
        register_manifest_commands(app, get_manifest_manager)
        return app

    def test_diff_identical(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_diff_identical: DiffResult,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should show identical when no changes."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.return_value = [sample_diff_identical]

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "identical" in result.output.lower()

    def test_diff_changed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_diff_changed: DiffResult,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should show diff text for changed resources."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.return_value = [sample_diff_changed]

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 0
        mock_manifest_manager.diff_manifests.assert_called_once()

    def test_diff_no_manifests(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should handle empty manifest list gracefully."""
        mock_manifest_manager.load_manifests.return_value = []

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "no manifests" in result.output.lower()

    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_diff_changed: DiffResult,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should support JSON output."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.return_value = [sample_diff_changed]

        result = cli_runner.invoke(
            app, ["manifests", "diff", str(tmp_manifest_file), "--output", "json"]
        )

        assert result.exit_code == 0
