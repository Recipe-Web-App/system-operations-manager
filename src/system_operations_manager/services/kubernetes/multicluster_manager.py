"""Multi-cluster Kubernetes operations manager.

Provides cross-cluster operations: status overview, multi-cluster deploy,
and resource synchronization between clusters.
"""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from system_operations_manager.integrations.kubernetes.models.multicluster import (
    ClusterDeployResult,
    ClusterStatus,
    ClusterSyncResult,
    MultiClusterDeployResult,
    MultiClusterStatusResult,
    MultiClusterSyncResult,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager
from system_operations_manager.services.kubernetes.manifest_manager import (
    SERVER_MANAGED_METADATA_FIELDS,
    SERVER_MANAGED_TOP_LEVEL_FIELDS,
    ManifestManager,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from system_operations_manager.integrations.kubernetes.client import KubernetesClient


class MultiClusterManager(K8sBaseManager):
    """Manager for multi-cluster Kubernetes operations.

    Provides operations that span multiple clusters by sequentially
    switching contexts, performing operations, and collecting results.
    The original context is always restored after operations complete.
    """

    _entity_name: str = "multicluster"

    def __init__(self, client: KubernetesClient) -> None:
        super().__init__(client)

    # -----------------------------------------------------------------------
    # Cluster Resolution
    # -----------------------------------------------------------------------

    def get_cluster_names(self) -> list[str]:
        """Get all configured cluster names.

        Returns:
            List of cluster names from the plugin configuration.
        """
        return list(self._client._config.clusters.keys())

    def _resolve_clusters(self, clusters: list[str] | None) -> list[str]:
        """Resolve cluster list to configured cluster names.

        Args:
            clusters: Specific cluster names, or None for all configured clusters.

        Returns:
            List of validated cluster names.

        Raises:
            ValueError: If specified cluster names are not in configuration.
        """
        configured = set(self._client._config.clusters.keys())

        if not configured:
            raise ValueError(
                "No clusters configured. Add clusters to the Kubernetes plugin configuration."
            )

        if clusters is None:
            return list(configured)

        unknown = set(clusters) - configured
        if unknown:
            raise ValueError(
                f"Unknown clusters: {', '.join(sorted(unknown))}. "
                f"Configured: {', '.join(sorted(configured))}"
            )

        return clusters

    # -----------------------------------------------------------------------
    # Context Management
    # -----------------------------------------------------------------------

    @contextmanager
    def _save_and_restore_context(self) -> Generator[None]:
        """Context manager that saves and restores the current cluster context.

        Ensures the original context is restored even if an error occurs
        during multi-cluster operations.
        """
        original_context = self._client.get_current_context()
        self._log.debug("saving_context", original=original_context)
        try:
            yield
        finally:
            if original_context and original_context != "unknown":
                try:
                    self._client.switch_context(original_context)
                    self._log.debug("restored_context", context=original_context)
                except Exception:
                    self._log.warning(
                        "failed_to_restore_context",
                        original=original_context,
                    )

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def multi_cluster_status(
        self,
        clusters: list[str] | None = None,
    ) -> MultiClusterStatusResult:
        """Get connectivity and version status for multiple clusters.

        Args:
            clusters: Specific cluster names, or None for all configured.

        Returns:
            Aggregated status result with per-cluster details.
        """
        target_clusters = self._resolve_clusters(clusters)
        self._log.info("checking_multi_cluster_status", clusters=target_clusters)

        statuses: list[ClusterStatus] = []

        with self._save_and_restore_context():
            for cluster_name in target_clusters:
                status = self._get_single_cluster_status(cluster_name)
                statuses.append(status)

        connected_count = sum(1 for s in statuses if s.connected)

        result = MultiClusterStatusResult(
            clusters=statuses,
            total=len(statuses),
            connected=connected_count,
            disconnected=len(statuses) - connected_count,
        )
        self._log.info(
            "multi_cluster_status_complete",
            total=result.total,
            connected=result.connected,
        )
        return result

    def _get_single_cluster_status(self, cluster_name: str) -> ClusterStatus:
        """Get status for a single cluster by switching context."""
        cluster_cfg = self._client._config.clusters[cluster_name]

        try:
            self._client.switch_context(cluster_name)
        except Exception as e:
            return ClusterStatus(
                cluster=cluster_name,
                context=cluster_cfg.context,
                connected=False,
                namespace=cluster_cfg.namespace,
                error=f"Failed to switch context: {e}",
            )

        connected = self._client.check_connection()
        if not connected:
            return ClusterStatus(
                cluster=cluster_name,
                context=cluster_cfg.context,
                connected=False,
                namespace=cluster_cfg.namespace,
                error="Cluster unreachable",
            )

        version: str | None = None
        node_count: int | None = None

        with contextlib.suppress(Exception):
            version = self._client.get_cluster_version()

        try:
            nodes = self._client.core_v1.list_node()
            node_count = len(nodes.items) if nodes.items else 0
        except Exception:
            pass

        return ClusterStatus(
            cluster=cluster_name,
            context=cluster_cfg.context,
            connected=True,
            version=version,
            node_count=node_count,
            namespace=cluster_cfg.namespace,
        )

    # -----------------------------------------------------------------------
    # Deploy
    # -----------------------------------------------------------------------

    def load_manifests_from_path(self, path: Path) -> list[dict[str, Any]]:
        """Load manifests from a file or directory path.

        Delegates to ManifestManager for YAML parsing.

        Args:
            path: Path to a YAML file or directory.

        Returns:
            List of parsed manifest dictionaries.
        """
        manifest_mgr = ManifestManager(self._client)
        return manifest_mgr.load_manifests(path)

    def load_manifests_from_string(self, content: str) -> list[dict[str, Any]]:
        """Parse manifests from a YAML string (e.g., stdin).

        Handles multi-document YAML (``---`` separated).

        Args:
            content: YAML string with one or more documents.

        Returns:
            List of parsed manifest dictionaries.

        Raises:
            ValueError: If the YAML cannot be parsed.
        """
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        yaml = YAML(typ="safe")
        try:
            documents = list(yaml.load_all(content))
        except YAMLError as e:
            raise ValueError(f"Failed to parse YAML from input: {e}") from e

        manifests: list[dict[str, Any]] = []
        for doc in documents:
            if doc is None:
                continue
            if not isinstance(doc, dict):
                self._log.warning(
                    "skipping_non_dict_document",
                    type=type(doc).__name__,
                )
                continue
            doc["_source_file"] = "<stdin>"
            manifests.append(doc)

        self._log.debug("loaded_manifests_from_string", count=len(manifests))
        return manifests

    def deploy_manifests_to_clusters(
        self,
        manifests: list[dict[str, Any]],
        *,
        clusters: list[str] | None = None,
        namespace: str | None = None,
        dry_run: bool = False,
    ) -> MultiClusterDeployResult:
        """Deploy manifests to multiple clusters.

        Args:
            manifests: Parsed manifest dictionaries.
            clusters: Target cluster names, or None for all configured.
            namespace: Override namespace for all resources.
            dry_run: If True, only simulate the deploy.

        Returns:
            Aggregated deploy result with per-cluster details.
        """
        target_clusters = self._resolve_clusters(clusters)
        self._log.info(
            "deploying_to_clusters",
            clusters=target_clusters,
            manifest_count=len(manifests),
            dry_run=dry_run,
        )

        cluster_results: list[ClusterDeployResult] = []

        with self._save_and_restore_context():
            for cluster_name in target_clusters:
                result = self._deploy_to_single_cluster(
                    cluster_name,
                    manifests,
                    namespace=namespace,
                    dry_run=dry_run,
                )
                cluster_results.append(result)

        successful = sum(1 for r in cluster_results if r.success)

        deploy_result = MultiClusterDeployResult(
            cluster_results=cluster_results,
            total_clusters=len(cluster_results),
            successful=successful,
            failed=len(cluster_results) - successful,
        )
        self._log.info(
            "deploy_complete",
            total=deploy_result.total_clusters,
            successful=deploy_result.successful,
            failed=deploy_result.failed,
        )
        return deploy_result

    def _deploy_to_single_cluster(
        self,
        cluster_name: str,
        manifests: list[dict[str, Any]],
        *,
        namespace: str | None,
        dry_run: bool,
    ) -> ClusterDeployResult:
        """Deploy manifests to a single cluster."""
        try:
            self._client.switch_context(cluster_name)
        except Exception as e:
            return ClusterDeployResult(
                cluster=cluster_name,
                success=False,
                error=f"Failed to switch context: {e}",
            )

        try:
            manifest_mgr = ManifestManager(self._client)
            apply_results = manifest_mgr.apply_manifests(
                manifests,
                namespace=namespace,
                dry_run=dry_run,
            )

            applied = sum(1 for r in apply_results if r.success)
            failed = sum(1 for r in apply_results if not r.success)
            results_data = [
                {
                    "resource": r.resource,
                    "action": r.action,
                    "namespace": r.namespace,
                    "success": r.success,
                    "message": r.message,
                }
                for r in apply_results
            ]

            return ClusterDeployResult(
                cluster=cluster_name,
                success=failed == 0,
                resources_applied=applied,
                resources_failed=failed,
                results=results_data,
            )
        except Exception as e:
            return ClusterDeployResult(
                cluster=cluster_name,
                success=False,
                error=str(e),
            )

    # -----------------------------------------------------------------------
    # Sync
    # -----------------------------------------------------------------------

    def sync_resource(
        self,
        source_cluster: str,
        target_clusters: list[str],
        *,
        resource_type: str,
        resource_name: str,
        namespace: str | None = None,
        dry_run: bool = False,
    ) -> MultiClusterSyncResult:
        """Sync a resource from one cluster to others.

        Reads the resource from the source cluster, strips server-managed
        fields, and applies it to each target cluster.

        Args:
            source_cluster: Cluster to read the resource from.
            target_clusters: Clusters to apply the resource to.
            resource_type: Kubernetes resource kind (e.g., 'Deployment').
            resource_name: Name of the resource.
            namespace: Namespace of the resource (for namespaced resources).
            dry_run: If True, only simulate the sync.

        Returns:
            Aggregated sync result with per-target-cluster details.
        """
        # Validate clusters exist
        all_clusters = [source_cluster, *target_clusters]
        self._resolve_clusters(all_clusters)

        self._log.info(
            "syncing_resource",
            source=source_cluster,
            targets=target_clusters,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

        cluster_results: list[ClusterSyncResult] = []

        with self._save_and_restore_context():
            # Step 1: Read resource from source cluster
            resource_dict = self._read_resource_from_cluster(
                source_cluster,
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
            )

            if resource_dict is None:
                # Source read failed, mark all targets as failed
                for target in target_clusters:
                    cluster_results.append(
                        ClusterSyncResult(
                            cluster=target,
                            success=False,
                            error=f"Failed to read {resource_type}/{resource_name} from {source_cluster}",
                        )
                    )
            else:
                # Step 2: Clean the resource for sync
                cleaned = self._strip_server_fields(resource_dict)

                # Step 3: Apply to each target cluster
                for target in target_clusters:
                    result = self._sync_to_single_cluster(
                        target,
                        cleaned,
                        dry_run=dry_run,
                    )
                    cluster_results.append(result)

        successful = sum(1 for r in cluster_results if r.success)

        sync_result = MultiClusterSyncResult(
            source_cluster=source_cluster,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            cluster_results=cluster_results,
            total_targets=len(cluster_results),
            successful=successful,
            failed=len(cluster_results) - successful,
        )
        self._log.info(
            "sync_complete",
            successful=sync_result.successful,
            failed=sync_result.failed,
        )
        return sync_result

    def _read_resource_from_cluster(
        self,
        cluster_name: str,
        *,
        resource_type: str,
        resource_name: str,
        namespace: str | None,
    ) -> dict[str, Any] | None:
        """Read a resource from a cluster using the dynamic client."""
        try:
            self._client.switch_context(cluster_name)
        except Exception as e:
            self._log.error(
                "sync_source_context_failed",
                cluster=cluster_name,
                error=str(e),
            )
            return None

        try:
            dynamic = self._get_dynamic_client()
            # Search across common API groups for the resource kind
            resource_api = self._find_resource_api(dynamic, resource_type)
            if resource_api is None:
                self._log.error("resource_kind_not_found", kind=resource_type)
                return None

            kwargs: dict[str, Any] = {"name": resource_name}
            if namespace:
                kwargs["namespace"] = namespace

            live_obj = resource_api.get(**kwargs)
            return live_obj.to_dict() if hasattr(live_obj, "to_dict") else dict(live_obj)
        except Exception as e:
            self._log.error(
                "sync_source_read_failed",
                cluster=cluster_name,
                resource=f"{resource_type}/{resource_name}",
                error=str(e),
            )
            return None

    def _find_resource_api(self, dynamic: Any, resource_type: str) -> Any:
        """Find the dynamic API resource for a given kind.

        Searches across API groups to find the matching resource kind.
        """
        try:
            # Try to discover the resource by kind
            for api_resource in dynamic.resources:
                if api_resource.kind == resource_type:
                    return api_resource
        except Exception:
            pass

        # Fallback: try common api_version/kind combinations
        common_api_versions = [
            "v1",
            "apps/v1",
            "batch/v1",
            "networking.k8s.io/v1",
            "rbac.authorization.k8s.io/v1",
            "storage.k8s.io/v1",
            "policy/v1",
        ]
        for api_version in common_api_versions:
            try:
                return dynamic.resources.get(api_version=api_version, kind=resource_type)
            except Exception:
                continue

        return None

    def _sync_to_single_cluster(
        self,
        cluster_name: str,
        resource_dict: dict[str, Any],
        *,
        dry_run: bool,
    ) -> ClusterSyncResult:
        """Apply a cleaned resource to a single target cluster."""
        try:
            self._client.switch_context(cluster_name)
        except Exception as e:
            return ClusterSyncResult(
                cluster=cluster_name,
                success=False,
                error=f"Failed to switch context: {e}",
            )

        if dry_run:
            return ClusterSyncResult(
                cluster=cluster_name,
                success=True,
                action="skipped (dry-run)",
            )

        try:
            manifest_mgr = ManifestManager(self._client)
            apply_results = manifest_mgr.apply_manifests([resource_dict])

            if apply_results and apply_results[0].success:
                return ClusterSyncResult(
                    cluster=cluster_name,
                    success=True,
                    action=apply_results[0].action,
                )
            error_msg = apply_results[0].message if apply_results else "No result"
            return ClusterSyncResult(
                cluster=cluster_name,
                success=False,
                error=error_msg,
            )
        except Exception as e:
            return ClusterSyncResult(
                cluster=cluster_name,
                success=False,
                error=str(e),
            )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _strip_server_fields(resource: dict[str, Any]) -> dict[str, Any]:
        """Remove server-managed fields from a resource for cross-cluster sync.

        Strips metadata fields (uid, resourceVersion, etc.) and top-level
        server fields (status) that should not be transferred between clusters.
        """
        cleaned = dict(resource)

        # Remove top-level server fields
        for top_field in SERVER_MANAGED_TOP_LEVEL_FIELDS:
            cleaned.pop(top_field, None)

        # Remove server-managed metadata fields
        metadata = cleaned.get("metadata")
        if isinstance(metadata, dict):
            metadata = dict(metadata)
            for meta_field in SERVER_MANAGED_METADATA_FIELDS:
                metadata.pop(meta_field, None)
            # Also strip cluster-specific annotations
            annotations = metadata.get("annotations")
            if isinstance(annotations, dict):
                annotations = {
                    k: v
                    for k, v in annotations.items()
                    if not k.startswith("kubectl.kubernetes.io/")
                }
                metadata["annotations"] = annotations if annotations else None
            cleaned["metadata"] = metadata

        return cleaned

    def _get_dynamic_client(self) -> Any:
        """Create a DynamicClient for the current context."""
        from kubernetes.client import ApiClient
        from kubernetes.dynamic import DynamicClient

        return DynamicClient(ApiClient())
