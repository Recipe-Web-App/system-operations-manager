"""Shared fixtures for Kong security command tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
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
    """Create a mock KongPluginManager for security commands."""
    manager = MagicMock()
    # Default enable return value
    manager.enable.return_value = KongPluginEntity(
        id="plugin-123",
        name="key-auth",
        enabled=True,
        config={},
    )
    return manager


@pytest.fixture
def mock_consumer_manager() -> MagicMock:
    """Create a mock ConsumerManager for credential operations."""
    manager = MagicMock()

    # Default return values for credential operations - use mock entities
    manager.add_credential.return_value = _create_mock_entity(
        {
            "id": "cred-123",
            "key": "test-credential-key",
            "created_at": 1234567890,
        }
    )
    manager.list_credentials.return_value = [
        _create_mock_entity({"id": "cred-1", "key": "test-key-1", "created_at": 1234567890}),
        _create_mock_entity({"id": "cred-2", "key": "test-key-2", "created_at": 1234567891}),
    ]
    manager.delete_credential.return_value = None

    # ACL-specific methods
    manager.add_to_acl_group.return_value = _create_mock_entity(
        {
            "id": "acl-123",
            "group": "admin-group",
            "created_at": 1234567890,
        }
    )
    manager.list_acl_groups.return_value = [
        _create_mock_entity({"id": "acl-1", "group": "admin", "created_at": 1234567890}),
        _create_mock_entity({"id": "acl-2", "group": "users", "created_at": 1234567891}),
    ]
    manager.remove_from_acl_group.return_value = None

    return manager


@pytest.fixture
def get_plugin_manager(mock_plugin_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock plugin manager."""
    return lambda: mock_plugin_manager


@pytest.fixture
def get_consumer_manager(mock_consumer_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock consumer manager."""
    return lambda: mock_consumer_manager


@pytest.fixture
def temp_cert_file(tmp_path: Path) -> Path:
    """Create a temporary certificate file for testing file reading."""
    cert_file = tmp_path / "test-cert.pem"
    cert_file.write_text("-----BEGIN CERTIFICATE-----\nTEST_CERT_DATA\n-----END CERTIFICATE-----\n")
    return cert_file


@pytest.fixture
def temp_key_file(tmp_path: Path) -> Path:
    """Create a temporary key file for testing file reading."""
    key_file = tmp_path / "test-key.pem"
    key_file.write_text(
        "-----BEGIN RSA PUBLIC KEY-----\nTEST_KEY_DATA\n-----END RSA PUBLIC KEY-----\n"
    )
    return key_file


def create_security_app(
    register_func: Callable[..., None],
    get_plugin_manager: Callable[[], Any],
    get_consumer_manager: Callable[[], Any] | None = None,
) -> typer.Typer:
    """Helper to create a Typer app with registered security commands.

    Args:
        register_func: The command registration function.
        get_plugin_manager: Factory for plugin manager.
        get_consumer_manager: Factory for consumer manager (optional).

    Returns:
        Configured Typer app for testing.
    """
    app = typer.Typer()
    if get_consumer_manager is not None:
        register_func(app, get_plugin_manager, get_consumer_manager)
    else:
        register_func(app, get_plugin_manager)
    return app
