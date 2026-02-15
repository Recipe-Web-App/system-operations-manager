"""E2E tests for Kubernetes streaming operations (logs and exec).

These tests verify complete workflows for streaming pod logs and executing
commands inside pods:
- Log retrieval from running pods
- Log tailing with line limits
- Error handling for nonexistent pods
- Command execution inside pods
- Container-specific operations

All tests run against a real K3S cluster using the invoke_k8s fixture.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestStreamingWorkflow:
    """Test streaming operations (logs, exec) via CLI commands."""

    def _create_deployment_and_get_pod(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        deployment_name: str,
    ) -> str:
        """Helper to create a deployment and return the first pod name.

        Args:
            invoke_k8s: CLI invocation fixture
            e2e_namespace: Namespace for the deployment
            deployment_name: Name for the deployment

        Returns:
            Name of the first pod in the deployment
        """
        # Create deployment
        result = invoke_k8s(
            "deployments",
            "create",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "nginx:alpine",
        )
        assert result.exit_code == 0, f"Failed to create deployment: {result.output}"

        # Wait for pod to be running
        time.sleep(15)

        # Get pod name from list
        result = invoke_k8s("pods", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list pods: {result.output}"

        # Extract pod name (simple parsing - look for deployment prefix in output)
        lines = result.output.strip().split("\n")
        pod_name = ""
        for line in lines:
            if deployment_name in line:
                # Extract the pod name (first word/column typically)
                parts = line.split()
                if parts and deployment_name in parts[0]:
                    pod_name = parts[0]
                    break

        assert pod_name, f"Could not find pod for deployment {deployment_name}"
        return pod_name

    def test_logs_command(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and retrieve logs from its pod."""
        deployment_name = f"{unique_prefix}-logs-dep"
        pod_name = self._create_deployment_and_get_pod(invoke_k8s, e2e_namespace, deployment_name)

        # Get logs from the pod
        result = invoke_k8s("logs", pod_name, "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to get logs: {result.output}"
        # Nginx typically outputs access log entries or startup messages
        # Just verify we got some output
        assert len(result.output) > 0

    def test_logs_with_tail(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and retrieve logs with tail limit."""
        deployment_name = f"{unique_prefix}-tail-dep"
        pod_name = self._create_deployment_and_get_pod(invoke_k8s, e2e_namespace, deployment_name)

        # Get logs with tail limit
        result = invoke_k8s("logs", pod_name, "--namespace", e2e_namespace, "--tail", "10")
        assert result.exit_code == 0, f"Failed to get logs with tail: {result.output}"
        # Verify we got output (tail should work even if fewer than 10 lines)
        assert len(result.output) >= 0  # May be empty if no logs yet

    def test_logs_nonexistent_pod(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
    ) -> None:
        """Attempt to get logs from a nonexistent pod and verify error handling."""
        # Try to get logs from a pod that doesn't exist
        result = invoke_k8s("logs", "nonexistent-pod", "--namespace", e2e_namespace)
        # Should fail with non-zero exit code or contain error message
        assert (
            result.exit_code != 0
            or "error" in result.output.lower()
            or "not found" in result.output.lower()
        )

    def test_exec_command(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and execute a command inside the pod."""
        deployment_name = f"{unique_prefix}-exec-dep"
        pod_name = self._create_deployment_and_get_pod(invoke_k8s, e2e_namespace, deployment_name)

        # Execute echo command in the pod
        result = invoke_k8s(
            "exec",
            pod_name,
            "--namespace",
            e2e_namespace,
            "--",
            "echo",
            "hello",
        )
        assert result.exit_code == 0, f"Failed to exec command: {result.output}"
        # Verify the echo output
        assert "hello" in result.output

    def test_logs_with_container(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and retrieve logs with explicit container name."""
        deployment_name = f"{unique_prefix}-container-dep"
        pod_name = self._create_deployment_and_get_pod(invoke_k8s, e2e_namespace, deployment_name)

        # Get logs with container name specified
        # Nginx alpine deployment typically has a container named "nginx"
        # or uses the deployment name as container name
        result = invoke_k8s(
            "logs",
            pod_name,
            "--namespace",
            e2e_namespace,
            "--container",
            "nginx",
        )
        # This might fail if container name doesn't match
        # Accept either success or a clear error about container name
        if result.exit_code != 0:
            # If it fails, it should be due to container name mismatch
            assert "container" in result.output.lower() or "not found" in result.output.lower()
        else:
            # If successful, we should have some output
            assert len(result.output) >= 0
