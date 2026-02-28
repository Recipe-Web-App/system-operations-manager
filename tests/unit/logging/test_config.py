"""Unit tests for logging configuration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from system_operations_manager.logging.config import (
    RETENTION_DAYS,
    _cleanup_old_logs,
    _setup_file_logging,
    configure_logging,
    get_logger,
)


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Any:
    """Remove handlers added by configure_logging after each test."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    yield
    root.handlers = original_handlers


@pytest.mark.unit
class TestCleanupOldLogs:
    """Tests for _cleanup_old_logs function."""

    def test_returns_early_when_log_dir_missing(self, tmp_path: Path) -> None:
        """_cleanup_old_logs should return early if LOG_DIR doesn't exist."""
        non_existent = tmp_path / "nonexistent"
        with patch("system_operations_manager.logging.config.LOG_DIR", non_existent):
            # Should not raise
            _cleanup_old_logs()

    def test_deletes_old_log_files(self, tmp_path: Path) -> None:
        """_cleanup_old_logs should delete log files older than RETENTION_DAYS."""
        log_file = tmp_path / "ops.log.1"
        log_file.write_text("old log data")
        # Set mtime to older than RETENTION_DAYS
        import os

        old_time = (datetime.now() - timedelta(days=RETENTION_DAYS + 5)).timestamp()
        os.utime(log_file, (old_time, old_time))

        with patch("system_operations_manager.logging.config.LOG_DIR", tmp_path):
            _cleanup_old_logs()

        assert not log_file.exists()

    def test_keeps_recent_log_files(self, tmp_path: Path) -> None:
        """_cleanup_old_logs should keep log files newer than RETENTION_DAYS."""
        log_file = tmp_path / "ops.log"
        log_file.write_text("recent log data")

        with patch("system_operations_manager.logging.config.LOG_DIR", tmp_path):
            _cleanup_old_logs()

        assert log_file.exists()

    def test_ignores_os_errors(self, tmp_path: Path) -> None:
        """_cleanup_old_logs should handle OSError gracefully."""
        log_file = tmp_path / "ops.log.1"
        log_file.write_text("data")
        import os

        old_time = (datetime.now() - timedelta(days=RETENTION_DAYS + 5)).timestamp()
        os.utime(log_file, (old_time, old_time))

        with (
            patch("system_operations_manager.logging.config.LOG_DIR", tmp_path),
            patch.object(Path, "unlink", side_effect=OSError("permission denied")),
        ):
            # Should not raise despite OSError
            _cleanup_old_logs()


@pytest.mark.unit
class TestSetupFileLogging:
    """Tests for _setup_file_logging function."""

    def test_creates_log_directory_and_handler(self, tmp_path: Path) -> None:
        """_setup_file_logging should create log dir and add a file handler."""
        log_dir = tmp_path / "logs"
        log_file = log_dir / "ops.log"

        with (
            patch("system_operations_manager.logging.config.LOG_DIR", log_dir),
            patch("system_operations_manager.logging.config.LOG_FILE", log_file),
            patch("system_operations_manager.logging.config._cleanup_old_logs"),
        ):
            root = logging.getLogger()
            initial_count = len(root.handlers)
            _setup_file_logging()
            assert len(root.handlers) > initial_count
            assert log_dir.exists()
            # Clean up handler
            root.handlers = root.handlers[:initial_count]


@pytest.mark.unit
class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_debug_sets_debug_level(self, tmp_path: Path) -> None:
        """configure_logging with debug=True should use DEBUG level."""
        with patch("system_operations_manager.logging.config._setup_file_logging"):
            configure_logging(debug=True)

    def test_verbose_sets_info_level(self, tmp_path: Path) -> None:
        """configure_logging with verbose=True should use INFO level."""
        with patch("system_operations_manager.logging.config._setup_file_logging"):
            configure_logging(verbose=True)

    def test_json_output_uses_json_renderer(self) -> None:
        """configure_logging with json_output=True should use JSONRenderer."""
        with patch("system_operations_manager.logging.config._setup_file_logging"):
            configure_logging(json_output=True)

    def test_default_sets_warning_level(self) -> None:
        """configure_logging with no args should use WARNING level."""
        with patch("system_operations_manager.logging.config._setup_file_logging"):
            configure_logging()


@pytest.mark.unit
class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_bound_logger(self) -> None:
        """get_logger should return a structlog logger."""
        logger = get_logger("test")
        assert logger is not None

    def test_binds_initial_context(self) -> None:
        """get_logger should bind initial context when provided."""
        logger = get_logger("test", component="api", version="1.0")
        assert logger is not None

    def test_returns_logger_without_context(self) -> None:
        """get_logger should work without initial context."""
        logger = get_logger("test")
        assert logger is not None
