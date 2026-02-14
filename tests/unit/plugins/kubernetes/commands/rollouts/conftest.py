"""Shared fixtures for Argo Rollouts command tests."""

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
def mock_rollouts_manager() -> MagicMock:
    """Create a mock RolloutsManager."""
    manager = MagicMock()

    # Rollouts
    manager.list_rollouts.return_value = []
    manager.get_rollout.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout",
            "namespace": "default",
            "strategy": "canary",
            "phase": "Healthy",
            "replicas": 3,
            "ready_replicas": 3,
            "canary_weight": 0,
            "image": "nginx:1.21",
        }
    )
    manager.create_rollout.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout",
            "namespace": "default",
            "strategy": "canary",
            "image": "nginx:1.21",
        }
    )
    manager.delete_rollout.return_value = None
    manager.get_rollout_status.return_value = {
        "name": "my-rollout",
        "namespace": "default",
        "phase": "Healthy",
        "message": None,
        "replicas": 3,
        "ready_replicas": 3,
        "current_step_index": None,
        "total_steps": 0,
        "canary_weight": 0,
        "stable_rs": "abc123",
        "canary_rs": "",
        "conditions": [],
    }
    manager.promote_rollout.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout",
            "namespace": "default",
            "phase": "Progressing",
        }
    )
    manager.abort_rollout.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout",
            "namespace": "default",
            "phase": "Degraded",
        }
    )
    manager.retry_rollout.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout",
            "namespace": "default",
            "phase": "Progressing",
        }
    )

    # AnalysisTemplates
    manager.list_analysis_templates.return_value = []
    manager.get_analysis_template.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "success-rate",
            "namespace": "default",
            "metrics_count": 2,
            "args": ["service-name"],
        }
    )

    # AnalysisRuns
    manager.list_analysis_runs.return_value = []
    manager.get_analysis_run.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-rollout-abc123",
            "namespace": "default",
            "phase": "Successful",
            "metrics_count": 2,
            "rollout_ref": "my-rollout",
        }
    )

    return manager


@pytest.fixture
def get_rollouts_manager(
    mock_rollouts_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock Rollouts manager."""
    return lambda: mock_rollouts_manager
