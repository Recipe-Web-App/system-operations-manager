"""Unit tests for KubernetesApp and ResourceType enum.

Tests the main TUI application for Kubernetes resource browsing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.binding import Binding

from system_operations_manager.tui.apps.kubernetes.app import (
    CLUSTER_SCOPED_TYPES,
    RESOURCE_TYPE_ORDER,
    KubernetesApp,
    ResourceType,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock KubernetesClient."""
    client = MagicMock()
    client.default_namespace = "default"
    client.get_current_context.return_value = "minikube"
    client.list_contexts.return_value = [
        {"name": "minikube", "cluster": "minikube", "namespace": "default"},
        {"name": "production", "cluster": "prod-cluster", "namespace": "default"},
    ]
    return client


# ============================================================================
# ResourceType Enum Tests
# ============================================================================


class TestResourceType:
    """Tests for ResourceType enum."""

    @pytest.mark.unit
    def test_resource_type_has_all_workload_types(self) -> None:
        """ResourceType includes all workload resource types."""
        workload_types = {
            ResourceType.PODS,
            ResourceType.DEPLOYMENTS,
            ResourceType.STATEFULSETS,
            ResourceType.DAEMONSETS,
            ResourceType.REPLICASETS,
        }
        assert workload_types.issubset(set(ResourceType))

    @pytest.mark.unit
    def test_resource_type_has_all_networking_types(self) -> None:
        """ResourceType includes all networking resource types."""
        networking_types = {
            ResourceType.SERVICES,
            ResourceType.INGRESSES,
            ResourceType.NETWORK_POLICIES,
        }
        assert networking_types.issubset(set(ResourceType))

    @pytest.mark.unit
    def test_resource_type_has_all_config_types(self) -> None:
        """ResourceType includes all configuration resource types."""
        config_types = {
            ResourceType.CONFIGMAPS,
            ResourceType.SECRETS,
        }
        assert config_types.issubset(set(ResourceType))

    @pytest.mark.unit
    def test_resource_type_has_all_cluster_types(self) -> None:
        """ResourceType includes all cluster resource types."""
        cluster_types = {
            ResourceType.NAMESPACES,
            ResourceType.NODES,
            ResourceType.EVENTS,
        }
        assert cluster_types.issubset(set(ResourceType))

    @pytest.mark.unit
    def test_resource_type_total_count(self) -> None:
        """ResourceType has exactly 13 resource types."""
        assert len(ResourceType) == 13

    @pytest.mark.unit
    def test_resource_type_values_are_human_readable(self) -> None:
        """ResourceType values are human-readable strings."""
        for rt in ResourceType:
            assert isinstance(rt.value, str)
            assert len(rt.value) > 0

    @pytest.mark.unit
    def test_cluster_scoped_types(self) -> None:
        """CLUSTER_SCOPED_TYPES contains only non-namespaced types."""
        assert ResourceType.NAMESPACES in CLUSTER_SCOPED_TYPES
        assert ResourceType.NODES in CLUSTER_SCOPED_TYPES
        assert ResourceType.PODS not in CLUSTER_SCOPED_TYPES
        assert ResourceType.SERVICES not in CLUSTER_SCOPED_TYPES

    @pytest.mark.unit
    def test_resource_type_order_contains_all_types(self) -> None:
        """RESOURCE_TYPE_ORDER contains all ResourceType members."""
        assert set(RESOURCE_TYPE_ORDER) == set(ResourceType)
        assert len(RESOURCE_TYPE_ORDER) == len(ResourceType)


# ============================================================================
# KubernetesApp Initialization Tests
# ============================================================================


class TestKubernetesAppInit:
    """Tests for KubernetesApp initialization."""

    @pytest.mark.unit
    def test_app_stores_client(self, mock_client: MagicMock) -> None:
        """App stores the Kubernetes client."""
        app = KubernetesApp(client=mock_client)
        assert app._client is mock_client

    @pytest.mark.unit
    def test_app_has_title(self, mock_client: MagicMock) -> None:
        """App has a title."""
        app = KubernetesApp(client=mock_client)
        assert app.TITLE == "Kubernetes Resource Browser"

    @pytest.mark.unit
    def test_app_has_css_path(self, mock_client: MagicMock) -> None:
        """App has a CSS path."""
        app = KubernetesApp(client=mock_client)
        assert app.CSS_PATH == "styles.tcss"

    @pytest.mark.unit
    def test_app_has_bindings(self, mock_client: MagicMock) -> None:
        """App defines keyboard bindings."""
        app = KubernetesApp(client=mock_client)
        assert len(app.BINDINGS) > 0

    @pytest.mark.unit
    def test_app_bindings_include_ecosystem(self) -> None:
        """App bindings include 'e' for ecosystem view."""
        binding_keys = [b.key if isinstance(b, Binding) else b[0] for b in KubernetesApp.BINDINGS]
        assert "e" in binding_keys


# ============================================================================
# KubernetesApp Async Tests
# ============================================================================


class TestKubernetesAppAsync:
    """Async tests for KubernetesApp."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_starts_with_resource_list_screen(self, mock_client: MagicMock) -> None:
        """App starts on ResourceListScreen."""
        app = KubernetesApp(client=mock_client)

        with (
            patch(
                "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
            ) as mock_ns_mgr_cls,
            patch(
                "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
            ) as mock_wl_mgr_cls,
        ):
            mock_ns_mgr_cls.return_value.list_namespaces.return_value = []
            mock_wl_mgr_cls.return_value.list_pods.return_value = []

            async with app.run_test():
                from system_operations_manager.tui.apps.kubernetes.screens import (
                    ResourceListScreen,
                )

                assert isinstance(app.screen, ResourceListScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_quit_action(self, mock_client: MagicMock) -> None:
        """Quit action exits the app."""
        app = KubernetesApp(client=mock_client)

        with (
            patch(
                "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
            ) as mock_ns_mgr_cls,
            patch(
                "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
            ) as mock_wl_mgr_cls,
        ):
            mock_ns_mgr_cls.return_value.list_namespaces.return_value = []
            mock_wl_mgr_cls.return_value.list_pods.return_value = []

            async with app.run_test() as pilot:
                await pilot.press("q")
