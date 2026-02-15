"""Integration tests for Kubernetes StorageManager against real K3S cluster."""

import pytest


@pytest.mark.integration
@pytest.mark.kubernetes
class TestStorageClasses:
    """Test operations for Kubernetes storage classes."""

    def test_list_storage_classes(self, storage_manager):
        """Test listing storage classes (K3S has local-path)."""
        storage_classes = storage_manager.list_storage_classes()

        assert len(storage_classes) > 0
        sc_names = [sc.name for sc in storage_classes]
        # K3S comes with local-path storage class by default
        assert "local-path" in sc_names

    def test_get_storage_class(self, storage_manager):
        """Test getting a specific storage class."""
        # K3S has local-path storage class by default
        sc = storage_manager.get_storage_class(name="local-path")

        assert sc.name == "local-path"


@pytest.mark.integration
@pytest.mark.kubernetes
class TestPVCOperations:
    """Test CRUD operations for persistent volume claims."""

    def test_create_pvc(self, storage_manager, test_namespace, unique_name):
        """Test creating a persistent volume claim."""
        pvc_name = f"pvc-{unique_name}"

        pvc = storage_manager.create_persistent_volume_claim(
            name=pvc_name,
            namespace=test_namespace,
            storage_class="local-path",
            access_modes=["ReadWriteOnce"],
            storage="100Mi",
            labels={"test": "integration"},
        )

        assert pvc.name == pvc_name
        assert pvc.namespace == test_namespace
        assert pvc.status in ["Pending", "Bound"]

    def test_list_pvcs(self, storage_manager, test_namespace, unique_name):
        """Test listing persistent volume claims."""
        pvc_name = f"pvc-{unique_name}"

        # Create a PVC
        storage_manager.create_persistent_volume_claim(
            name=pvc_name,
            namespace=test_namespace,
            storage_class="local-path",
            access_modes=["ReadWriteOnce"],
            storage="100Mi",
        )

        # List PVCs
        pvcs = storage_manager.list_persistent_volume_claims(namespace=test_namespace)

        assert len(pvcs) > 0
        pvc_names = [pvc.name for pvc in pvcs]
        assert pvc_name in pvc_names

    def test_delete_pvc(self, storage_manager, test_namespace, unique_name):
        """Test deleting a persistent volume claim."""
        pvc_name = f"pvc-{unique_name}"

        # Create a PVC
        storage_manager.create_persistent_volume_claim(
            name=pvc_name,
            namespace=test_namespace,
            storage_class="local-path",
            access_modes=["ReadWriteOnce"],
            storage="100Mi",
        )

        # Delete the PVC
        storage_manager.delete_persistent_volume_claim(name=pvc_name, namespace=test_namespace)

        # Verify it's deleted by checking list
        pvcs = storage_manager.list_persistent_volume_claims(namespace=test_namespace)
        pvc_names = [pvc.name for pvc in pvcs]
        assert pvc_name not in pvc_names
