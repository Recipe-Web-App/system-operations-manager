"""Unit tests for Kubernetes manifest apply command."""

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
from system_operations_manager.services.kubernetes.manifest_manager import (
    ApplyResult,
    ValidationResult,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestApplyCommand:
    """Tests for the ``manifests apply`` command."""

    @pytest.fixture
    def app(self, get_manifest_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with manifest commands."""
        app = typer.Typer()
        register_manifest_commands(app, get_manifest_manager)
        return app

    def test_apply_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        sample_apply_created: ApplyResult,
        tmp_manifest_file: Path,
    ) -> None:
        """apply should succeed when manifests are valid and apply works."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]
        mock_manifest_manager.apply_manifests.return_value = [sample_apply_created]

        result = cli_runner.invoke(app, ["manifests", "apply", str(tmp_manifest_file)])

        assert result.exit_code == 0
        mock_manifest_manager.apply_manifests.assert_called_once()

    def test_apply_validation_failure_blocks(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_fail: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """apply should exit 1 when validation fails (without --force)."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_fail]

        result = cli_runner.invoke(app, ["manifests", "apply", str(tmp_manifest_file)])

        assert result.exit_code == 1
        mock_manifest_manager.apply_manifests.assert_not_called()

    def test_apply_with_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """apply --dry-run should pass dry_run=True to manager."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]
        mock_manifest_manager.apply_manifests.return_value = [
            ApplyResult(
                resource="Deployment/test-app",
                action="skipped (client dry-run)",
                namespace="default",
                success=True,
                message="Would apply to cluster",
            )
        ]

        result = cli_runner.invoke(app, ["manifests", "apply", str(tmp_manifest_file), "--dry-run"])

        assert result.exit_code == 0
        call_kwargs = mock_manifest_manager.apply_manifests.call_args
        assert call_kwargs.kwargs.get("dry_run") is True or call_kwargs[1].get("dry_run") is True

    def test_apply_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        sample_apply_created: ApplyResult,
        tmp_manifest_file: Path,
    ) -> None:
        """apply -n should pass namespace to manager."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]
        mock_manifest_manager.apply_manifests.return_value = [sample_apply_created]

        result = cli_runner.invoke(
            app, ["manifests", "apply", str(tmp_manifest_file), "-n", "production"]
        )

        assert result.exit_code == 0
        call_args = mock_manifest_manager.apply_manifests.call_args
        assert call_args[0][1] == "production" or call_args.kwargs.get("namespace") == "production"

    def test_apply_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_manifest_manager: MagicMock,
        sample_valid_manifest: dict[str, object],
        sample_validation_ok: ValidationResult,
        tmp_manifest_file: Path,
    ) -> None:
        """apply should handle KubernetesError gracefully."""
        mock_manifest_manager.load_manifests.return_value = [sample_valid_manifest]
        mock_manifest_manager.validate_manifests.return_value = [sample_validation_ok]
        mock_manifest_manager.apply_manifests.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["manifests", "apply", str(tmp_manifest_file)])

        assert result.exit_code == 1
