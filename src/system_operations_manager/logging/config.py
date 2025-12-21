"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

# Log file configuration
LOG_DIR = Path.home() / ".local" / "state" / "ops"
LOG_FILE = LOG_DIR / "ops.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Keep 5 rotated files
RETENTION_DAYS = 30  # Delete logs older than 30 days


def _cleanup_old_logs() -> None:
    """Delete log files older than RETENTION_DAYS."""
    if not LOG_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for log_file in LOG_DIR.glob("ops.log*"):
        try:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                log_file.unlink()
        except OSError:
            pass  # Ignore errors during cleanup


def _setup_file_logging() -> None:
    """Set up rotating file handler for persistent logging."""
    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up old logs
    _cleanup_old_logs()

    # Create rotating file handler with JSON format
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
    )
    file_handler.setLevel(logging.DEBUG)  # Capture everything to file

    # Use structlog's ProcessorFormatter for consistent JSON output
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.UnicodeDecoder(),
            ],
        )
    )

    logging.getLogger().addHandler(file_handler)


def configure_logging(
    verbose: bool = False,
    debug: bool = False,
    json_output: bool = False,
) -> None:
    """Configure structured logging for the application.

    Logs are written to both console and file. File logs are stored at
    ~/.local/state/ops/ops.log with automatic rotation (10MB max, 5 backups)
    and retention cleanup (30 days).

    Args:
        verbose: Enable verbose (INFO level) output.
        debug: Enable debug mode (DEBUG level).
        json_output: Output logs in JSON format (useful for production).
    """
    # Determine log level
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    # Shared processors for all outputs
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog to use stdlib logging (enables file handler)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure console handler with human-readable output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    if json_output:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=debug,
                ),
            ),
            foreign_pre_chain=shared_processors,
        )
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Let handlers filter
    root_logger.addHandler(console_handler)

    # Set up rotating file logging
    _setup_file_logging()


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.BoundLogger:
    """Get a configured logger with optional initial context.

    Args:
        name: Logger name. If None, uses the calling module's name.
        **initial_context: Initial context variables to bind to the logger.

    Returns:
        A bound structlog logger.
    """
    logger: structlog.BoundLogger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger
