"""Unit tests for kustomize build command."""

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
from system_operations_manager.services.kubernetes.kustomize_manager import KustomizeBuildOutput


@pytest.mark.unit
@pytest.mark.kubernetes
class TestBuildCommand:
    """Tests for the ``kustomize build`` command."""

    @pytest.fixture
    def app(self, get_kustomize_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with kustomize commands."""
        app = typer.Typer()
        register_kustomize_commands(app, get_kustomize_manager)
        return app

    def test_build_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_build_success: KustomizeBuildOutput,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should print rendered YAML on success."""
        mock_kustomize_manager.build.return_value = sample_build_success

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "ConfigMap" in result.stdout

    def test_build_failure(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_build_failure: KustomizeBuildOutput,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should exit 1 on failure."""
        mock_kustomize_manager.build.return_value = sample_build_failure

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "Build failed" in result.stdout

    def test_build_with_output_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
        tmp_path: Path,
    ) -> None:
        """build --output-file should show file path."""
        output_file = tmp_path / "rendered.yaml"
        mock_kustomize_manager.build.return_value = KustomizeBuildOutput(
            path=str(tmp_kustomization_dir),
            rendered_yaml="apiVersion: v1\n",
            success=True,
            output_file=str(output_file),
        )

        result = cli_runner.invoke(
            app,
            [
                "kustomize",
                "build",
                str(tmp_kustomization_dir),
                "--output-file",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert "written to" in result.stdout

    def test_build_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should show install link when binary not found."""
        mock_kustomize_manager.build.side_effect = KustomizeBinaryNotFoundError()

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "not found" in result.stdout
        assert "kustomize" in result.stdout

    def test_build_passes_helm_flag(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_build_success: KustomizeBuildOutput,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build --enable-helm should pass flag to manager."""
        mock_kustomize_manager.build.return_value = sample_build_success

        result = cli_runner.invoke(
            app, ["kustomize", "build", str(tmp_kustomization_dir), "--enable-helm"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_kustomize_manager.build.call_args.kwargs
        assert call_kwargs.get("enable_helm") is True

    def test_build_kustomize_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should handle KustomizeError gracefully (line 171)."""
        mock_kustomize_manager.build.side_effect = KustomizeError(
            message="Build failed", stderr="error details"
        )

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "Kustomize error" in result.stdout

    def test_build_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should handle KubernetesError gracefully (line 173)."""
        mock_kustomize_manager.build.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 1

    def test_build_kustomize_error_with_stderr(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """build should display stderr in _handle_kustomize_error (lines 366-369)."""
        mock_kustomize_manager.build.side_effect = KustomizeError(
            message="Build failed", stderr="stderr output from kustomize"
        )

        result = cli_runner.invoke(app, ["kustomize", "build", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "stderr output from kustomize" in result.stdout
