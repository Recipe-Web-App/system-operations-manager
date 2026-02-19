"""Unit tests for ExternalSecretsManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.models.external_secrets import (
    ExternalSecretSummary,
    SecretStoreSummary,
)
from system_operations_manager.services.kubernetes.externalsecrets_manager import (
    CLUSTER_SECRET_STORE_PLURAL,
    ESO_GROUP,
    ESO_NAMESPACE,
    ESO_VERSION,
    EXTERNAL_SECRET_PLURAL,
    SECRET_STORE_PLURAL,
    ExternalSecretsManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def manager(mock_k8s_client: MagicMock) -> ExternalSecretsManager:
    """Create an ExternalSecretsManager with mocked client."""
    return ExternalSecretsManager(mock_k8s_client)


# =============================================================================
# SecretStore Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretStoreOperations:
    """Tests for namespaced SecretStore CRUD operations."""

    def test_list_secret_stores_success_with_items(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_secret_stores should return one summary per item in the API response."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [{}, {}]
        }

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_secret_stores()

        assert len(result) == 2
        assert mock_from.call_count == 2
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            SECRET_STORE_PLURAL,
        )

    def test_list_secret_stores_with_label_selector(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_secret_stores should forward label_selector to the API call."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_secret_stores(label_selector="env=prod")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            SECRET_STORE_PLURAL,
            label_selector="env=prod",
        )

    def test_list_secret_stores_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_secret_stores should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = Exception(
            "connection refused"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_secret_stores()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_secret_store should call get_namespaced_custom_object and parse the result."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_secret_store("my-store")

        assert result is mock_summary
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            SECRET_STORE_PLURAL,
            "my-store",
        )

    def test_get_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_secret_store("missing-store")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_create_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_secret_store should build the correct CRD body and return a summary."""
        provider_config = {"vault": {"server": "https://vault.example.com"}}
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.create_secret_store("vault-store", provider_config=provider_config)

        assert result is mock_summary
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        group, version, ns, plural, body = call_args[0]
        assert group == ESO_GROUP
        assert version == ESO_VERSION
        assert ns == "default"
        assert plural == SECRET_STORE_PLURAL
        assert body["kind"] == "SecretStore"
        assert body["apiVersion"] == f"{ESO_GROUP}/{ESO_VERSION}"
        assert body["metadata"]["name"] == "vault-store"
        assert body["metadata"]["namespace"] == "default"
        assert body["metadata"]["labels"] == {}
        assert body["spec"]["provider"] == provider_config

    def test_create_secret_store_with_labels(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_secret_store should embed provided labels in the metadata."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object"):
            manager.create_secret_store(
                "aws-store",
                provider_config={"aws": {"service": "SecretsManager"}},
                labels={"team": "platform", "env": "prod"},
            )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["metadata"]["labels"] == {"team": "platform", "env": "prod"}

    def test_create_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "conflict"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.create_secret_store(
                "vault-store", provider_config={"vault": {"server": "https://vault.example.com"}}
            )

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_delete_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_secret_store should call delete_namespaced_custom_object."""
        manager.delete_secret_store("vault-store")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            SECRET_STORE_PLURAL,
            "vault-store",
        )

    def test_delete_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.delete_secret_store("vault-store")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# ClusterSecretStore Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterSecretStoreOperations:
    """Tests for cluster-scoped ClusterSecretStore CRUD operations."""

    def test_list_cluster_secret_stores_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_secret_stores should return summaries for all items."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": [{}]}

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_cluster_secret_stores()

        assert len(result) == 1
        mock_from.assert_called_once_with({}, is_cluster_store=True)
        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            CLUSTER_SECRET_STORE_PLURAL,
        )

    def test_list_cluster_secret_stores_with_label_selector(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_secret_stores should forward label_selector to the API call."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

        manager.list_cluster_secret_stores(label_selector="tier=infra")

        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            CLUSTER_SECRET_STORE_PLURAL,
            label_selector="tier=infra",
        )

    def test_list_cluster_secret_stores_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_secret_stores should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.side_effect = Exception(
            "connection refused"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_cluster_secret_stores()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_cluster_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_secret_store should call get_cluster_custom_object with is_cluster_store=True."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_cluster_secret_store("global-vault")

        assert result is mock_summary
        mock_from.assert_called_once_with({}, is_cluster_store=True)
        mock_k8s_client.custom_objects.get_cluster_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            CLUSTER_SECRET_STORE_PLURAL,
            "global-vault",
        )

    def test_get_cluster_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_cluster_secret_store("missing-store")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_create_cluster_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_secret_store should omit namespace from metadata and set kind correctly."""
        provider_config = {"aws": {"service": "SecretsManager", "region": "us-east-1"}}
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.create_cluster_secret_store(
                "global-aws", provider_config=provider_config
            )

        assert result is mock_summary
        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        group, version, plural, body = call_args[0]
        assert group == ESO_GROUP
        assert version == ESO_VERSION
        assert plural == CLUSTER_SECRET_STORE_PLURAL
        assert body["kind"] == "ClusterSecretStore"
        assert body["apiVersion"] == f"{ESO_GROUP}/{ESO_VERSION}"
        assert body["metadata"]["name"] == "global-aws"
        assert "namespace" not in body["metadata"]
        assert body["metadata"]["labels"] == {}
        assert body["spec"]["provider"] == provider_config

    def test_create_cluster_secret_store_with_labels(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_secret_store should embed provided labels in the metadata."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = {}

        with patch.object(SecretStoreSummary, "from_k8s_object"):
            manager.create_cluster_secret_store(
                "global-vault",
                provider_config={"vault": {"server": "https://vault.example.com"}},
                labels={"managed-by": "ops-cli"},
            )

        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        body = call_args[0][3]
        assert body["metadata"]["labels"] == {"managed-by": "ops-cli"}

    def test_create_cluster_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.side_effect = Exception(
            "already exists"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.create_cluster_secret_store(
                "global-vault",
                provider_config={"vault": {"server": "https://vault.example.com"}},
            )

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_delete_cluster_secret_store_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_cluster_secret_store should call delete_cluster_custom_object."""
        manager.delete_cluster_secret_store("global-vault")

        mock_k8s_client.custom_objects.delete_cluster_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            CLUSTER_SECRET_STORE_PLURAL,
            "global-vault",
        )

    def test_delete_cluster_secret_store_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_cluster_secret_store should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.delete_cluster_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.delete_cluster_secret_store("global-vault")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# ExternalSecret Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExternalSecretOperations:
    """Tests for namespaced ExternalSecret CRUD operations."""

    def test_list_external_secrets_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_external_secrets should return one summary per item in the API response."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [{}, {}, {}]
        }

        with patch.object(ExternalSecretSummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_external_secrets()

        assert len(result) == 3
        assert mock_from.call_count == 3
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            EXTERNAL_SECRET_PLURAL,
        )

    def test_list_external_secrets_with_label_selector(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_external_secrets should forward label_selector to the API call."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_external_secrets(label_selector="app=backend")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            EXTERNAL_SECRET_PLURAL,
            label_selector="app=backend",
        )

    def test_list_external_secrets_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_external_secrets should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = Exception(
            "timeout"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_external_secrets()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_external_secret_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_external_secret should call get_namespaced_custom_object and parse the result."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(ExternalSecretSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_external_secret("db-password")

        assert result is mock_summary
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            EXTERNAL_SECRET_PLURAL,
            "db-password",
        )

    def test_get_external_secret_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_external_secret should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_external_secret("missing-secret")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_create_external_secret_default_params(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_external_secret should build a correct body using defaults when no optional params are given."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(ExternalSecretSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.create_external_secret("db-password", store_name="vault-store")

        assert result is mock_summary
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        group, version, ns, plural, body = call_args[0]
        assert group == ESO_GROUP
        assert version == ESO_VERSION
        assert ns == "default"
        assert plural == EXTERNAL_SECRET_PLURAL
        assert body["kind"] == "ExternalSecret"
        assert body["apiVersion"] == f"{ESO_GROUP}/{ESO_VERSION}"
        assert body["metadata"]["name"] == "db-password"
        assert body["metadata"]["namespace"] == "default"
        assert body["metadata"]["labels"] == {}
        assert body["spec"]["refreshInterval"] == "1h"
        assert body["spec"]["secretStoreRef"]["name"] == "vault-store"
        assert body["spec"]["secretStoreRef"]["kind"] == "SecretStore"
        assert body["spec"]["target"] == {}
        assert body["spec"]["data"] == []

    def test_create_external_secret_all_params(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_external_secret should correctly embed all optional parameters."""
        data_mappings = [
            {"secretKey": "password", "remoteRef": {"key": "secret/db", "property": "password"}}
        ]
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(ExternalSecretSummary, "from_k8s_object"):
            manager.create_external_secret(
                "db-creds",
                "production",
                store_name="global-vault",
                store_kind="ClusterSecretStore",
                data=data_mappings,
                target_name="postgres-secret",
                refresh_interval="30m",
                labels={"app": "backend"},
            )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["metadata"]["name"] == "db-creds"
        assert body["metadata"]["namespace"] == "production"
        assert body["metadata"]["labels"] == {"app": "backend"}
        assert body["spec"]["refreshInterval"] == "30m"
        assert body["spec"]["secretStoreRef"]["name"] == "global-vault"
        assert body["spec"]["secretStoreRef"]["kind"] == "ClusterSecretStore"
        assert body["spec"]["target"] == {"name": "postgres-secret"}
        assert body["spec"]["data"] == data_mappings

    def test_create_external_secret_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_external_secret should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "conflict"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.create_external_secret("db-password", store_name="vault-store")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_delete_external_secret_success(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_external_secret should call delete_namespaced_custom_object."""
        manager.delete_external_secret("db-password")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            ESO_GROUP,
            ESO_VERSION,
            "default",
            EXTERNAL_SECRET_PLURAL,
            "db-password",
        )

    def test_delete_external_secret_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_external_secret should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.delete_external_secret("db-password")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Sync Status
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSyncStatus:
    """Tests for get_sync_status."""

    def test_get_sync_status_ready_with_all_fields(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_sync_status should return a dict with ready=True and all populated fields."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "db-password", "namespace": "default"},
            "spec": {
                "target": {"name": "postgres-secret"},
            },
            "status": {
                "syncedResourceVersion": "v1",
                "refreshTime": "2026-01-01T00:05:00Z",
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "True",
                        "message": "Secret synced successfully",
                    }
                ],
            },
        }

        result = manager.get_sync_status("db-password")

        assert result["name"] == "db-password"
        assert result["namespace"] == "default"
        assert result["ready"] is True
        assert result["message"] == "Secret synced successfully"
        assert result["synced_resource_version"] == "v1"
        assert result["refresh_time"] == "2026-01-01T00:05:00Z"
        assert result["target_secret"] == "postgres-secret"
        assert len(result["conditions"]) == 1

    def test_get_sync_status_not_ready(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_sync_status should return ready=False when the Ready condition status is not True."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "api-key", "namespace": "staging"},
            "spec": {},
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "False",
                        "message": "SecretStore not configured",
                    }
                ],
            },
        }

        result = manager.get_sync_status("api-key", "staging")

        assert result["ready"] is False
        assert result["message"] == "SecretStore not configured"

    def test_get_sync_status_no_conditions(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_sync_status should return ready=False and empty conditions list when status has no conditions."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "fresh-secret"},
            "spec": {},
            "status": {},
        }

        result = manager.get_sync_status("fresh-secret")

        assert result["ready"] is False
        assert result["message"] is None
        assert result["synced_resource_version"] is None
        assert result["refresh_time"] is None
        assert result["conditions"] == []

    def test_get_sync_status_target_name_falls_back_to_metadata_name(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_sync_status should use metadata.name as target_secret when spec.target has no name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "app-secret"},
            "spec": {
                "target": {},
            },
            "status": {},
        }

        result = manager.get_sync_status("app-secret")

        assert result["target_secret"] == "app-secret"

    def test_get_sync_status_api_error(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_sync_status should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_sync_status("missing-secret")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Operator Status
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOperatorStatus:
    """Tests for get_operator_status."""

    def test_get_operator_status_running_pods(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_operator_status should return running=True when all pods are Running."""
        mock_pod = MagicMock()
        mock_pod.metadata.name = "external-secrets-abc12"
        mock_pod.status.phase = "Running"
        mock_pod.spec.containers = [
            MagicMock(image="ghcr.io/external-secrets/external-secrets:v0.9.0")
        ]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = manager.get_operator_status()

        assert result["running"] is True
        assert len(result["pods"]) == 1
        assert result["pods"][0]["name"] == "external-secrets-abc12"
        assert result["pods"][0]["status"] == "Running"
        mock_k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(
            namespace=ESO_NAMESPACE,
            label_selector="app.kubernetes.io/name=external-secrets",
        )

    def test_get_operator_status_no_pods(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_operator_status should return running=False when no pods are found."""
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = []

        result = manager.get_operator_status()

        assert result["running"] is False
        assert result["pods"] == []

    def test_get_operator_status_pod_not_running(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_operator_status should return running=False when at least one pod is not Running."""
        mock_pod_running = MagicMock()
        mock_pod_running.metadata.name = "eso-pod-1"
        mock_pod_running.status.phase = "Running"
        mock_pod_running.spec.containers = [
            MagicMock(image="ghcr.io/external-secrets/external-secrets:v0.9.0")
        ]

        mock_pod_pending = MagicMock()
        mock_pod_pending.metadata.name = "eso-pod-2"
        mock_pod_pending.status.phase = "Pending"
        mock_pod_pending.spec.containers = [
            MagicMock(image="ghcr.io/external-secrets/external-secrets:v0.9.0")
        ]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [
            mock_pod_running,
            mock_pod_pending,
        ]

        result = manager.get_operator_status()

        assert result["running"] is False
        assert len(result["pods"]) == 2

    def test_get_operator_status_extracts_version_from_image_tag(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_operator_status should parse the version from the container image tag."""
        mock_pod = MagicMock()
        mock_pod.metadata.name = "eso-controller-xyz"
        mock_pod.status.phase = "Running"
        mock_pod.spec.containers = [
            MagicMock(image="ghcr.io/external-secrets/external-secrets:v0.9.11")
        ]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = manager.get_operator_status()

        assert result.get("version") == "v0.9.11"

    def test_get_operator_status_api_error_returns_error_dict(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_operator_status should return an error dict when the API call fails."""
        mock_k8s_client.core_v1.list_namespaced_pod.side_effect = Exception("unreachable")

        result = manager.get_operator_status()

        assert result["running"] is False
        assert result["pods"] == []
        assert "error" in result
        assert "external-secrets" in result["error"]


# =============================================================================
# Namespace Resolution
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespaceResolution:
    """Tests verifying namespace fall-through to client default."""

    def test_list_secret_stores_uses_explicit_namespace(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, it should be forwarded verbatim to the API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_secret_stores(namespace="kube-system")

        call_args = mock_k8s_client.custom_objects.list_namespaced_custom_object.call_args
        assert call_args[0][2] == "kube-system"

    def test_get_external_secret_uses_explicit_namespace(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given for get_external_secret, it should be forwarded."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(ExternalSecretSummary, "from_k8s_object"):
            manager.get_external_secret("my-secret", "production")

        call_args = mock_k8s_client.custom_objects.get_namespaced_custom_object.call_args
        assert call_args[0][2] == "production"

    def test_delete_external_secret_uses_explicit_namespace(
        self,
        manager: ExternalSecretsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given for delete_external_secret, it should be forwarded."""
        manager.delete_external_secret("my-secret", "staging")

        call_args = mock_k8s_client.custom_objects.delete_namespaced_custom_object.call_args
        assert call_args[0][2] == "staging"


# =============================================================================
# Constants
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConstants:
    """Tests verifying that module-level ESO constants are correct."""

    def test_eso_group_constant(self) -> None:
        """ESO_GROUP should be the external-secrets.io API group."""
        assert ESO_GROUP == "external-secrets.io"

    def test_eso_version_constant(self) -> None:
        """ESO_VERSION should be v1beta1."""
        assert ESO_VERSION == "v1beta1"

    def test_secret_store_plural_constant(self) -> None:
        """SECRET_STORE_PLURAL should be secretstores."""
        assert SECRET_STORE_PLURAL == "secretstores"

    def test_cluster_secret_store_plural_constant(self) -> None:
        """CLUSTER_SECRET_STORE_PLURAL should be clustersecretstores."""
        assert CLUSTER_SECRET_STORE_PLURAL == "clustersecretstores"

    def test_external_secret_plural_constant(self) -> None:
        """EXTERNAL_SECRET_PLURAL should be externalsecrets."""
        assert EXTERNAL_SECRET_PLURAL == "externalsecrets"

    def test_eso_namespace_constant(self) -> None:
        """ESO_NAMESPACE should be external-secrets."""
        assert ESO_NAMESPACE == "external-secrets"
