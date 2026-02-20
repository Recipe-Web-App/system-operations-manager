"""Shared fixtures for Flux command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer

from system_operations_manager.plugins.kubernetes.commands.flux import (
    register_flux_commands,
)


@pytest.fixture
def mock_flux_manager() -> MagicMock:
    """Create a mock FluxManager with default return values."""
    manager = MagicMock()

    # GitRepository defaults
    manager.list_git_repositories.return_value = []
    manager.get_git_repository.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "podinfo", "namespace": "flux-system"}
    )
    manager.create_git_repository.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "podinfo", "namespace": "flux-system"}
    )
    manager.delete_git_repository.return_value = None
    manager.suspend_git_repository.return_value = {"name": "podinfo", "suspended": True}
    manager.resume_git_repository.return_value = {"name": "podinfo", "suspended": False}
    manager.reconcile_git_repository.return_value = {"name": "podinfo", "reconciled": True}
    manager.get_git_repository_status.return_value = {
        "name": "podinfo",
        "ready": True,
    }

    # HelmRepository defaults
    manager.list_helm_repositories.return_value = []
    manager.get_helm_repository.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "bitnami", "namespace": "flux-system"}
    )
    manager.create_helm_repository.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "bitnami", "namespace": "flux-system"}
    )
    manager.delete_helm_repository.return_value = None
    manager.suspend_helm_repository.return_value = {"name": "bitnami", "suspended": True}
    manager.resume_helm_repository.return_value = {"name": "bitnami", "suspended": False}
    manager.reconcile_helm_repository.return_value = {"name": "bitnami", "reconciled": True}
    manager.get_helm_repository_status.return_value = {
        "name": "bitnami",
        "ready": True,
    }

    # Kustomization defaults
    manager.list_kustomizations.return_value = []
    manager.get_kustomization.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "app-ks", "namespace": "flux-system"}
    )
    manager.create_kustomization.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "app-ks", "namespace": "flux-system"}
    )
    manager.delete_kustomization.return_value = None
    manager.suspend_kustomization.return_value = {"name": "app-ks", "suspended": True}
    manager.resume_kustomization.return_value = {"name": "app-ks", "suspended": False}
    manager.reconcile_kustomization.return_value = {"name": "app-ks", "reconciled": True}
    manager.get_kustomization_status.return_value = {
        "name": "app-ks",
        "ready": True,
    }

    # HelmRelease defaults
    manager.list_helm_releases.return_value = []
    manager.get_helm_release.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "nginx", "namespace": "flux-system"}
    )
    manager.create_helm_release.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "nginx", "namespace": "flux-system"}
    )
    manager.delete_helm_release.return_value = None
    manager.suspend_helm_release.return_value = {"name": "nginx", "suspended": True}
    manager.resume_helm_release.return_value = {"name": "nginx", "suspended": False}
    manager.reconcile_helm_release.return_value = {"name": "nginx", "reconciled": True}
    manager.get_helm_release_status.return_value = {
        "name": "nginx",
        "ready": True,
    }

    return manager


@pytest.fixture
def get_flux_manager(mock_flux_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock Flux manager."""
    return lambda: mock_flux_manager


@pytest.fixture
def app(get_flux_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a Typer app with Flux commands registered."""
    test_app = typer.Typer()
    register_flux_commands(test_app, get_flux_manager)
    return test_app
