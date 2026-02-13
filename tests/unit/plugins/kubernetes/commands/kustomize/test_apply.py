"""Unit tests for kustomize apply command."""

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
from system_operations_manager.services.kubernetes.manifest_manager import ApplyResult


@pytest.mark.unit
@pytest.mark.kubernetes
class TestApplyCommand:
    """Tests for the ``kustomize apply`` command."""

    @pytest.fixture
    def app(self, get_kustomize_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with kustomize commands."""
        app = typer.Typer()
        register_kustomize_commands(app, get_kustomize_manager)
        return app

    def test_apply_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_apply_created: ApplyResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """apply should succeed and show results."""
        mock_kustomize_manager.apply.return_value = [sample_apply_created]

        result = cli_runner.invoke(app, ["kustomize", "apply", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        mock_kustomize_manager.apply.assert_called_once()

    def test_apply_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_apply_created: ApplyResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """apply -n should pass namespace to manager."""
        mock_kustomize_manager.apply.return_value = [sample_apply_created]

        result = cli_runner.invoke(
            app, ["kustomize", "apply", str(tmp_kustomization_dir), "-n", "production"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_kustomize_manager.apply.call_args
        assert (
            call_kwargs[1].get("namespace") == "production"
            or call_kwargs.kwargs.get("namespace") == "production"
        )

    def test_apply_with_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """apply --dry-run should pass dry_run=True."""
        mock_kustomize_manager.apply.return_value = [
            ApplyResult(
                resource="ConfigMap/test",
                action="skipped (client dry-run)",
                namespace="default",
                success=True,
                message="Would apply",
            )
        ]

        result = cli_runner.invoke(
            app, ["kustomize", "apply", str(tmp_kustomization_dir), "--dry-run"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_kustomize_manager.apply.call_args
        assert call_kwargs.kwargs.get("dry_run") is True or call_kwargs[1].get("dry_run") is True

    def test_apply_failure_exits_1(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_apply_failed: ApplyResult,
        tmp_kustomization_dir: Path,
    ) -> None:
        """apply should exit 1 when any resource fails."""
        mock_kustomize_manager.apply.return_value = [sample_apply_failed]

        result = cli_runner.invoke(app, ["kustomize", "apply", str(tmp_kustomization_dir)])

        assert result.exit_code == 1

    def test_apply_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """apply should handle KubernetesError gracefully."""
        mock_kustomize_manager.apply.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["kustomize", "apply", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
