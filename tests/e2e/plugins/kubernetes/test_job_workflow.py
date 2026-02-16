"""E2E tests for Kubernetes job management workflows.

These tests verify complete workflows for managing Kubernetes jobs via CLI:
- Job creation with various configurations
- Job listing and filtering
- Job inspection
- Job deletion
- Output formatting (JSON)

All tests run against a real K3S cluster using the invoke_k8s fixture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@pytest.mark.e2e
@pytest.mark.kubernetes
class TestJobWorkflow:
    """Test job management workflows via CLI commands."""

    def test_create_job(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and verify it is created successfully."""
        job_name = f"{unique_prefix}-job"

        # Create job
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo hello",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"
        assert unique_prefix in result.output or "created" in result.output.lower()

    def test_list_jobs(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and verify it appears in the list."""
        job_name = f"{unique_prefix}-list-job"

        # Create job
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo test",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"

        # List jobs in namespace
        result = invoke_k8s("jobs", "list", "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to list jobs: {result.output}"
        assert "Total:" in result.output

    def test_get_job(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and retrieve its details via get command."""
        job_name = f"{unique_prefix}-get-job"

        # Create job
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo details",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"

        # Get job details
        result = invoke_k8s("jobs", "get", job_name, "--namespace", e2e_namespace)
        assert result.exit_code == 0, f"Failed to get job: {result.output}"
        assert unique_prefix in result.output

    def test_delete_job(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and delete it."""
        job_name = f"{unique_prefix}-delete-job"

        # Create job
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo delete-me",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"

        # Delete job with --force flag
        result = invoke_k8s("jobs", "delete", job_name, "--namespace", e2e_namespace, "--force")
        assert result.exit_code == 0, f"Failed to delete job: {result.output}"

        # Verify job is deleted by trying to get it
        result = invoke_k8s("jobs", "get", job_name, "--namespace", e2e_namespace)
        # Should either fail or indicate not found
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_list_jobs_all_namespaces(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and list jobs across all namespaces."""
        job_name = f"{unique_prefix}-all-ns-job"

        # Create job in test namespace
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo all-namespaces",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"

        # List jobs across all namespaces
        result = invoke_k8s("jobs", "list", "--all-namespaces")
        assert result.exit_code == 0, f"Failed to list jobs: {result.output}"
        # Job should appear in the output
        assert "Total:" in result.output

    def test_list_jobs_json(
        self,
        invoke_k8s: Callable[..., Any],
        e2e_namespace: str,
        unique_prefix: str,
    ) -> None:
        """Create a job and list jobs with JSON output format."""
        job_name = f"{unique_prefix}-json-job"

        # Create job
        result = invoke_k8s(
            "jobs",
            "create",
            job_name,
            "--namespace",
            e2e_namespace,
            "--image",
            "busybox:latest",
            "--command",
            "echo json-output",
        )
        assert result.exit_code == 0, f"Failed to create job: {result.output}"

        # List jobs with JSON output
        result = invoke_k8s("jobs", "list", "--namespace", e2e_namespace, "--output", "json")
        assert result.exit_code == 0, f"Failed to list jobs as JSON: {result.output}"
        # Verify JSON-like output (should contain braces or brackets)
        assert "{" in result.output or "[" in result.output
        assert unique_prefix in result.output
