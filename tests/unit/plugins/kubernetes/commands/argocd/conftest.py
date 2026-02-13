"""Shared fixtures for ArgoCD command tests."""

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
def mock_argocd_manager() -> MagicMock:
    """Create a mock ArgoCDManager."""
    manager = MagicMock()

    # Applications
    manager.list_applications.return_value = []
    manager.get_application.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-app",
            "namespace": "argocd",
            "project": "default",
            "repo_url": "https://github.com/org/repo",
            "path": "k8s",
            "sync_status": "Synced",
            "health_status": "Healthy",
        }
    )
    manager.create_application.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-app",
            "namespace": "argocd",
            "project": "default",
            "repo_url": "https://github.com/org/repo",
        }
    )
    manager.delete_application.return_value = None

    # Sync/Rollback/Health/Diff
    manager.sync_application.return_value = {
        "name": "my-app",
        "namespace": "argocd",
        "sync": {"prune": False, "dryRun": False},
        "initiated_by": {"username": "ops-cli"},
    }
    manager.rollback_application.return_value = {
        "name": "my-app",
        "namespace": "argocd",
        "target_revision": "abc123",
        "revision_id": 0,
    }
    manager.get_application_health.return_value = {
        "name": "my-app",
        "namespace": "argocd",
        "health_status": "Healthy",
        "message": None,
        "resources": [],
        "conditions": [],
    }
    manager.diff_application.return_value = {
        "name": "my-app",
        "namespace": "argocd",
        "sync_status": "Synced",
        "revision": "abc123",
        "out_of_sync_resources": [],
        "total_resources": 5,
        "synced_resources": 5,
    }

    # Projects
    manager.list_projects.return_value = []
    manager.get_project.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-project",
            "namespace": "argocd",
            "description": "Test project",
            "source_repos": ["*"],
        }
    )
    manager.create_project.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-project",
            "namespace": "argocd",
            "description": "Test project",
        }
    )
    manager.delete_project.return_value = None

    return manager


@pytest.fixture
def get_argocd_manager(
    mock_argocd_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock ArgoCD manager."""
    return lambda: mock_argocd_manager
