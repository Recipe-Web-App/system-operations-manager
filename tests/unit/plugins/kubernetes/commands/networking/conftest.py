"""Shared fixtures for Kubernetes networking command tests."""

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
def mock_networking_manager() -> MagicMock:
    """Create a mock NetworkingManager."""
    manager = MagicMock()

    # Services
    manager.list_services.return_value = []
    manager.get_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-service",
            "namespace": "default",
            "type": "ClusterIP",
        }
    )
    manager.create_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-service", "namespace": "default"}
    )
    manager.update_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-service", "namespace": "default"}
    )
    manager.delete_service.return_value = None

    # Ingresses
    manager.list_ingresses.return_value = []
    manager.get_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-ingress",
            "namespace": "default",
            "class_name": "nginx",
        }
    )
    manager.create_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-ingress", "namespace": "default"}
    )
    manager.update_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-ingress", "namespace": "default"}
    )
    manager.delete_ingress.return_value = None

    # Network Policies
    manager.list_network_policies.return_value = []
    manager.get_network_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-netpol",
            "namespace": "default",
            "policy_types": ["Ingress"],
        }
    )
    manager.create_network_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-netpol", "namespace": "default"}
    )
    manager.delete_network_policy.return_value = None

    return manager


@pytest.fixture
def get_networking_manager(
    mock_networking_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock networking manager."""
    return lambda: mock_networking_manager
