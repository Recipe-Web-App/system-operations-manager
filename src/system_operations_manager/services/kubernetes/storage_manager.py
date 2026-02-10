"""Kubernetes storage resource manager.

Manages PersistentVolumes, PersistentVolumeClaims, and StorageClasses
through the Kubernetes API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.storage import (
    PersistentVolumeClaimSummary,
    PersistentVolumeSummary,
    StorageClassSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class StorageManager(K8sBaseManager):
    """Manager for Kubernetes storage resources.

    Provides operations for PersistentVolumes (cluster-scoped),
    PersistentVolumeClaims (namespaced), and StorageClasses (cluster-scoped).
    """

    _entity_name = "storage"

    # =========================================================================
    # PersistentVolume Operations (Cluster-Scoped)
    # =========================================================================

    def list_persistent_volumes(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[PersistentVolumeSummary]:
        """List persistent volumes.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of persistent volume summaries.
        """
        self._log.debug("listing_persistent_volumes")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.core_v1.list_persistent_volume(**kwargs)
            items = [PersistentVolumeSummary.from_k8s_object(pv) for pv in result.items]
            self._log.debug("listed_persistent_volumes", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "PersistentVolume", None, None)

    def get_persistent_volume(self, name: str) -> PersistentVolumeSummary:
        """Get a single persistent volume by name.

        Args:
            name: PersistentVolume name.

        Returns:
            PersistentVolume summary.
        """
        self._log.debug("getting_persistent_volume", name=name)
        try:
            result = self._client.core_v1.read_persistent_volume(name=name)
            return PersistentVolumeSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "PersistentVolume", name, None)

    def delete_persistent_volume(self, name: str) -> None:
        """Delete a persistent volume.

        Args:
            name: PersistentVolume name.
        """
        self._log.info("deleting_persistent_volume", name=name)
        try:
            self._client.core_v1.delete_persistent_volume(name=name)
            self._log.info("deleted_persistent_volume", name=name)
        except Exception as e:
            self._handle_api_error(e, "PersistentVolume", name, None)

    # =========================================================================
    # PersistentVolumeClaim Operations (Namespaced)
    # =========================================================================

    def list_persistent_volume_claims(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[PersistentVolumeClaimSummary]:
        """List persistent volume claims.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of PVC summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_pvcs", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.core_v1.list_persistent_volume_claim_for_all_namespaces(
                    **kwargs
                )
            else:
                result = self._client.core_v1.list_namespaced_persistent_volume_claim(
                    namespace=ns, **kwargs
                )

            items = [PersistentVolumeClaimSummary.from_k8s_object(pvc) for pvc in result.items]
            self._log.debug("listed_pvcs", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "PersistentVolumeClaim", None, ns)

    def get_persistent_volume_claim(
        self, name: str, namespace: str | None = None
    ) -> PersistentVolumeClaimSummary:
        """Get a single PVC by name.

        Args:
            name: PVC name.
            namespace: Target namespace.

        Returns:
            PVC summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_pvc", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_persistent_volume_claim(
                name=name, namespace=ns
            )
            return PersistentVolumeClaimSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "PersistentVolumeClaim", name, ns)

    def create_persistent_volume_claim(
        self,
        name: str,
        namespace: str | None = None,
        *,
        storage_class: str | None = None,
        access_modes: list[str] | None = None,
        storage: str = "1Gi",
        labels: dict[str, str] | None = None,
    ) -> PersistentVolumeClaimSummary:
        """Create a persistent volume claim.

        Args:
            name: PVC name.
            namespace: Target namespace.
            storage_class: StorageClass name.
            access_modes: Access modes (e.g., ['ReadWriteOnce']).
            storage: Storage size (e.g., '10Gi').
            labels: PVC labels.

        Returns:
            Created PVC summary.
        """
        from kubernetes.client import (
            V1ObjectMeta,
            V1PersistentVolumeClaim,
            V1PersistentVolumeClaimSpec,
            V1ResourceRequirements,
        )

        ns = self._resolve_namespace(namespace)
        modes = access_modes or ["ReadWriteOnce"]

        body = V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            spec=V1PersistentVolumeClaimSpec(
                storage_class_name=storage_class,
                access_modes=modes,
                resources=V1ResourceRequirements(
                    requests={"storage": storage},
                ),
            ),
        )

        self._log.info("creating_pvc", name=name, namespace=ns, storage=storage)
        try:
            result = self._client.core_v1.create_namespaced_persistent_volume_claim(
                namespace=ns, body=body
            )
            self._log.info("created_pvc", name=name, namespace=ns)
            return PersistentVolumeClaimSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "PersistentVolumeClaim", name, ns)

    def delete_persistent_volume_claim(self, name: str, namespace: str | None = None) -> None:
        """Delete a persistent volume claim.

        Args:
            name: PVC name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_pvc", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_persistent_volume_claim(name=name, namespace=ns)
            self._log.info("deleted_pvc", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "PersistentVolumeClaim", name, ns)

    # =========================================================================
    # StorageClass Operations (Cluster-Scoped)
    # =========================================================================

    def list_storage_classes(self) -> list[StorageClassSummary]:
        """List storage classes.

        Returns:
            List of storage class summaries.
        """
        self._log.debug("listing_storage_classes")
        try:
            result = self._client.storage_v1.list_storage_class()
            items = [StorageClassSummary.from_k8s_object(sc) for sc in result.items]
            self._log.debug("listed_storage_classes", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "StorageClass", None, None)

    def get_storage_class(self, name: str) -> StorageClassSummary:
        """Get a single storage class by name.

        Args:
            name: StorageClass name.

        Returns:
            StorageClass summary.
        """
        self._log.debug("getting_storage_class", name=name)
        try:
            result = self._client.storage_v1.read_storage_class(name=name)
            return StorageClassSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StorageClass", name, None)
