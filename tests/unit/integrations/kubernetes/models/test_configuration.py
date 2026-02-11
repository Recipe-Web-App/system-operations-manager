"""Unit tests for Kubernetes configuration resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.configuration import (
    ConfigMapSummary,
    SecretSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfigMapSummary:
    """Test ConfigMapSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete ConfigMap."""
        obj = MagicMock()
        obj.metadata.name = "app-config"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-cm-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "myapp"}
        obj.metadata.annotations = {"description": "Application configuration"}

        obj.data = {
            "config.yaml": "app: myapp\nport: 8080",
            "settings.json": '{"debug": true}',
            "database.conf": "host=localhost",
        }
        obj.binary_data = {
            "logo.png": "iVBORw0KGgo...",
        }

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.name == "app-config"
        assert cm.namespace == "default"
        assert cm.data_keys == ["config.yaml", "database.conf", "settings.json"]
        assert cm.binary_data_keys == ["logo.png"]

    def test_from_k8s_object_data_only(self) -> None:
        """Test from_k8s_object with only data."""
        obj = MagicMock()
        obj.metadata.name = "data-config"
        obj.metadata.namespace = "prod"

        obj.data = {"key1": "value1", "key2": "value2"}
        obj.binary_data = None

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.name == "data-config"
        assert cm.data_keys == ["key1", "key2"]
        assert cm.binary_data_keys == []

    def test_from_k8s_object_binary_only(self) -> None:
        """Test from_k8s_object with only binary data."""
        obj = MagicMock()
        obj.metadata.name = "binary-config"
        obj.metadata.namespace = "default"

        obj.data = None
        obj.binary_data = {"file.bin": "AQIDBAU="}

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.data_keys == []
        assert cm.binary_data_keys == ["file.bin"]

    def test_from_k8s_object_empty(self) -> None:
        """Test from_k8s_object with empty ConfigMap."""
        obj = MagicMock()
        obj.metadata.name = "empty-config"
        obj.metadata.namespace = "default"

        obj.data = {}
        obj.binary_data = {}

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.data_keys == []
        assert cm.binary_data_keys == []

    def test_from_k8s_object_no_data(self) -> None:
        """Test from_k8s_object with no data or binary_data."""
        obj = MagicMock()
        obj.metadata.name = "no-data"
        obj.data = None
        obj.binary_data = None

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.data_keys == []
        assert cm.binary_data_keys == []

    def test_data_keys_sorted(self) -> None:
        """Test that data_keys are sorted alphabetically."""
        obj = MagicMock()
        obj.metadata.name = "sorted-config"
        obj.data = {"zzz": "last", "aaa": "first", "mmm": "middle"}
        obj.binary_data = None

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.data_keys == ["aaa", "mmm", "zzz"]

    def test_binary_data_keys_sorted(self) -> None:
        """Test that binary_data_keys are sorted alphabetically."""
        obj = MagicMock()
        obj.metadata.name = "sorted-binary"
        obj.data = None
        obj.binary_data = {"file3.bin": "c", "file1.bin": "a", "file2.bin": "b"}

        cm = ConfigMapSummary.from_k8s_object(obj)

        assert cm.binary_data_keys == ["file1.bin", "file2.bin", "file3.bin"]

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ConfigMapSummary._entity_name == "configmap"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretSummary:
    """Test SecretSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Secret."""
        obj = MagicMock()
        obj.metadata.name = "db-credentials"
        obj.metadata.namespace = "production"
        obj.metadata.uid = "uid-secret-456"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "database"}
        obj.metadata.annotations = {"managed-by": "vault"}

        obj.type = "kubernetes.io/basic-auth"
        obj.data = {
            "username": "YWRtaW4=",
            "password": "cGFzc3dvcmQxMjM=",
        }

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.name == "db-credentials"
        assert secret.namespace == "production"
        assert secret.type == "kubernetes.io/basic-auth"
        assert secret.data_keys == ["password", "username"]

    def test_from_k8s_object_opaque(self) -> None:
        """Test from_k8s_object with Opaque secret."""
        obj = MagicMock()
        obj.metadata.name = "api-key"
        obj.metadata.namespace = "default"

        obj.type = "Opaque"
        obj.data = {"api-key": "c2VjcmV0"}

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.type == "Opaque"
        assert secret.data_keys == ["api-key"]

    def test_from_k8s_object_tls(self) -> None:
        """Test from_k8s_object with TLS secret."""
        obj = MagicMock()
        obj.metadata.name = "tls-cert"
        obj.metadata.namespace = "ingress"

        obj.type = "kubernetes.io/tls"
        obj.data = {
            "tls.crt": "LS0tLS1CRUdJTi...",
            "tls.key": "LS0tLS1CRUdJTi...",
        }

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.type == "kubernetes.io/tls"
        assert "tls.crt" in secret.data_keys
        assert "tls.key" in secret.data_keys

    def test_from_k8s_object_empty(self) -> None:
        """Test from_k8s_object with empty Secret."""
        obj = MagicMock()
        obj.metadata.name = "empty-secret"
        obj.metadata.namespace = "default"

        obj.type = "Opaque"
        obj.data = {}

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.data_keys == []

    def test_from_k8s_object_no_data(self) -> None:
        """Test from_k8s_object with None data."""
        obj = MagicMock()
        obj.metadata.name = "no-data-secret"
        obj.type = "Opaque"
        obj.data = None

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.data_keys == []

    def test_from_k8s_object_default_type(self) -> None:
        """Test from_k8s_object with default type."""
        obj = MagicMock()
        obj.metadata.name = "default-type"
        obj.type = None
        obj.data = {"key": "value"}

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.type == "Opaque"

    def test_data_keys_sorted(self) -> None:
        """Test that data_keys are sorted alphabetically."""
        obj = MagicMock()
        obj.metadata.name = "sorted-secret"
        obj.type = "Opaque"
        obj.data = {
            "zzz-key": "last",
            "aaa-key": "first",
            "mmm-key": "middle",
        }

        secret = SecretSummary.from_k8s_object(obj)

        assert secret.data_keys == ["aaa-key", "mmm-key", "zzz-key"]

    def test_no_secret_values_exposed(self) -> None:
        """Test that actual secret values are never exposed."""
        obj = MagicMock()
        obj.metadata.name = "secure-secret"
        obj.type = "Opaque"
        obj.data = {
            "password": "dGhpc2lzc2VjcmV0",
            "token": "YW5vdGhlcnNlY3JldA==",
        }

        secret = SecretSummary.from_k8s_object(obj)

        # Only key names should be present
        assert secret.data_keys == ["password", "token"]
        # Secret object should not have the actual values accessible
        assert "dGhpc2lzc2VjcmV0" not in str(secret.data_keys)
        assert "YW5vdGhlcnNlY3JldA==" not in str(secret.data_keys)

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert SecretSummary._entity_name == "secret"
