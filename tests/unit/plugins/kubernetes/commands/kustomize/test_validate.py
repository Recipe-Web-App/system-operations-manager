"""Unit tests for kustomize validate command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.kustomize_client import (
    KustomizeBinaryNotFoundError,
    KustomizeError,
)
from system_operations_manager.plugins.kubernetes.commands.kustomize import (
    register_kustomize_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidateCommand:
    """Tests for the ``kustomize validate`` command."""

    @pytest.fixture
    def app(self, get_kustomize_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with kustomize commands."""
        app = typer.Typer()
        register_kustomize_commands(app, get_kustomize_manager)
        return app

    def test_validate_valid(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """validate should show valid message."""
        mock_kustomize_manager.validate.return_value = (True, None)

        result = cli_runner.invoke(app, ["kustomize", "validate", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """validate should exit 1 for invalid kustomization."""
        mock_kustomize_manager.validate.return_value = (False, "Missing resources field")

        result = cli_runner.invoke(app, ["kustomize", "validate", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()
        assert "Missing resources field" in result.stdout

    def test_validate_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """validate should show install link when binary not found."""
        mock_kustomize_manager.validate.side_effect = KustomizeBinaryNotFoundError()

        result = cli_runner.invoke(app, ["kustomize", "validate", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_validate_kustomize_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """validate should handle KustomizeError gracefully (line 349)."""
        mock_kustomize_manager.validate.side_effect = KustomizeError(
            message="Validation failed", stderr="some kustomize output"
        )

        result = cli_runner.invoke(app, ["kustomize", "validate", str(tmp_kustomization_dir)])

        assert result.exit_code == 1
        assert "Kustomize error" in result.stdout
