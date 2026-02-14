"""Shared fixtures for Kubernetes command tests."""

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
def mock_workload_manager() -> MagicMock:
    """Create a mock WorkloadManager."""
    return MagicMock()


@pytest.fixture
def get_workload_manager(mock_workload_manager: MagicMock) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock WorkloadManager."""
    return lambda: mock_workload_manager


@pytest.fixture
def mock_namespace_cluster_manager() -> MagicMock:
    """Create a mock NamespaceClusterManager."""
    return MagicMock()


@pytest.fixture
def get_namespace_cluster_manager(
    mock_namespace_cluster_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock NamespaceClusterManager."""
    return lambda: mock_namespace_cluster_manager


@pytest.fixture
def mock_kustomize_manager() -> MagicMock:
    """Create a mock KustomizeManager."""
    return MagicMock()


@pytest.fixture
def get_kustomize_manager(mock_kustomize_manager: MagicMock) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock KustomizeManager."""
    return lambda: mock_kustomize_manager


@pytest.fixture
def mock_manifest_manager() -> MagicMock:
    """Create a mock ManifestManager."""
    return MagicMock()


@pytest.fixture
def get_manifest_manager(mock_manifest_manager: MagicMock) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock ManifestManager."""
    return lambda: mock_manifest_manager
