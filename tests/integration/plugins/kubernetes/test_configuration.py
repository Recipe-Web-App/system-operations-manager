"""Integration tests for ConfigurationManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesNotFoundError
from system_operations_manager.services.kubernetes import ConfigurationManager


@pytest.mark.integration
@pytest.mark.kubernetes
class TestConfigMapCRUD:
    """Test ConfigMap CRUD operations."""

    def test_create_config_map(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_config_map should create a new configmap."""
        cm_name = f"test-cm-{unique_name}"
        data = {"key1": "value1", "key2": "value2"}

        result = config_manager.create_config_map(
            cm_name,
            test_namespace,
            data=data,
        )

        assert result.name == cm_name
        assert result.namespace == test_namespace
        assert len(result.keys) == 2
        assert "key1" in result.keys
        assert "key2" in result.keys

    def test_list_config_maps(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_config_maps should return created configmaps."""
        cm_name = f"test-cm-{unique_name}"
        config_manager.create_config_map(
            cm_name,
            test_namespace,
            data={"test": "data"},
        )

        config_maps = config_manager.list_config_maps(test_namespace)

        assert len(config_maps) >= 1
        assert any(cm.name == cm_name for cm in config_maps)

    def test_get_config_map(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """get_config_map should retrieve a configmap by name."""
        cm_name = f"test-cm-{unique_name}"
        config_manager.create_config_map(
            cm_name,
            test_namespace,
            data={"foo": "bar"},
        )

        result = config_manager.get_config_map(cm_name, test_namespace)

        assert result.name == cm_name
        assert result.namespace == test_namespace
        assert "foo" in result.keys

    def test_get_config_map_data(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """get_config_map_data should retrieve actual data values."""
        cm_name = f"test-cm-{unique_name}"
        data = {"key1": "value1", "key2": "value2"}
        config_manager.create_config_map(
            cm_name,
            test_namespace,
            data=data,
        )

        result = config_manager.get_config_map_data(cm_name, test_namespace)

        assert result == data
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"

    def test_update_config_map(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """update_config_map should update configmap data."""
        cm_name = f"test-cm-{unique_name}"
        config_manager.create_config_map(
            cm_name,
            test_namespace,
            data={"original": "data"},
        )

        new_data = {"updated": "value", "new_key": "new_value"}
        result = config_manager.update_config_map(
            cm_name,
            test_namespace,
            data=new_data,
        )

        assert result.name == cm_name
        assert "updated" in result.keys
        assert "new_key" in result.keys

        # Verify data was updated
        data = config_manager.get_config_map_data(cm_name, test_namespace)
        assert data["updated"] == "value"
        assert data["new_key"] == "new_value"

    def test_delete_config_map(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """delete_config_map should delete a configmap."""
        cm_name = f"test-cm-{unique_name}"
        config_manager.create_config_map(
            cm_name,
            test_namespace,
            data={"test": "data"},
        )

        config_manager.delete_config_map(cm_name, test_namespace)

        # Verify deletion
        with pytest.raises(KubernetesNotFoundError):
            config_manager.get_config_map(cm_name, test_namespace)

    def test_get_nonexistent_configmap_raises(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
    ) -> None:
        """get_config_map should raise KubernetesNotFoundError for missing configmap."""
        with pytest.raises(KubernetesNotFoundError):
            config_manager.get_config_map("nonexistent-cm", test_namespace)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestSecretCRUD:
    """Test Secret CRUD operations."""

    def test_create_secret(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_secret should create an Opaque secret."""
        secret_name = f"test-secret-{unique_name}"
        data = {"username": "admin", "password": "secret123"}

        result = config_manager.create_secret(
            secret_name,
            test_namespace,
            data=data,
            secret_type="Opaque",
        )

        assert result.name == secret_name
        assert result.namespace == test_namespace
        assert result.type == "Opaque"
        assert len(result.keys) == 2
        assert "username" in result.keys
        assert "password" in result.keys

    def test_list_secrets(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_secrets should return created secrets."""
        secret_name = f"test-secret-{unique_name}"
        config_manager.create_secret(
            secret_name,
            test_namespace,
            data={"key": "value"},
        )

        secrets = config_manager.list_secrets(test_namespace)

        assert len(secrets) >= 1
        assert any(s.name == secret_name for s in secrets)

    def test_get_secret(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """get_secret should retrieve secret with keys only, no values."""
        secret_name = f"test-secret-{unique_name}"
        config_manager.create_secret(
            secret_name,
            test_namespace,
            data={"api_key": "supersecret"},
        )

        result = config_manager.get_secret(secret_name, test_namespace)

        assert result.name == secret_name
        assert result.namespace == test_namespace
        assert "api_key" in result.keys
        # Values should not be exposed in summary

    def test_delete_secret(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """delete_secret should delete a secret."""
        secret_name = f"test-secret-{unique_name}"
        config_manager.create_secret(
            secret_name,
            test_namespace,
            data={"key": "value"},
        )

        config_manager.delete_secret(secret_name, test_namespace)

        # Verify deletion
        with pytest.raises(KubernetesNotFoundError):
            config_manager.get_secret(secret_name, test_namespace)

    def test_get_nonexistent_secret_raises(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
    ) -> None:
        """get_secret should raise KubernetesNotFoundError for missing secret."""
        with pytest.raises(KubernetesNotFoundError):
            config_manager.get_secret("nonexistent-secret", test_namespace)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestSecretTypes:
    """Test specialized secret types."""

    def test_create_tls_secret(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_tls_secret should create a TLS secret."""
        secret_name = f"test-tls-{unique_name}"
        # Dummy self-signed cert and key (base64-encoded values are fine for testing)
        cert = "-----BEGIN CERTIFICATE-----\nMIICdummy\n-----END CERTIFICATE-----"
        key = "-----BEGIN PRIVATE KEY-----\nMIIEdummy\n-----END PRIVATE KEY-----"

        result = config_manager.create_tls_secret(
            secret_name,
            test_namespace,
            cert=cert,
            key=key,
        )

        assert result.name == secret_name
        assert result.namespace == test_namespace
        assert result.type == "kubernetes.io/tls"
        assert "tls.crt" in result.keys
        assert "tls.key" in result.keys

    def test_create_docker_registry_secret(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_docker_registry_secret should create a docker-registry secret."""
        secret_name = f"test-docker-{unique_name}"

        result = config_manager.create_docker_registry_secret(
            secret_name,
            test_namespace,
            server="https://registry.example.com",
            username="testuser",
            password="testpass",
            email="test@example.com",
        )

        assert result.name == secret_name
        assert result.namespace == test_namespace
        assert result.type == "kubernetes.io/dockerconfigjson"
        assert ".dockerconfigjson" in result.keys

    def test_create_tls_secret_with_labels(
        self,
        config_manager: ConfigurationManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """create_tls_secret should support labels."""
        secret_name = f"test-tls-{unique_name}"
        cert = "-----BEGIN CERTIFICATE-----\nMIICdummy\n-----END CERTIFICATE-----"
        key = "-----BEGIN PRIVATE KEY-----\nMIIEdummy\n-----END PRIVATE KEY-----"
        labels = {"app": "web", "environment": "staging"}

        result = config_manager.create_tls_secret(
            secret_name,
            test_namespace,
            cert=cert,
            key=key,
            labels=labels,
        )

        assert result.name == secret_name
        assert result.labels is not None
        assert result.labels["app"] == "web"
        assert result.labels["environment"] == "staging"
