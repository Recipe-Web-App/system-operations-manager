"""Shared fixtures for Kubernetes jobs command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_job_manager() -> MagicMock:
    """Create a mock JobManager."""
    manager = MagicMock()

    # Jobs
    manager.list_jobs.return_value = []
    manager.get_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-job",
            "namespace": "default",
            "completions": 1,
            "succeeded": 1,
        }
    )
    manager.create_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-job", "namespace": "default"}
    )
    manager.delete_job.return_value = None

    # CronJobs
    manager.list_cron_jobs.return_value = []
    manager.get_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-cronjob",
            "namespace": "default",
            "schedule": "*/5 * * * *",
        }
    )
    manager.create_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cronjob", "namespace": "default"}
    )
    manager.update_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cronjob", "namespace": "default"}
    )
    manager.delete_cron_job.return_value = None
    manager.suspend_cron_job.return_value = None
    manager.resume_cron_job.return_value = None

    return manager


@pytest.fixture
def get_job_manager(mock_job_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock job manager."""
    return lambda: mock_job_manager
