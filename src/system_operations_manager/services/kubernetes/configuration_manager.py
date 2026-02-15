"""Kubernetes configuration resource manager.

Manages ConfigMaps and Secrets through the Kubernetes API.
Secret values are never exposed in display models for security.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from system_operations_manager.integrations.kubernetes.models.configuration import (
    ConfigMapSummary,
    SecretSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class ConfigurationManager(K8sBaseManager):
    """Manager for Kubernetes configuration resources.

    Provides CRUD operations for ConfigMaps and Secrets, including
    specialized Secret types (TLS, docker-registry).

    Security: Secret values are never included in display model responses.
    """

    _entity_name = "configuration"

    # =========================================================================
    # ConfigMap Operations
    # =========================================================================

    def list_config_maps(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[ConfigMapSummary]:
        """List configmaps.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of configmap summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_configmaps", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.core_v1.list_config_map_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_config_map(namespace=ns, **kwargs)

            items = [ConfigMapSummary.from_k8s_object(cm) for cm in result.items]
            self._log.debug("listed_configmaps", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", None, ns)

    def get_config_map(self, name: str, namespace: str | None = None) -> ConfigMapSummary:
        """Get a single configmap by name (metadata only).

        Args:
            name: ConfigMap name.
            namespace: Target namespace.

        Returns:
            ConfigMap summary (keys listed, values not included).
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_configmap", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_config_map(name=name, namespace=ns)
            return ConfigMapSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", name, ns)

    def get_config_map_data(self, name: str, namespace: str | None = None) -> dict[str, str]:
        """Get the actual data values of a configmap.

        Args:
            name: ConfigMap name.
            namespace: Target namespace.

        Returns:
            Dictionary of key-value pairs.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_configmap_data", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_config_map(name=name, namespace=ns)
            return dict(result.data or {})
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", name, ns)

    def create_config_map(
        self,
        name: str,
        namespace: str | None = None,
        *,
        data: dict[str, str] | None = None,
        labels: dict[str, str] | None = None,
    ) -> ConfigMapSummary:
        """Create a configmap.

        Args:
            name: ConfigMap name.
            namespace: Target namespace.
            data: Key-value pairs for the configmap.
            labels: ConfigMap labels.

        Returns:
            Created configmap summary.
        """
        from kubernetes.client import V1ConfigMap, V1ObjectMeta

        ns = self._resolve_namespace(namespace)

        body = V1ConfigMap(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            data=data,
        )

        self._log.info("creating_configmap", name=name, namespace=ns)
        try:
            result = self._client.core_v1.create_namespaced_config_map(namespace=ns, body=body)
            self._log.info("created_configmap", name=name, namespace=ns)
            return ConfigMapSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", name, ns)

    def update_config_map(
        self,
        name: str,
        namespace: str | None = None,
        *,
        data: dict[str, str] | None = None,
    ) -> ConfigMapSummary:
        """Update a configmap's data (patch).

        Args:
            name: ConfigMap name.
            namespace: Target namespace.
            data: New key-value pairs (replaces existing data).

        Returns:
            Updated configmap summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_configmap", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {}
            if data is not None:
                patch["data"] = data

            result = self._client.core_v1.patch_namespaced_config_map(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_configmap", name=name, namespace=ns)
            return ConfigMapSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", name, ns)

    def delete_config_map(self, name: str, namespace: str | None = None) -> None:
        """Delete a configmap.

        Args:
            name: ConfigMap name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_configmap", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_config_map(name=name, namespace=ns)
            self._log.info("deleted_configmap", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "ConfigMap", name, ns)

    # =========================================================================
    # Secret Operations
    # =========================================================================

    def list_secrets(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[SecretSummary]:
        """List secrets (keys only, values hidden).

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of secret summaries (no secret values).
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_secrets", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.core_v1.list_secret_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_secret(namespace=ns, **kwargs)

            items = [SecretSummary.from_k8s_object(s) for s in result.items]
            self._log.debug("listed_secrets", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Secret", None, ns)

    def get_secret(self, name: str, namespace: str | None = None) -> SecretSummary:
        """Get a single secret by name (keys only, values hidden).

        Args:
            name: Secret name.
            namespace: Target namespace.

        Returns:
            Secret summary (no secret values).
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_secret", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_secret(name=name, namespace=ns)
            return SecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)

    def create_secret(
        self,
        name: str,
        namespace: str | None = None,
        *,
        data: dict[str, str] | None = None,
        secret_type: str = "Opaque",
        labels: dict[str, str] | None = None,
    ) -> SecretSummary:
        """Create a secret.

        Args:
            name: Secret name.
            namespace: Target namespace.
            data: Key-value pairs (values will be base64-encoded).
            secret_type: Secret type (Opaque, kubernetes.io/tls, etc.).
            labels: Secret labels.

        Returns:
            Created secret summary.
        """
        from kubernetes.client import V1ObjectMeta, V1Secret

        ns = self._resolve_namespace(namespace)

        # Base64-encode string values
        encoded_data = None
        if data:
            encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}

        body = V1Secret(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            type=secret_type,
            data=encoded_data,
        )

        self._log.info("creating_secret", name=name, namespace=ns, type=secret_type)
        try:
            result = self._client.core_v1.create_namespaced_secret(namespace=ns, body=body)
            self._log.info("created_secret", name=name, namespace=ns)
            return SecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)

    def create_tls_secret(
        self,
        name: str,
        namespace: str | None = None,
        *,
        cert: str,
        key: str,
        labels: dict[str, str] | None = None,
    ) -> SecretSummary:
        """Create a TLS secret.

        Args:
            name: Secret name.
            namespace: Target namespace.
            cert: PEM-encoded certificate.
            key: PEM-encoded private key.
            labels: Secret labels.

        Returns:
            Created secret summary.
        """
        from kubernetes.client import V1ObjectMeta, V1Secret

        ns = self._resolve_namespace(namespace)

        body = V1Secret(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            type="kubernetes.io/tls",
            data={
                "tls.crt": base64.b64encode(cert.encode()).decode(),
                "tls.key": base64.b64encode(key.encode()).decode(),
            },
        )

        self._log.info("creating_tls_secret", name=name, namespace=ns)
        try:
            result = self._client.core_v1.create_namespaced_secret(namespace=ns, body=body)
            self._log.info("created_tls_secret", name=name, namespace=ns)
            return SecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)

    def create_docker_registry_secret(
        self,
        name: str,
        namespace: str | None = None,
        *,
        server: str,
        username: str,
        password: str,
        email: str = "",
        labels: dict[str, str] | None = None,
    ) -> SecretSummary:
        """Create a docker-registry secret.

        Args:
            name: Secret name.
            namespace: Target namespace.
            server: Docker registry server URL.
            username: Registry username.
            password: Registry password.
            email: Registry email.
            labels: Secret labels.

        Returns:
            Created secret summary.
        """
        from kubernetes.client import V1ObjectMeta, V1Secret

        ns = self._resolve_namespace(namespace)

        docker_config = {
            "auths": {
                server: {
                    "username": username,
                    "password": password,
                    "email": email,
                    "auth": base64.b64encode(f"{username}:{password}".encode()).decode(),
                }
            }
        }

        body = V1Secret(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            type="kubernetes.io/dockerconfigjson",
            data={
                ".dockerconfigjson": base64.b64encode(json.dumps(docker_config).encode()).decode(),
            },
        )

        self._log.info("creating_docker_registry_secret", name=name, namespace=ns, server=server)
        try:
            result = self._client.core_v1.create_namespaced_secret(namespace=ns, body=body)
            self._log.info("created_docker_registry_secret", name=name, namespace=ns)
            return SecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)

    def delete_secret(self, name: str, namespace: str | None = None) -> None:
        """Delete a secret.

        Args:
            name: Secret name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_secret", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_secret(name=name, namespace=ns)
            self._log.info("deleted_secret", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)

    def update_secret(
        self,
        name: str,
        namespace: str | None = None,
        *,
        data: dict[str, str] | None = None,
    ) -> SecretSummary:
        """Update a secret's data (patch).

        Args:
            name: Secret name.
            namespace: Target namespace.
            data: New key-value pairs (values will be base64-encoded).

        Returns:
            Updated secret summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_secret", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {}
            if data is not None:
                patch["data"] = {
                    k: base64.b64encode(v.encode()).decode() for k, v in data.items()
                }

            result = self._client.core_v1.patch_namespaced_secret(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_secret", name=name, namespace=ns)
            return SecretSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Secret", name, ns)
