"""Shared fixtures for optimization command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.optimization import (
    OptimizationSummary,
    OrphanPod,
    ResourceMetrics,
    ResourceSpec,
    RightsizingRecommendation,
    StaleJob,
    WorkloadResourceAnalysis,
)


@pytest.fixture
def mock_optimization_manager() -> MagicMock:
    """Create a mock OptimizationManager."""
    return MagicMock()


@pytest.fixture
def get_optimization_manager(
    mock_optimization_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock OptimizationManager."""
    return lambda: mock_optimization_manager


@pytest.fixture
def sample_analysis() -> WorkloadResourceAnalysis:
    """Create a sample workload resource analysis."""
    return WorkloadResourceAnalysis(
        name="test-deployment",
        namespace="default",
        workload_type="Deployment",
        replicas=3,
        total_usage=ResourceMetrics(cpu_millicores=150, memory_bytes=256 * 1024 * 1024),
        total_spec=ResourceSpec(
            cpu_request_millicores=1000,
            cpu_limit_millicores=2000,
            memory_request_bytes=1024 * 1024 * 1024,
            memory_limit_bytes=2 * 1024 * 1024 * 1024,
        ),
        cpu_utilization_pct=15.0,
        memory_utilization_pct=25.0,
        status="overprovisioned",
    )


@pytest.fixture
def sample_recommendation() -> RightsizingRecommendation:
    """Create a sample right-sizing recommendation."""
    return RightsizingRecommendation(
        name="test-deployment",
        namespace="default",
        workload_type="Deployment",
        current_spec=ResourceSpec(
            cpu_request_millicores=1000,
            cpu_limit_millicores=2000,
            memory_request_bytes=1024 * 1024 * 1024,
            memory_limit_bytes=2 * 1024 * 1024 * 1024,
        ),
        current_usage=ResourceMetrics(cpu_millicores=150, memory_bytes=256 * 1024 * 1024),
        recommended_cpu_request_millicores=195,
        recommended_memory_request_bytes=348_127_232,
        recommended_cpu_limit_millicores=390,
        recommended_memory_limit_bytes=522_190_848,
        cpu_savings_millicores=805,
        memory_savings_bytes=727_711_744,
    )


@pytest.fixture
def sample_orphan_pod() -> OrphanPod:
    """Create a sample orphan pod."""
    return OrphanPod(
        name="stray-pod",
        namespace="default",
        phase="Running",
        node_name="worker-1",
        cpu_usage="5m",
        memory_usage="32Mi",
        creation_timestamp="2026-01-01T00:00:00+00:00",
    )


@pytest.fixture
def sample_stale_job() -> StaleJob:
    """Create a sample stale job."""
    return StaleJob(
        name="old-migration",
        namespace="default",
        status="Complete",
        completion_time="2026-01-01T00:00:00+00:00",
        age_hours=720.0,
        creation_timestamp="2025-12-31T00:00:00+00:00",
    )


@pytest.fixture
def sample_summary() -> OptimizationSummary:
    """Create a sample optimization summary."""
    return OptimizationSummary(
        total_workloads_analyzed=10,
        overprovisioned_count=3,
        underutilized_count=1,
        ok_count=6,
        orphan_pod_count=2,
        stale_job_count=4,
        total_cpu_waste_millicores=2500,
        total_memory_waste_bytes=4 * 1024 * 1024 * 1024,
    )
