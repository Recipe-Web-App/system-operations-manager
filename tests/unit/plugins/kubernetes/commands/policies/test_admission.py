"""Unit tests for Kyverno admission controller status commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
)
from system_operations_manager.plugins.kubernetes.commands.policies import (
    register_policy_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAdmissionCommands:
    """Tests for Kyverno admission controller status commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_admission_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """status should show admission controller status."""
        mock_kyverno_manager.get_admission_status.return_value = {
            "running": True,
            "pods": [
                {"name": "kyverno-admission-controller-xyz", "status": "Running"},
            ],
            "version": "v1.11.0",
        }

        result = cli_runner.invoke(app, ["admission", "status"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_admission_status.assert_called_once()

    def test_admission_status_not_running(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """status should handle non-running controller."""
        mock_kyverno_manager.get_admission_status.return_value = {
            "running": False,
            "pods": [],
            "error": "Could not reach kyverno namespace",
        }

        result = cli_runner.invoke(app, ["admission", "status"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_admission_status.assert_called_once()

    def test_admission_status_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """status should handle connection errors."""
        mock_kyverno_manager.get_admission_status.side_effect = KubernetesConnectionError(
            message="Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["admission", "status"])

        assert result.exit_code == 1
