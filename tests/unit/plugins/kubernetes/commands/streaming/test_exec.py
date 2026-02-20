"""Unit tests for Kubernetes exec command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.streaming import (
    _run_interactive_session,
    _run_non_interactive_session,
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

    def test_exec_kubernetes_error_base_class(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """exec should handle the base KubernetesError (lines 374-375)."""
        mock_streaming_manager.exec_command.side_effect = KubernetesError(
            message="generic kubernetes failure"
        )

        result = cli_runner.invoke(app, ["exec", "my-pod"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRunNonInteractiveSession:
    """Tests for _run_non_interactive_session (lines 473-490)."""

    def test_non_interactive_reads_stdout(self) -> None:
        """_run_non_interactive_session should print stdout from the ws_client."""
        mock_ws = MagicMock()
        # is_open: True once to enter loop, then False to exit.
        mock_ws.is_open.side_effect = [True, False]
        mock_ws.peek_stdout.return_value = True
        mock_ws.read_stdout.return_value = "hello\n"
        mock_ws.peek_stderr.return_value = False
        mock_ws.returncode = 0

        _run_non_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()

    def test_non_interactive_reads_stderr(self) -> None:
        """_run_non_interactive_session should print stderr from the ws_client."""
        mock_ws = MagicMock()
        mock_ws.is_open.side_effect = [True, False]
        mock_ws.peek_stdout.return_value = False
        mock_ws.peek_stderr.return_value = True
        mock_ws.read_stderr.return_value = "error line\n"
        mock_ws.returncode = 0

        _run_non_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()

    def test_non_interactive_raises_exit_on_nonzero_returncode(self) -> None:
        """_run_non_interactive_session should raise typer.Exit with the returncode."""
        mock_ws = MagicMock()
        mock_ws.is_open.return_value = False
        mock_ws.returncode = 1

        with pytest.raises(typer.Exit) as exc_info:
            _run_non_interactive_session(mock_ws)

        assert exc_info.value.exit_code == 1
        mock_ws.close.assert_called_once()

    def test_non_interactive_zero_returncode_does_not_raise(self) -> None:
        """_run_non_interactive_session should not raise Exit when returncode is 0."""
        mock_ws = MagicMock()
        mock_ws.is_open.return_value = False
        mock_ws.returncode = 0

        _run_non_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()

    def test_non_interactive_keyboard_interrupt_exits_cleanly(self) -> None:
        """_run_non_interactive_session should handle KeyboardInterrupt gracefully."""
        mock_ws = MagicMock()
        mock_ws.is_open.side_effect = [True]
        mock_ws.update.side_effect = KeyboardInterrupt
        mock_ws.returncode = 0

        # Should not propagate the KeyboardInterrupt.
        _run_non_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRunInteractiveSession:
    """Tests for _run_interactive_session (lines 429-462)."""

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stdin")
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stdout")
    def test_interactive_reads_stdout_and_closes(
        self, mock_stdout: MagicMock, mock_stdin: MagicMock
    ) -> None:
        """_run_interactive_session should read ws stdout and close on exit."""

        mock_ws = MagicMock()
        # Loop once then exit.
        mock_ws.is_open.side_effect = [True, False]
        mock_ws.peek_stdout.return_value = True
        mock_ws.read_stdout.return_value = "output\n"
        mock_ws.peek_stderr.return_value = False

        mock_stdin.fileno.return_value = 0

        with (
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setraw"),
            patch("select.select", return_value=([], [], [])),
        ):
            _run_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stdin")
    def test_interactive_keyboard_interrupt_closes(self, mock_stdin: MagicMock) -> None:
        """_run_interactive_session should handle KeyboardInterrupt and close ws_client."""
        mock_ws = MagicMock()
        mock_ws.is_open.return_value = True
        mock_ws.update.side_effect = KeyboardInterrupt

        mock_stdin.fileno.return_value = 0

        with (
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setraw"),
            patch("select.select", return_value=([], [], [])),
        ):
            _run_interactive_session(mock_ws)

        mock_ws.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stdin")
    def test_interactive_writes_stdin_to_ws(self, mock_stdin: MagicMock) -> None:
        """_run_interactive_session should forward stdin keystrokes to ws_client."""
        mock_ws = MagicMock()
        mock_ws.is_open.side_effect = [True, False]
        mock_ws.peek_stdout.return_value = False
        mock_ws.peek_stderr.return_value = False

        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = "x"

        with (
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setraw"),
            # Simulate stdin being readable.
            patch("select.select", return_value=([mock_stdin], [], [])),
        ):
            _run_interactive_session(mock_ws)

        mock_ws.write_stdin.assert_called_once_with("x")
        mock_ws.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stderr")
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.sys.stdin")
    def test_interactive_reads_stderr(self, mock_stdin: MagicMock, mock_stderr: MagicMock) -> None:
        """_run_interactive_session should write ws stderr to sys.stderr (lines 449-450)."""
        mock_ws = MagicMock()
        mock_ws.is_open.side_effect = [True, False]
        mock_ws.peek_stdout.return_value = False
        mock_ws.peek_stderr.return_value = True
        mock_ws.read_stderr.return_value = "error output\n"

        mock_stdin.fileno.return_value = 0

        with (
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setraw"),
            patch("select.select", return_value=([], [], [])),
        ):
            _run_interactive_session(mock_ws)

        mock_stderr.write.assert_called_once_with("error output\n")
        mock_stderr.flush.assert_called_once()
        mock_ws.close.assert_called_once()
