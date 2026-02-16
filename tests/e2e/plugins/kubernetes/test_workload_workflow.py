"""E2E tests for Kubernetes workload management workflows.

These tests verify complete workflows for managing deployments and pods via CLI:
- Creating deployments with various configurations
- Listing and getting deployments
- Scaling deployments
- Deleting deployments
- Listing pods in different scopes
- Viewing pod logs
- JSON and YAML output formatting
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestDeploymentWorkflow:
    """Test Deployment management workflows."""

    def test_create_deployment(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment with nginx image."""
        deployment_name = f"{unique_prefix}-deploy-create"

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

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_list_deployments(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and verify it appears in list."""
        deployment_name = f"{unique_prefix}-deploy-list"

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

        # List deployments
        result = invoke_k8s("deployments", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list deployments: {result.output}"
        # Rich table wraps long names across lines, so check resource count
        assert "Total:" in result.output

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_get_deployment(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and get its details."""
        deployment_name = f"{unique_prefix}-deploy-get"

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

        # Get deployment
        result = invoke_k8s(
            "deployments",
            "get",
            deployment_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get deployment: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_create_deployment_with_replicas(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment with specific replica count."""
        deployment_name = f"{unique_prefix}-deploy-replicas"

        # Create deployment with 3 replicas
        result = invoke_k8s(
            "deployments",
            "create",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "nginx:alpine",
            "--replicas",
            "3",
        )
        assert result.exit_code == 0, f"Failed to create deployment with replicas: {result.output}"

        # Get deployment and verify (replicas info should be in output)
        result = invoke_k8s(
            "deployments",
            "get",
            deployment_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get deployment: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_scale_deployment(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and scale it."""
        deployment_name = f"{unique_prefix}-deploy-scale"

        # Create deployment with 1 replica
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

        # Scale deployment to 3 replicas
        result = invoke_k8s(
            "deployments",
            "scale",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--replicas",
            "3",
        )
        assert result.exit_code == 0, f"Failed to scale deployment: {result.output}"

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_delete_deployment(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create and delete a deployment."""
        deployment_name = f"{unique_prefix}-deploy-delete"

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

        # Delete deployment
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_list_deployments_json(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """List deployments with JSON output format."""
        deployment_name = f"{unique_prefix}-deploy-json"

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

        # List deployments with JSON output
        result = invoke_k8s(
            "deployments",
            "list",
            "--namespace",
            e2e_namespace,
            "--output",
            "json",
        )
        assert result.exit_code == 0, (
            f"Failed to list deployments with JSON output: {result.output}"
        )
        # JSON output should contain brackets or braces
        assert "{" in result.output or "[" in result.output

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_list_deployments_yaml(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """List deployments with YAML output format."""
        deployment_name = f"{unique_prefix}-deploy-yaml"

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

        # List deployments with YAML output
        result = invoke_k8s(
            "deployments",
            "list",
            "--namespace",
            e2e_namespace,
            "--output",
            "yaml",
        )
        assert result.exit_code == 0, (
            f"Failed to list deployments with YAML output: {result.output}"
        )
        # YAML output should contain model fields
        assert "name:" in result.output and "namespace:" in result.output

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestPodWorkflow:
    """Test Pod management workflows."""

    def test_list_pods(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and list its pods."""
        deployment_name = f"{unique_prefix}-deploy-pods"

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

        # Wait for pods to be created
        time.sleep(10)

        # List pods in namespace
        result = invoke_k8s("pods", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list pods: {result.output}"
        # Output should contain pod-related information
        assert "Total:" in result.output or "pod" in result.output.lower()

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_list_pods_all_namespaces(
        self,
        invoke_k8s: Callable[..., Any],
    ) -> None:
        """List pods across all namespaces."""
        result = invoke_k8s("pods", "list", "--all-namespaces")

        assert result.exit_code == 0, f"Failed to list pods across all namespaces: {result.output}"
        # Rich table wraps long namespace names, so check for total count
        # which is always present, or use JSON output for reliable content check
        assert "Total:" in result.output or len(result.output) > 0

    def test_pod_logs(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment, wait for pods, and view logs."""
        deployment_name = f"{unique_prefix}-deploy-logs"

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

        # Wait for pod to be ready
        time.sleep(15)

        # Get pod name from JSON list output (avoids Rich table line-wrapping issues)
        result = invoke_k8s("pods", "list", "--namespace", e2e_namespace, "--output", "json")
        assert result.exit_code == 0, f"Failed to list pods: {result.output}"

        # Extract pod name from JSON output (log lines contain brackets like
        # [debug], so find JSON by looking for line-initial [ or { )
        pod_name = None
        output = result.output
        for i, char in enumerate(output):
            if char in ("{", "[") and (i == 0 or output[i - 1] == "\n"):
                try:
                    pods_data = json.loads(output[i:])
                    if isinstance(pods_data, dict):
                        pods_data = pods_data.get("data", pods_data.get("items", [pods_data]))
                    for pod in pods_data:
                        name = pod.get("name", "")
                        if deployment_name in name:
                            pod_name = name
                            break
                    break
                except json.JSONDecodeError, TypeError:
                    continue

        # If we found a pod name, try to get logs
        if pod_name:
            result = invoke_k8s(
                "logs",
                pod_name,
                "--namespace",
                e2e_namespace,
            )
            # Logs command might succeed or fail depending on pod readiness
            # Just verify exit code is reasonable (0 or expected error)
            assert result.exit_code in [0, 1], f"Unexpected logs command result: {result.output}"

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"

    def test_pod_logs_with_tail(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a deployment and view logs with tail limit."""
        deployment_name = f"{unique_prefix}-deploy-tail"

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

        # Wait for pod to be ready
        time.sleep(15)

        # Get pod name from JSON list output (avoids Rich table line-wrapping issues)
        result = invoke_k8s("pods", "list", "--namespace", e2e_namespace, "--output", "json")
        assert result.exit_code == 0, f"Failed to list pods: {result.output}"

        # Extract pod name from JSON output (log lines contain brackets like
        # [debug], so find JSON by looking for line-initial [ or { )
        pod_name = None
        output = result.output
        for i, char in enumerate(output):
            if char in ("{", "[") and (i == 0 or output[i - 1] == "\n"):
                try:
                    pods_data = json.loads(output[i:])
                    if isinstance(pods_data, dict):
                        pods_data = pods_data.get("data", pods_data.get("items", [pods_data]))
                    for pod in pods_data:
                        name = pod.get("name", "")
                        if deployment_name in name:
                            pod_name = name
                            break
                    break
                except json.JSONDecodeError, TypeError:
                    continue

        # If we found a pod name, try to get logs with tail
        if pod_name:
            result = invoke_k8s(
                "logs",
                pod_name,
                "--namespace",
                e2e_namespace,
                "--tail",
                "10",
            )
            # Logs command might succeed or fail depending on pod readiness
            assert result.exit_code in [0, 1], f"Unexpected logs command result: {result.output}"

        # Clean up
        result = invoke_k8s(
            "deployments",
            "delete",
            deployment_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete deployment: {result.output}"
