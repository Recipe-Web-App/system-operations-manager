"""Shared fixtures for streaming command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_streaming_manager() -> MagicMock:
    """Create a mock StreamingManager."""
    return MagicMock()


@pytest.fixture
def get_streaming_manager(mock_streaming_manager: MagicMock) -> Callable[[], MagicMock]:
    """Create a factory function that returns mock StreamingManager."""
    return lambda: mock_streaming_manager
