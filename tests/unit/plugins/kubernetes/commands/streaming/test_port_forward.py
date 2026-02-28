"""Unit tests for Kubernetes port-forward command."""

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
    _accept_connections,
    _bridge_connection,
    _parse_duration,
    _parse_port_mappings,
    _parse_target,
    _run_port_forward,
    register_streaming_commands,
)


@pytest.mark.unit
class TestParseTarget:
    """Tests for the _parse_target helper."""

    def test_plain_pod_name(self) -> None:
        assert _parse_target("my-pod") == ("pod", "my-pod")

    def test_pod_prefix(self) -> None:
        assert _parse_target("pod/my-pod") == ("pod", "my-pod")

    def test_svc_prefix(self) -> None:
        assert _parse_target("svc/my-service") == ("svc", "my-service")

    def test_service_prefix(self) -> None:
        assert _parse_target("service/my-service") == ("svc", "my-service")


@pytest.mark.unit
class TestParsePortMappings:
    """Tests for the _parse_port_mappings helper."""

    def test_single_port(self) -> None:
        assert _parse_port_mappings(["80"]) == [(80, 80)]

    def test_local_remote(self) -> None:
        assert _parse_port_mappings(["8080:80"]) == [(8080, 80)]

    def test_multiple_ports(self) -> None:
        assert _parse_port_mappings(["8080:80", "9090:9090"]) == [
            (8080, 80),
            (9090, 9090),
        ]

    def test_invalid_port(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_port_mappings(["invalid"])

    def test_empty_mapping(self) -> None:
        assert _parse_port_mappings([]) == []


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPortForwardCommand:
    """Tests for the port-forward CLI command."""

    @pytest.fixture
    def app(self, get_streaming_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with streaming commands."""
        app = typer.Typer()
        register_streaming_commands(app, get_streaming_manager)
        return app

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_pod(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should forward to a pod."""
        mock_pf = MagicMock()
        mock_streaming_manager.port_forward.return_value = mock_pf

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80"])

        assert result.exit_code == 0
        mock_streaming_manager.port_forward.assert_called_once_with(
            "my-pod", None, ports=[(8080, 80)]
        )
        mock_run_pf.assert_called_once_with(mock_pf, [(8080, 80)], "127.0.0.1")

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_service(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward svc/ should resolve service to pod."""
        mock_streaming_manager.resolve_service_to_pod.return_value = "nginx-abc123"
        mock_pf = MagicMock()
        mock_streaming_manager.port_forward.return_value = mock_pf

        result = cli_runner.invoke(app, ["port-forward", "svc/my-service", "8080:80"])

        assert result.exit_code == 0
        mock_streaming_manager.resolve_service_to_pod.assert_called_once_with("my-service", None)
        mock_streaming_manager.port_forward.assert_called_once_with(
            "nginx-abc123", None, ports=[(8080, 80)]
        )

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_with_namespace(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward -n should pass namespace."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80", "-n", "staging"])

        assert result.exit_code == 0
        call_args = mock_streaming_manager.port_forward.call_args
        assert call_args[0][1] == "staging"

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_custom_address(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward --address should bind to custom address."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(
            app,
            ["port-forward", "my-pod", "8080:80", "--address", "0.0.0.0"],
        )

        assert result.exit_code == 0
        mock_run_pf.assert_called_once()
        assert mock_run_pf.call_args[0][2] == "0.0.0.0"

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_multiple_ports(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should handle multiple port mappings."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80", "9090:9090"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.port_forward.call_args[1]
        assert call_kwargs["ports"] == [(8080, 80), (9090, 9090)]

    def test_port_forward_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should handle KubernetesError."""
        mock_streaming_manager.port_forward.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="missing-pod"
        )

        result = cli_runner.invoke(app, ["port-forward", "missing-pod", "8080:80"])

        assert result.exit_code == 1


@pytest.mark.unit
class TestParseDurationZero:
    """Tests for the zero-total branch of _parse_duration (line 67)."""

    def test_parse_duration_zero_seconds(self) -> None:
        """_parse_duration('0s') should raise BadParameter because total is 0."""
        with pytest.raises(typer.BadParameter, match="greater than zero"):
            _parse_duration("0s")

    def test_parse_duration_all_zeros(self) -> None:
        """_parse_duration('0h0m0s') should raise BadParameter because total is 0."""
        with pytest.raises(typer.BadParameter, match="greater than zero"):
            _parse_duration("0h0m0s")

    def test_parse_duration_zero_hours(self) -> None:
        """_parse_duration('0h') should raise BadParameter because total is 0."""
        with pytest.raises(typer.BadParameter, match="greater than zero"):
            _parse_duration("0h")

    def test_parse_duration_zero_minutes(self) -> None:
        """_parse_duration('0m') should raise BadParameter because total is 0."""
        with pytest.raises(typer.BadParameter, match="greater than zero"):
            _parse_duration("0m")


@pytest.mark.unit
class TestParseTargetNoMatch:
    """Tests for the no-match branch of _parse_target (line 88).

    The regex _TARGET_RE = r"^(?:(pod|svc|service)/)?(.+)$" requires at least one
    character for the name group (.+).  An empty string is the only input that
    cannot match, triggering the BadParameter branch at line 88.
    """

    def test_parse_target_empty_string(self) -> None:
        """_parse_target('') should raise BadParameter because regex requires .+ for name."""
        with pytest.raises(typer.BadParameter):
            _parse_target("")


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRunPortForward:
    """Tests for the _run_port_forward socket/threading function (lines 140-166)."""

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep",
        side_effect=KeyboardInterrupt,
    )
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.socket.socket")
    def test_run_port_forward_single_mapping(
        self, mock_socket_class: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """_run_port_forward should bind, listen, start accept thread, then clean up on Ctrl-C."""
        mock_server = MagicMock()
        # Make accept() raise OSError immediately so the daemon thread exits cleanly.
        mock_server.accept.side_effect = OSError("closed")
        mock_socket_class.return_value = mock_server
        mock_pf = MagicMock()

        _run_port_forward(mock_pf, [(8080, 80)], "127.0.0.1")

        mock_socket_class.assert_called_once()
        mock_server.setsockopt.assert_called_once()
        mock_server.bind.assert_called_once_with(("127.0.0.1", 8080))
        mock_server.listen.assert_called_once_with(5)
        mock_server.close.assert_called_once()

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep",
        side_effect=KeyboardInterrupt,
    )
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.socket.socket")
    def test_run_port_forward_multiple_mappings(
        self, mock_socket_class: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """_run_port_forward should create one server socket per port mapping."""
        server_a = MagicMock()
        server_b = MagicMock()
        server_a.accept.side_effect = OSError("closed")
        server_b.accept.side_effect = OSError("closed")
        mock_socket_class.side_effect = [server_a, server_b]
        mock_pf = MagicMock()

        _run_port_forward(mock_pf, [(8080, 80), (9090, 9090)], "127.0.0.1")

        assert mock_socket_class.call_count == 2
        server_a.bind.assert_called_once_with(("127.0.0.1", 8080))
        server_b.bind.assert_called_once_with(("127.0.0.1", 9090))
        server_a.close.assert_called_once()
        server_b.close.assert_called_once()

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep",
        side_effect=KeyboardInterrupt,
    )
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.socket.socket")
    def test_run_port_forward_custom_address(
        self, mock_socket_class: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """_run_port_forward should use the provided bind address."""
        mock_server = MagicMock()
        mock_server.accept.side_effect = OSError("closed")
        mock_socket_class.return_value = mock_server
        mock_pf = MagicMock()

        _run_port_forward(mock_pf, [(3000, 3000)], "0.0.0.0")

        mock_server.bind.assert_called_once_with(("0.0.0.0", 3000))

    @patch(
        "system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep",
        side_effect=KeyboardInterrupt,
    )
    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.socket.socket")
    def test_run_port_forward_server_close_oserror_suppressed(
        self, mock_socket_class: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """_run_port_forward should suppress OSError when closing the server socket."""
        mock_server = MagicMock()
        mock_server.accept.side_effect = OSError("closed")
        mock_server.close.side_effect = OSError("already closed")
        mock_socket_class.return_value = mock_server
        mock_pf = MagicMock()

        # Should not raise even though close() raises OSError.
        _run_port_forward(mock_pf, [(8080, 80)], "127.0.0.1")

        mock_server.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAcceptConnections:
    """Tests for the _accept_connections loop (lines 181-192)."""

    def test_accept_connections_oserror_breaks_loop(self) -> None:
        """_accept_connections should return cleanly when accept raises OSError."""
        mock_server = MagicMock()
        mock_server.accept.side_effect = OSError("socket closed")
        mock_pf = MagicMock()

        # Should return without raising.
        _accept_connections(mock_server, mock_pf, 80)

        mock_server.accept.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.threading.Thread")
    def test_accept_connections_spawns_bridge_thread(self, mock_thread_class: MagicMock) -> None:
        """_accept_connections should spawn a daemon bridge thread for each connection."""
        mock_server = MagicMock()
        mock_client = MagicMock()
        # First call returns a client connection, second call raises OSError to exit the loop.
        mock_server.accept.side_effect = [(mock_client, ("127.0.0.1", 54321)), OSError("done")]
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        mock_pf = MagicMock()

        _accept_connections(mock_server, mock_pf, 80)

        mock_thread_class.assert_called_once()
        call_kwargs = mock_thread_class.call_args[1]
        assert call_kwargs["daemon"] is True
        assert call_kwargs["args"] == (mock_client, mock_pf, 80)
        mock_thread.start.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestBridgeConnection:
    """Tests for the _bridge_connection data-relay loop (lines 207-240)."""

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep")
    def test_bridge_connection_relays_data_from_client_to_pod(self, mock_sleep: MagicMock) -> None:
        """_bridge_connection should forward data from client socket to pod pf socket."""
        mock_pf = MagicMock()
        mock_pf_socket = MagicMock()
        mock_pf.socket.return_value = mock_pf_socket

        mock_client = MagicMock()
        # First recv returns data; second returns empty bytes to break the inner loop.
        mock_client.recv.side_effect = [b"GET / HTTP/1.1\r\n", b""]
        # Pod side has no data (BlockingIOError) then breaks due to empty client data.
        mock_pf_socket.recv.side_effect = BlockingIOError

        _bridge_connection(mock_client, mock_pf, 80)

        mock_pf.socket.assert_called_once_with(80)
        mock_pf_socket.sendall.assert_called_once_with(b"GET / HTTP/1.1\r\n")
        mock_client.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep")
    def test_bridge_connection_relays_data_from_pod_to_client(self, mock_sleep: MagicMock) -> None:
        """_bridge_connection should forward data from pod pf socket to client socket."""
        mock_pf = MagicMock()
        mock_pf_socket = MagicMock()
        mock_pf.socket.return_value = mock_pf_socket

        mock_client = MagicMock()
        # Client side raises BlockingIOError (no data from client yet).
        mock_client.recv.side_effect = BlockingIOError
        # Pod sends one chunk then empty to break the loop.
        mock_pf_socket.recv.side_effect = [b"HTTP/1.1 200 OK\r\n", b""]

        _bridge_connection(mock_client, mock_pf, 80)

        mock_client.sendall.assert_called_once_with(b"HTTP/1.1 200 OK\r\n")
        mock_client.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep")
    def test_bridge_connection_client_blocking_io_is_ignored(self, mock_sleep: MagicMock) -> None:
        """_bridge_connection should silently retry when client recv raises BlockingIOError."""
        mock_pf = MagicMock()
        mock_pf_socket = MagicMock()
        mock_pf.socket.return_value = mock_pf_socket

        mock_client = MagicMock()
        # BlockingIOError first, then empty bytes to stop the loop.
        mock_client.recv.side_effect = [BlockingIOError, b""]
        mock_pf_socket.recv.side_effect = BlockingIOError

        _bridge_connection(mock_client, mock_pf, 80)

        # No sendall expected since client had no real data.
        mock_pf_socket.sendall.assert_not_called()
        mock_client.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep")
    def test_bridge_connection_exception_logs_and_closes(self, mock_sleep: MagicMock) -> None:
        """_bridge_connection should log unexpected exceptions and always close client socket."""
        mock_pf = MagicMock()
        mock_pf_socket = MagicMock()
        mock_pf.socket.return_value = mock_pf_socket

        mock_client = MagicMock()
        # Raise an unexpected error to trigger the except branch.
        mock_client.recv.side_effect = RuntimeError("unexpected")

        _bridge_connection(mock_client, mock_pf, 80)

        # Client socket must still be closed in the finally block.
        mock_client.close.assert_called_once()

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming.time.sleep")
    def test_bridge_connection_client_close_oserror_suppressed(self, mock_sleep: MagicMock) -> None:
        """_bridge_connection should suppress OSError when closing the client socket."""
        mock_pf = MagicMock()
        mock_pf_socket = MagicMock()
        mock_pf.socket.return_value = mock_pf_socket

        mock_client = MagicMock()
        mock_client.recv.return_value = b""
        mock_pf_socket.recv.side_effect = BlockingIOError
        mock_client.close.side_effect = OSError("already closed")

        # Should not raise.
        _bridge_connection(mock_client, mock_pf, 80)
