"""Shared fixtures for Kubernetes config resources command tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """Create a mock ConfigurationManager."""
    manager = MagicMock()

    # Default return values
    manager.list_config_maps.return_value = []
    manager.get_config_map.return_value = MagicMock(
        model_dump=lambda: {
            "name": "test-config",
            "namespace": "default",
            "data": {"key1": "value1"},
        }
    )
    manager.get_config_map_data.return_value = {"key1": "value1"}
    manager.create_config_map.return_value = MagicMock(
        model_dump=lambda: {"name": "test-config", "namespace": "default"}
    )
    manager.update_config_map.return_value = MagicMock(
        model_dump=lambda: {"name": "test-config", "namespace": "default"}
    )
    manager.delete_config_map.return_value = None

    # Secrets
    manager.list_secrets.return_value = []
    manager.get_secret.return_value = MagicMock(
        model_dump=lambda: {
            "name": "test-secret",
            "namespace": "default",
            "type": "Opaque",
        }
    )
    manager.create_secret.return_value = MagicMock(
        model_dump=lambda: {"name": "test-secret", "namespace": "default"}
    )
    manager.create_tls_secret.return_value = MagicMock(
        model_dump=lambda: {"name": "test-tls", "namespace": "default"}
    )
    manager.create_docker_registry_secret.return_value = MagicMock(
        model_dump=lambda: {"name": "test-registry", "namespace": "default"}
    )
    manager.delete_secret.return_value = None

    return manager


@pytest.fixture
def get_config_manager(mock_config_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock config manager."""
    return lambda: mock_config_manager


@pytest.fixture
def sample_configmap_data() -> dict[str, Any]:
    """Sample configmap data."""
    return {
        "name": "my-config",
        "namespace": "default",
        "data": {"app.conf": "server=localhost", "db.conf": "host=db"},
        "data_keys": "app.conf,db.conf",
        "age": "5d",
    }


@pytest.fixture
def sample_secret_data() -> dict[str, Any]:
    """Sample secret data."""
    return {
        "name": "my-secret",
        "namespace": "default",
        "type": "Opaque",
        "data_keys": "username,password",
        "age": "10d",
    }
