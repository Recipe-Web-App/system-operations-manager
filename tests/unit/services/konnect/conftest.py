"""Shared fixtures for Konnect service tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock KonnectClient."""
    return MagicMock()
