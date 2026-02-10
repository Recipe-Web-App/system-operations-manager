"""Kubernetes API client wrapper.

Provides a multi-cluster client that wraps the official kubernetes Python client
with context switching, lazy API group initialization, retry logic, and consistent
error translation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConflictError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesValidationError,
)

if TYPE_CHECKING:
    from kubernetes.client import (
        AppsV1Api,
        BatchV1Api,
        CoreV1Api,
        NetworkingV1Api,
        RbacAuthorizationV1Api,
        StorageV1Api,
        VersionApi,
    )

    from system_operations_manager.integrations.kubernetes.config import (
        KubernetesPluginConfig,
    )

logger = structlog.get_logger()


class KubernetesClient:
    """Multi-cluster Kubernetes API client.

    Wraps the official kubernetes Python client with:
    - Multi-cluster context management via kubeconfig
    - Lazy API group initialization
    - Automatic retry with tenacity for transient errors
    - Consistent error translation to custom exceptions
    - Context manager support

    Example:
        ```python
        from system_operations_manager.integrations.kubernetes import KubernetesClient
        from system_operations_manager.integrations.kubernetes.config import (
            KubernetesPluginConfig,
        )

        config = KubernetesPluginConfig.from_env()
        with KubernetesClient(config) as client:
            nodes = client.core_v1.list_node()
            print(f"Cluster has {len(nodes.items)} nodes")
        ```
    """

    def __init__(self, plugin_config: KubernetesPluginConfig) -> None:
        """Initialize Kubernetes client from plugin config.

        Loads kubeconfig and sets the active context. If no clusters are
        configured, falls back to default kubeconfig auto-detection
        (matching the existing KubernetesService behavior).

        Args:
            plugin_config: Complete plugin configuration.
        """
        self._config = plugin_config
        self._retries = plugin_config.defaults.retry_attempts
        self._current_context: str | None = None

        # Lazy-loaded API group instances
        self._core_v1: CoreV1Api | None = None
        self._apps_v1: AppsV1Api | None = None
        self._batch_v1: BatchV1Api | None = None
        self._networking_v1: NetworkingV1Api | None = None
        self._rbac_v1: RbacAuthorizationV1Api | None = None
        self._storage_v1: StorageV1Api | None = None
        self._version_api: VersionApi | None = None

        # Load kubeconfig
        self._load_config()

        logger.info(
            "Kubernetes client initialized",
            context=self._current_context,
            default_namespace=plugin_config.get_active_namespace(),
        )

    def _load_config(self) -> None:
        """Load Kubernetes configuration from kubeconfig or in-cluster."""
        from kubernetes import config
        from kubernetes.config import ConfigException

        active_context = self._config.get_active_context()

        try:
            # Determine kubeconfig path
            kubeconfig_path = None
            if self._config.active_cluster and self._config.active_cluster in self._config.clusters:
                cluster_cfg = self._config.clusters[self._config.active_cluster]
                kubeconfig_path = cluster_cfg.kubeconfig

            config.load_kube_config(
                config_file=kubeconfig_path,
                context=active_context,
            )
            self._current_context = active_context
            logger.debug(
                "loaded_kubeconfig",
                context=active_context,
                kubeconfig=kubeconfig_path,
            )
        except ConfigException:
            try:
                config.load_incluster_config()
                self._current_context = "in-cluster"
                logger.debug("loaded_incluster_config")
            except ConfigException as e:
                raise KubernetesConnectionError(
                    message="Cannot load Kubernetes configuration. "
                    "Ensure kubeconfig exists or running inside a cluster.",
                    original_error=e,
                ) from e

        # Reset cached API instances on config change
        self._invalidate_api_cache()

    def _invalidate_api_cache(self) -> None:
        """Clear cached API group instances."""
        self._core_v1 = None
        self._apps_v1 = None
        self._batch_v1 = None
        self._networking_v1 = None
        self._rbac_v1 = None
        self._storage_v1 = None
        self._version_api = None

    # =========================================================================
    # Lazy API Group Accessors
    # =========================================================================

    @property
    def core_v1(self) -> CoreV1Api:
        """Get CoreV1Api instance (pods, services, namespaces, secrets, configmaps, etc.)."""
        if self._core_v1 is None:
            from kubernetes.client import CoreV1Api

            self._core_v1 = CoreV1Api()
        return self._core_v1

    @property
    def apps_v1(self) -> AppsV1Api:
        """Get AppsV1Api instance (deployments, statefulsets, daemonsets, replicasets)."""
        if self._apps_v1 is None:
            from kubernetes.client import AppsV1Api

            self._apps_v1 = AppsV1Api()
        return self._apps_v1

    @property
    def batch_v1(self) -> BatchV1Api:
        """Get BatchV1Api instance (jobs, cronjobs)."""
        if self._batch_v1 is None:
            from kubernetes.client import BatchV1Api

            self._batch_v1 = BatchV1Api()
        return self._batch_v1

    @property
    def networking_v1(self) -> NetworkingV1Api:
        """Get NetworkingV1Api instance (ingresses, networkpolicies)."""
        if self._networking_v1 is None:
            from kubernetes.client import NetworkingV1Api

            self._networking_v1 = NetworkingV1Api()
        return self._networking_v1

    @property
    def rbac_v1(self) -> RbacAuthorizationV1Api:
        """Get RbacAuthorizationV1Api instance (roles, clusterroles, bindings)."""
        if self._rbac_v1 is None:
            from kubernetes.client import RbacAuthorizationV1Api

            self._rbac_v1 = RbacAuthorizationV1Api()
        return self._rbac_v1

    @property
    def storage_v1(self) -> StorageV1Api:
        """Get StorageV1Api instance (storageclasses, pvs, pvcs)."""
        if self._storage_v1 is None:
            from kubernetes.client import StorageV1Api

            self._storage_v1 = StorageV1Api()
        return self._storage_v1

    @property
    def version_api(self) -> VersionApi:
        """Get VersionApi instance for cluster version info."""
        if self._version_api is None:
            from kubernetes.client import VersionApi

            self._version_api = VersionApi()
        return self._version_api

    # =========================================================================
    # Context Management
    # =========================================================================

    def switch_context(self, context_name: str) -> None:
        """Switch to a different Kubernetes context.

        Args:
            context_name: The kubeconfig context name or a named cluster
                from the plugin config.

        Raises:
            KubernetesConnectionError: If the context cannot be loaded.
        """
        from kubernetes import config
        from kubernetes.config import ConfigException

        # Check if it's a named cluster in our config
        kubeconfig_path = None
        if context_name in self._config.clusters:
            cluster_cfg = self._config.clusters[context_name]
            context_name = cluster_cfg.context
            kubeconfig_path = cluster_cfg.kubeconfig

        try:
            config.load_kube_config(
                config_file=kubeconfig_path,
                context=context_name,
            )
            self._current_context = context_name
            self._invalidate_api_cache()
            logger.info("switched_context", context=context_name)
        except ConfigException as e:
            raise KubernetesConnectionError(
                message=f"Failed to switch to context '{context_name}'",
                original_error=e,
            ) from e

    def get_current_context(self) -> str:
        """Get the current active context name.

        Returns:
            The current context name, or 'in-cluster' if running inside a pod.
        """
        return self._current_context or "unknown"

    def list_contexts(self) -> list[dict[str, Any]]:
        """List all available kubeconfig contexts.

        Returns:
            List of context dictionaries with 'name', 'cluster', and 'namespace' keys.
        """
        from kubernetes import config

        try:
            contexts, active = config.list_kube_config_contexts()
        except Exception:
            return []

        result = []
        for ctx in contexts:
            ctx_info = ctx.get("context", {})
            result.append(
                {
                    "name": ctx.get("name", ""),
                    "cluster": ctx_info.get("cluster", ""),
                    "namespace": ctx_info.get("namespace", "default"),
                    "active": ctx.get("name") == active.get("name") if active else False,
                }
            )
        return result

    # =========================================================================
    # Error Translation
    # =========================================================================

    @staticmethod
    def translate_api_exception(
        e: Exception,
        resource_type: str | None = None,
        resource_name: str | None = None,
        namespace: str | None = None,
    ) -> KubernetesError:
        """Translate a kubernetes ApiException to a custom exception.

        Args:
            e: The original ApiException.
            resource_type: Type of resource being operated on.
            resource_name: Name of the resource.
            namespace: Namespace of the resource.

        Returns:
            An appropriate KubernetesError subclass.
        """
        from kubernetes.client import ApiException

        if not isinstance(e, ApiException):
            return KubernetesError(
                message=str(e),
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
            )

        status = e.status

        if status in (401, 403):
            return KubernetesAuthError(
                message=e.reason or "Authentication/authorization failed",
                status_code=status,
                reason=e.reason,
            )

        if status == 404:
            return KubernetesNotFoundError(
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
            )

        if status == 409:
            return KubernetesConflictError(
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
            )

        if status in (400, 422):
            return KubernetesValidationError(
                message=e.reason or "Validation failed",
                status_code=status,
            )

        return KubernetesError(
            message=e.reason or f"Kubernetes API error: {status}",
            status_code=status,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

    # =========================================================================
    # Retry Decorator
    # =========================================================================

    def make_retry_decorator(self) -> Any:
        """Create a retry decorator for transient connection errors.

        Returns:
            A tenacity retry decorator configured with exponential backoff.
        """
        return retry(
            retry=retry_if_exception_type(KubernetesConnectionError),
            stop=stop_after_attempt(self._retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )

    # =========================================================================
    # Connection Check
    # =========================================================================

    def check_connection(self) -> bool:
        """Check if connection to the Kubernetes API server is working.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            self.version_api.get_code()
            return True
        except Exception:
            return False

    def get_cluster_version(self) -> str:
        """Get the Kubernetes cluster version string.

        Returns:
            Kubernetes version (e.g., "v1.28.3").

        Raises:
            KubernetesConnectionError: If the cluster is unreachable.
        """
        try:
            version_info = self.version_api.get_code()
            return f"v{version_info.major}.{version_info.minor}"
        except Exception as e:
            raise KubernetesConnectionError(
                message="Failed to get cluster version",
                original_error=e,
            ) from e

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def default_namespace(self) -> str:
        """Get the default namespace from config."""
        return self._config.get_active_namespace()

    @property
    def timeout(self) -> int:
        """Get the configured timeout."""
        return self._config.get_active_timeout()

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def close(self) -> None:
        """Close the client and release resources."""
        self._invalidate_api_cache()
        logger.debug("Kubernetes client closed")

    def __enter__(self) -> KubernetesClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
