"""Shared fixtures for Kong traffic control command tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity


def _create_mock_entity(data: dict[str, Any]) -> MagicMock:
    """Create a mock entity that behaves like a Pydantic model.

    The formatter calls model_dump() on entities, so we need mocks
    that support this interface.
    """
    mock = MagicMock()
    mock.model_dump.return_value = data
    # Also set attributes for direct access
    for key, value in data.items():
        setattr(mock, key, value)
    return mock


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_plugin_manager() -> MagicMock:
    """Create a mock KongPluginManager for traffic commands."""
    manager = MagicMock()
    # Default enable return value
    manager.enable.return_value = KongPluginEntity(
        id="plugin-123",
        name="rate-limiting",
        enabled=True,
        config={},
    )
    # Default list return value (empty)
    manager.list.return_value = []
    # Default disable return value
    manager.disable.return_value = None
    return manager


@pytest.fixture
def get_plugin_manager(mock_plugin_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock plugin manager."""
    return lambda: mock_plugin_manager


def create_traffic_app(
    register_func: Callable[..., None],
    get_plugin_manager: Callable[[], Any],
) -> typer.Typer:
    """Helper to create a Typer app with registered traffic commands.

    Args:
        register_func: The command registration function.
        get_plugin_manager: Factory for plugin manager.

    Returns:
        Configured Typer app for testing.
    """
    app = typer.Typer()
    register_func(app, get_plugin_manager)
    return app
