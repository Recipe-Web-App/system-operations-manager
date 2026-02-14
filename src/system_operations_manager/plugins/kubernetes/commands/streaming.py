"""Streaming CLI commands for Kubernetes.

Provides top-level ``logs``, ``exec``, and ``port-forward`` commands
that handle interactive and streaming I/O with Kubernetes pods.
"""

from __future__ import annotations

import contextlib
import re
import socket
import sys
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    NamespaceOption,
    console,
    handle_k8s_error,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes.streaming_manager import StreamingManager

# Duration regex: matches "1h", "30m", "5s", "1h30m", "2h15m30s", etc.
_DURATION_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")

# Port mapping regex: matches "8080:80" or "80"
_PORT_MAPPING_RE = re.compile(r"^(\d+)(?::(\d+))?$")

# Target regex: matches "pod/name", "svc/name", "service/name", or "name"
_TARGET_RE = re.compile(r"^(?:(pod|svc|service)/)?(.+)$")


def _parse_duration(duration: str) -> int:
    """Parse a duration string to seconds.

    Supports formats like "1h", "30m", "5s", "1h30m", "2h15m30s".

    Args:
        duration: Duration string.

    Returns:
        Duration in seconds.

    Raises:
        typer.BadParameter: If the duration string is invalid.
    """
    match = _DURATION_RE.match(duration.strip())
    if not match or not any(match.groups()):
        raise typer.BadParameter(
            f"Invalid duration '{duration}'. Use format like '1h', '30m', '5s', or '1h30m'."
        )

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds

    if total <= 0:
        raise typer.BadParameter("Duration must be greater than zero.")

    return total


def _parse_target(target: str) -> tuple[str, str]:
    """Parse a port-forward target string.

    Supports "pod/name", "svc/name", "service/name", or plain "name" (assumes pod).

    Args:
        target: Target string.

    Returns:
        Tuple of (target_type, target_name) where type is "pod" or "svc".

    Raises:
        typer.BadParameter: If the target format is invalid.
    """
    match = _TARGET_RE.match(target)
    if not match:
        raise typer.BadParameter(
            f"Invalid target '{target}'. Use format 'pod/<name>', 'svc/<name>', or '<pod-name>'."
        )

    target_type = match.group(1) or "pod"
    target_name = match.group(2)

    if target_type == "service":
        target_type = "svc"

    return target_type, target_name


def _parse_port_mappings(mappings: list[str]) -> list[tuple[int, int]]:
    """Parse port mapping strings.

    Supports "local:remote" or "port" (uses same port for both).

    Args:
        mappings: List of port mapping strings.

    Returns:
        List of (local_port, remote_port) tuples.

    Raises:
        typer.BadParameter: If any mapping is invalid.
    """
    ports: list[tuple[int, int]] = []
    for mapping in mappings:
        match = _PORT_MAPPING_RE.match(mapping.strip())
        if not match:
            raise typer.BadParameter(
                f"Invalid port mapping '{mapping}'. Use format 'local:remote' or 'port'."
            )
        first = int(match.group(1))
        second = int(match.group(2)) if match.group(2) else first
        ports.append((first, second))
    return ports


def _run_port_forward(
    pf: Any,
    ports: list[tuple[int, int]],
    address: str,
) -> None:
    """Run local TCP listeners that forward to the Kubernetes pod.

    Args:
        pf: Port-forward object from kubernetes.stream.portforward.
        ports: List of (local_port, remote_port) tuples.
        address: Local address to bind to.
    """
    servers: list[socket.socket] = []

    try:
        for local_port, remote_port in ports:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((address, local_port))
            server.listen(5)
            servers.append(server)
            console.print(f"Forwarding from {address}:{local_port} -> {remote_port}")

            accept_thread = threading.Thread(
                target=_accept_connections,
                args=(server, pf, remote_port),
                daemon=True,
            )
            accept_thread.start()

        console.print("[dim]Press Ctrl+C to stop port forwarding.[/dim]")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopping port forwarding...[/dim]")
    finally:
        for server in servers:
            with contextlib.suppress(OSError):
                server.close()


