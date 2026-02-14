"""Unit tests for Kubernetes storage resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.storage import (
    PersistentVolumeClaimSummary,
    PersistentVolumeSummary,
    StorageClassSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPersistentVolumeSummary:
    """Test PersistentVolumeSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete PersistentVolume."""
        obj = MagicMock()
        obj.metadata.name = "pv-nfs-001"
        obj.metadata.uid = "uid-pv-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"type": "nfs"}
        obj.metadata.annotations = {}

        obj.spec.capacity = {"storage": "10Gi"}
        obj.spec.access_modes = ["ReadWriteMany"]
        obj.spec.persistent_volume_reclaim_policy = "Retain"
        obj.spec.storage_class_name = "nfs"

        obj.spec.claim_ref.namespace = "default"
        obj.spec.claim_ref.name = "data-pvc"

        obj.status.phase = "Bound"

        pv = PersistentVolumeSummary.from_k8s_object(obj)

        assert pv.name == "pv-nfs-001"
        assert pv.capacity == "10Gi"
        assert pv.access_modes == ["ReadWriteMany"]
        assert pv.reclaim_policy == "Retain"
        assert pv.status == "Bound"
        assert pv.storage_class == "nfs"
        assert pv.claim_ref == "default/data-pvc"

    def test_from_k8s_object_available(self) -> None:
        """Test from_k8s_object with available PV."""
        obj = MagicMock()
        obj.metadata.name = "pv-available"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.capacity = {"storage": "5Gi"}
        obj.spec.access_modes = ["ReadWriteOnce"]
        obj.spec.persistent_volume_reclaim_policy = "Delete"
        obj.spec.storage_class_name = "fast"
        obj.spec.claim_ref = None

        obj.status.phase = "Available"

        pv = PersistentVolumeSummary.from_k8s_object(obj)

        assert pv.status == "Available"
        assert pv.claim_ref is None

    def test_from_k8s_object_no_claim_namespace(self) -> None:
        """Test from_k8s_object with claim_ref without namespace."""
        obj = MagicMock()
        obj.metadata.name = "pv-no-ns"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.capacity = {"storage": "1Gi"}
        obj.spec.access_modes = ["ReadWriteOnce"]
        obj.spec.persistent_volume_reclaim_policy = "Recycle"
        obj.spec.storage_class_name = None

        # Create a proper claim_ref mock
        claim_ref = MagicMock()
        claim_ref.namespace = ""
        claim_ref.name = "orphan-pvc"
        obj.spec.claim_ref = claim_ref

        obj.status.phase = "Bound"

        pv = PersistentVolumeSummary.from_k8s_object(obj)

        assert pv.claim_ref == "orphan-pvc"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal PV."""
        obj = MagicMock()
        obj.metadata.name = "minimal-pv"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.capacity = {}
        obj.spec.access_modes = None
        obj.spec.persistent_volume_reclaim_policy = None
        obj.spec.storage_class_name = None
        obj.spec.claim_ref = None

        obj.status.phase = None

        pv = PersistentVolumeSummary.from_k8s_object(obj)

        assert pv.name == "minimal-pv"
        assert pv.capacity is None
        assert pv.access_modes == []
        assert pv.status == "Available"

    def test_from_k8s_object_multiple_access_modes(self) -> None:
        """Test from_k8s_object with multiple access modes."""
        obj = MagicMock()
        obj.metadata.name = "multi-mode-pv"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.capacity = {"storage": "20Gi"}
        obj.spec.access_modes = ["ReadWriteOnce", "ReadOnlyMany"]
        obj.spec.persistent_volume_reclaim_policy = "Retain"
        obj.spec.storage_class_name = "standard"
        obj.spec.claim_ref = None
        obj.status.phase = "Available"

        pv = PersistentVolumeSummary.from_k8s_object(obj)

        assert pv.access_modes == ["ReadWriteOnce", "ReadOnlyMany"]

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert PersistentVolumeSummary._entity_name == "persistentvolume"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPersistentVolumeClaimSummary:
    """Test PersistentVolumeClaimSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete PVC."""
        obj = MagicMock()
        obj.metadata.name = "data-pvc"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-pvc-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "database"}
        obj.metadata.annotations = {}

        obj.spec.volume_name = "pv-nfs-001"
        obj.spec.storage_class_name = "nfs"

        obj.status.phase = "Bound"
        obj.status.capacity = {"storage": "10Gi"}
        obj.status.access_modes = ["ReadWriteMany"]

        pvc = PersistentVolumeClaimSummary.from_k8s_object(obj)

        assert pvc.name == "data-pvc"
        assert pvc.namespace == "default"
        assert pvc.status == "Bound"
        assert pvc.volume == "pv-nfs-001"
        assert pvc.capacity == "10Gi"
        assert pvc.access_modes == ["ReadWriteMany"]
        assert pvc.storage_class == "nfs"

    def test_from_k8s_object_pending(self) -> None:
        """Test from_k8s_object with pending PVC."""
        obj = MagicMock()
        obj.metadata.name = "pending-pvc"
        obj.metadata.namespace = "production"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.volume_name = None
        obj.spec.storage_class_name = "fast"

        obj.status.phase = "Pending"
        obj.status.capacity = None
        obj.status.access_modes = None

        pvc = PersistentVolumeClaimSummary.from_k8s_object(obj)

        assert pvc.status == "Pending"
        assert pvc.volume is None
        assert pvc.capacity is None

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal PVC."""
        obj = MagicMock()
        obj.metadata.name = "minimal-pvc"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.volume_name = None
        obj.spec.storage_class_name = None

        obj.status.phase = None
        obj.status.capacity = {}
        obj.status.access_modes = None

        pvc = PersistentVolumeClaimSummary.from_k8s_object(obj)

        assert pvc.name == "minimal-pvc"
        assert pvc.status == "Pending"
        assert pvc.access_modes == []

    def test_from_k8s_object_no_capacity(self) -> None:
        """Test from_k8s_object with empty capacity."""
        obj = MagicMock()
        obj.metadata.name = "no-cap-pvc"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.volume_name = "pv-001"
        obj.spec.storage_class_name = "standard"

        obj.status.phase = "Bound"
        obj.status.capacity = {}
        obj.status.access_modes = ["ReadWriteOnce"]

        pvc = PersistentVolumeClaimSummary.from_k8s_object(obj)

        assert pvc.capacity is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert PersistentVolumeClaimSummary._entity_name == "persistentvolumeclaim"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStorageClassSummary:
    """Test StorageClassSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete StorageClass."""
        obj = MagicMock()
        obj.metadata.name = "fast-ssd"
        obj.metadata.uid = "uid-sc-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"type": "ssd"}
        obj.metadata.annotations = {}

        obj.provisioner = "kubernetes.io/aws-ebs"
        obj.reclaim_policy = "Delete"
        obj.volume_binding_mode = "WaitForFirstConsumer"
        obj.allow_volume_expansion = True

        sc = StorageClassSummary.from_k8s_object(obj)

        assert sc.name == "fast-ssd"
        assert sc.provisioner == "kubernetes.io/aws-ebs"
        assert sc.reclaim_policy == "Delete"
        assert sc.volume_binding_mode == "WaitForFirstConsumer"
        assert sc.allow_volume_expansion is True

    def test_from_k8s_object_nfs(self) -> None:
        """Test from_k8s_object with NFS provisioner."""
        obj = MagicMock()
        obj.metadata.name = "nfs"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.provisioner = "example.com/nfs"
        obj.reclaim_policy = "Retain"
        obj.volume_binding_mode = "Immediate"
        obj.allow_volume_expansion = False

        sc = StorageClassSummary.from_k8s_object(obj)

        assert sc.provisioner == "example.com/nfs"
        assert sc.reclaim_policy == "Retain"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal StorageClass."""
        obj = MagicMock()
        obj.metadata.name = "minimal-sc"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.provisioner = None
        obj.reclaim_policy = None
        obj.volume_binding_mode = None
        obj.allow_volume_expansion = None

        sc = StorageClassSummary.from_k8s_object(obj)

        assert sc.name == "minimal-sc"
        assert sc.provisioner == ""
        assert sc.allow_volume_expansion is False

    def test_from_k8s_object_various_provisioners(self) -> None:
        """Test from_k8s_object with different provisioners."""
        provisioners = [
            "kubernetes.io/gce-pd",
            "kubernetes.io/azure-disk",
            "csi.storage.k8s.io",
            "ebs.csi.aws.com",
        ]

        for prov in provisioners:
            obj = MagicMock()
            obj.metadata.name = "test-sc"
            obj.metadata.uid = None
            obj.metadata.creation_timestamp = None
            obj.metadata.labels = None
            obj.metadata.annotations = None
            obj.provisioner = prov
            obj.reclaim_policy = None
            obj.volume_binding_mode = None
            obj.allow_volume_expansion = None

            sc = StorageClassSummary.from_k8s_object(obj)
            assert sc.provisioner == prov

    def test_from_k8s_object_expansion_enabled(self) -> None:
        """Test from_k8s_object with volume expansion enabled."""
        obj = MagicMock()
        obj.metadata.name = "expandable-sc"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.provisioner = "kubernetes.io/gce-pd"
        obj.reclaim_policy = "Delete"
        obj.volume_binding_mode = "Immediate"
        obj.allow_volume_expansion = True

        sc = StorageClassSummary.from_k8s_object(obj)

        assert sc.allow_volume_expansion is True

    def test_from_k8s_object_expansion_disabled(self) -> None:
        """Test from_k8s_object with volume expansion disabled."""
        obj = MagicMock()
        obj.metadata.name = "fixed-sc"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.provisioner = "kubernetes.io/aws-ebs"
        obj.reclaim_policy = "Retain"
        obj.volume_binding_mode = "WaitForFirstConsumer"
        obj.allow_volume_expansion = False

        sc = StorageClassSummary.from_k8s_object(obj)

        assert sc.allow_volume_expansion is False

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert StorageClassSummary._entity_name == "storageclass"
