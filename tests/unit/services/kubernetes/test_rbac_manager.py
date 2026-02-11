"""Unit tests for RBACManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.rbac_manager import RBACManager


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def rbac_manager(mock_k8s_client: MagicMock) -> RBACManager:
    """Create an RBACManager instance with mocked client."""
    return RBACManager(mock_k8s_client)


class TestServiceAccountOperations:
    """Tests for ServiceAccount operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_service_accounts_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list service accounts successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_service_account.return_value = mock_response

        result = rbac_manager.list_service_accounts()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_service_accounts_empty(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no service accounts exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_service_account.return_value = mock_response

        result = rbac_manager.list_service_accounts()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_service_accounts_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing service accounts."""
        mock_k8s_client.core_v1.list_namespaced_service_account.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.list_service_accounts()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_service_account_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get service account successfully."""
        mock_sa = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_service_account.return_value = mock_sa

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.ServiceAccountSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.get_service_account("test-sa")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_service_account_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting service account."""
        mock_k8s_client.core_v1.read_namespaced_service_account.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.get_service_account("test-sa")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_service_account_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create service account successfully."""
        mock_sa = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_service_account.return_value = mock_sa

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.ServiceAccountSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.create_service_account("test-sa")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_service_account_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating service account."""
        mock_k8s_client.core_v1.create_namespaced_service_account.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.create_service_account("test-sa")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_service_account_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete service account successfully."""
        rbac_manager.delete_service_account("test-sa")

        mock_k8s_client.core_v1.delete_namespaced_service_account.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_service_account_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting service account."""
        mock_k8s_client.core_v1.delete_namespaced_service_account.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.delete_service_account("test-sa")


class TestRoleOperations:
    """Tests for Role operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_roles_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list roles successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_namespaced_role.return_value = mock_response

        result = rbac_manager.list_roles()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_roles_empty(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should return empty list when no roles exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_namespaced_role.return_value = mock_response

        result = rbac_manager.list_roles()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_roles_error(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when listing roles."""
        mock_k8s_client.rbac_v1.list_namespaced_role.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.list_roles()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_role_success(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should get role successfully."""
        mock_role = MagicMock()
        mock_k8s_client.rbac_v1.read_namespaced_role.return_value = mock_role

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.get_role("test-role")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_role_error(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when getting role."""
        mock_k8s_client.rbac_v1.read_namespaced_role.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.get_role("test-role")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_role_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create role successfully."""
        mock_role = MagicMock()
        mock_k8s_client.rbac_v1.create_namespaced_role.return_value = mock_role

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.create_role("test-role")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_role_error(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when creating role."""
        mock_k8s_client.rbac_v1.create_namespaced_role.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.create_role("test-role")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_role_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete role successfully."""
        rbac_manager.delete_role("test-role")

        mock_k8s_client.rbac_v1.delete_namespaced_role.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_role_error(self, rbac_manager: RBACManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when deleting role."""
        mock_k8s_client.rbac_v1.delete_namespaced_role.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.delete_role("test-role")


class TestClusterRoleOperations:
    """Tests for ClusterRole operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_roles_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list cluster roles successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_cluster_role.return_value = mock_response

        result = rbac_manager.list_cluster_roles()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_roles_empty(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no cluster roles exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_cluster_role.return_value = mock_response

        result = rbac_manager.list_cluster_roles()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_roles_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing cluster roles."""
        mock_k8s_client.rbac_v1.list_cluster_role.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.list_cluster_roles()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_role_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get cluster role successfully."""
        mock_role = MagicMock()
        mock_k8s_client.rbac_v1.read_cluster_role.return_value = mock_role

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.get_cluster_role("test-cluster-role")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_role_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting cluster role."""
        mock_k8s_client.rbac_v1.read_cluster_role.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.get_cluster_role("test-cluster-role")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cluster_role_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create cluster role successfully."""
        mock_role = MagicMock()
        mock_k8s_client.rbac_v1.create_cluster_role.return_value = mock_role

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.create_cluster_role("test-cluster-role")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cluster_role_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating cluster role."""
        mock_k8s_client.rbac_v1.create_cluster_role.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.create_cluster_role("test-cluster-role")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cluster_role_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete cluster role successfully."""
        rbac_manager.delete_cluster_role("test-cluster-role")

        mock_k8s_client.rbac_v1.delete_cluster_role.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cluster_role_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting cluster role."""
        mock_k8s_client.rbac_v1.delete_cluster_role.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.delete_cluster_role("test-cluster-role")


class TestRoleBindingOperations:
    """Tests for RoleBinding operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_role_bindings_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list role bindings successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_namespaced_role_binding.return_value = mock_response

        result = rbac_manager.list_role_bindings()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_role_bindings_empty(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no role bindings exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_namespaced_role_binding.return_value = mock_response

        result = rbac_manager.list_role_bindings()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_role_bindings_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing role bindings."""
        mock_k8s_client.rbac_v1.list_namespaced_role_binding.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.list_role_bindings()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get role binding successfully."""
        mock_rb = MagicMock()
        mock_k8s_client.rbac_v1.read_namespaced_role_binding.return_value = mock_rb

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleBindingSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.get_role_binding("test-rb")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting role binding."""
        mock_k8s_client.rbac_v1.read_namespaced_role_binding.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.get_role_binding("test-rb")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create role binding successfully."""
        mock_rb = MagicMock()
        mock_k8s_client.rbac_v1.create_namespaced_role_binding.return_value = mock_rb

        # Mock kubernetes.client classes to avoid ImportError
        with (
            patch("kubernetes.client.V1ObjectMeta"),
            patch("kubernetes.client.V1RoleBinding"),
            patch("kubernetes.client.V1RoleRef"),
            patch("kubernetes.client.V1Subject"),
            patch(
                "system_operations_manager.services.kubernetes.rbac_manager.RoleBindingSummary.from_k8s_object"
            ) as mock_from_k8s,
        ):
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.create_role_binding(
                "test-rb", role_ref={"name": "role"}, subjects=[{"name": "sa"}]
            )

            assert result == mock_summary
            mock_k8s_client.rbac_v1.create_namespaced_role_binding.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating role binding."""
        mock_k8s_client.rbac_v1.create_namespaced_role_binding.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        # Mock kubernetes.client classes to avoid ImportError
        with (
            patch("kubernetes.client.V1ObjectMeta"),
            patch("kubernetes.client.V1RoleBinding"),
            patch("kubernetes.client.V1RoleRef"),
            patch("kubernetes.client.V1Subject"),
            pytest.raises(RuntimeError, match="Translated error"),
        ):
            rbac_manager.create_role_binding(
                "test-rb", role_ref={"name": "role"}, subjects=[{"name": "sa"}]
            )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete role binding successfully."""
        rbac_manager.delete_role_binding("test-rb")

        mock_k8s_client.rbac_v1.delete_namespaced_role_binding.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting role binding."""
        mock_k8s_client.rbac_v1.delete_namespaced_role_binding.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.delete_role_binding("test-rb")


class TestClusterRoleBindingOperations:
    """Tests for ClusterRoleBinding operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_role_bindings_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list cluster role bindings successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_cluster_role_binding.return_value = mock_response

        result = rbac_manager.list_cluster_role_bindings()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_role_bindings_empty(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no cluster role bindings exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.rbac_v1.list_cluster_role_binding.return_value = mock_response

        result = rbac_manager.list_cluster_role_bindings()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cluster_role_bindings_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing cluster role bindings."""
        mock_k8s_client.rbac_v1.list_cluster_role_binding.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.list_cluster_role_bindings()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get cluster role binding successfully."""
        mock_crb = MagicMock()
        mock_k8s_client.rbac_v1.read_cluster_role_binding.return_value = mock_crb

        with patch(
            "system_operations_manager.services.kubernetes.rbac_manager.RoleBindingSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.get_cluster_role_binding("test-crb")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting cluster role binding."""
        mock_k8s_client.rbac_v1.read_cluster_role_binding.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.get_cluster_role_binding("test-crb")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cluster_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create cluster role binding successfully."""
        mock_crb = MagicMock()
        mock_k8s_client.rbac_v1.create_cluster_role_binding.return_value = mock_crb

        # Mock kubernetes.client classes to avoid ImportError
        with (
            patch("kubernetes.client.V1ObjectMeta"),
            patch("kubernetes.client.V1ClusterRoleBinding"),
            patch("kubernetes.client.V1RoleRef"),
            patch("kubernetes.client.V1Subject"),
            patch(
                "system_operations_manager.services.kubernetes.rbac_manager.RoleBindingSummary.from_k8s_object"
            ) as mock_from_k8s,
        ):
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = rbac_manager.create_cluster_role_binding(
                "test-crb", role_ref={"name": "cluster-role"}, subjects=[{"name": "sa"}]
            )

            assert result == mock_summary
            mock_k8s_client.rbac_v1.create_cluster_role_binding.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cluster_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating cluster role binding."""
        mock_k8s_client.rbac_v1.create_cluster_role_binding.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        # Mock kubernetes.client classes to avoid ImportError
        with (
            patch("kubernetes.client.V1ObjectMeta"),
            patch("kubernetes.client.V1ClusterRoleBinding"),
            patch("kubernetes.client.V1RoleRef"),
            patch("kubernetes.client.V1Subject"),
            pytest.raises(RuntimeError, match="Translated error"),
        ):
            rbac_manager.create_cluster_role_binding(
                "test-crb", role_ref={"name": "cluster-role"}, subjects=[{"name": "sa"}]
            )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cluster_role_binding_success(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete cluster role binding successfully."""
        rbac_manager.delete_cluster_role_binding("test-crb")

        mock_k8s_client.rbac_v1.delete_cluster_role_binding.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cluster_role_binding_error(
        self, rbac_manager: RBACManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting cluster role binding."""
        mock_k8s_client.rbac_v1.delete_cluster_role_binding.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            rbac_manager.delete_cluster_role_binding("test-crb")
