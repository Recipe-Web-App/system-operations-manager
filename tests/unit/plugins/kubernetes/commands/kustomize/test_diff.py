"""Unit tests for kustomize diff command."""

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
from system_operations_manager.integrations.kubernetes.kustomize_client import (
    KustomizeBinaryNotFoundError,
    KustomizeError,
)
from system_operations_manager.plugins.kubernetes.commands.kustomize import (
    register_kustomize_commands,
)
from system_operations_manager.services.kubernetes.manifest_manager import DiffResult


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDiffCommand:
    """Tests for the ``kustomize diff`` command."""

    @pytest.fixture
    def app(self, get_kustomize_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with kustomize commands."""
        app = typer.Typer()
        register_kustomize_commands(app, get_kustomize_manager)
        return app

    def test_diff_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_diff_changed: DiffResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff should show results on success."""
        mock_kustomize_manager.diff.return_value = [sample_diff_changed]

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        mock_kustomize_manager.diff.assert_called_once()

    def test_diff_identical_resources(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_diff_identical: DiffResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff should handle identical resources."""
        mock_kustomize_manager.diff.return_value = [sample_diff_identical]

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 0

    def test_diff_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_diff_changed: DiffResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff -n should pass namespace to manager."""
        mock_kustomize_manager.diff.return_value = [sample_diff_changed]

        result = cli_runner.invoke(
            app, ["kustomize", "diff", str(tmp_kustomization_dir), "-n", "staging"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_kustomize_manager.diff.call_args
        assert call_kwargs.kwargs.get("namespace") == "staging"

    def test_diff_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff should handle KubernetesError gracefully."""
        mock_kustomize_manager.diff.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 1

    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_diff_changed: DiffResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff --output json should use formatter.format_dict (line 264)."""
        mock_kustomize_manager.diff.return_value = [sample_diff_changed]

        result = cli_runner.invoke(
            app, ["kustomize", "diff", str(tmp_kustomization_dir), "--output", "json"]
        )

        assert result.exit_code == 0
        mock_kustomize_manager.diff.assert_called_once()

    def test_diff_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff should handle KustomizeBinaryNotFoundError (line 270)."""
        mock_kustomize_manager.diff.side_effect = KustomizeBinaryNotFoundError()

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_diff_table_shows_normal_diff_lines(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff table should print unchanged context lines in diff (line 431)."""
        diff_result = DiffResult(
            resource="ConfigMap/test",
            namespace="default",
            diff="context line\n+added line\n-removed line\n@@ hunk @@\nnormal line",
            exists_on_cluster=True,
            identical=False,
        )
        mock_kustomize_manager.diff.return_value = [diff_result]

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "ConfigMap/test" in result.stdout

    def test_diff_table_shows_new_resource_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff table should show New status when resource does not exist on cluster (line 415)."""
        diff_result = DiffResult(
            resource="ConfigMap/brand-new",
            namespace="default",
            diff="+new line",
            exists_on_cluster=False,
            identical=False,
        )
        mock_kustomize_manager.diff.return_value = [diff_result]

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "ConfigMap/brand-new" in result.stdout

    def test_diff_kustomize_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """diff should handle KustomizeError gracefully (line 272)."""
        mock_kustomize_manager.diff.side_effect = KustomizeError(message="Diff failed", stderr=None)

        result = cli_runner.invoke(app, ["kustomize", "diff", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "Kustomize error" in result.stdout
