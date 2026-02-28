"""Unit tests for Kubernetes manifest diff command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
)
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

    def test_diff_file_not_found_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should handle FileNotFoundError gracefully (lines 211-213)."""
        mock_manifest_manager.load_manifests.side_effect = FileNotFoundError(
            "Manifest file not found"
        )

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_diff_value_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        tmp_manifest_file: Path,
    ) -> None:
        """diff should handle ValueError gracefully (lines 211-213)."""
        mock_manifest_manager.load_manifests.side_effect = ValueError("Invalid YAML")

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 1

    def test_diff_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        tmp_manifest_file: Path,
    ) -> None:
        """diff should handle KubernetesError gracefully (lines 214-215)."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 1

    def test_diff_table_new_resource_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        tmp_manifest_file: Path,
    ) -> None:
        """diff table should show New status when resource not on cluster (line 336)."""
        new_resource = DiffResult(
            resource="Deployment/new-app",
            namespace="default",
            diff="+image: nginx:latest",
            exists_on_cluster=False,
            identical=False,
        )
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.return_value = [new_resource]

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "Deployment/new-app" in result.stdout

    def test_diff_table_prints_normal_context_lines(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        tmp_manifest_file: Path,
    ) -> None:
        """diff table should print unchanged context lines in diff (line 353)."""
        diff_with_context = DiffResult(
            resource="Deployment/test-app",
            namespace="default",
            diff="+added\n-removed\n@@ hunk @@\nunchanged context line",
            exists_on_cluster=True,
            identical=False,
        )
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.diff_manifests.return_value = [diff_with_context]

        result = cli_runner.invoke(app, ["manifests", "diff", str(tmp_manifest_file)])

        assert result.exit_code == 0
        assert "Deployment/test-app" in result.stdout
