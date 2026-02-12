"""Shared fixtures for Kyverno policy command tests."""

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
def mock_kyverno_manager() -> MagicMock:
    """Create a mock KyvernoManager."""
    manager = MagicMock()

    # ClusterPolicies
    manager.list_cluster_policies.return_value = []
    manager.get_cluster_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "require-labels",
            "validation_failure_action": "Audit",
            "background": True,
            "rules_count": 1,
            "ready": True,
        }
    )
    manager.create_cluster_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "require-labels"}
    )
    manager.delete_cluster_policy.return_value = None

    # Namespaced Policies
    manager.list_policies.return_value = []
    manager.get_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "restrict-images",
            "namespace": "default",
            "validation_failure_action": "Enforce",
            "rules_count": 2,
            "ready": True,
        }
    )
    manager.create_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "restrict-images", "namespace": "default"}
    )
    manager.delete_policy.return_value = None

    # PolicyReports
    manager.list_policy_reports.return_value = []
    manager.get_policy_report.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "polr-test",
            "namespace": "default",
            "pass_count": 5,
            "fail_count": 1,
            "warn_count": 0,
            "error_count": 0,
            "skip_count": 0,
        }
    )

    # ClusterPolicyReports
    manager.list_cluster_policy_reports.return_value = []
    manager.get_cluster_policy_report.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "cpolr-test",
            "pass_count": 10,
            "fail_count": 2,
            "warn_count": 1,
            "error_count": 0,
            "skip_count": 0,
        }
    )

    # Admission
    manager.get_admission_status.return_value = {
        "running": True,
        "pods": [{"name": "kyverno-admission-controller-xyz", "status": "Running"}],
    }

    # Validate
    manager.validate_policy.return_value = {
        "valid": True,
        "policy": MagicMock(model_dump=lambda **kwargs: {"name": "test-policy"}),
    }

    return manager


@pytest.fixture
def get_kyverno_manager(
    mock_kyverno_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock Kyverno manager."""
    return lambda: mock_kyverno_manager
