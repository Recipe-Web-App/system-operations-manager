"""Shared fixtures for External Secrets command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_external_secrets_manager() -> MagicMock:
    """Create a mock ExternalSecretsManager."""
    manager = MagicMock()

    # SecretStores
    manager.list_secret_stores.return_value = []
    manager.get_secret_store.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "vault-store",
            "namespace": "default",
            "provider_type": "vault",
            "ready": True,
            "message": None,
        }
    )
    manager.create_secret_store.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "vault-store",
            "namespace": "default",
            "provider_type": "vault",
        }
    )
    manager.delete_secret_store.return_value = None

    # ClusterSecretStores
    manager.list_cluster_secret_stores.return_value = []
    manager.get_cluster_secret_store.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "aws-store",
            "provider_type": "aws",
            "ready": True,
            "message": None,
        }
    )
    manager.create_cluster_secret_store.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "aws-store",
            "provider_type": "aws",
        }
    )
    manager.delete_cluster_secret_store.return_value = None

    # ExternalSecrets
    manager.list_external_secrets.return_value = []
    manager.get_external_secret.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-secret",
            "namespace": "default",
            "store_name": "vault-store",
            "store_kind": "SecretStore",
            "refresh_interval": "1h",
            "data_count": 2,
            "ready": True,
        }
    )
    manager.create_external_secret.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-secret",
            "namespace": "default",
            "store_name": "vault-store",
        }
    )
    manager.delete_external_secret.return_value = None

    # Sync status
    manager.get_sync_status.return_value = {
        "name": "my-secret",
        "namespace": "default",
        "ready": True,
        "message": None,
        "synced_resource_version": "12345",
        "refresh_time": "2025-01-01T00:00:00Z",
        "target_secret": "my-secret",
        "conditions": [],
    }

    # Operator status
    manager.get_operator_status.return_value = {
        "running": True,
        "pods": [{"name": "external-secrets-xyz", "status": "Running"}],
    }

    return manager


@pytest.fixture
def get_external_secrets_manager(
    mock_external_secrets_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock ExternalSecrets manager."""
    return lambda: mock_external_secrets_manager
