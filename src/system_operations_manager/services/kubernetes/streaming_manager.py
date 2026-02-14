"""Streaming operations manager for Kubernetes.

Provides log streaming, interactive exec, and port forwarding
through the Kubernetes API.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

if TYPE_CHECKING:
    pass


class StreamingManager(K8sBaseManager):
    """Manager for streaming Kubernetes operations.

    Handles log streaming (static and follow), interactive exec
    sessions, and port forwarding for pods and services.
    """

    _entity_name = "streaming"

    # =========================================================================
    # Log Streaming
    # =========================================================================

    def stream_logs(
        self,
        pod_name: str,
        namespace: str | None = None,
        *,
        container: str | None = None,
        follow: bool = False,
        tail_lines: int | None = None,
        previous: bool = False,
        timestamps: bool = False,
        since_seconds: int | None = None,
    ) -> str | Iterator[str]:
        """Get or stream logs from a pod.

        Args:
            pod_name: Pod name.
            namespace: Target namespace.
            container: Specific container name.
            follow: Stream logs in real-time.
            tail_lines: Number of lines from the end.
            previous: Logs from previous container instance.
            timestamps: Include timestamps in output.
            since_seconds: Only return logs newer than this many seconds.

        Returns:
            Log content as string (static) or iterator of lines (streaming).
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug(
            "streaming_logs",
            pod=pod_name,
            namespace=ns,
            follow=follow,
            container=container,
        )

        if follow:
            return self._follow_logs(
                pod_name,
                ns,
                container=container,
                tail_lines=tail_lines,
                previous=previous,
                timestamps=timestamps,
                since_seconds=since_seconds,
            )

        try:
            kwargs: dict[str, Any] = {"name": pod_name, "namespace": ns}
            if container:
                kwargs["container"] = container
            if tail_lines is not None:
                kwargs["tail_lines"] = tail_lines
            if previous:
                kwargs["previous"] = previous
            if timestamps:
                kwargs["timestamps"] = timestamps
            if since_seconds is not None:
                kwargs["since_seconds"] = since_seconds

            logs: str = self._client.core_v1.read_namespaced_pod_log(**kwargs)
            return logs
        except Exception as e:
            self._handle_api_error(e, "Pod", pod_name, ns)

    def _follow_logs(
        self,
        pod_name: str,
        namespace: str,
        *,
        container: str | None = None,
        tail_lines: int | None = None,
        previous: bool = False,
        timestamps: bool = False,
        since_seconds: int | None = None,
    ) -> Iterator[str]:
        """Stream logs from a pod in follow mode.

        Args:
            pod_name: Pod name.
            namespace: Target namespace.
            container: Specific container name.
            tail_lines: Number of lines from the end.
            previous: Logs from previous container instance.
            timestamps: Include timestamps in output.
            since_seconds: Only return logs newer than this many seconds.

        Yields:
            Log lines as strings.
        """
        kwargs: dict[str, Any] = {
            "name": pod_name,
            "namespace": namespace,
            "follow": True,
            "_preload_content": False,
        }
        if container:
            kwargs["container"] = container
        if tail_lines is not None:
            kwargs["tail_lines"] = tail_lines
        if previous:
            kwargs["previous"] = previous
        if timestamps:
            kwargs["timestamps"] = timestamps
        if since_seconds is not None:
            kwargs["since_seconds"] = since_seconds

        try:
            stream = self._client.core_v1.read_namespaced_pod_log(**kwargs)
        except Exception as e:
            self._handle_api_error(e, "Pod", pod_name, namespace)

        for line in stream:
            if isinstance(line, bytes):
                yield line.decode("utf-8", errors="replace")
            else:
                yield str(line)

    # =========================================================================
    # Exec
    # =========================================================================

    def exec_command(
        self,
        pod_name: str,
        namespace: str | None = None,
        *,
        command: list[str] | None = None,
        container: str | None = None,
        stdin: bool = True,
        tty: bool = True,
    ) -> Any:
        """Execute a command in a pod container.

        Args:
            pod_name: Pod name.
            namespace: Target namespace.
            command: Command to execute (defaults to ["/bin/sh"]).
            container: Specific container name.
            stdin: Pass stdin to the container.
            tty: Allocate a TTY.

        Returns:
            WebSocket client for interactive I/O.
        """
        import kubernetes.stream

        ns = self._resolve_namespace(namespace)
        exec_command = command or ["/bin/sh"]
        self._log.debug(
            "exec_command",
            pod=pod_name,
            namespace=ns,
            command=exec_command,
            container=container,
        )

        try:
            kwargs: dict[str, Any] = {
                "name": pod_name,
                "namespace": ns,
                "command": exec_command,
                "stdin": stdin,
                "stdout": True,
                "stderr": True,
                "tty": tty,
                "_preload_content": False,
            }
            if container:
                kwargs["container"] = container

            ws_client = kubernetes.stream.stream(
                self._client.core_v1.connect_get_namespaced_pod_exec,
                **kwargs,
            )
            return ws_client
        except Exception as e:
            self._handle_api_error(e, "Pod", pod_name, ns)

    # =========================================================================
    # Port Forward
    # =========================================================================

    def port_forward(
        self,
        pod_name: str,
        namespace: str | None = None,
        *,
        ports: list[tuple[int, int]] | None = None,
    ) -> Any:
        """Establish port forwarding to a pod.

        Args:
            pod_name: Pod name.
            namespace: Target namespace.
            ports: List of (local_port, remote_port) tuples.

        Returns:
            Port-forward object with socket interface per port.
        """
        import kubernetes.stream

        ns = self._resolve_namespace(namespace)
        port_list = ports or []
        self._log.debug(
            "port_forward",
            pod=pod_name,
            namespace=ns,
            ports=port_list,
        )

        try:
            port_str = ",".join(str(remote) for _, remote in port_list)
            pf = kubernetes.stream.portforward(
                self._client.core_v1.connect_get_namespaced_pod_portforward,
                name=pod_name,
                namespace=ns,
                ports=port_str,
            )
            self._log.info(
                "port_forward_established",
                pod=pod_name,
                namespace=ns,
                ports=port_list,
            )
            return pf
        except Exception as e:
            self._handle_api_error(e, "Pod", pod_name, ns)

    def resolve_service_to_pod(
        self,
        service_name: str,
        namespace: str | None = None,
    ) -> str:
        """Resolve a service to a backing pod name.

        Reads the service's selector labels and finds a matching pod.

        Args:
            service_name: Service name.
            namespace: Target namespace.

        Returns:
            Name of a pod backing the service.

        Raises:
            KubernetesNotFoundError: If service or backing pods not found.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug(
            "resolving_service_to_pod",
            service=service_name,
            namespace=ns,
        )

        try:
            svc = self._client.core_v1.read_namespaced_service(
                name=service_name,
                namespace=ns,
            )
        except Exception as e:
            self._handle_api_error(e, "Service", service_name, ns)

        selector = svc.spec.selector
        if not selector:
            raise KubernetesNotFoundError(
                resource_type="Pod",
                resource_name=f"(backing service '{service_name}')",
                namespace=ns,
            )

        label_selector = ",".join(f"{k}={v}" for k, v in selector.items())

        try:
            pods = self._client.core_v1.list_namespaced_pod(
                namespace=ns,
                label_selector=label_selector,
            )
        except Exception as e:
            self._handle_api_error(e, "Pod", service_name, ns)

        if not pods.items:
            raise KubernetesNotFoundError(
                resource_type="Pod",
                resource_name=f"(backing service '{service_name}')",
                namespace=ns,
            )

        pod_name: str = pods.items[0].metadata.name
        self._log.info(
            "service_resolved_to_pod",
            service=service_name,
            pod=pod_name,
            namespace=ns,
        )
        return pod_name
