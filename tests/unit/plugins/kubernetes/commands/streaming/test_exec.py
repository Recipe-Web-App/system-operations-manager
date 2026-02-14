"""Unit tests for Kubernetes exec command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.streaming import (
    register_streaming_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExecCommand:
    """Tests for the exec CLI command."""

    @pytest.fixture
    def app(self, get_streaming_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with streaming commands."""
        app = typer.Typer()
        register_streaming_commands(app, get_streaming_manager)
        return app

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming._run_non_interactive_session"
    )
    def test_exec_default(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec should call exec_command with defaults (no tty, no stdin)."""
        mock_ws = MagicMock()
        mock_streaming_manager.exec_command.return_value = mock_ws

        result = cli_runner.invoke(app, ["exec", "my-pod"])

        assert result.exit_code == 0
        mock_streaming_manager.exec_command.assert_called_once_with(
            "my-pod",
            None,
            command=None,
            container=None,
            stdin=False,
            tty=False,
        )
        mock_run.assert_called_once_with(mock_ws)

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming._run_non_interactive_session"
    )
    def test_exec_with_command(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec should pass extra args as command."""
        mock_streaming_manager.exec_command.return_value = MagicMock()

        result = cli_runner.invoke(app, ["exec", "my-pod", "--", "ls", "-la"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.exec_command.call_args[1]
        assert call_kwargs["command"] == ["ls", "-la"]

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming._run_non_interactive_session"
    )
    def test_exec_with_container(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec -c should pass container."""
        mock_streaming_manager.exec_command.return_value = MagicMock()

        result = cli_runner.invoke(app, ["exec", "my-pod", "-c", "sidecar"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.exec_command.call_args[1]
        assert call_kwargs["container"] == "sidecar"

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming._run_non_interactive_session"
    )
    def test_exec_with_namespace(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec -n should pass namespace."""
        mock_streaming_manager.exec_command.return_value = MagicMock()

        result = cli_runner.invoke(app, ["exec", "my-pod", "-n", "production"])

        assert result.exit_code == 0
        call_args = mock_streaming_manager.exec_command.call_args
        assert call_args[0][1] == "production"

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming._run_interactive_session"
    )
    def test_exec_interactive(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec -it should use interactive session."""
        mock_streaming_manager.exec_command.return_value = MagicMock()

        result = cli_runner.invoke(app, ["exec", "my-pod", "-i", "-t"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.exec_command.call_args[1]
        assert call_kwargs["stdin"] is True
        assert call_kwargs["tty"] is True
        mock_run.assert_called_once()

    def test_exec_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec should handle KubernetesError."""
        mock_streaming_manager.exec_command.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="missing-pod"
        )

        result = cli_runner.invoke(app, ["exec", "missing-pod"])

        assert result.exit_code == 1
