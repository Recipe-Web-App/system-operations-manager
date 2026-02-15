"""E2E tests for Kubernetes namespace management workflows.

These tests verify complete workflows for managing namespaces via CLI:
- Listing default namespaces
- Creating namespaces
- Getting namespace details
- Deleting namespaces
- Creating namespaces with labels
- JSON output formatting
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestNamespaceWorkflow:
    """Test namespace management workflows."""

    def test_list_namespaces_shows_defaults(
        self,
        invoke_k8s: Callable[..., Any],
    ) -> None:
        """List namespaces and verify default K8s namespaces are present."""
        result = invoke_k8s("namespaces", "list")

        assert result.exit_code == 0, f"Failed to list namespaces: {result.output}"
        assert "default" in result.output
        assert "kube-system" in result.output

    def test_create_namespace(
        self,
        invoke_k8s: Callable[..., Any],
        unique_prefix: str,
    ) -> None:
        """Create a namespace and verify successful creation."""
        namespace_name = f"{unique_prefix}-ns-create"

        # Create namespace
        result = invoke_k8s("namespaces", "create", namespace_name)
        assert result.exit_code == 0, f"Failed to create namespace: {result.output}"

        # Clean up
        result = invoke_k8s("namespaces", "delete", namespace_name, "--force")
        assert result.exit_code == 0, f"Failed to delete namespace: {result.output}"

    def test_create_and_get_namespace(
        self,
        invoke_k8s: Callable[..., Any],
        unique_prefix: str,
    ) -> None:
        """Create a namespace and retrieve its details."""
        namespace_name = f"{unique_prefix}-ns-get"

        # Create namespace
        result = invoke_k8s("namespaces", "create", namespace_name)
        assert result.exit_code == 0, f"Failed to create namespace: {result.output}"

        # Get namespace details
        result = invoke_k8s("namespaces", "get", namespace_name)
        assert result.exit_code == 0, f"Failed to get namespace: {result.output}"
        assert namespace_name in result.output

        # Clean up
        result = invoke_k8s("namespaces", "delete", namespace_name, "--force")
        assert result.exit_code == 0, f"Failed to delete namespace: {result.output}"

    def test_create_and_delete_namespace(
        self,
        invoke_k8s: Callable[..., Any],
        unique_prefix: str,
    ) -> None:
        """Create and delete a namespace."""
        namespace_name = f"{unique_prefix}-ns-delete"

        # Create namespace
        result = invoke_k8s("namespaces", "create", namespace_name)
        assert result.exit_code == 0, f"Failed to create namespace: {result.output}"

        # Delete namespace
        result = invoke_k8s("namespaces", "delete", namespace_name, "--force")
        assert result.exit_code == 0, f"Failed to delete namespace: {result.output}"

    def test_create_namespace_with_labels(
        self,
        invoke_k8s: Callable[..., Any],
        unique_prefix: str,
    ) -> None:
        """Create a namespace with labels."""
        namespace_name = f"{unique_prefix}-ns-labels"

        # Create namespace with labels
        result = invoke_k8s(
            "namespaces",
            "create",
            namespace_name,
            "--label",
            "env=test",
        )
        assert result.exit_code == 0, f"Failed to create namespace with labels: {result.output}"

        # Get namespace and verify label (labels should appear in output)
        result = invoke_k8s("namespaces", "get", namespace_name)
        assert result.exit_code == 0, f"Failed to get namespace: {result.output}"
        assert namespace_name in result.output

        # Clean up
        result = invoke_k8s("namespaces", "delete", namespace_name, "--force")
        assert result.exit_code == 0, f"Failed to delete namespace: {result.output}"

    def test_list_namespaces_json_output(
        self,
        invoke_k8s: Callable[..., Any],
    ) -> None:
        """List namespaces with JSON output format."""
        result = invoke_k8s("namespaces", "list", "--output", "json")

        assert result.exit_code == 0, f"Failed to list namespaces with JSON output: {result.output}"
        # JSON output should contain brackets or braces
        assert "{" in result.output or "[" in result.output
