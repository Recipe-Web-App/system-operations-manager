"""Unit tests for Kubernetes StreamingManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.services.kubernetes.streaming_manager import StreamingManager


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def streaming_manager(mock_k8s_client: MagicMock) -> StreamingManager:
    """Create a StreamingManager with a mocked client."""
    return StreamingManager(mock_k8s_client)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStreamLogs:
    """Tests for StreamingManager.stream_logs."""

    def test_static_logs_default(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """stream_logs should return static log string."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = "line1\nline2"

        result = streaming_manager.stream_logs("my-pod")

        assert result == "line1\nline2"
        mock_k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="my-pod", namespace="default"
        )

    def test_static_logs_with_all_options(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """stream_logs should forward all options to the API."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = "filtered logs"

        result = streaming_manager.stream_logs(
            "my-pod",
            "production",
            container="sidecar",
            tail_lines=100,
            previous=True,
            timestamps=True,
            since_seconds=3600,
        )

        assert result == "filtered logs"
        mock_k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="my-pod",
            namespace="production",
            container="sidecar",
            tail_lines=100,
            previous=True,
            timestamps=True,
            since_seconds=3600,
        )

    def test_follow_logs_returns_iterator(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """stream_logs with follow=True should return an iterator."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = iter(
            [b"line1\n", b"line2\n"]
        )

        result = streaming_manager.stream_logs("my-pod", follow=True)

        lines = list(result)
        assert lines == ["line1\n", "line2\n"]
        mock_k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="my-pod",
            namespace="default",
            follow=True,
            _preload_content=False,
        )

    def test_follow_logs_decodes_bytes(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Follow mode should decode bytes to strings."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = iter(
            [b"hello\n", "already a string\n"]
        )

        result = streaming_manager.stream_logs("my-pod", follow=True)
        lines = list(result)

        assert lines == ["hello\n", "already a string\n"]

    def test_follow_logs_with_options(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Follow mode should forward all options."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = iter([b"data\n"])

        result = streaming_manager.stream_logs(
            "my-pod",
            "staging",
            container="app",
            follow=True,
            tail_lines=50,
            timestamps=True,
        )
        list(result)

        mock_k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="my-pod",
            namespace="staging",
            container="app",
            follow=True,
            _preload_content=False,
            tail_lines=50,
            timestamps=True,
        )

    def test_static_logs_api_error(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """stream_logs should translate API errors."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.return_value = KubernetesNotFoundError(
            resource_type="Pod", resource_name="my-pod"
        )

        with pytest.raises(KubernetesNotFoundError):
            streaming_manager.stream_logs("my-pod")


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExecCommand:
    """Tests for StreamingManager.exec_command."""

    @patch("kubernetes.stream.stream")
    def test_exec_default_command(
        self,
        mock_stream: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """exec_command should default to /bin/sh."""
        mock_ws = MagicMock()
        mock_stream.return_value = mock_ws

        result = streaming_manager.exec_command("my-pod")

        assert result == mock_ws
        mock_stream.assert_called_once_with(
            mock_k8s_client.core_v1.connect_get_namespaced_pod_exec,
            name="my-pod",
            namespace="default",
            command=["/bin/sh"],
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            _preload_content=False,
        )

    @patch("kubernetes.stream.stream")
    def test_exec_custom_command(
        self,
        mock_stream: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """exec_command should pass custom command."""
        mock_stream.return_value = MagicMock()

        streaming_manager.exec_command("my-pod", command=["ls", "-la"])

        call_kwargs = mock_stream.call_args[1]
        assert call_kwargs["command"] == ["ls", "-la"]

    @patch("kubernetes.stream.stream")
    def test_exec_with_container(
        self,
        mock_stream: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """exec_command should pass container option."""
        mock_stream.return_value = MagicMock()

        streaming_manager.exec_command("my-pod", container="sidecar")

        call_kwargs = mock_stream.call_args[1]
        assert call_kwargs["container"] == "sidecar"

    @patch("kubernetes.stream.stream")
    def test_exec_no_tty(
        self,
        mock_stream: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """exec_command should respect tty=False."""
        mock_stream.return_value = MagicMock()

        streaming_manager.exec_command("my-pod", tty=False, stdin=False)

        call_kwargs = mock_stream.call_args[1]
        assert call_kwargs["tty"] is False
        assert call_kwargs["stdin"] is False

    def test_exec_api_error(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """exec_command should translate API errors."""
        mock_k8s_client.translate_api_exception.return_value = KubernetesNotFoundError(
            resource_type="Pod", resource_name="my-pod"
        )

        with (
            patch(
                "kubernetes.stream.stream",
                side_effect=Exception("connect failed"),
            ),
            pytest.raises(KubernetesNotFoundError),
        ):
            streaming_manager.exec_command("my-pod")


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPortForward:
    """Tests for StreamingManager.port_forward."""

    @patch("kubernetes.stream.portforward")
    def test_port_forward_calls_api(
        self,
        mock_portforward: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """port_forward should call the portforward API."""
        mock_pf = MagicMock()
        mock_portforward.return_value = mock_pf

        result = streaming_manager.port_forward("my-pod", ports=[(8080, 80)])

        assert result == mock_pf
        mock_portforward.assert_called_once_with(
            mock_k8s_client.core_v1.connect_get_namespaced_pod_portforward,
            name="my-pod",
            namespace="default",
            ports="80",
        )

    @patch("kubernetes.stream.portforward")
    def test_port_forward_multiple_ports(
        self,
        mock_portforward: MagicMock,
        streaming_manager: StreamingManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """port_forward should join multiple remote ports."""
        mock_portforward.return_value = MagicMock()

        streaming_manager.port_forward("my-pod", "staging", ports=[(8080, 80), (9090, 9090)])

        call_kwargs = mock_portforward.call_args[1]
        assert call_kwargs["ports"] == "80,9090"
        assert call_kwargs["namespace"] == "staging"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestResolveServiceToPod:
    """Tests for StreamingManager.resolve_service_to_pod."""

    def test_resolve_service_success(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """resolve_service_to_pod should return matching pod name."""
        mock_svc = MagicMock()
        mock_svc.spec.selector = {"app": "nginx"}
        mock_k8s_client.core_v1.read_namespaced_service.return_value = mock_svc

        mock_pod = MagicMock()
        mock_pod.metadata.name = "nginx-abc123"
        mock_pods = MagicMock()
        mock_pods.items = [mock_pod]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = mock_pods

        result = streaming_manager.resolve_service_to_pod("my-service")

        assert result == "nginx-abc123"
        mock_k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(
            namespace="default",
            label_selector="app=nginx",
        )

    def test_resolve_service_no_selector(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """resolve_service_to_pod should raise if service has no selector."""
        mock_svc = MagicMock()
        mock_svc.spec.selector = None
        mock_k8s_client.core_v1.read_namespaced_service.return_value = mock_svc

        with pytest.raises(KubernetesNotFoundError):
            streaming_manager.resolve_service_to_pod("my-service")

    def test_resolve_service_no_pods(
        self, streaming_manager: StreamingManager, mock_k8s_client: MagicMock
    ) -> None:
        """resolve_service_to_pod should raise if no pods match."""
        mock_svc = MagicMock()
        mock_svc.spec.selector = {"app": "nginx"}
        mock_k8s_client.core_v1.read_namespaced_service.return_value = mock_svc

        mock_pods = MagicMock()
        mock_pods.items = []
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = mock_pods

        with pytest.raises(KubernetesNotFoundError):
            streaming_manager.resolve_service_to_pod("my-service")
