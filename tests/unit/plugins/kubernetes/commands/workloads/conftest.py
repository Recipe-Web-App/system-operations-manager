"""Shared fixtures for workload command tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_pod() -> MagicMock:
    """Create a sample pod object with model_dump."""
    pod = MagicMock()
    pod.model_dump.return_value = {
        "name": "test-pod",
        "namespace": "default",
        "phase": "Running",
        "ready_count": "1/1",
        "restarts": 0,
        "node_name": "worker-1",
        "pod_ip": "10.0.1.5",
        "age": "2d",
    }
    return pod


@pytest.fixture
def sample_deployment() -> MagicMock:
    """Create a sample deployment object with model_dump."""
    deployment = MagicMock()
    deployment.model_dump.return_value = {
        "name": "test-deployment",
        "namespace": "default",
        "ready_replicas": 3,
        "replicas": 3,
        "updated_replicas": 3,
        "available_replicas": 3,
        "age": "5d",
    }
    return deployment


@pytest.fixture
def sample_statefulset() -> MagicMock:
    """Create a sample statefulset object with model_dump."""
    sts = MagicMock()
    sts.model_dump.return_value = {
        "name": "test-sts",
        "namespace": "default",
        "ready_replicas": 2,
        "replicas": 2,
        "service_name": "test-svc",
        "age": "3d",
    }
    return sts


@pytest.fixture
def sample_daemonset() -> MagicMock:
    """Create a sample daemonset object with model_dump."""
    ds = MagicMock()
    ds.model_dump.return_value = {
        "name": "test-ds",
        "namespace": "default",
        "desired_number_scheduled": 3,
        "current_number_scheduled": 3,
        "number_ready": 3,
        "age": "10d",
    }
    return ds


@pytest.fixture
def sample_replicaset() -> MagicMock:
    """Create a sample replicaset object with model_dump."""
    rs = MagicMock()
    rs.model_dump.return_value = {
        "name": "test-rs",
        "namespace": "default",
        "ready_replicas": 2,
        "replicas": 2,
        "age": "1d",
    }
    return rs
