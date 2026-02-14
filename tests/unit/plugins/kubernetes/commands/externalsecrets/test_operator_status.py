"""Unit tests for ESO operator status commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
)
from system_operations_manager.plugins.kubernetes.commands.externalsecrets import (
    register_external_secrets_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestESOStatusCommands:
    """Tests for ESO operator status commands."""

    @pytest.fixture
    def app(self, get_external_secrets_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with external secrets commands."""
        app = typer.Typer()
        register_external_secrets_commands(app, get_external_secrets_manager)
        return app

    def test_operator_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """status should show operator status."""
        result = cli_runner.invoke(app, ["eso", "status"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_operator_status.assert_called_once()

    def test_operator_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """status with --output json should produce JSON output."""
        result = cli_runner.invoke(app, ["eso", "status", "-o", "json"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_operator_status.assert_called_once()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_external_secrets_manager.get_operator_status.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(app, ["eso", "status"])

        assert result.exit_code == 1
