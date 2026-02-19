"""Shared fixtures for Kubernetes service tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client with API sub-mocks.

    Provides pre-configured sub-mocks for common K8s API groups:
    core_v1, apps_v1, batch_v1, custom_objects, networking_v1, rbac_v1, storage_v1.
    """
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client
