"""Shared pytest fixtures for system_operations_manager tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.cli.main import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Generator[Path]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_file(temp_dir: Path) -> Path:
    """Create a temporary config file."""
    config_path = temp_dir / ".ops.yaml"
    config_path.write_text(
        """
version: "1.0"
environment: test
profiles:
  default:
    debug: true
"""
    )
    return config_path


@pytest.fixture
def mock_config() -> dict[str, object]:
    """Provide a mock configuration dictionary."""
    return {
        "version": "1.0",
        "environment": "test",
        "debug": True,
        "plugins": {
            "core": {"enabled": True},
        },
    }


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset environment variables for each test."""
    # Clear any OPS_ prefixed environment variables
    for key in list(os.environ.keys()):
        if key.startswith("OPS_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def capture_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Fixture to capture log output."""
    import logging

    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def cli_app() -> typer.Typer:
    """Return the CLI app for testing."""
    return app
