"""Shared fixtures for multicluster command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.multicluster import (
    ClusterDeployResult,
    ClusterStatus,
    ClusterSyncResult,
    MultiClusterDeployResult,
    MultiClusterStatusResult,
    MultiClusterSyncResult,
)


@pytest.fixture
def mock_multicluster_manager() -> MagicMock:
    """Create a mock MultiClusterManager."""
    return MagicMock()


@pytest.fixture
def get_multicluster_manager(
    mock_multicluster_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock MultiClusterManager."""
    return lambda: mock_multicluster_manager


@pytest.fixture
def sample_status_result() -> MultiClusterStatusResult:
    """Create a sample multi-cluster status result."""
    return MultiClusterStatusResult(
        clusters=[
            ClusterStatus(
                cluster="staging",
                context="staging-ctx",
                connected=True,
                version="v1.28",
                node_count=3,
                namespace="default",
            ),
            ClusterStatus(
                cluster="production",
                context="production-ctx",
                connected=True,
                version="v1.28",
                node_count=5,
                namespace="default",
            ),
        ],
        total=2,
        connected=2,
        disconnected=0,
    )


@pytest.fixture
def sample_status_partial_failure() -> MultiClusterStatusResult:
    """Create a status result with one disconnected cluster."""
    return MultiClusterStatusResult(
        clusters=[
            ClusterStatus(
                cluster="staging",
                context="staging-ctx",
                connected=True,
                version="v1.28",
                node_count=3,
                namespace="default",
            ),
            ClusterStatus(
                cluster="production",
                context="production-ctx",
                connected=False,
                namespace="default",
                error="Cluster unreachable",
            ),
        ],
        total=2,
        connected=1,
        disconnected=1,
    )


@pytest.fixture
def sample_deploy_result() -> MultiClusterDeployResult:
    """Create a sample deploy result."""
    return MultiClusterDeployResult(
        cluster_results=[
            ClusterDeployResult(
                cluster="staging",
                success=True,
                resources_applied=2,
                resources_failed=0,
            ),
            ClusterDeployResult(
                cluster="production",
                success=True,
                resources_applied=2,
                resources_failed=0,
            ),
        ],
        total_clusters=2,
        successful=2,
        failed=0,
    )


@pytest.fixture
def sample_deploy_partial_failure() -> MultiClusterDeployResult:
    """Create a deploy result with one cluster failing."""
    return MultiClusterDeployResult(
        cluster_results=[
            ClusterDeployResult(
                cluster="staging",
                success=True,
                resources_applied=2,
                resources_failed=0,
            ),
            ClusterDeployResult(
                cluster="production",
                success=False,
                resources_applied=1,
                resources_failed=1,
                error="Apply failed: permission denied",
            ),
        ],
        total_clusters=2,
        successful=1,
        failed=1,
    )


@pytest.fixture
def sample_sync_result() -> MultiClusterSyncResult:
    """Create a sample sync result."""
    return MultiClusterSyncResult(
        source_cluster="staging",
        resource_type="ConfigMap",
        resource_name="app-config",
        namespace="default",
        cluster_results=[
            ClusterSyncResult(
                cluster="production",
                success=True,
                action="configured",
            ),
        ],
        total_targets=1,
        successful=1,
        failed=0,
    )


@pytest.fixture
def sample_sync_failure() -> MultiClusterSyncResult:
    """Create a sync result with failure."""
    return MultiClusterSyncResult(
        source_cluster="staging",
        resource_type="ConfigMap",
        resource_name="app-config",
        namespace="default",
        cluster_results=[
            ClusterSyncResult(
                cluster="production",
                success=False,
                error="Failed to read ConfigMap/app-config from staging",
            ),
        ],
        total_targets=1,
        successful=0,
        failed=1,
    )
