"""Shared fixtures for cluster command tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_node() -> MagicMock:
    """Create a sample node object with model_dump."""
    node = MagicMock()
    node.model_dump.return_value = {
        "name": "worker-1",
        "status": "Ready",
        "roles": "worker",
        "version": "v1.28.0",
        "internal_ip": "192.168.1.10",
        "os_image": "Ubuntu 22.04.3 LTS",
        "age": "30d",
    }
    return node


@pytest.fixture
def sample_event() -> MagicMock:
    """Create a sample event object with model_dump."""
    event = MagicMock()
    event.model_dump.return_value = {
        "last_timestamp": "2024-01-15T10:30:00Z",
        "type": "Warning",
        "reason": "BackOff",
        "source_component": "kubelet",
        "message": "Back-off restarting failed container",
        "count": 5,
    }
    return event
