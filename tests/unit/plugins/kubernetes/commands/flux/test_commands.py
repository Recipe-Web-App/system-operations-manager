"""Unit tests for Flux CD CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
)

# =============================================================================
# GitRepository Commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxGitRepository:
    """Tests for flux source git commands."""

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "list"])
        assert result.exit_code == 0
        mock_flux_manager.list_git_repositories.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "list", "-n", "flux-system"])
        assert result.exit_code == 0
        mock_flux_manager.list_git_repositories.assert_called_once_with(
            namespace="flux-system",
            label_selector=None,
        )

    def test_list_with_label_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "list", "-l", "app=podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.list_git_repositories.assert_called_once_with(
            namespace=None,
            label_selector="app=podinfo",
        )

    def test_list_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.list_git_repositories.side_effect = KubernetesError(message="forbidden")
        result = cli_runner.invoke(app, ["flux", "source", "git", "list"])
        assert result.exit_code == 1

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "get", "podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.get_git_repository.assert_called_once_with("podinfo", namespace=None)

    def test_get_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "get", "podinfo", "-o", "json"])
        assert result.exit_code == 0

    def test_get_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_git_repository.side_effect = KubernetesError(message="not found")
        result = cli_runner.invoke(app, ["flux", "source", "git", "get", "podinfo"])
        assert result.exit_code == 1

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "git",
                "create",
                "podinfo",
                "--url",
                "https://github.com/stefanprodan/podinfo",
                "--branch",
                "main",
            ],
        )
        assert result.exit_code == 0
        mock_flux_manager.create_git_repository.assert_called_once_with(
            "podinfo",
            namespace=None,
            url="https://github.com/stefanprodan/podinfo",
            ref_branch="main",
            ref_tag=None,
            ref_semver=None,
            ref_commit=None,
            interval="1m",
            secret_ref=None,
        )

    def test_create_with_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "git",
                "create",
                "podinfo",
                "--url",
                "https://github.com/org/repo",
                "-n",
                "flux-system",
                "--tag",
                "v1.0.0",
                "--interval",
                "5m",
                "--secret-ref",
                "git-creds",
            ],
        )
        assert result.exit_code == 0
        mock_flux_manager.create_git_repository.assert_called_once()

    def test_create_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.create_git_repository.side_effect = KubernetesError(
            message="already exists"
        )
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "git",
                "create",
                "podinfo",
                "--url",
                "https://github.com/org/repo",
            ],
        )
        assert result.exit_code == 1

    def test_delete_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "delete", "podinfo", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output
        mock_flux_manager.delete_git_repository.assert_called_once_with("podinfo", namespace=None)

    def test_delete_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.delete_git_repository.side_effect = KubernetesError(message="not found")
        result = cli_runner.invoke(app, ["flux", "source", "git", "delete", "podinfo", "--force"])
        assert result.exit_code == 1

    def test_suspend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "suspend", "podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.suspend_git_repository.assert_called_once_with("podinfo", namespace=None)

    def test_suspend_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.suspend_git_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "git", "suspend", "podinfo"])
        assert result.exit_code == 1

    def test_resume(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "resume", "podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.resume_git_repository.assert_called_once_with("podinfo", namespace=None)

    def test_resume_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.resume_git_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "git", "resume", "podinfo"])
        assert result.exit_code == 1

    def test_reconcile(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "reconcile", "podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.reconcile_git_repository.assert_called_once_with(
            "podinfo", namespace=None
        )

    def test_reconcile_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.reconcile_git_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "git", "reconcile", "podinfo"])
        assert result.exit_code == 1

    def test_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "git", "status", "podinfo"])
        assert result.exit_code == 0
        mock_flux_manager.get_git_repository_status.assert_called_once_with(
            "podinfo", namespace=None
        )

    def test_status_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app, ["flux", "source", "git", "status", "podinfo", "-o", "json"]
        )
        assert result.exit_code == 0

    def test_status_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_git_repository_status.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "git", "status", "podinfo"])
        assert result.exit_code == 1


# =============================================================================
# HelmRepository Commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxHelmRepository:
    """Tests for flux source helm commands."""

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "list"])
        assert result.exit_code == 0
        mock_flux_manager.list_helm_repositories.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.list_helm_repositories.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "list"])
        assert result.exit_code == 1

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "get", "bitnami"])
        assert result.exit_code == 0
        mock_flux_manager.get_helm_repository.assert_called_once_with("bitnami", namespace=None)

    def test_get_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_helm_repository.side_effect = KubernetesError(message="not found")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "get", "bitnami"])
        assert result.exit_code == 1

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "helm",
                "create",
                "bitnami",
                "--url",
                "https://charts.bitnami.com/bitnami",
            ],
        )
        assert result.exit_code == 0
        mock_flux_manager.create_helm_repository.assert_called_once_with(
            "bitnami",
            namespace=None,
            url="https://charts.bitnami.com/bitnami",
            repo_type="default",
            interval="1m",
            secret_ref=None,
        )

    def test_create_oci_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "helm",
                "create",
                "ghcr",
                "--url",
                "oci://ghcr.io/fluxcd/charts",
                "--type",
                "oci",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = mock_flux_manager.create_helm_repository.call_args
        assert call_kwargs.kwargs["repo_type"] == "oci"

    def test_create_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.create_helm_repository.side_effect = KubernetesError(message="conflict")
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "source",
                "helm",
                "create",
                "bitnami",
                "--url",
                "https://charts.bitnami.com/bitnami",
            ],
        )
        assert result.exit_code == 1

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "delete", "bitnami", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.delete_helm_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "delete", "bitnami", "--force"])
        assert result.exit_code == 1

    def test_suspend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "suspend", "bitnami"])
        assert result.exit_code == 0
        mock_flux_manager.suspend_helm_repository.assert_called_once()

    def test_suspend_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.suspend_helm_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "suspend", "bitnami"])
        assert result.exit_code == 1

    def test_resume(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "resume", "bitnami"])
        assert result.exit_code == 0
        mock_flux_manager.resume_helm_repository.assert_called_once()

    def test_resume_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.resume_helm_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "resume", "bitnami"])
        assert result.exit_code == 1

    def test_reconcile(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "reconcile", "bitnami"])
        assert result.exit_code == 0
        mock_flux_manager.reconcile_helm_repository.assert_called_once()

    def test_reconcile_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.reconcile_helm_repository.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "reconcile", "bitnami"])
        assert result.exit_code == 1

    def test_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "source", "helm", "status", "bitnami"])
        assert result.exit_code == 0
        mock_flux_manager.get_helm_repository_status.assert_called_once()

    def test_status_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_helm_repository_status.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "source", "helm", "status", "bitnami"])
        assert result.exit_code == 1


# =============================================================================
# Kustomization Commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxKustomization:
    """Tests for flux ks commands."""

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "list"])
        assert result.exit_code == 0
        mock_flux_manager.list_kustomizations.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.list_kustomizations.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "list"])
        assert result.exit_code == 1

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "get", "app-ks"])
        assert result.exit_code == 0
        mock_flux_manager.get_kustomization.assert_called_once_with("app-ks", namespace=None)

    def test_get_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_kustomization.side_effect = KubernetesError(message="not found")
        result = cli_runner.invoke(app, ["flux", "ks", "get", "app-ks"])
        assert result.exit_code == 1

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "ks",
                "create",
                "app-ks",
                "--source-name",
                "podinfo",
                "--source-kind",
                "GitRepository",
            ],
        )
        assert result.exit_code == 0
        mock_flux_manager.create_kustomization.assert_called_once_with(
            "app-ks",
            namespace=None,
            source_kind="GitRepository",
            source_name="podinfo",
            source_namespace=None,
            path="./",
            interval="5m",
            prune=True,
            target_namespace=None,
        )

    def test_create_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "ks",
                "create",
                "app-ks",
                "--source-name",
                "podinfo",
                "--source-kind",
                "GitRepository",
                "--source-namespace",
                "flux-system",
                "--path",
                "./deploy",
                "--interval",
                "10m",
                "--no-prune",
                "--target-namespace",
                "app-ns",
                "-n",
                "flux-system",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = mock_flux_manager.create_kustomization.call_args
        assert call_kwargs.kwargs["source_namespace"] == "flux-system"
        assert call_kwargs.kwargs["path"] == "./deploy"
        assert call_kwargs.kwargs["prune"] is False
        assert call_kwargs.kwargs["target_namespace"] == "app-ns"

    def test_create_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.create_kustomization.side_effect = KubernetesError(message="conflict")
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "ks",
                "create",
                "app-ks",
                "--source-name",
                "podinfo",
                "--source-kind",
                "GitRepository",
            ],
        )
        assert result.exit_code == 1

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "delete", "app-ks", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.delete_kustomization.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "delete", "app-ks", "--force"])
        assert result.exit_code == 1

    def test_suspend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "suspend", "app-ks"])
        assert result.exit_code == 0
        mock_flux_manager.suspend_kustomization.assert_called_once()

    def test_suspend_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.suspend_kustomization.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "suspend", "app-ks"])
        assert result.exit_code == 1

    def test_resume(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "resume", "app-ks"])
        assert result.exit_code == 0
        mock_flux_manager.resume_kustomization.assert_called_once()

    def test_resume_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.resume_kustomization.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "resume", "app-ks"])
        assert result.exit_code == 1

    def test_reconcile(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "reconcile", "app-ks"])
        assert result.exit_code == 0
        mock_flux_manager.reconcile_kustomization.assert_called_once()

    def test_reconcile_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.reconcile_kustomization.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "reconcile", "app-ks"])
        assert result.exit_code == 1

    def test_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "status", "app-ks"])
        assert result.exit_code == 0
        mock_flux_manager.get_kustomization_status.assert_called_once()

    def test_status_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "ks", "status", "app-ks", "-o", "json"])
        assert result.exit_code == 0

    def test_status_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_kustomization_status.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "ks", "status", "app-ks"])
        assert result.exit_code == 1


# =============================================================================
# HelmRelease Commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxHelmRelease:
    """Tests for flux hr commands."""

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "list"])
        assert result.exit_code == 0
        mock_flux_manager.list_helm_releases.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.list_helm_releases.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "list"])
        assert result.exit_code == 1

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "get", "nginx"])
        assert result.exit_code == 0
        mock_flux_manager.get_helm_release.assert_called_once_with("nginx", namespace=None)

    def test_get_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_helm_release.side_effect = KubernetesError(message="not found")
        result = cli_runner.invoke(app, ["flux", "hr", "get", "nginx"])
        assert result.exit_code == 1

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "hr",
                "create",
                "nginx",
                "--chart",
                "nginx",
                "--source-name",
                "bitnami",
                "--source-kind",
                "HelmRepository",
            ],
        )
        assert result.exit_code == 0
        mock_flux_manager.create_helm_release.assert_called_once_with(
            "nginx",
            namespace=None,
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
            chart_source_namespace=None,
            interval="5m",
            target_namespace=None,
        )

    def test_create_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "hr",
                "create",
                "nginx",
                "--chart",
                "nginx",
                "--source-name",
                "bitnami",
                "--source-kind",
                "HelmRepository",
                "--source-namespace",
                "flux-system",
                "--interval",
                "10m",
                "--target-namespace",
                "web",
                "-n",
                "flux-system",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = mock_flux_manager.create_helm_release.call_args
        assert call_kwargs.kwargs["chart_source_namespace"] == "flux-system"
        assert call_kwargs.kwargs["target_namespace"] == "web"

    def test_create_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.create_helm_release.side_effect = KubernetesError(message="conflict")
        result = cli_runner.invoke(
            app,
            [
                "flux",
                "hr",
                "create",
                "nginx",
                "--chart",
                "nginx",
                "--source-name",
                "bitnami",
                "--source-kind",
                "HelmRepository",
            ],
        )
        assert result.exit_code == 1

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "delete", "nginx", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.delete_helm_release.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "delete", "nginx", "--force"])
        assert result.exit_code == 1

    def test_suspend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "suspend", "nginx"])
        assert result.exit_code == 0
        mock_flux_manager.suspend_helm_release.assert_called_once()

    def test_suspend_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.suspend_helm_release.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "suspend", "nginx"])
        assert result.exit_code == 1

    def test_resume(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "resume", "nginx"])
        assert result.exit_code == 0
        mock_flux_manager.resume_helm_release.assert_called_once()

    def test_resume_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.resume_helm_release.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "resume", "nginx"])
        assert result.exit_code == 1

    def test_reconcile(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "reconcile", "nginx"])
        assert result.exit_code == 0
        mock_flux_manager.reconcile_helm_release.assert_called_once()

    def test_reconcile_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.reconcile_helm_release.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "reconcile", "nginx"])
        assert result.exit_code == 1

    def test_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "status", "nginx"])
        assert result.exit_code == 0
        mock_flux_manager.get_helm_release_status.assert_called_once()

    def test_status_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["flux", "hr", "status", "nginx", "-o", "json"])
        assert result.exit_code == 0

    def test_status_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_flux_manager: MagicMock,
    ) -> None:
        mock_flux_manager.get_helm_release_status.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["flux", "hr", "status", "nginx"])
        assert result.exit_code == 1
