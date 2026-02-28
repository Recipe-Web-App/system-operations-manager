"""Unit tests for Argo Workflows Kubernetes resource models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.models.argo_workflows import (
    CronWorkflowSummary,
    WorkflowArtifact,
    WorkflowSummary,
    WorkflowTemplateSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowSummary:
    """Test WorkflowSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "my-workflow-abc12",
                "namespace": "argo",
                "uid": "uid-wf-001",
                "creationTimestamp": "2026-01-15T10:00:00Z",
                "labels": {"workflows.argoproj.io/phase": "Succeeded"},
                "annotations": {"example.com/owner": "team-a"},
            },
            "spec": {
                "entrypoint": "main",
            },
            "status": {
                "phase": "Succeeded",
                "startedAt": "2026-01-15T10:00:00Z",
                "finishedAt": "2026-01-15T10:05:30Z",
                "message": "Workflow completed successfully",
                "progress": "5/5",
                "estimatedDuration": 300,
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.name == "my-workflow-abc12"
        assert wf.namespace == "argo"
        assert wf.uid == "uid-wf-001"
        assert wf.creation_timestamp == "2026-01-15T10:00:00Z"
        assert wf.labels == {"workflows.argoproj.io/phase": "Succeeded"}
        assert wf.annotations == {"example.com/owner": "team-a"}
        assert wf.phase == "Succeeded"
        assert wf.started_at == "2026-01-15T10:00:00Z"
        assert wf.finished_at == "2026-01-15T10:05:30Z"
        assert wf.duration == "5m30s"
        assert wf.message == "Workflow completed successfully"
        assert wf.progress == "5/5"
        assert wf.entrypoint == "main"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only required fields present."""
        obj = {
            "metadata": {"name": "minimal-workflow"},
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.name == "minimal-workflow"
        assert wf.namespace is None
        assert wf.uid is None
        assert wf.phase == "Unknown"
        assert wf.started_at is None
        assert wf.finished_at is None
        assert wf.duration == ""
        assert wf.message is None
        assert wf.progress == "0/0"
        assert wf.entrypoint == ""

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with missing status section."""
        obj = {
            "metadata": {
                "name": "no-status-workflow",
                "namespace": "default",
            },
            "spec": {
                "entrypoint": "build",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.name == "no-status-workflow"
        assert wf.phase == "Unknown"
        assert wf.started_at is None
        assert wf.finished_at is None
        assert wf.duration == ""
        assert wf.progress == "0/0"
        assert wf.entrypoint == "build"

    def test_duration_hours_and_minutes(self) -> None:
        """Test duration calculation when elapsed time exceeds one hour."""
        obj = {
            "metadata": {"name": "long-workflow"},
            "status": {
                "phase": "Succeeded",
                "startedAt": "2026-01-15T08:00:00Z",
                "finishedAt": "2026-01-15T09:30:45Z",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.duration == "1h30m"

    def test_duration_minutes_and_seconds(self) -> None:
        """Test duration calculation for sub-hour elapsed time."""
        obj = {
            "metadata": {"name": "medium-workflow"},
            "status": {
                "phase": "Succeeded",
                "startedAt": "2026-01-15T10:00:00Z",
                "finishedAt": "2026-01-15T10:12:08Z",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.duration == "12m8s"

    def test_duration_seconds_only(self) -> None:
        """Test duration calculation for sub-minute elapsed time."""
        obj = {
            "metadata": {"name": "fast-workflow"},
            "status": {
                "phase": "Succeeded",
                "startedAt": "2026-01-15T10:00:00Z",
                "finishedAt": "2026-01-15T10:00:42Z",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.duration == "42s"

    def test_duration_no_finished_at(self) -> None:
        """Test duration is empty string when finishedAt is missing."""
        obj = {
            "metadata": {"name": "running-workflow"},
            "status": {
                "phase": "Running",
                "startedAt": "2026-01-15T10:00:00Z",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.started_at == "2026-01-15T10:00:00Z"
        assert wf.finished_at is None
        assert wf.duration == ""

    def test_running_workflow_in_progress(self) -> None:
        """Test a workflow that is currently running."""
        obj = {
            "metadata": {
                "name": "in-progress",
                "namespace": "workflows",
                "uid": "uid-run-999",
            },
            "spec": {"entrypoint": "pipeline"},
            "status": {
                "phase": "Running",
                "startedAt": "2026-01-15T09:00:00Z",
                "progress": "3/7",
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.phase == "Running"
        assert wf.progress == "3/7"
        assert wf.finished_at is None

    def test_empty_labels_and_annotations_become_none(self) -> None:
        """Test that empty labels/annotations dicts are coerced to None."""
        obj = {
            "metadata": {
                "name": "clean-workflow",
                "labels": {},
                "annotations": {},
            },
        }

        wf = WorkflowSummary.from_k8s_object(obj)

        assert wf.labels is None
        assert wf.annotations is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert WorkflowSummary._entity_name == "argo_workflow"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowTemplateSummary:
    """Test WorkflowTemplateSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "ci-pipeline-template",
                "namespace": "argo",
                "uid": "uid-wft-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"app": "ci"},
                "annotations": {
                    "workflows.argoproj.io/description": "CI pipeline for microservices",
                },
            },
            "spec": {
                "entrypoint": "build-and-test",
                "templates": [
                    {"name": "build-and-test"},
                    {"name": "build"},
                    {"name": "test"},
                ],
            },
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.name == "ci-pipeline-template"
        assert wft.namespace == "argo"
        assert wft.uid == "uid-wft-001"
        assert wft.labels == {"app": "ci"}
        assert wft.description == "CI pipeline for microservices"
        assert wft.entrypoint == "build-and-test"
        assert wft.templates_count == 3

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-template"},
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.name == "bare-template"
        assert wft.namespace is None
        assert wft.description == ""
        assert wft.entrypoint == ""
        assert wft.templates_count == 0

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with no status section (templates have no status)."""
        obj = {
            "metadata": {
                "name": "no-spec-template",
                "namespace": "ci",
            },
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.name == "no-spec-template"
        assert wft.templates_count == 0
        assert wft.description == ""

    def test_description_from_annotation(self) -> None:
        """Test that description is pulled from the annotation key."""
        obj = {
            "metadata": {
                "name": "annotated-template",
                "annotations": {
                    "workflows.argoproj.io/description": "My annotated description",
                    "other.annotation/key": "ignored",
                },
            },
            "spec": {"entrypoint": "entry"},
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.description == "My annotated description"

    def test_description_empty_when_annotation_absent(self) -> None:
        """Test that description is empty when annotation is not present."""
        obj = {
            "metadata": {
                "name": "no-desc-template",
                "annotations": {"other.key": "value"},
            },
            "spec": {"entrypoint": "main"},
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.description == ""

    def test_templates_count_with_many_templates(self) -> None:
        """Test template counting with multiple entries."""
        templates = [{"name": f"step-{i}"} for i in range(10)]
        obj = {
            "metadata": {"name": "large-template"},
            "spec": {"entrypoint": "step-0", "templates": templates},
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.templates_count == 10

    def test_empty_annotations_gives_empty_description(self) -> None:
        """Test that no annotations results in an empty description."""
        obj = {
            "metadata": {
                "name": "no-annotations-template",
                "labels": {},
                "annotations": {},
            },
            "spec": {"entrypoint": "run"},
        }

        wft = WorkflowTemplateSummary.from_k8s_object(obj)

        assert wft.description == ""
        assert wft.labels is None
        assert wft.annotations is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert WorkflowTemplateSummary._entity_name == "workflow_template"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronWorkflowSummary:
    """Test CronWorkflowSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "nightly-report",
                "namespace": "argo",
                "uid": "uid-cron-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"team": "data"},
                "annotations": {"description": "Nightly report generator"},
            },
            "spec": {
                "schedule": "0 2 * * *",
                "timezone": "America/New_York",
                "suspend": False,
                "concurrencyPolicy": "Forbid",
            },
            "status": {
                "active": [
                    {"name": "nightly-report-xyz"},
                    {"name": "nightly-report-abc"},
                ],
                "lastScheduledTime": "2026-01-15T02:00:00Z",
            },
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.name == "nightly-report"
        assert cron.namespace == "argo"
        assert cron.uid == "uid-cron-001"
        assert cron.labels == {"team": "data"}
        assert cron.schedule == "0 2 * * *"
        assert cron.timezone == "America/New_York"
        assert cron.suspend is False
        assert cron.concurrency_policy == "Forbid"
        assert cron.active_count == 2
        assert cron.last_scheduled == "2026-01-15T02:00:00Z"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-cron"},
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.name == "bare-cron"
        assert cron.namespace is None
        assert cron.schedule == ""
        assert cron.timezone == ""
        assert cron.suspend is False
        assert cron.concurrency_policy == "Allow"
        assert cron.active_count == 0
        assert cron.last_scheduled is None

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with no status section."""
        obj = {
            "metadata": {
                "name": "no-status-cron",
                "namespace": "batch",
            },
            "spec": {
                "schedule": "*/5 * * * *",
                "timezone": "UTC",
            },
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.active_count == 0
        assert cron.last_scheduled is None

    def test_suspended_cron_workflow(self) -> None:
        """Test a suspended CronWorkflow."""
        obj = {
            "metadata": {"name": "paused-cron", "namespace": "argo"},
            "spec": {
                "schedule": "0 12 * * 1",
                "timezone": "Europe/London",
                "suspend": True,
                "concurrencyPolicy": "Replace",
            },
            "status": {},
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.suspend is True
        assert cron.schedule == "0 12 * * 1"
        assert cron.concurrency_policy == "Replace"

    def test_active_count_with_empty_active_list(self) -> None:
        """Test that an empty active list yields active_count of zero."""
        obj = {
            "metadata": {"name": "idle-cron"},
            "spec": {"schedule": "0 0 * * *"},
            "status": {"active": []},
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.active_count == 0

    def test_active_count_with_single_active_workflow(self) -> None:
        """Test that a single active workflow is counted correctly."""
        obj = {
            "metadata": {"name": "single-active-cron", "namespace": "argo"},
            "spec": {"schedule": "0 6 * * *"},
            "status": {
                "active": [{"name": "single-active-cron-111aaa"}],
                "lastScheduledTime": "2026-01-15T06:00:00Z",
            },
        }

        cron = CronWorkflowSummary.from_k8s_object(obj)

        assert cron.active_count == 1
        assert cron.last_scheduled == "2026-01-15T06:00:00Z"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert CronWorkflowSummary._entity_name == "cron_workflow"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowArtifact:
    """Test WorkflowArtifact model."""

    def test_from_k8s_object_s3_artifact(self) -> None:
        """Test from_k8s_object with an S3 artifact."""
        artifact = {
            "name": "main-logs",
            "path": "/tmp/main.log",
            "s3": {
                "bucket": "my-artifact-bucket",
                "key": "workflows/abc123/main-logs.tgz",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact, node_id="abc123")

        assert wa.name == "main-logs"
        assert wa.node_id == "abc123"
        assert wa.path == "/tmp/main.log"
        assert wa.artifact_type == "s3"
        assert wa.bucket == "my-artifact-bucket"
        assert wa.key == "workflows/abc123/main-logs.tgz"

    def test_from_k8s_object_gcs_artifact(self) -> None:
        """Test from_k8s_object with a GCS artifact."""
        artifact = {
            "name": "build-output",
            "path": "/workspace/build",
            "gcs": {
                "bucket": "gcs-artifacts",
                "key": "builds/output.tar.gz",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact, node_id="node-gcs")

        assert wa.artifact_type == "gcs"
        assert wa.bucket == "gcs-artifacts"
        assert wa.key == "builds/output.tar.gz"

    def test_from_k8s_object_http_artifact(self) -> None:
        """Test from_k8s_object with an HTTP artifact (no bucket/key)."""
        artifact = {
            "name": "remote-config",
            "path": "/tmp/config.json",
            "http": {
                "url": "https://example.com/config.json",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact)

        assert wa.artifact_type == "http"
        assert wa.bucket == ""
        assert wa.key == ""

    def test_from_k8s_object_git_artifact(self) -> None:
        """Test from_k8s_object with a git artifact."""
        artifact = {
            "name": "source-code",
            "path": "/src",
            "git": {
                "repo": "https://github.com/example/repo.git",
                "revision": "main",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact, node_id="git-node")

        assert wa.artifact_type == "git"
        assert wa.bucket == ""
        assert wa.key == ""

    def test_from_k8s_object_unknown_type(self) -> None:
        """Test from_k8s_object when no recognised storage key is present."""
        artifact = {
            "name": "mystery-artifact",
            "path": "/tmp/mystery",
        }

        wa = WorkflowArtifact.from_k8s_object(artifact)

        assert wa.name == "mystery-artifact"
        assert wa.artifact_type == "unknown"
        assert wa.bucket == ""
        assert wa.key == ""

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with an empty artifact dict."""
        wa = WorkflowArtifact.from_k8s_object({})

        assert wa.name == ""
        assert wa.node_id == ""
        assert wa.path == ""
        assert wa.artifact_type == "unknown"
        assert wa.bucket == ""
        assert wa.key == ""

    def test_from_k8s_object_artifactory_artifact(self) -> None:
        """Test from_k8s_object with an Artifactory artifact."""
        artifact = {
            "name": "jar-artifact",
            "path": "/artifacts/app.jar",
            "artifactory": {
                "url": "https://artifactory.example.com/repo/app.jar",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact, node_id="build-node")

        assert wa.artifact_type == "artifactory"
        assert wa.node_id == "build-node"

    def test_from_k8s_object_oss_artifact(self) -> None:
        """Test from_k8s_object with an OSS artifact."""
        artifact = {
            "name": "oss-data",
            "path": "/data/output",
            "oss": {
                "bucket": "oss-bucket",
                "key": "data/output.tar.gz",
            },
        }

        wa = WorkflowArtifact.from_k8s_object(artifact)

        assert wa.artifact_type == "oss"
        assert wa.bucket == "oss-bucket"
        assert wa.key == "data/output.tar.gz"

    def test_node_id_defaults_to_empty_string(self) -> None:
        """Test that node_id defaults to empty string when not provided."""
        artifact = {"name": "test", "s3": {"bucket": "b", "key": "k"}}

        wa = WorkflowArtifact.from_k8s_object(artifact)

        assert wa.node_id == ""
