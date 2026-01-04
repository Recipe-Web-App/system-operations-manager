"""Shared fixtures for Kong config command tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.config import (
    ApplyOperation,
    ConfigDiff,
    ConfigDiffSummary,
    ConfigValidationError,
    ConfigValidationResult,
    DeclarativeConfig,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """Create a mock ConfigManager."""
    manager = MagicMock()

    # Default export state
    manager.export_state.return_value = DeclarativeConfig(
        services=[
            {"name": "api-1", "host": "localhost", "port": 8001},
            {"name": "api-2", "host": "localhost", "port": 8002},
        ],
        routes=[
            {"name": "route-1", "paths": ["/api/v1"], "service": {"name": "api-1"}},
        ],
        upstreams=[],
        consumers=[
            {"username": "user1"},
        ],
        plugins=[
            {"name": "rate-limiting", "config": {"minute": 100}},
        ],
    )

    # Default validation result (valid)
    manager.validate_config.return_value = ConfigValidationResult(
        valid=True,
        errors=[],
        warnings=[],
    )

    # Default diff result (no changes)
    manager.diff_config.return_value = ConfigDiffSummary(
        total_changes=0,
        creates={},
        updates={},
        deletes={},
        diffs=[],
    )

    # Default apply result
    manager.apply_config.return_value = [
        ApplyOperation(
            operation="create",
            entity_type="services",
            id_or_name="api-1",
            result="success",
        ),
    ]

    return manager


@pytest.fixture
def get_config_manager(mock_config_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock config manager."""
    return lambda: mock_config_manager


@pytest.fixture
def sample_valid_config() -> dict[str, Any]:
    """Sample valid Kong configuration."""
    return {
        "_format_version": "3.0",
        "services": [
            {
                "name": "test-service",
                "host": "httpbin.org",
                "port": 80,
                "protocol": "http",
            }
        ],
        "routes": [
            {
                "name": "test-route",
                "paths": ["/test"],
                "service": {"name": "test-service"},
            }
        ],
    }


@pytest.fixture
def sample_invalid_config() -> dict[str, Any]:
    """Sample invalid Kong configuration (route references unknown service)."""
    return {
        "_format_version": "3.0",
        "services": [],
        "routes": [
            {
                "name": "test-route",
                "paths": ["/test"],
                "service": {"name": "nonexistent-service"},
            }
        ],
    }


@pytest.fixture
def sample_diff_with_changes() -> ConfigDiffSummary:
    """Sample diff with changes."""
    return ConfigDiffSummary(
        total_changes=3,
        creates={"services": 1},
        updates={"routes": 1},
        deletes={"plugins": 1},
        diffs=[
            ConfigDiff(
                entity_type="services",
                operation="create",
                id_or_name="new-service",
                desired={"name": "new-service", "host": "localhost"},
            ),
            ConfigDiff(
                entity_type="routes",
                operation="update",
                id_or_name="existing-route",
                current={"name": "existing-route", "paths": ["/old"]},
                desired={"name": "existing-route", "paths": ["/new"]},
                changes={"paths": (["/old"], ["/new"])},
            ),
            ConfigDiff(
                entity_type="plugins",
                operation="delete",
                id_or_name="old-plugin",
                current={"name": "rate-limiting", "id": "old-plugin"},
            ),
        ],
    )


@pytest.fixture
def sample_validation_errors() -> ConfigValidationResult:
    """Sample validation result with errors."""
    return ConfigValidationResult(
        valid=False,
        errors=[
            ConfigValidationError(
                path="routes[0].service",
                message="Route references unknown service: bad-service",
                entity_type="route",
                entity_name="test-route",
            ),
        ],
        warnings=[
            ConfigValidationError(
                path="plugins[0]",
                message="Plugin has no scope - will be global",
                entity_type="plugin",
                entity_name="rate-limiting",
            ),
        ],
    )
