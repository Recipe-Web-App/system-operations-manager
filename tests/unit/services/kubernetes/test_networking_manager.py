"""Unit tests for NetworkingManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.networking_manager import (
    NetworkingManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def networking_manager(mock_k8s_client: MagicMock) -> NetworkingManager:
    """Create a NetworkingManager instance with mocked client."""
    return NetworkingManager(mock_k8s_client)


class TestServiceOperations:
    """Tests for Service operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_services_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list services successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_service.return_value = mock_response

        result = networking_manager.list_services()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_services_empty(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no services exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_service.return_value = mock_response

        result = networking_manager.list_services()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_services_all_namespaces(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list services across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_service_for_all_namespaces.return_value = mock_response

        result = networking_manager.list_services(all_namespaces=True)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_services_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing services."""
        mock_k8s_client.core_v1.list_namespaced_service.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.list_services()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_service_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get service successfully."""
        mock_service = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_service.return_value = mock_service

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.ServiceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.get_service("test-svc")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_service_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting service."""
        mock_k8s_client.core_v1.read_namespaced_service.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.get_service("test-svc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_service_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create service successfully."""
        mock_service = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_service.return_value = mock_service

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.ServiceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.create_service("test-svc", type="ClusterIP")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_service_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating service."""
        mock_k8s_client.core_v1.create_namespaced_service.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.create_service("test-svc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_service_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update service successfully."""
        mock_service = MagicMock()
        mock_k8s_client.core_v1.patch_namespaced_service.return_value = mock_service

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.ServiceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.update_service("test-svc", type="LoadBalancer")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_service_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating service."""
        mock_k8s_client.core_v1.patch_namespaced_service.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.update_service("test-svc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_service_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete service successfully."""
        networking_manager.delete_service("test-svc")

        mock_k8s_client.core_v1.delete_namespaced_service.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_service_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting service."""
        mock_k8s_client.core_v1.delete_namespaced_service.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.delete_service("test-svc")


class TestIngressOperations:
    """Tests for Ingress operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_ingresses_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list ingresses successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.networking_v1.list_namespaced_ingress.return_value = mock_response

        result = networking_manager.list_ingresses()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_ingresses_empty(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no ingresses exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.networking_v1.list_namespaced_ingress.return_value = mock_response

        result = networking_manager.list_ingresses()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_ingresses_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing ingresses."""
        mock_k8s_client.networking_v1.list_namespaced_ingress.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.list_ingresses()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_ingress_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get ingress successfully."""
        mock_ingress = MagicMock()
        mock_k8s_client.networking_v1.read_namespaced_ingress.return_value = mock_ingress

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.IngressSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.get_ingress("test-ing")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_ingress_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting ingress."""
        mock_k8s_client.networking_v1.read_namespaced_ingress.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.get_ingress("test-ing")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_ingress_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create ingress successfully."""
        mock_ingress = MagicMock()
        mock_k8s_client.networking_v1.create_namespaced_ingress.return_value = mock_ingress

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.IngressSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.create_ingress("test-ing", class_name="nginx")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_ingress_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating ingress."""
        mock_k8s_client.networking_v1.create_namespaced_ingress.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.create_ingress("test-ing")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_ingress_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update ingress successfully."""
        mock_ingress = MagicMock()
        mock_k8s_client.networking_v1.patch_namespaced_ingress.return_value = mock_ingress

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.IngressSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.update_ingress("test-ing", class_name="traefik")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_ingress_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating ingress."""
        mock_k8s_client.networking_v1.patch_namespaced_ingress.side_effect = Exception(
            "Update error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.update_ingress("test-ing")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_ingress_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete ingress successfully."""
        networking_manager.delete_ingress("test-ing")

        mock_k8s_client.networking_v1.delete_namespaced_ingress.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_ingress_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting ingress."""
        mock_k8s_client.networking_v1.delete_namespaced_ingress.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.delete_ingress("test-ing")


class TestNetworkPolicyOperations:
    """Tests for NetworkPolicy operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_network_policies_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list network policies successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.networking_v1.list_namespaced_network_policy.return_value = mock_response

        result = networking_manager.list_network_policies()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_network_policies_empty(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no network policies exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.networking_v1.list_namespaced_network_policy.return_value = mock_response

        result = networking_manager.list_network_policies()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_network_policies_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing network policies."""
        mock_k8s_client.networking_v1.list_namespaced_network_policy.side_effect = Exception(
            "API error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.list_network_policies()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_network_policy_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get network policy successfully."""
        mock_netpol = MagicMock()
        mock_k8s_client.networking_v1.read_namespaced_network_policy.return_value = mock_netpol

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkPolicySummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.get_network_policy("test-netpol")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_network_policy_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting network policy."""
        mock_k8s_client.networking_v1.read_namespaced_network_policy.side_effect = Exception(
            "Not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.get_network_policy("test-netpol")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_network_policy_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create network policy successfully."""
        mock_netpol = MagicMock()
        mock_k8s_client.networking_v1.create_namespaced_network_policy.return_value = mock_netpol

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkPolicySummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.create_network_policy("test-netpol")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_network_policy_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating network policy."""
        mock_k8s_client.networking_v1.create_namespaced_network_policy.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.create_network_policy("test-netpol")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_network_policy_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete network policy successfully."""
        networking_manager.delete_network_policy("test-netpol")

        mock_k8s_client.networking_v1.delete_namespaced_network_policy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_network_policy_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting network policy."""
        mock_k8s_client.networking_v1.delete_namespaced_network_policy.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.delete_network_policy("test-netpol")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_network_policy_success(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update network policy successfully."""
        mock_netpol = MagicMock()
        mock_k8s_client.networking_v1.patch_namespaced_network_policy.return_value = mock_netpol

        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkPolicySummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = networking_manager.update_network_policy(
                "test-netpol", pod_selector={"app": "web"}, policy_types=["Ingress"]
            )

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_network_policy_error(
        self, networking_manager: NetworkingManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating network policy."""
        mock_k8s_client.networking_v1.patch_namespaced_network_policy.side_effect = Exception(
            "Update error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            networking_manager.update_network_policy("test-netpol")
