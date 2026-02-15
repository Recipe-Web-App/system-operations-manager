"""Unit tests for ConfigurationManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.configuration_manager import (
    ConfigurationManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def config_manager(mock_k8s_client: MagicMock) -> ConfigurationManager:
    """Create a ConfigurationManager instance with mocked client."""
    return ConfigurationManager(mock_k8s_client)


class TestConfigMapOperations:
    """Tests for ConfigMap operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_config_maps_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list configmaps successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_config_map.return_value = mock_response

        result = config_manager.list_config_maps()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_config_maps_empty(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no configmaps exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_config_map.return_value = mock_response

        result = config_manager.list_config_maps()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_config_maps_all_namespaces(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list configmaps across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_config_map_for_all_namespaces.return_value = mock_response

        result = config_manager.list_config_maps(all_namespaces=True)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_config_maps_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing configmaps."""
        mock_k8s_client.core_v1.list_namespaced_config_map.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.list_config_maps()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_config_map_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get configmap successfully."""
        mock_cm = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_config_map.return_value = mock_cm

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigMapSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.get_config_map("test-cm")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_config_map_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting configmap."""
        mock_k8s_client.core_v1.read_namespaced_config_map.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.get_config_map("test-cm")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_config_map_data_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get configmap data successfully."""
        mock_cm = MagicMock()
        mock_cm.data = {"key1": "value1", "key2": "value2"}
        mock_k8s_client.core_v1.read_namespaced_config_map.return_value = mock_cm

        result = config_manager.get_config_map_data("test-cm")

        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_config_map_data_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting configmap data."""
        mock_k8s_client.core_v1.read_namespaced_config_map.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.get_config_map_data("test-cm")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_config_map_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create configmap successfully."""
        mock_cm = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_config_map.return_value = mock_cm

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigMapSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.create_config_map("test-cm", data={"key": "value"})

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_config_map_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating configmap."""
        mock_k8s_client.core_v1.create_namespaced_config_map.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.create_config_map("test-cm")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_config_map_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update configmap successfully."""
        mock_cm = MagicMock()
        mock_k8s_client.core_v1.patch_namespaced_config_map.return_value = mock_cm

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigMapSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.update_config_map("test-cm", data={"key": "new-value"})

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_config_map_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating configmap."""
        mock_k8s_client.core_v1.patch_namespaced_config_map.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.update_config_map("test-cm", data={})

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_config_map_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete configmap successfully."""
        config_manager.delete_config_map("test-cm")

        mock_k8s_client.core_v1.delete_namespaced_config_map.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_config_map_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting configmap."""
        mock_k8s_client.core_v1.delete_namespaced_config_map.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.delete_config_map("test-cm")


class TestSecretOperations:
    """Tests for Secret operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_secrets_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list secrets successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_secret.return_value = mock_response

        result = config_manager.list_secrets()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_secrets_empty(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no secrets exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_secret.return_value = mock_response

        result = config_manager.list_secrets()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_secrets_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing secrets."""
        mock_k8s_client.core_v1.list_namespaced_secret.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.list_secrets()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get secret successfully."""
        mock_secret = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_secret.return_value = mock_secret

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.SecretSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.get_secret("test-secret")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting secret."""
        mock_k8s_client.core_v1.read_namespaced_secret.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.get_secret("test-secret")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create secret successfully."""
        mock_secret = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_secret.return_value = mock_secret

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.SecretSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.create_secret("test-secret", data={"key": "value"})

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating secret."""
        mock_k8s_client.core_v1.create_namespaced_secret.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.create_secret("test-secret")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_tls_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create TLS secret successfully."""
        mock_secret = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_secret.return_value = mock_secret

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.SecretSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.create_tls_secret("test-tls", cert="cert-data", key="key-data")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_tls_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating TLS secret."""
        mock_k8s_client.core_v1.create_namespaced_secret.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.create_tls_secret("test-tls", cert="cert", key="key")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_docker_registry_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create docker-registry secret successfully."""
        mock_secret = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_secret.return_value = mock_secret

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.SecretSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.create_docker_registry_secret(
                "test-docker",
                server="https://docker.io",
                username="user",
                password="pass",
            )

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_docker_registry_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating docker-registry secret."""
        mock_k8s_client.core_v1.create_namespaced_secret.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.create_docker_registry_secret(
                "test-docker", server="server", username="user", password="pass"
            )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete secret successfully."""
        config_manager.delete_secret("test-secret")

        mock_k8s_client.core_v1.delete_namespaced_secret.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting secret."""
        mock_k8s_client.core_v1.delete_namespaced_secret.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.delete_secret("test-secret")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_secret_success(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update secret successfully."""
        mock_secret = MagicMock()
        mock_k8s_client.core_v1.patch_namespaced_secret.return_value = mock_secret

        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.SecretSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = config_manager.update_secret("test-secret", data={"key": "value"})

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_secret_error(
        self, config_manager: ConfigurationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating secret."""
        mock_k8s_client.core_v1.patch_namespaced_secret.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            config_manager.update_secret("test-secret", data={})
