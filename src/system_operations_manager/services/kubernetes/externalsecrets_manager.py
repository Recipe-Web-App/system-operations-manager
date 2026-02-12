"""External Secrets Operator resource manager.

Manages ExternalSecrets, SecretStores, and ClusterSecretStores
through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.external_secrets import (
    ExternalSecretSummary,
    SecretStoreSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# ESO CRD coordinates
ESO_GROUP = "external-secrets.io"
ESO_VERSION = "v1beta1"
SECRET_STORE_PLURAL = "secretstores"
CLUSTER_SECRET_STORE_PLURAL = "clustersecretstores"
EXTERNAL_SECRET_PLURAL = "externalsecrets"

# ESO operator namespace
ESO_NAMESPACE = "external-secrets"


class ExternalSecretsManager(K8sBaseManager):
    """Manager for External Secrets Operator resources.

    Provides CRUD operations for ExternalSecrets, SecretStores,
    and ClusterSecretStores.  All CRD resources are accessed via
    ``CustomObjectsApi``.
    """

    _entity_name = "external_secrets"

    # =========================================================================
    # SecretStore Operations (namespaced)
    # =========================================================================

    def list_secret_stores(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[SecretStoreSummary]:
        """List SecretStores in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of secret store summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_secret_stores", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                SECRET_STORE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            stores = [SecretStoreSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_secret_stores", count=len(stores), namespace=ns)
            return stores
        except Exception as e:
            self._handle_api_error(e, "SecretStore", None, ns)

    def get_secret_store(
        self,
        name: str,
        namespace: str | None = None,
    ) -> SecretStoreSummary:
        """Get a single SecretStore by name.

        Args:
            name: SecretStore name.
            namespace: Target namespace.

        Returns:
            Secret store summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_secret_store", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                SECRET_STORE_PLURAL,
                name,
            )
            return SecretStoreSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "SecretStore", name, ns)

    def create_secret_store(
        self,
        name: str,
        namespace: str | None = None,
        *,
        provider_config: dict[str, Any],
        labels: dict[str, str] | None = None,
    ) -> SecretStoreSummary:
        """Create a new SecretStore.

        Args:
            name: SecretStore name.
            namespace: Target namespace.
            provider_config: Provider configuration dict (e.g. ``{"vault": {"server": "..."}}``)
            labels: Optional labels.

        Returns:
            Created secret store summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_secret_store", name=name, namespace=ns)
        body: dict[str, Any] = {
            "apiVersion": f"{ESO_GROUP}/{ESO_VERSION}",
            "kind": "SecretStore",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "provider": provider_config,
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                SECRET_STORE_PLURAL,
                body,
            )
            self._log.info("created_secret_store", name=name, namespace=ns)
            return SecretStoreSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "SecretStore", name, ns)

    def delete_secret_store(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a SecretStore.

        Args:
            name: SecretStore name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_secret_store", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                SECRET_STORE_PLURAL,
                name,
            )
            self._log.info("deleted_secret_store", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "SecretStore", name, ns)

    # =========================================================================
    # ClusterSecretStore Operations (cluster-scoped)
    # =========================================================================

    def list_cluster_secret_stores(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[SecretStoreSummary]:
        """List ClusterSecretStores.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of cluster secret store summaries.
        """
        self._log.debug("listing_cluster_secret_stores")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_cluster_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                CLUSTER_SECRET_STORE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            stores = [
                SecretStoreSummary.from_k8s_object(item, is_cluster_store=True) for item in items
            ]
            self._log.debug("listed_cluster_secret_stores", count=len(stores))
            return stores
        except Exception as e:
            self._handle_api_error(e, "ClusterSecretStore")

    def get_cluster_secret_store(self, name: str) -> SecretStoreSummary:
        """Get a single ClusterSecretStore by name.

        Args:
            name: ClusterSecretStore name.

        Returns:
            Cluster secret store summary.
        """
        self._log.debug("getting_cluster_secret_store", name=name)
        try:
            result = self._client.custom_objects.get_cluster_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                CLUSTER_SECRET_STORE_PLURAL,
                name,
            )
            return SecretStoreSummary.from_k8s_object(result, is_cluster_store=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterSecretStore", name)

    def create_cluster_secret_store(
        self,
        name: str,
        *,
        provider_config: dict[str, Any],
        labels: dict[str, str] | None = None,
    ) -> SecretStoreSummary:
        """Create a new ClusterSecretStore.

        Args:
            name: ClusterSecretStore name.
            provider_config: Provider configuration dict.
            labels: Optional labels.

        Returns:
            Created cluster secret store summary.
        """
        self._log.debug("creating_cluster_secret_store", name=name)
        body: dict[str, Any] = {
            "apiVersion": f"{ESO_GROUP}/{ESO_VERSION}",
            "kind": "ClusterSecretStore",
            "metadata": {
                "name": name,
                "labels": labels or {},
            },
            "spec": {
                "provider": provider_config,
            },
        }
        try:
            result = self._client.custom_objects.create_cluster_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                CLUSTER_SECRET_STORE_PLURAL,
                body,
            )
            self._log.info("created_cluster_secret_store", name=name)
            return SecretStoreSummary.from_k8s_object(result, is_cluster_store=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterSecretStore", name)

    def delete_cluster_secret_store(self, name: str) -> None:
        """Delete a ClusterSecretStore.

        Args:
            name: ClusterSecretStore name to delete.
        """
        self._log.debug("deleting_cluster_secret_store", name=name)
        try:
            self._client.custom_objects.delete_cluster_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                CLUSTER_SECRET_STORE_PLURAL,
                name,
            )
            self._log.info("deleted_cluster_secret_store", name=name)
        except Exception as e:
            self._handle_api_error(e, "ClusterSecretStore", name)

    # =========================================================================
    # ExternalSecret Operations (namespaced)
    # =========================================================================

    def list_external_secrets(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[ExternalSecretSummary]:
        """List ExternalSecrets in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of external secret summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_external_secrets", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                EXTERNAL_SECRET_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            secrets = [ExternalSecretSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_external_secrets", count=len(secrets), namespace=ns)
            return secrets
        except Exception as e:
            self._handle_api_error(e, "ExternalSecret", None, ns)

    def get_external_secret(
        self,
        name: str,
        namespace: str | None = None,
    ) -> ExternalSecretSummary:
        """Get a single ExternalSecret by name.

        Args:
            name: ExternalSecret name.
            namespace: Target namespace.

        Returns:
            External secret summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_external_secret", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                EXTERNAL_SECRET_PLURAL,
                name,
            )
            return ExternalSecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ExternalSecret", name, ns)

    def create_external_secret(
        self,
        name: str,
        namespace: str | None = None,
        *,
        store_name: str,
        store_kind: str = "SecretStore",
        data: list[dict[str, Any]] | None = None,
        target_name: str | None = None,
        refresh_interval: str = "1h",
        labels: dict[str, str] | None = None,
    ) -> ExternalSecretSummary:
        """Create a new ExternalSecret.

        Args:
            name: ExternalSecret name.
            namespace: Target namespace.
            store_name: Name of the SecretStore/ClusterSecretStore to use.
            store_kind: Kind of store (SecretStore or ClusterSecretStore).
            data: List of data mapping dicts with ``secretKey`` and ``remoteRef``.
            target_name: Override target K8s Secret name (defaults to ES name).
            refresh_interval: Sync interval (e.g. ``1h``, ``30m``).
            labels: Optional labels.

        Returns:
            Created external secret summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_external_secret", name=name, namespace=ns)

        target: dict[str, Any] = {}
        if target_name:
            target["name"] = target_name

        body: dict[str, Any] = {
            "apiVersion": f"{ESO_GROUP}/{ESO_VERSION}",
            "kind": "ExternalSecret",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "refreshInterval": refresh_interval,
                "secretStoreRef": {
                    "name": store_name,
                    "kind": store_kind,
                },
                "target": target,
                "data": data or [],
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                EXTERNAL_SECRET_PLURAL,
                body,
            )
            self._log.info("created_external_secret", name=name, namespace=ns)
            return ExternalSecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ExternalSecret", name, ns)

    def delete_external_secret(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete an ExternalSecret.

        Args:
            name: ExternalSecret name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_external_secret", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                EXTERNAL_SECRET_PLURAL,
                name,
            )
            self._log.info("deleted_external_secret", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "ExternalSecret", name, ns)

    # =========================================================================
    # Sync Status
    # =========================================================================

    def get_sync_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed sync status for an ExternalSecret.

        Returns more detailed status information than the summary model,
        including raw conditions and target secret name.

        Args:
            name: ExternalSecret name.
            namespace: Target namespace.

        Returns:
            Dict with ``ready``, ``synced_resource_version``, ``refresh_time``,
            ``target_secret``, and ``conditions`` keys.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_sync_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ESO_GROUP,
                ESO_VERSION,
                ns,
                EXTERNAL_SECRET_PLURAL,
                name,
            )
            spec: dict[str, Any] = result.get("spec", {})
            status: dict[str, Any] = result.get("status", {})

            ready = False
            message = None
            for condition in status.get("conditions", []):
                if condition.get("type") == "Ready":
                    ready = condition.get("status") == "True"
                    message = condition.get("message")
                    break

            target: dict[str, Any] = spec.get("target", {})
            target_secret = target.get("name") or result.get("metadata", {}).get("name", "")

            return {
                "name": name,
                "namespace": ns,
                "ready": ready,
                "message": message,
                "synced_resource_version": status.get("syncedResourceVersion"),
                "refresh_time": status.get("refreshTime"),
                "target_secret": target_secret,
                "conditions": status.get("conditions", []),
            }
        except Exception as e:
            self._handle_api_error(e, "ExternalSecret", name, ns)

    # =========================================================================
    # Operator Status
    # =========================================================================

    def get_operator_status(self) -> dict[str, Any]:
        """Check External Secrets Operator status.

        Looks for ESO pods in the ``external-secrets`` namespace to determine
        whether the operator is running.

        Returns:
            Dict with ``running`` (bool), ``pods`` (list), and optionally
            ``version`` (str) keys.
        """
        self._log.debug("checking_operator_status")
        try:
            result = self._client.core_v1.list_namespaced_pod(
                namespace=ESO_NAMESPACE,
                label_selector="app.kubernetes.io/name=external-secrets",
            )
            pods = []
            version = None
            for pod in result.items or []:
                pod_name = pod.metadata.name if pod.metadata else "unknown"
                pod_status = pod.status.phase if pod.status else "Unknown"
                pods.append({"name": pod_name, "status": pod_status})

                if version is None and pod.spec and pod.spec.containers:
                    image = pod.spec.containers[0].image or ""
                    if ":" in image:
                        version = image.rsplit(":", 1)[1]

            status: dict[str, Any] = {
                "running": len(pods) > 0 and all(p["status"] == "Running" for p in pods),
                "pods": pods,
            }
            if version:
                status["version"] = version

            self._log.debug("operator_status", running=status["running"], pod_count=len(pods))
            return status
        except Exception:
            return {
                "running": False,
                "pods": [],
                "error": "Could not reach external-secrets namespace",
            }
