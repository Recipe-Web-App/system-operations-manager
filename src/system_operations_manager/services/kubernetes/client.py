"""Kubernetes service client.

Provides centralized Kubernetes operations for the system operations manager.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kubernetes.client import V1Namespace, V1Secret

logger = structlog.get_logger()


class KubernetesService:
    """Centralized Kubernetes service for common operations.

    Handles Kubernetes client initialization and provides methods for:
    - Namespace management
    - Secret management
    - ConfigMap management

    Example:
        >>> k8s = KubernetesService()
        >>> k8s.ensure_namespace("kong")
        >>> k8s.create_tls_secret("kong", "my-secret", cert_pem, key_pem)
    """

    def __init__(self) -> None:
        """Initialize Kubernetes service.

        Loads kubeconfig from default locations or in-cluster config.
        """
        from kubernetes import client, config

        self._log = logger.bind(service="kubernetes")

        try:
            config.load_kube_config()
            self._log.debug("loaded_kubeconfig")
        except config.ConfigException:
            config.load_incluster_config()
            self._log.debug("loaded_incluster_config")

        self._core_v1 = client.CoreV1Api()
        self._apps_v1 = client.AppsV1Api()

    # =========================================================================
    # Namespace Operations
    # =========================================================================

    def namespace_exists(self, name: str) -> bool:
        """Check if a namespace exists.

        Args:
            name: Namespace name.

        Returns:
            True if namespace exists, False otherwise.
        """
        from kubernetes.client import ApiException

        try:
            self._core_v1.read_namespace(name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_namespace(self, name: str) -> V1Namespace:
        """Create a namespace.

        Args:
            name: Namespace name.

        Returns:
            Created namespace object.

        Raises:
            ApiException: If namespace already exists or creation fails.
        """
        from kubernetes import client

        ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
        result = self._core_v1.create_namespace(ns)
        self._log.info("namespace_created", namespace=name)
        return result

    def ensure_namespace(self, name: str) -> V1Namespace:
        """Ensure a namespace exists, creating if necessary.

        Args:
            name: Namespace name.

        Returns:
            Namespace object (existing or newly created).
        """
        from kubernetes.client import ApiException

        try:
            return self._core_v1.read_namespace(name)
        except ApiException as e:
            if e.status == 404:
                return self.create_namespace(name)
            raise

    def delete_namespace(self, name: str) -> None:
        """Delete a namespace.

        Args:
            name: Namespace name.
        """
        self._core_v1.delete_namespace(name)
        self._log.info("namespace_deleted", namespace=name)

    # =========================================================================
    # Secret Operations
    # =========================================================================

    def secret_exists(self, namespace: str, name: str) -> bool:
        """Check if a secret exists.

        Args:
            namespace: Namespace name.
            name: Secret name.

        Returns:
            True if secret exists, False otherwise.
        """
        from kubernetes.client import ApiException

        try:
            self._core_v1.read_namespaced_secret(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_secret(
        self,
        namespace: str,
        name: str,
        data: dict[str, str],
        secret_type: str = "Opaque",
    ) -> V1Secret:
        """Create a secret.

        Args:
            namespace: Namespace name.
            name: Secret name.
            data: Secret data (will be stored as string_data).
            secret_type: Secret type (default: Opaque).

        Returns:
            Created secret object.
        """
        from kubernetes import client

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            type=secret_type,
            string_data=data,
        )
        result = self._core_v1.create_namespaced_secret(namespace, secret)
        self._log.info("secret_created", namespace=namespace, name=name)
        return result

    def create_tls_secret(
        self,
        namespace: str,
        name: str,
        cert_pem: str,
        key_pem: str,
        *,
        force: bool = False,
    ) -> V1Secret:
        """Create a TLS secret.

        Args:
            namespace: Namespace name.
            name: Secret name.
            cert_pem: Certificate PEM data.
            key_pem: Private key PEM data.
            force: If True, delete existing secret first.

        Returns:
            Created secret object.

        Raises:
            RuntimeError: If secret exists and force=False.
        """
        if self.secret_exists(namespace, name):
            if not force:
                raise RuntimeError(
                    f"Secret '{name}' already exists in namespace '{namespace}'. "
                    "Use force=True to overwrite."
                )
            self.delete_secret(namespace, name)

        return self.create_secret(
            namespace=namespace,
            name=name,
            data={"tls.crt": cert_pem, "tls.key": key_pem},
            secret_type="kubernetes.io/tls",
        )

    def delete_secret(self, namespace: str, name: str) -> None:
        """Delete a secret.

        Args:
            namespace: Namespace name.
            name: Secret name.
        """
        self._core_v1.delete_namespaced_secret(name, namespace)
        self._log.info("secret_deleted", namespace=namespace, name=name)

    def get_secret(self, namespace: str, name: str) -> V1Secret:
        """Get a secret.

        Args:
            namespace: Namespace name.
            name: Secret name.

        Returns:
            Secret object.
        """
        return self._core_v1.read_namespaced_secret(name, namespace)

    # =========================================================================
    # ConfigMap Operations
    # =========================================================================

    def configmap_exists(self, namespace: str, name: str) -> bool:
        """Check if a configmap exists.

        Args:
            namespace: Namespace name.
            name: ConfigMap name.

        Returns:
            True if configmap exists, False otherwise.
        """
        from kubernetes.client import ApiException

        try:
            self._core_v1.read_namespaced_config_map(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_configmap(
        self,
        namespace: str,
        name: str,
        data: dict[str, str],
    ) -> None:
        """Create a configmap.

        Args:
            namespace: Namespace name.
            name: ConfigMap name.
            data: ConfigMap data.
        """
        from kubernetes import client

        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            data=data,
        )
        self._core_v1.create_namespaced_config_map(namespace, configmap)
        self._log.info("configmap_created", namespace=namespace, name=name)

    def delete_configmap(self, namespace: str, name: str) -> None:
        """Delete a configmap.

        Args:
            namespace: Namespace name.
            name: ConfigMap name.
        """
        self._core_v1.delete_namespaced_config_map(name, namespace)
        self._log.info("configmap_deleted", namespace=namespace, name=name)
