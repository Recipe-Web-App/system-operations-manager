"""Shared fixtures for Kubernetes storage command tests."""

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
def mock_storage_manager() -> MagicMock:
    """Create a mock StorageManager."""
    manager = MagicMock()

    # Persistent Volumes
    manager.list_persistent_volumes.return_value = []
    manager.get_persistent_volume.return_value = MagicMock(
        model_dump=lambda: {
            "name": "test-pv",
            "capacity": "10Gi",
            "status": "Available",
        }
    )
    manager.delete_persistent_volume.return_value = None

    # Persistent Volume Claims
    manager.list_persistent_volume_claims.return_value = []
    manager.get_persistent_volume_claim.return_value = MagicMock(
        model_dump=lambda: {
            "name": "test-pvc",
            "namespace": "default",
            "status": "Bound",
        }
    )
    manager.create_persistent_volume_claim.return_value = MagicMock(
        model_dump=lambda: {"name": "test-pvc", "namespace": "default"}
    )
    manager.delete_persistent_volume_claim.return_value = None

    # Storage Classes
    manager.list_storage_classes.return_value = []
    manager.get_storage_class.return_value = MagicMock(
        model_dump=lambda: {
            "name": "standard",
            "provisioner": "kubernetes.io/gce-pd",
        }
    )

    return manager


@pytest.fixture
def get_storage_manager(mock_storage_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock storage manager."""
    return lambda: mock_storage_manager
