"""E2E tests for Kubernetes ConfigMap and Secret management workflows.

These tests verify complete workflows for managing configuration via CLI:
- Creating and listing ConfigMaps
- Getting ConfigMap details
- Deleting ConfigMaps
- Creating and listing Secrets
- Getting Secret details (without exposing values)
- Deleting Secrets
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
class TestConfigMapWorkflow:
    """Test ConfigMap management workflows."""

    def test_create_configmap(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a ConfigMap with data."""
        cm_name = f"{unique_prefix}-cm-create"

        # Create ConfigMap
        result = invoke_k8s(
            "configmaps",
            "create",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "key1=value1",
        )
        assert result.exit_code == 0, f"Failed to create ConfigMap: {result.output}"

        # Clean up
        result = invoke_k8s(
            "configmaps",
            "delete",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete ConfigMap: {result.output}"

    def test_list_configmaps(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a ConfigMap and verify it appears in list."""
        cm_name = f"{unique_prefix}-cm-list"

        # Create ConfigMap
        result = invoke_k8s(
            "configmaps",
            "create",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "key1=value1",
        )
        assert result.exit_code == 0, f"Failed to create ConfigMap: {result.output}"

        # List ConfigMaps
        result = invoke_k8s("configmaps", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list ConfigMaps: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "configmaps",
            "delete",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete ConfigMap: {result.output}"

    def test_get_configmap(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a ConfigMap and get its details."""
        cm_name = f"{unique_prefix}-cm-get"

        # Create ConfigMap
        result = invoke_k8s(
            "configmaps",
            "create",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "key1=value1",
        )
        assert result.exit_code == 0, f"Failed to create ConfigMap: {result.output}"

        # Get ConfigMap
        result = invoke_k8s(
            "configmaps",
            "get",
            cm_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get ConfigMap: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "configmaps",
            "delete",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete ConfigMap: {result.output}"

    def test_delete_configmap(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create and delete a ConfigMap."""
        cm_name = f"{unique_prefix}-cm-delete"

        # Create ConfigMap
        result = invoke_k8s(
            "configmaps",
            "create",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "key1=value1",
        )
        assert result.exit_code == 0, f"Failed to create ConfigMap: {result.output}"

        # Delete ConfigMap
        result = invoke_k8s(
            "configmaps",
            "delete",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete ConfigMap: {result.output}"

    def test_configmap_json_output(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """List ConfigMaps with JSON output format."""
        cm_name = f"{unique_prefix}-cm-json"

        # Create ConfigMap
        result = invoke_k8s(
            "configmaps",
            "create",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "key1=value1",
        )
        assert result.exit_code == 0, f"Failed to create ConfigMap: {result.output}"

        # List ConfigMaps with JSON output
        result = invoke_k8s(
            "configmaps",
            "list",
            "--namespace",
            e2e_namespace,
            "--output",
            "json",
        )
        assert result.exit_code == 0, f"Failed to list ConfigMaps with JSON output: {result.output}"
        # JSON output should contain brackets or braces
        assert "{" in result.output or "[" in result.output

        # Clean up
        result = invoke_k8s(
            "configmaps",
            "delete",
            cm_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete ConfigMap: {result.output}"


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestSecretWorkflow:
    """Test Secret management workflows."""

    def test_create_secret(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a Secret with data."""
        secret_name = f"{unique_prefix}-secret-create"

        # Create Secret
        result = invoke_k8s(
            "secrets",
            "create",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "password=secret123",
        )
        assert result.exit_code == 0, f"Failed to create Secret: {result.output}"

        # Clean up
        result = invoke_k8s(
            "secrets",
            "delete",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete Secret: {result.output}"

    def test_list_secrets(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a Secret and verify it appears in list."""
        secret_name = f"{unique_prefix}-secret-list"

        # Create Secret
        result = invoke_k8s(
            "secrets",
            "create",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "password=secret123",
        )
        assert result.exit_code == 0, f"Failed to create Secret: {result.output}"

        # List Secrets
        result = invoke_k8s("secrets", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list Secrets: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "secrets",
            "delete",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete Secret: {result.output}"

    def test_get_secret(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a Secret and get its details."""
        secret_name = f"{unique_prefix}-secret-get"

        # Create Secret
        result = invoke_k8s(
            "secrets",
            "create",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "password=secret123",
        )
        assert result.exit_code == 0, f"Failed to create Secret: {result.output}"

        # Get Secret
        result = invoke_k8s(
            "secrets",
            "get",
            secret_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get Secret: {result.output}"
        assert unique_prefix in result.output

        # Clean up
        result = invoke_k8s(
            "secrets",
            "delete",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete Secret: {result.output}"

    def test_delete_secret(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create and delete a Secret."""
        secret_name = f"{unique_prefix}-secret-delete"

        # Create Secret
        result = invoke_k8s(
            "secrets",
            "create",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--data",
            "password=secret123",
        )
        assert result.exit_code == 0, f"Failed to create Secret: {result.output}"

        # Delete Secret
        result = invoke_k8s(
            "secrets",
            "delete",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete Secret: {result.output}"

    def test_secret_values_not_exposed(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Verify that secret values are not exposed in plain text."""
        secret_name = f"{unique_prefix}-secret-secure"
        secret_value = "supersecret123"

        # Create Secret
        result = invoke_k8s(
            "secrets",
            "create",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--data",
            f"password={secret_value}",
        )
        assert result.exit_code == 0, f"Failed to create Secret: {result.output}"

        # Get Secret and verify the plain text value is not in output
        result = invoke_k8s(
            "secrets",
            "get",
            secret_name,
            "--namespace",
            e2e_namespace,
        )
        assert result.exit_code == 0, f"Failed to get Secret: {result.output}"
        assert unique_prefix in result.output
        # The actual secret value should NOT appear in plain text
        assert secret_value not in result.output

        # Clean up
        result = invoke_k8s(
            "secrets",
            "delete",
            secret_name,
            "--namespace",
            e2e_namespace,
            "--force",
        )
        assert result.exit_code == 0, f"Failed to delete Secret: {result.output}"
