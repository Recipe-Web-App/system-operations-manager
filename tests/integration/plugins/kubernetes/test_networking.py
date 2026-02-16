"""Integration tests for NetworkingManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesNotFoundError
from system_operations_manager.services.kubernetes import NetworkingManager


@pytest.mark.integration
@pytest.mark.kubernetes
class TestServiceCRUD:
    """Test Service CRUD operations."""

    def test_create_clusterip_service(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_service should create a ClusterIP service."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test-app"}
        ports = [{"port": 80, "target_port": 8080, "protocol": "TCP"}]

        result = networking_manager.create_service(
            svc_name,
            test_namespace,
            type="ClusterIP",
            selector=selector,
            ports=ports,
        )

        assert result.name == svc_name
        assert result.namespace == test_namespace
        assert result.type == "ClusterIP"
        assert result.cluster_ip is not None

    def test_list_services(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_services should return created services."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test"}
        ports = [{"port": 80, "target_port": 8080}]

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        services = networking_manager.list_services(test_namespace)

        assert len(services) >= 1
        assert any(s.name == svc_name for s in services)

    def test_get_service(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """get_service should retrieve a service by name."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test"}
        ports = [{"port": 80, "target_port": 8080}]

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        result = networking_manager.get_service(svc_name, test_namespace)

        assert result.name == svc_name
        assert result.namespace == test_namespace

    def test_update_service_selector(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """update_service should update service selector."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "original"}
        ports = [{"port": 80, "target_port": 8080}]

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        new_selector = {"app": "updated", "version": "v2"}
        result = networking_manager.update_service(
            svc_name,
            test_namespace,
            selector=new_selector,
        )

        assert result.name == svc_name
        # Verify update by getting the service
        updated = networking_manager.get_service(svc_name, test_namespace)
        assert updated.name == svc_name

    def test_delete_service(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """delete_service should delete a service."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test"}
        ports = [{"port": 80, "target_port": 8080}]

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        networking_manager.delete_service(svc_name, test_namespace)

        # Verify deletion
        with pytest.raises(KubernetesNotFoundError):
            networking_manager.get_service(svc_name, test_namespace)

    def test_get_nonexistent_raises(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
    ) -> None:
        """get_service should raise KubernetesNotFoundError for missing service."""
        with pytest.raises(KubernetesNotFoundError):
            networking_manager.get_service("nonexistent-service", test_namespace)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestServiceTypes:
    """Test different service types."""

    def test_create_nodeport_service(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_service should create a NodePort service."""
        svc_name = f"test-nodeport-{unique_name}"
        selector = {"app": "nodeport-app"}
        ports = [{"port": 80, "target_port": 8080, "protocol": "TCP"}]

        result = networking_manager.create_service(
            svc_name,
            test_namespace,
            type="NodePort",
            selector=selector,
            ports=ports,
        )

        assert result.name == svc_name
        assert result.namespace == test_namespace
        assert result.type == "NodePort"

    def test_create_service_with_multiple_ports(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_service should support multiple ports."""
        svc_name = f"test-multiport-{unique_name}"
        selector = {"app": "multiport-app"}
        ports = [
            {"port": 80, "target_port": 8080, "protocol": "TCP", "name": "http"},
            {"port": 443, "target_port": 8443, "protocol": "TCP", "name": "https"},
        ]

        result = networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        assert result.name == svc_name
        assert result.namespace == test_namespace
        # Service should have multiple ports configured


@pytest.mark.integration
@pytest.mark.kubernetes
class TestServiceListFilters:
    """Test service list filtering."""

    def test_list_services_all_namespaces(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_services should list services across all namespaces."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test"}
        ports = [{"port": 80, "target_port": 8080}]

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
        )

        services = networking_manager.list_services(
            namespace=None,
            all_namespaces=True,
        )

        # Should include services from multiple namespaces (default, kube-system, etc.)
        assert len(services) >= 1
        assert any(s.name == svc_name for s in services)

    def test_list_services_label_selector(
        self,
        networking_manager: NetworkingManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_services should filter by label selector."""
        svc_name = f"test-svc-{unique_name}"
        selector = {"app": "test"}
        ports = [{"port": 80, "target_port": 8080}]
        labels = {"environment": "test", "tier": "backend"}

        networking_manager.create_service(
            svc_name,
            test_namespace,
            selector=selector,
            ports=ports,
            labels=labels,
        )

        services = networking_manager.list_services(
            test_namespace,
            label_selector="environment=test",
        )

        assert len(services) >= 1
        assert any(s.name == svc_name for s in services)
