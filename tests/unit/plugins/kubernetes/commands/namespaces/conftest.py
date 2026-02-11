"""Shared fixtures for namespace command tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_namespace() -> MagicMock:
    """Create a sample namespace object with model_dump."""
    namespace = MagicMock()
    namespace.model_dump.return_value = {
        "name": "test-namespace",
        "status": "Active",
        "age": "10d",
    }
    return namespace