def _accept_connections(
    server: socket.socket,
    pf: Any,
    remote_port: int,
) -> None:
    """Accept local TCP connections and bridge to the port-forward.

    Args:
        server: Local TCP server socket.
        pf: Port-forward object.
        remote_port: Remote port to forward to.
    """
    while True:
        try:
            client_sock, _ = server.accept()
        except OSError:
            break

        bridge_thread = threading.Thread(
            target=_bridge_connection,
            args=(client_sock, pf, remote_port),
            daemon=True,
        )
        bridge_thread.start()


def _bridge_connection(
    client_sock: socket.socket,
    pf: Any,
    remote_port: int,
) -> None:
    """Bridge a local TCP connection to the Kubernetes port-forward.

    Args:
        client_sock: Local client socket.
        pf: Port-forward object.
        remote_port: Remote port to forward to.
    """
    try:
        pf_socket = pf.socket(remote_port)
        client_sock.setblocking(False)
        pf_socket.setblocking(False)

        while True:
            # Read from local client, write to pod
            try:
                data = client_sock.recv(4096)
                if not data:
                    break
                pf_socket.sendall(data)
            except BlockingIOError:
                # Non-blocking socket: no data available right now, try again on next loop
                pass

            # Read from pod, write to local client
            try:
                data = pf_socket.recv(4096)
                if not data:
                    break
                client_sock.sendall(data)
            except BlockingIOError:
                # Non-blocking socket: no data available right now, try again on next loop
                pass

            time.sleep(0.01)
    except Exception:
        pass
    finally:
        with contextlib.suppress(OSError):
            client_sock.close()


