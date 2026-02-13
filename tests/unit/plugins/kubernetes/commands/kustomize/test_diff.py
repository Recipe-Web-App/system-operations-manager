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
