"""E2E tests for Kubernetes networking management workflows.

These tests verify complete workflows for managing services via CLI:
- Creating services with various configurations
- Listing services
- Getting service details
- Creating NodePort services
- Deleting services
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
class TestServiceWorkflow:
    """Test Service management workflows."""

    def test_create_service(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a service with port mapping."""
        service_name = f"{unique_prefix}-svc-create"

        # Create service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # Clean up
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"

    def test_list_services(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a service and verify it appears in list."""
        service_name = f"{unique_prefix}-svc-list"

        # Create service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # List services
        result = invoke_k8s("services", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list services: {result.output}"
        assert service_name in result.output

        # Clean up
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"

    def test_get_service(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a service and get its details."""
        service_name = f"{unique_prefix}-svc-get"

        # Create service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # Get service
        result = invoke_k8s(
            "services",
            "get",
            service_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get service: {result.output}"
        assert service_name in result.output

        # Clean up
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"

    def test_create_nodeport_service(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a NodePort service."""
        service_name = f"{unique_prefix}-svc-nodeport"

        # Create NodePort service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
            "--type",
            "NodePort",
        )
        assert result.exit_code == 0, f"Failed to create NodePort service: {result.output}"

        # Get service and verify type
        result = invoke_k8s(
            "services",
            "get",
            service_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get service: {result.output}"
        assert service_name in result.output
        # NodePort should be mentioned in the output
        assert "NodePort" in result.output or "nodeport" in result.output.lower()

        # Clean up
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"

    def test_delete_service(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create and delete a service."""
        service_name = f"{unique_prefix}-svc-delete"

        # Create service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # Delete service
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"

    def test_list_services_json(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """List services with JSON output format."""
        service_name = f"{unique_prefix}-svc-json"

        # Create service
        result = invoke_k8s(
            "services",
            "create",
            service_name,
            "--namespace",
            e2e_namespace,
            "--port",
            "80:8080",
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # List services with JSON output
        result = invoke_k8s(
            "services",
            "list",
            "--namespace",
            e2e_namespace,
            "--output",
            "json",
        )
        assert result.exit_code == 0, f"Failed to list services with JSON output: {result.output}"
        # JSON output should contain brackets or braces
        assert "{" in result.output or "[" in result.output

        # Clean up
        result = invoke_k8s(
            "services",
            "delete",
            service_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete service: {result.output}"