def register_streaming_commands(
    app: typer.Typer,
    get_manager: Callable[[], StreamingManager],
) -> None:
    """Register streaming commands on the Kubernetes CLI app.

    Adds top-level ``logs``, ``exec``, and ``port-forward`` commands.

    Args:
        app: Parent Typer app (k8s_app).
        get_manager: Factory function returning a StreamingManager instance.
    """

    # =========================================================================
    # logs
    # =========================================================================

    @app.command("logs")
    def logs_command(
        pod: Annotated[str, typer.Argument(help="Pod name")],
        namespace: NamespaceOption = None,
        container: Annotated[
            str | None,
            typer.Option("--container", "-c", help="Container name"),
        ] = None,
        follow: Annotated[
            bool,
            typer.Option("--follow", "-f", help="Stream logs in real-time"),
        ] = False,
        tail: Annotated[
            int | None,
            typer.Option("--tail", help="Number of lines from the end of the logs"),
        ] = None,
        previous: Annotated[
            bool,
            typer.Option("--previous", "-p", help="Show logs from previous container instance"),
        ] = False,
        timestamps: Annotated[
            bool,
            typer.Option("--timestamps", help="Include timestamps in log output"),
        ] = False,
        since: Annotated[
            str | None,
            typer.Option("--since", help="Show logs since duration (e.g., 1h, 30m, 5s)"),
        ] = None,
    ) -> None:
        """Get or stream pod logs.

        Examples:
            ops k8s logs my-pod
            ops k8s logs my-pod --follow
            ops k8s logs my-pod --tail 100 -c sidecar
            ops k8s logs my-pod --since 1h --timestamps
        """
        try:
            manager = get_manager()
            since_seconds = _parse_duration(since) if since else None
            result = manager.stream_logs(
                pod,
                namespace,
                container=container,
                follow=follow,
                tail_lines=tail,
                previous=previous,
                timestamps=timestamps,
                since_seconds=since_seconds,
            )

            if isinstance(result, str):
                console.print(result)
            else:
                try:
                    for line in result:
                        console.print(line, end="")
                except KeyboardInterrupt:
                    console.print("\n[dim]Log streaming stopped.[/dim]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # =========================================================================
    # exec
    # =========================================================================

    @app.command(
        "exec",
        context_settings={"allow_extra_args": True},
    )
    def exec_command(
        ctx: typer.Context,
        pod: Annotated[str, typer.Argument(help="Pod name")],
        namespace: NamespaceOption = None,
        container: Annotated[
            str | None,
            typer.Option("--container", "-c", help="Container name"),
        ] = None,
        stdin_opt: Annotated[
            bool,
            typer.Option("--stdin", "-i", help="Pass stdin to the container"),
        ] = False,
        tty: Annotated[
            bool,
            typer.Option("--tty", "-t", help="Allocate a TTY"),
        ] = False,
    ) -> None:
        """Execute a command in a pod container.

        Use ``-it`` for an interactive shell, or pass a command after ``--``.

        Examples:
            ops k8s exec my-pod -it
            ops k8s exec my-pod -- ls -la
            ops k8s exec my-pod -c sidecar -it -- /bin/bash
            ops k8s exec my-pod -- cat /etc/hosts
        """
        extra = [a for a in ctx.args if a != "--"]
        command = extra or None
        try:
            manager = get_manager()
            ws_client = manager.exec_command(
                pod,
                namespace,
                command=command,
                container=container,
                stdin=stdin_opt,
                tty=tty,
            )

            if tty and stdin_opt:
                _run_interactive_session(ws_client)
            else:
                _run_non_interactive_session(ws_client)
        except KubernetesError as e:
            handle_k8s_error(e)

    # =========================================================================
    # port-forward
    # =========================================================================

    @app.command("port-forward")
    def port_forward_command(
        target: Annotated[
            str,
            typer.Argument(help="Target: pod/<name>, svc/<name>, or <pod-name>"),
        ],
        port_mappings: Annotated[
            list[str],
            typer.Argument(help="Port mappings: [local:]remote (e.g., 8080:80)"),
        ],
        namespace: NamespaceOption = None,
        address: Annotated[
            str,
            typer.Option("--address", help="Local address to bind to"),
        ] = "127.0.0.1",
    ) -> None:
        """Forward local ports to a pod or service.

        Examples:
            ops k8s port-forward my-pod 8080:80
            ops k8s port-forward svc/my-service 8080:80 9090:9090
            ops k8s port-forward my-pod 3000 --address 0.0.0.0
        """
        try:
            manager = get_manager()
            target_type, target_name = _parse_target(target)
            ports = _parse_port_mappings(port_mappings)

            pod_name = target_name
            if target_type == "svc":
                pod_name = manager.resolve_service_to_pod(target_name, namespace)
                console.print(f"[dim]Resolved service '{target_name}' to pod '{pod_name}'[/dim]")

            pf = manager.port_forward(pod_name, namespace, ports=ports)
            _run_port_forward(pf, ports, address)
        except KubernetesError as e:
            handle_k8s_error(e)


def _run_interactive_session(ws_client: Any) -> None:
    """Run an interactive TTY session with the container.

    Puts the terminal in raw mode for proper shell interaction
    (arrow keys, tab completion, ctrl-c forwarded to container).

    Args:
        ws_client: WebSocket client from kubernetes.stream.
    """
    try:
        import select
        import termios
        import tty as tty_module
    except ImportError:
        console.print(
            "[red]Error:[/red] Interactive exec requires a Unix terminal "
            "(termios not available on this platform)."
        )
        raise typer.Exit(1) from None

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty_module.setraw(sys.stdin.fileno())
        while ws_client.is_open():
            ws_client.update(timeout=0.1)
            if ws_client.peek_stdout():
                sys.stdout.write(ws_client.read_stdout())
                sys.stdout.flush()
            if ws_client.peek_stderr():
                sys.stderr.write(ws_client.read_stderr())
                sys.stderr.flush()

            readable, _, _ = select.select([sys.stdin], [], [], 0)
            if readable:
                data = sys.stdin.read(1)
                if data:
                    ws_client.write_stdin(data)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        ws_client.close()


def _run_non_interactive_session(ws_client: Any) -> None:
    """Run a non-interactive exec session.

    Reads stdout/stderr from the WebSocket and prints to console.

    Args:
        ws_client: WebSocket client from kubernetes.stream.
    """
    try:
        while ws_client.is_open():
            ws_client.update(timeout=1)
            if ws_client.peek_stdout():
                sys.stdout.write(ws_client.read_stdout())
                sys.stdout.flush()
            if ws_client.peek_stderr():
                sys.stderr.write(ws_client.read_stderr())
                sys.stderr.flush()
    except KeyboardInterrupt:
        pass
    finally:
        ws_client.close()

    returncode = ws_client.returncode
    if returncode:
        raise typer.Exit(returncode)
