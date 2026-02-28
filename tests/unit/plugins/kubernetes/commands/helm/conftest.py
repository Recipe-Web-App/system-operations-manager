"""Shared fixtures for Helm command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer

from system_operations_manager.integrations.kubernetes.models.helm import (
    HelmChart,
    HelmCommandResult,
    HelmRelease,
    HelmReleaseHistory,
    HelmReleaseStatus,
    HelmRepo,
    HelmTemplateResult,
)
from system_operations_manager.plugins.kubernetes.commands.helm import (
    register_helm_commands,
)


@pytest.fixture
def mock_helm_manager() -> MagicMock:
    """Create a mock HelmManager with default return values."""
    manager = MagicMock()

    manager.install.return_value = HelmCommandResult(success=True, stdout="Release installed")
    manager.upgrade.return_value = HelmCommandResult(success=True, stdout="Release upgraded")
    manager.rollback.return_value = HelmCommandResult(success=True, stdout="Rollback complete")
    manager.uninstall.return_value = HelmCommandResult(success=True, stdout="Release uninstalled")
    manager.list_releases.return_value = [
        HelmRelease(
            name="nginx",
            namespace="default",
            revision=1,
            status="deployed",
            chart="nginx-15.0.0",
            app_version="1.25.0",
            updated="2024-01-01",
        ),
    ]
    manager.history.return_value = [
        HelmReleaseHistory(
            revision=1,
            status="deployed",
            chart="nginx-15.0.0",
            app_version="1.25.0",
            description="Install complete",
            updated="2024-01-01",
        ),
    ]
    manager.status.return_value = HelmReleaseStatus(
        name="nginx",
        namespace="default",
        revision=1,
        status="deployed",
        description="Install complete",
        notes="Visit http://localhost",
    )
    manager.get_values.return_value = "replicaCount: 2\nimage:\n  tag: latest"
    manager.template.return_value = HelmTemplateResult(
        rendered_yaml="apiVersion: v1\nkind: Service",
        success=True,
    )
    manager.search_repo.return_value = [
        HelmChart(
            name="bitnami/nginx",
            chart_version="15.0.0",
            app_version="1.25.0",
            description="NGINX Open Source",
        ),
    ]
    manager.repo_list.return_value = [
        HelmRepo(name="bitnami", url="https://charts.bitnami.com/bitnami"),
    ]
    manager.repo_add.return_value = None
    manager.repo_update.return_value = None
    manager.repo_remove.return_value = None

    return manager


@pytest.fixture
def get_helm_manager(mock_helm_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock Helm manager."""
    return lambda: mock_helm_manager


@pytest.fixture
def app(get_helm_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a Typer app with Helm commands registered."""
    test_app = typer.Typer()
    register_helm_commands(test_app, get_helm_manager)
    return test_app
