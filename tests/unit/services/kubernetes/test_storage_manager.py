"""Unit tests for StorageManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.storage_manager import (
    StorageManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def storage_manager(mock_k8s_client: MagicMock) -> StorageManager:
    """Create a StorageManager instance with mocked client."""
    return StorageManager(mock_k8s_client)


class TestPersistentVolumeOperations:
    """Tests for PersistentVolume operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volumes_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list persistent volumes successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_persistent_volume.return_value = mock_response

        result = storage_manager.list_persistent_volumes()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volumes_empty(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no persistent volumes exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_persistent_volume.return_value = mock_response

        result = storage_manager.list_persistent_volumes()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volumes_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing persistent volumes."""
        mock_k8s_client.core_v1.list_persistent_volume.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.list_persistent_volumes()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_persistent_volume_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get persistent volume successfully."""
        mock_pv = MagicMock()
        mock_k8s_client.core_v1.read_persistent_volume.return_value = mock_pv

        with patch(
            "system_operations_manager.services.kubernetes.storage_manager.PersistentVolumeSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = storage_manager.get_persistent_volume("test-pv")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_persistent_volume_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting persistent volume."""
        mock_k8s_client.core_v1.read_persistent_volume.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.get_persistent_volume("test-pv")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_persistent_volume_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete persistent volume successfully."""
        storage_manager.delete_persistent_volume("test-pv")

        mock_k8s_client.core_v1.delete_persistent_volume.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_persistent_volume_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting persistent volume."""
        mock_k8s_client.core_v1.delete_persistent_volume.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.delete_persistent_volume("test-pv")


class TestPersistentVolumeClaimOperations:
    """Tests for PersistentVolumeClaim operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volume_claims_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list persistent volume claims successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_persistent_volume_claim.return_value = mock_response

        result = storage_manager.list_persistent_volume_claims()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volume_claims_empty(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no PVCs exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_persistent_volume_claim.return_value = mock_response

        result = storage_manager.list_persistent_volume_claims()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volume_claims_all_namespaces(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list PVCs across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_persistent_volume_claim_for_all_namespaces.return_value = (
            mock_response
        )

        result = storage_manager.list_persistent_volume_claims(all_namespaces=True)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_persistent_volume_claims_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing PVCs."""
        mock_k8s_client.core_v1.list_namespaced_persistent_volume_claim.side_effect = Exception(
            "API error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.list_persistent_volume_claims()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_persistent_volume_claim_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get persistent volume claim successfully."""
        mock_pvc = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_persistent_volume_claim.return_value = mock_pvc

        with patch(
            "system_operations_manager.services.kubernetes.storage_manager.PersistentVolumeClaimSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = storage_manager.get_persistent_volume_claim("test-pvc")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_persistent_volume_claim_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting PVC."""
        mock_k8s_client.core_v1.read_namespaced_persistent_volume_claim.side_effect = Exception(
            "Not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.get_persistent_volume_claim("test-pvc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_persistent_volume_claim_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create persistent volume claim successfully."""
        mock_pvc = MagicMock()
        mock_k8s_client.core_v1.create_namespaced_persistent_volume_claim.return_value = mock_pvc

        with patch(
            "system_operations_manager.services.kubernetes.storage_manager.PersistentVolumeClaimSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = storage_manager.create_persistent_volume_claim("test-pvc", storage="10Gi")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_persistent_volume_claim_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating PVC."""
        mock_k8s_client.core_v1.create_namespaced_persistent_volume_claim.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.create_persistent_volume_claim("test-pvc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_persistent_volume_claim_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete persistent volume claim successfully."""
        storage_manager.delete_persistent_volume_claim("test-pvc")

        mock_k8s_client.core_v1.delete_namespaced_persistent_volume_claim.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_persistent_volume_claim_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting PVC."""
        mock_k8s_client.core_v1.delete_namespaced_persistent_volume_claim.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.delete_persistent_volume_claim("test-pvc")


class TestStorageClassOperations:
    """Tests for StorageClass operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_storage_classes_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list storage classes successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.storage_v1.list_storage_class.return_value = mock_response

        result = storage_manager.list_storage_classes()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_storage_classes_empty(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no storage classes exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.storage_v1.list_storage_class.return_value = mock_response

        result = storage_manager.list_storage_classes()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_storage_classes_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing storage classes."""
        mock_k8s_client.storage_v1.list_storage_class.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.list_storage_classes()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_storage_class_success(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get storage class successfully."""
        mock_sc = MagicMock()
        mock_k8s_client.storage_v1.read_storage_class.return_value = mock_sc

        with patch(
            "system_operations_manager.services.kubernetes.storage_manager.StorageClassSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = storage_manager.get_storage_class("test-sc")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_storage_class_error(
        self, storage_manager: StorageManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting storage class."""
        mock_k8s_client.storage_v1.read_storage_class.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            storage_manager.get_storage_class("test-sc")
