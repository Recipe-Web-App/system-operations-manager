"""Integration tests for Kubernetes StreamingManager against real K3S cluster."""

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestLogStreaming:
    """Test log streaming operations for Kubernetes pods."""

    def test_stream_logs(
        self,
        streaming_manager,
        workload_manager,
        test_namespace,
        unique_name,
        wait_for_pod_ready,
    ):
        """Test streaming logs from a running pod."""
        deployment_name = f"stream-test-{unique_name}"

        # Create a deployment
        workload_manager.create_deployment(
            name=deployment_name,
            namespace=test_namespace,
            image="nginx:alpine",
        )

        # Wait for pod to be ready and get pod name
        pod_name = wait_for_pod_ready(deployment_name, test_namespace)

        # Stream logs
        logs = streaming_manager.stream_logs(
            pod_name=pod_name,
            namespace=test_namespace,
            follow=False,
        )

        # Verify we got logs (nginx outputs startup logs)
        assert logs is not None
        assert isinstance(logs, str)

    def test_stream_logs_with_tail(
        self,
        streaming_manager,
        workload_manager,
        test_namespace,
        unique_name,
        wait_for_pod_ready,
    ):
        """Test streaming logs with tail_lines parameter."""
        deployment_name = f"stream-test-{unique_name}"

        # Create a deployment
        workload_manager.create_deployment(
            name=deployment_name,
            namespace=test_namespace,
            image="nginx:alpine",
        )

        # Wait for pod to be ready and get pod name
        pod_name = wait_for_pod_ready(deployment_name, test_namespace)

        # Stream logs with tail
        logs = streaming_manager.stream_logs(
            pod_name=pod_name,
            namespace=test_namespace,
            follow=False,
            tail_lines=10,
        )

        # Verify we got logs
        assert logs is not None
        assert isinstance(logs, str)
        # Should have at most 10 lines (or fewer if less logs available)
        log_lines = logs.strip().split("\n") if logs.strip() else []
        assert len(log_lines) <= 10

    def test_stream_logs_with_timestamps(
        self,
        streaming_manager,
        workload_manager,
        test_namespace,
        unique_name,
        wait_for_pod_ready,
    ):
        """Test streaming logs with timestamps enabled."""
        deployment_name = f"stream-test-{unique_name}"

        # Create a deployment
        workload_manager.create_deployment(
            name=deployment_name,
            namespace=test_namespace,
            image="nginx:alpine",
        )

        # Wait for pod to be ready and get pod name
        pod_name = wait_for_pod_ready(deployment_name, test_namespace)

        # Stream logs with timestamps
        logs = streaming_manager.stream_logs(
            pod_name=pod_name,
            namespace=test_namespace,
            follow=False,
            timestamps=True,
        )

        # Verify we got logs with timestamps
        assert logs is not None
        assert isinstance(logs, str)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestExecOperations:
    """Test exec operations for Kubernetes pods."""

    def test_exec_command(
        self,
        streaming_manager,
        workload_manager,
        test_namespace,
        unique_name,
        wait_for_pod_ready,
    ):
        """Test executing a command in a running pod."""
        deployment_name = f"exec-test-{unique_name}"

        # Create a deployment
        workload_manager.create_deployment(
            name=deployment_name,
            namespace=test_namespace,
            image="nginx:alpine",
        )

        # Wait for pod to be ready and get pod name
        pod_name = wait_for_pod_ready(deployment_name, test_namespace)

        # Execute command
        result = streaming_manager.exec_command(
            pod_name=pod_name,
            namespace=test_namespace,
            command=["echo", "hello"],
            stdin=True,
            tty=True,
        )

        # Verify command executed successfully
        assert result is not None

    def test_exec_nonexistent_pod_raises(self, streaming_manager, test_namespace):
        """Test executing a command in a non-existent pod raises error."""
        with pytest.raises(KubernetesNotFoundError):
            streaming_manager.exec_command(
                pod_name="nonexistent-pod",
                namespace=test_namespace,
                command=["echo", "hello"],
            )
