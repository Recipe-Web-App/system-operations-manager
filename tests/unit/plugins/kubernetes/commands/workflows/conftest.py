"""Shared fixtures for Argo Workflows command tests."""

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
def mock_workflows_manager() -> MagicMock:
    """Create a mock WorkflowsManager."""
    manager = MagicMock()

    # Workflows
    manager.list_workflows.return_value = []
    manager.get_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-workflow",
            "namespace": "default",
            "phase": "Succeeded",
            "progress": "3/3",
            "duration": "2m30s",
            "entrypoint": "main",
        }
    )
    manager.create_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-workflow",
            "namespace": "default",
            "phase": "Pending",
        }
    )
    manager.delete_workflow.return_value = None
    manager.get_workflow_logs.return_value = "workflow logs here"

    # WorkflowTemplates
    manager.list_workflow_templates.return_value = []
    manager.get_workflow_template.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-template",
            "namespace": "default",
            "entrypoint": "main",
            "templates_count": 3,
            "description": "A workflow template",
        }
    )
    manager.create_workflow_template.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-template",
            "namespace": "default",
        }
    )
    manager.delete_workflow_template.return_value = None

    # CronWorkflows
    manager.list_cron_workflows.return_value = []
    manager.get_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "namespace": "default",
            "schedule": "0 0 * * *",
            "suspend": False,
            "active_count": 0,
        }
    )
    manager.create_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "namespace": "default",
            "schedule": "0 0 * * *",
        }
    )
    manager.delete_cron_workflow.return_value = None
    manager.suspend_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "suspend": True,
        }
    )
    manager.resume_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "suspend": False,
        }
    )

    # Artifacts
    manager.list_workflow_artifacts.return_value = []

    return manager


@pytest.fixture
def get_workflows_manager(
    mock_workflows_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock Workflows manager."""
    return lambda: mock_workflows_manager
