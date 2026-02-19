"""Shared fixtures for observability integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest


@pytest.fixture
def mock_httpx_client(mocker: Any) -> MagicMock:
    """Create a mock httpx client.

    Patches httpx.Client so that any observability client
    constructor will receive this mock.
    """
    mock_client = MagicMock(spec=httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client
