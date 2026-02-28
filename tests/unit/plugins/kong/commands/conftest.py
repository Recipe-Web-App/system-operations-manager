"""Shared fixtures for Kong command tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock ServiceManager."""
    return MagicMock()


@pytest.fixture
def mock_route_manager() -> MagicMock:
    """Create a mock RouteManager."""
    return MagicMock()


@pytest.fixture
def mock_consumer_manager() -> MagicMock:
    """Create a mock ConsumerManager."""
    return MagicMock()


@pytest.fixture
def mock_plugin_manager() -> MagicMock:
    """Create a mock KongPluginManager."""
    return MagicMock()


@pytest.fixture
def mock_upstream_manager() -> MagicMock:
    """Create a mock UpstreamManager."""
    return MagicMock()


@pytest.fixture
def mock_registry_manager() -> MagicMock:
    """Create a mock RegistryManager."""
    return MagicMock()


@pytest.fixture
def mock_openapi_sync_manager() -> MagicMock:
    """Create a mock OpenAPISyncManager."""
    return MagicMock()


@pytest.fixture
def mock_deployment_manager() -> MagicMock:
    """Create a mock KongDeploymentManager."""
    return MagicMock()


@pytest.fixture
def mock_unified_query_service() -> MagicMock:
    """Create a mock UnifiedQueryService."""
    return MagicMock()


@pytest.fixture
def mock_dual_write_service() -> MagicMock:
    """Create a mock DualWriteService."""
    return MagicMock()


@pytest.fixture
def mock_metrics_manager() -> MagicMock:
    """Create a mock MetricsManager."""
    return MagicMock()


@pytest.fixture
def mock_logs_manager() -> MagicMock:
    """Create a mock LogsManager."""
    return MagicMock()


@pytest.fixture
def mock_tracing_manager() -> MagicMock:
    """Create a mock TracingManager."""
    return MagicMock()
