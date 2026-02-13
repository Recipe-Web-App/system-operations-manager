"""Unit tests for WorkflowsManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.workflows_manager import (
    WorkflowsManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def workflows_manager(mock_k8s_client: MagicMock) -> WorkflowsManager:
    """Create a WorkflowsManager instance with mocked client."""
    return WorkflowsManager(mock_k8s_client)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowOperations:
    """Tests for Workflow operations."""

    def test_list_workflows_success(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list workflows successfully."""
        mock_wf_dict = {
            "metadata": {"name": "test-workflow", "namespace": "default"},
            "spec": {},
            "status": {"phase": "Succeeded"},
        }
        mock_response = {"items": [mock_wf_dict]}
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_summary.phase = "Succeeded"
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.list_workflows()

            assert len(result) == 1
            assert result[0] == mock_summary
            mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once()

    def test_list_workflows_with_phase_filter(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should filter workflows by phase."""
        mock_wf1 = MagicMock()
        mock_wf1.phase = "Running"
        mock_wf2 = MagicMock()
        mock_wf2.phase = "Succeeded"

        mock_response: dict[str, Any] = {"items": [{}, {}]}
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowSummary.from_k8s_object",
            side_effect=[mock_wf1, mock_wf2],
        ):
            result = workflows_manager.list_workflows(phase="Running")

            assert len(result) == 1
            assert result[0].phase == "Running"

    def test_get_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get a single workflow."""
        mock_wf_dict = {
            "metadata": {"name": "test-workflow"},
            "spec": {},
            "status": {},
        }
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_wf_dict

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.get_workflow("test-workflow")

            assert result == mock_summary
            mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
                "argoproj.io", "v1alpha1", "default", "workflows", "test-workflow"
            )

    def test_create_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create a workflow."""
        mock_response = {
            "metadata": {"name": "new-workflow"},
            "spec": {},
            "status": {},
        }
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.create_workflow(
                "new-workflow",
                template_ref="my-template",
                arguments={"param1": "value1"},
            )

            assert result == mock_summary
            call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
            assert call_args[0][2] == "default"  # namespace
            assert call_args[0][3] == "workflows"
            body = call_args[0][4]
            assert body["metadata"]["name"] == "new-workflow"
            assert body["spec"]["workflowTemplateRef"]["name"] == "my-template"

    def test_delete_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete a workflow."""
        workflows_manager.delete_workflow("test-workflow")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            "argoproj.io", "v1alpha1", "default", "workflows", "test-workflow"
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowTemplateOperations:
    """Tests for WorkflowTemplate operations."""

    def test_list_workflow_templates(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list workflow templates."""
        mock_response: dict[str, Any] = {"items": []}
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = mock_response

        result = workflows_manager.list_workflow_templates()

        assert result == []
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once()

    def test_get_workflow_template(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get a workflow template."""
        mock_template = {
            "metadata": {"name": "test-template"},
            "spec": {},
        }
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_template

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowTemplateSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.get_workflow_template("test-template")

            assert result == mock_summary

    def test_create_workflow_template(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create a workflow template."""
        spec = {"entrypoint": "main", "templates": []}
        mock_response = {"metadata": {"name": "new-template"}, "spec": spec}
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowTemplateSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.create_workflow_template("new-template", spec=spec)

            assert result == mock_summary

    def test_delete_workflow_template(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete a workflow template."""
        workflows_manager.delete_workflow_template("test-template")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            "argoproj.io", "v1alpha1", "default", "workflowtemplates", "test-template"
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronWorkflowOperations:
    """Tests for CronWorkflow operations."""

    def test_list_cron_workflows(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list cron workflows."""
        mock_response: dict[str, Any] = {"items": []}
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = mock_response

        result = workflows_manager.list_cron_workflows()

        assert result == []

    def test_get_cron_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get a cron workflow."""
        mock_cron = {
            "metadata": {"name": "test-cron"},
            "spec": {"schedule": "0 0 * * *"},
            "status": {},
        }
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_cron

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.CronWorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.get_cron_workflow("test-cron")

            assert result == mock_summary

    def test_create_cron_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create a cron workflow."""
        mock_response = {
            "metadata": {"name": "new-cron"},
            "spec": {"schedule": "0 0 * * *"},
            "status": {},
        }
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.CronWorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.create_cron_workflow(
                "new-cron",
                schedule="0 0 * * *",
                template_ref="my-template",
            )

            assert result == mock_summary

    def test_delete_cron_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete a cron workflow."""
        workflows_manager.delete_cron_workflow("test-cron")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            "argoproj.io", "v1alpha1", "default", "cronworkflows", "test-cron"
        )

    def test_suspend_cron_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should suspend a cron workflow."""
        mock_response = {
            "metadata": {"name": "test-cron"},
            "spec": {"suspend": True},
            "status": {},
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.CronWorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.suspend_cron_workflow("test-cron")

            assert result == mock_summary
            call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
            patch_body = call_args[0][5]
            assert patch_body["spec"]["suspend"] is True

    def test_resume_cron_workflow(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should resume a cron workflow."""
        mock_response = {
            "metadata": {"name": "test-cron"},
            "spec": {"suspend": False},
            "status": {},
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.CronWorkflowSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workflows_manager.resume_cron_workflow("test-cron")

            assert result == mock_summary
            call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
            patch_body = call_args[0][5]
            assert patch_body["spec"]["suspend"] is False


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowLogsAndArtifacts:
    """Tests for workflow logs and artifacts operations."""

    def test_get_workflow_logs_static(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get static workflow logs."""
        mock_wf = {
            "status": {
                "nodes": {
                    "node1": {"type": "Pod", "id": "pod-123"},
                }
            }
        }
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_wf
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = "log output"

        result = workflows_manager.get_workflow_logs("test-workflow", follow=False)

        assert isinstance(result, str)
        assert "pod-123" in result
        assert "log output" in result

    def test_get_workflow_logs_no_pods(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle workflows with no pods."""
        mock_wf: dict[str, Any] = {"status": {"nodes": {}}}
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_wf

        result = workflows_manager.get_workflow_logs("test-workflow", follow=False)

        assert "No pods found" in result

    def test_list_workflow_artifacts(
        self, workflows_manager: WorkflowsManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list workflow artifacts."""
        mock_wf = {
            "status": {
                "nodes": {
                    "node1": {
                        "outputs": {
                            "artifacts": [
                                {
                                    "name": "result",
                                    "path": "/tmp/result.txt",
                                    "s3": {"bucket": "my-bucket", "key": "results/file.txt"},
                                }
                            ]
                        }
                    }
                }
            }
        }
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = mock_wf

        with patch(
            "system_operations_manager.services.kubernetes.workflows_manager.WorkflowArtifact.from_k8s_object"
        ) as mock_from_k8s:
            mock_artifact = MagicMock()
            mock_from_k8s.return_value = mock_artifact

            result = workflows_manager.list_workflow_artifacts("test-workflow")

            assert len(result) == 1
            assert result[0] == mock_artifact
