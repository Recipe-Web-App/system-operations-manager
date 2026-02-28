"""Integration tests for Kubernetes JobManager against real K3S cluster."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.services.kubernetes import JobManager

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.integration
@pytest.mark.kubernetes
class TestJobCRUD:
    """Test CRUD operations for Kubernetes jobs."""

    def test_create_job(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """Test creating a simple job."""
        job_name = f"job-{unique_name}"

        job = job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
            labels={"test": "integration"},
        )

        assert job.name == job_name
        assert job.namespace == test_namespace

    def test_list_jobs(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """Test listing jobs in a namespace."""
        job_name = f"job-{unique_name}"

        # Create a job first
        job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
            labels={"test": "list-test"},
        )

        # List jobs
        jobs = job_manager.list_jobs(namespace=test_namespace)

        assert len(jobs) > 0
        job_names = [j.name for j in jobs]
        assert job_name in job_names

    def test_get_job(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """Test getting a specific job."""
        job_name = f"job-{unique_name}"

        # Create a job
        created_job = job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
        )

        # Get the job
        job = job_manager.get_job(name=job_name, namespace=test_namespace)

        assert job.name == created_job.name
        assert job.namespace == created_job.namespace

    def test_delete_job(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """Test deleting a job."""
        job_name = f"job-{unique_name}"

        # Create a job
        job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
        )

        # Delete the job
        job_manager.delete_job(name=job_name, namespace=test_namespace)

        # Verify it's deleted
        with pytest.raises(KubernetesNotFoundError):
            job_manager.get_job(name=job_name, namespace=test_namespace)

    def test_get_nonexistent_raises(
        self,
        job_manager: JobManager,
        test_namespace: str,
    ) -> None:
        """Test getting a non-existent job raises KubernetesNotFoundError."""
        with pytest.raises(KubernetesNotFoundError):
            job_manager.get_job(name="nonexistent-job", namespace=test_namespace)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestJobExecution:
    """Test job execution and completion."""

    def test_job_completes_successfully(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
        wait_for_job_complete: Callable[..., Any],
    ) -> None:
        """Test that a job runs and completes successfully."""
        job_name = f"job-{unique_name}"

        # Create a job
        job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
        )

        # Wait for completion
        completed_job = wait_for_job_complete(job_name, test_namespace)

        assert completed_job.status.succeeded >= 1
        assert completed_job.metadata.name == job_name

    def test_create_job_with_completions(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
        wait_for_job_complete: Callable[..., Any],
    ) -> None:
        """Test creating a job with multiple completions."""
        job_name = f"job-{unique_name}"

        # Create a job with 3 completions
        job = job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
            completions=3,
            parallelism=2,
        )

        assert job.name == job_name

        # Wait for completion
        completed_job = wait_for_job_complete(job_name, test_namespace, timeout=120)

        assert completed_job.status.succeeded >= 1

    def test_create_job_with_labels(
        self,
        job_manager: JobManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """Test creating a job with custom labels."""
        job_name = f"job-{unique_name}"

        job_manager.create_job(
            name=job_name,
            namespace=test_namespace,
            image="busybox:latest",
            command=["echo", "hello"],
            labels={"app": "test", "env": "integration"},
        )

        # Retrieve and verify labels are set
        retrieved_job = job_manager.get_job(name=job_name, namespace=test_namespace)
        assert retrieved_job.name == job_name
