"""Unit tests for Kubernetes job resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.jobs import (
    CronJobSummary,
    JobSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestJobSummary:
    """Test JobSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Job."""
        obj = MagicMock()
        obj.metadata.name = "batch-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-job-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "batch"}
        obj.metadata.annotations = {"description": "Data processing job"}

        obj.spec.completions = 10
        obj.status.succeeded = 8
        obj.status.failed = 1
        obj.status.active = 1
        obj.status.start_time = "2024-01-01T00:05:00Z"
        obj.status.completion_time = None

        job = JobSummary.from_k8s_object(obj)

        assert job.name == "batch-job"
        assert job.namespace == "default"
        assert job.completions == 10
        assert job.succeeded == 8
        assert job.failed == 1
        assert job.active == 1
        assert job.start_time == "2024-01-01T00:05:00Z"
        assert job.completion_time is None

    def test_from_k8s_object_completed(self) -> None:
        """Test from_k8s_object with completed Job."""
        obj = MagicMock()
        obj.metadata.name = "completed-job"
        obj.metadata.namespace = "production"

        obj.spec.completions = 5
        obj.status.succeeded = 5
        obj.status.failed = 0
        obj.status.active = 0
        obj.status.start_time = "2024-01-01T10:00:00Z"
        obj.status.completion_time = "2024-01-01T10:15:00Z"

        job = JobSummary.from_k8s_object(obj)

        assert job.succeeded == 5
        assert job.failed == 0
        assert job.active == 0
        assert job.completion_time == "2024-01-01T10:15:00Z"

    def test_from_k8s_object_failed(self) -> None:
        """Test from_k8s_object with failed Job."""
        obj = MagicMock()
        obj.metadata.name = "failed-job"
        obj.metadata.namespace = "default"

        obj.spec.completions = 1
        obj.status.succeeded = 0
        obj.status.failed = 3
        obj.status.active = 0
        obj.status.start_time = "2024-01-01T12:00:00Z"
        obj.status.completion_time = "2024-01-01T12:10:00Z"

        job = JobSummary.from_k8s_object(obj)

        assert job.succeeded == 0
        assert job.failed == 3

    def test_from_k8s_object_no_completions(self) -> None:
        """Test from_k8s_object with Job without completions spec."""
        obj = MagicMock()
        obj.metadata.name = "unlimited-job"
        obj.metadata.namespace = "default"

        obj.spec.completions = None
        obj.status.succeeded = 100
        obj.status.failed = 0
        obj.status.active = 0
        obj.status.start_time = None
        obj.status.completion_time = None

        job = JobSummary.from_k8s_object(obj)

        assert job.completions is None
        assert job.succeeded == 100

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal Job."""
        obj = MagicMock()
        obj.metadata.name = "minimal-job"

        obj.spec.completions = None
        obj.status.succeeded = None
        obj.status.failed = None
        obj.status.active = None
        obj.status.start_time = None
        obj.status.completion_time = None

        job = JobSummary.from_k8s_object(obj)

        assert job.name == "minimal-job"
        assert job.completions is None
        assert job.succeeded == 0
        assert job.failed == 0
        assert job.active == 0

    def test_from_k8s_object_zero_values(self) -> None:
        """Test from_k8s_object handles zero values correctly."""
        obj = MagicMock()
        obj.metadata.name = "zero-job"

        obj.spec.completions = 0
        obj.status.succeeded = 0
        obj.status.failed = 0
        obj.status.active = 0

        job = JobSummary.from_k8s_object(obj)

        assert job.completions == 0
        assert job.succeeded == 0
        assert job.failed == 0
        assert job.active == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert JobSummary._entity_name == "job"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronJobSummary:
    """Test CronJobSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete CronJob."""
        obj = MagicMock()
        obj.metadata.name = "nightly-backup"
        obj.metadata.namespace = "production"
        obj.metadata.uid = "uid-cron-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "backup"}
        obj.metadata.annotations = {"schedule": "nightly"}

        obj.spec.schedule = "0 2 * * *"
        obj.spec.suspend = False

        # Active jobs
        active_job1 = MagicMock()
        active_job2 = MagicMock()
        obj.status.active = [active_job1, active_job2]

        obj.status.last_schedule_time = "2024-01-02T02:00:00Z"
        obj.status.last_successful_time = "2024-01-02T02:15:00Z"

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.name == "nightly-backup"
        assert cronjob.namespace == "production"
        assert cronjob.schedule == "0 2 * * *"
        assert cronjob.suspend is False
        assert cronjob.active_count == 2
        assert cronjob.last_schedule_time == "2024-01-02T02:00:00Z"
        assert cronjob.last_successful_time == "2024-01-02T02:15:00Z"

    def test_from_k8s_object_suspended(self) -> None:
        """Test from_k8s_object with suspended CronJob."""
        obj = MagicMock()
        obj.metadata.name = "suspended-job"
        obj.metadata.namespace = "default"

        obj.spec.schedule = "*/5 * * * *"
        obj.spec.suspend = True
        obj.status.active = []
        obj.status.last_schedule_time = None
        obj.status.last_successful_time = None

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.suspend is True
        assert cronjob.active_count == 0

    def test_from_k8s_object_never_run(self) -> None:
        """Test from_k8s_object with CronJob that never ran."""
        obj = MagicMock()
        obj.metadata.name = "new-cronjob"
        obj.metadata.namespace = "default"

        obj.spec.schedule = "0 0 * * 0"
        obj.spec.suspend = False
        obj.status.active = None
        obj.status.last_schedule_time = None
        obj.status.last_successful_time = None

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.active_count == 0
        assert cronjob.last_schedule_time is None
        assert cronjob.last_successful_time is None

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal CronJob."""
        obj = MagicMock()
        obj.metadata.name = "minimal-cron"

        obj.spec.schedule = None
        obj.spec.suspend = None
        obj.status.active = None
        obj.status.last_schedule_time = None
        obj.status.last_successful_time = None

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.name == "minimal-cron"
        assert cronjob.schedule == ""
        assert cronjob.suspend is False
        assert cronjob.active_count == 0

    def test_from_k8s_object_various_schedules(self) -> None:
        """Test from_k8s_object with different schedule formats."""
        test_cases = [
            "*/10 * * * *",  # Every 10 minutes
            "0 */2 * * *",  # Every 2 hours
            "0 0 * * 1-5",  # Weekdays at midnight
            "@hourly",  # Every hour
            "@daily",  # Every day
        ]

        for schedule in test_cases:
            obj = MagicMock()
            obj.metadata.name = "test-cron"
            obj.spec.schedule = schedule
            obj.spec.suspend = False
            obj.status.active = []

            cronjob = CronJobSummary.from_k8s_object(obj)
            assert cronjob.schedule == schedule

    def test_from_k8s_object_multiple_active_jobs(self) -> None:
        """Test from_k8s_object with multiple active jobs."""
        obj = MagicMock()
        obj.metadata.name = "busy-cron"
        obj.spec.schedule = "* * * * *"
        obj.spec.suspend = False

        # Create 5 active jobs
        obj.status.active = [MagicMock() for _ in range(5)]

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.active_count == 5

    def test_from_k8s_object_suspend_false_explicit(self) -> None:
        """Test from_k8s_object with explicitly False suspend."""
        obj = MagicMock()
        obj.metadata.name = "active-cron"
        obj.spec.schedule = "0 0 * * *"
        obj.spec.suspend = False
        obj.status.active = []

        cronjob = CronJobSummary.from_k8s_object(obj)

        assert cronjob.suspend is False

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert CronJobSummary._entity_name == "cronjob"
