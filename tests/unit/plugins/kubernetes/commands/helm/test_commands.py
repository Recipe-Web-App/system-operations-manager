"""Unit tests for Helm CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
)
from system_operations_manager.integrations.kubernetes.helm_client import (
    HelmBinaryNotFoundError,
    HelmError,
)
from system_operations_manager.integrations.kubernetes.models.helm import (
    HelmTemplateResult,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmInstall:
    """Tests for helm install command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "install", "my-release", "bitnami/nginx"])
        assert result.exit_code == 0
        assert "Release installed" in result.output
        mock_helm_manager.install.assert_called_once_with(
            "my-release",
            "bitnami/nginx",
            namespace=None,
            values_files=None,
            set_values=None,
            version=None,
            create_namespace=False,
            wait=False,
            timeout=None,
            dry_run=False,
        )

    def test_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app, ["helm", "install", "my-release", "bitnami/nginx", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        mock_helm_manager.install.assert_called_once()

    def test_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "helm",
                "install",
                "my-release",
                "bitnami/nginx",
                "-n",
                "production",
                "-f",
                "values.yaml",
                "--set",
                "replicaCount=3",
                "--version",
                "15.0.0",
                "--create-namespace",
                "--wait",
                "--timeout",
                "5m0s",
            ],
        )
        assert result.exit_code == 0
        mock_helm_manager.install.assert_called_once_with(
            "my-release",
            "bitnami/nginx",
            namespace="production",
            values_files=["values.yaml"],
            set_values=["replicaCount=3"],
            version="15.0.0",
            create_namespace=True,
            wait=True,
            timeout="5m0s",
            dry_run=False,
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.install.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "install", "rel", "chart"])
        assert result.exit_code == 1
        assert "helm binary not found" in result.output.lower() or "Error" in result.output

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.install.side_effect = HelmError("release exists", stderr="already exists")
        result = cli_runner.invoke(app, ["helm", "install", "rel", "chart"])
        assert result.exit_code == 1
        assert "Helm error" in result.output

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.install.side_effect = KubernetesError(message="connection refused")
        result = cli_runner.invoke(app, ["helm", "install", "rel", "chart"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmUpgrade:
    """Tests for helm upgrade command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "upgrade", "my-release", "bitnami/nginx"])
        assert result.exit_code == 0
        assert "Release upgraded" in result.output
        mock_helm_manager.upgrade.assert_called_once()

    def test_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app, ["helm", "upgrade", "my-release", "bitnami/nginx", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_install_flag(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "helm",
                "upgrade",
                "my-release",
                "bitnami/nginx",
                "--install",
                "--create-namespace",
            ],
        )
        assert result.exit_code == 0
        mock_helm_manager.upgrade.assert_called_once()
        call_kwargs = mock_helm_manager.upgrade.call_args
        assert call_kwargs.kwargs["install"] is True
        assert call_kwargs.kwargs["create_namespace"] is True

    def test_reuse_and_reset_values(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            ["helm", "upgrade", "my-release", "bitnami/nginx", "--reuse-values"],
        )
        assert result.exit_code == 0
        call_kwargs = mock_helm_manager.upgrade.call_args
        assert call_kwargs.kwargs["reuse_values"] is True

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.upgrade.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "upgrade", "rel", "chart"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.upgrade.side_effect = HelmError("failed")
        result = cli_runner.invoke(app, ["helm", "upgrade", "rel", "chart"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.upgrade.side_effect = KubernetesError(message="timeout")
        result = cli_runner.invoke(app, ["helm", "upgrade", "rel", "chart"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRollback:
    """Tests for helm rollback command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "rollback", "my-release"])
        assert result.exit_code == 0
        mock_helm_manager.rollback.assert_called_once_with(
            "my-release",
            None,
            namespace=None,
            wait=False,
            timeout=None,
            dry_run=False,
        )

    def test_with_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "rollback", "my-release", "3"])
        assert result.exit_code == 0
        mock_helm_manager.rollback.assert_called_once_with(
            "my-release",
            3,
            namespace=None,
            wait=False,
            timeout=None,
            dry_run=False,
        )

    def test_dry_run_with_wait(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "rollback", "my-release", "--dry-run", "--wait"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.rollback.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "rollback", "rel"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.rollback.side_effect = HelmError("no revision found")
        result = cli_runner.invoke(app, ["helm", "rollback", "rel"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.rollback.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["helm", "rollback", "rel"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmUninstall:
    """Tests for helm uninstall command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "uninstall", "my-release"])
        assert result.exit_code == 0
        mock_helm_manager.uninstall.assert_called_once_with(
            "my-release",
            namespace=None,
            keep_history=False,
            dry_run=False,
        )

    def test_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "uninstall", "my-release", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_keep_history(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "uninstall", "my-release", "--keep-history"])
        assert result.exit_code == 0
        mock_helm_manager.uninstall.assert_called_once_with(
            "my-release",
            namespace=None,
            keep_history=True,
            dry_run=False,
        )

    def test_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "uninstall", "my-release", "-n", "production"])
        assert result.exit_code == 0
        mock_helm_manager.uninstall.assert_called_once_with(
            "my-release",
            namespace="production",
            keep_history=False,
            dry_run=False,
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.uninstall.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "uninstall", "rel"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.uninstall.side_effect = HelmError("not found")
        result = cli_runner.invoke(app, ["helm", "uninstall", "rel"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.uninstall.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["helm", "uninstall", "rel"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmList:
    """Tests for helm list command."""

    def test_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 0
        assert "nginx" in result.output
        mock_helm_manager.list_releases.assert_called_once_with(
            namespace=None,
            all_namespaces=False,
            all_releases=False,
            filter_pattern=None,
        )

    def test_no_releases(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.list_releases.return_value = []
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 0
        assert "No releases found" in result.output

    def test_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "list", "--output", "json"])
        assert result.exit_code == 0

    def test_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "list", "-A"])
        assert result.exit_code == 0
        mock_helm_manager.list_releases.assert_called_once_with(
            namespace=None,
            all_namespaces=True,
            all_releases=False,
            filter_pattern=None,
        )

    def test_filter_pattern(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "list", "--filter", "my-*"])
        assert result.exit_code == 0
        mock_helm_manager.list_releases.assert_called_once_with(
            namespace=None,
            all_namespaces=False,
            all_releases=False,
            filter_pattern="my-*",
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.list_releases.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.list_releases.side_effect = HelmError("access denied")
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmHistory:
    """Tests for helm history command."""

    def test_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "history", "my-release"])
        assert result.exit_code == 0
        mock_helm_manager.history.assert_called_once_with(
            "my-release",
            namespace=None,
            max_revisions=None,
        )

    def test_no_history(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.history.return_value = []
        result = cli_runner.invoke(app, ["helm", "history", "my-release"])
        assert result.exit_code == 0
        assert "No history found" in result.output

    def test_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "history", "my-release", "--output", "json"])
        assert result.exit_code == 0

    def test_max_revisions(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "history", "my-release", "--max", "5"])
        assert result.exit_code == 0
        mock_helm_manager.history.assert_called_once_with(
            "my-release",
            namespace=None,
            max_revisions=5,
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.history.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "history", "rel"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.history.side_effect = HelmError("not found")
        result = cli_runner.invoke(app, ["helm", "history", "rel"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.history.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["helm", "history", "rel"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmStatus:
    """Tests for helm status command."""

    def test_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "status", "my-release"])
        assert result.exit_code == 0
        assert "nginx" in result.output
        mock_helm_manager.status.assert_called_once_with(
            "my-release",
            namespace=None,
            revision=None,
        )

    def test_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "status", "my-release", "--output", "json"])
        assert result.exit_code == 0

    def test_with_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "status", "my-release", "--revision", "3"])
        assert result.exit_code == 0
        mock_helm_manager.status.assert_called_once_with(
            "my-release",
            namespace=None,
            revision=3,
        )

    def test_status_without_notes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        from system_operations_manager.integrations.kubernetes.models.helm import (
            HelmReleaseStatus,
        )

        mock_helm_manager.status.return_value = HelmReleaseStatus(
            name="nginx",
            namespace="default",
            revision=1,
            status="deployed",
            description="Install complete",
            notes="",
            raw="",
        )
        result = cli_runner.invoke(app, ["helm", "status", "my-release"])
        assert result.exit_code == 0

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.status.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "status", "rel"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.status.side_effect = HelmError("not found")
        result = cli_runner.invoke(app, ["helm", "status", "rel"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmGetValues:
    """Tests for helm get-values command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "get-values", "my-release"])
        assert result.exit_code == 0
        assert "replicaCount" in result.output
        mock_helm_manager.get_values.assert_called_once_with(
            "my-release",
            namespace=None,
            all_values=False,
            revision=None,
        )

    def test_all_values(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "get-values", "my-release", "--all"])
        assert result.exit_code == 0
        mock_helm_manager.get_values.assert_called_once_with(
            "my-release",
            namespace=None,
            all_values=True,
            revision=None,
        )

    def test_with_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "get-values", "my-release", "--revision", "2"])
        assert result.exit_code == 0
        mock_helm_manager.get_values.assert_called_once_with(
            "my-release",
            namespace=None,
            all_values=False,
            revision=2,
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.get_values.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "get-values", "rel"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.get_values.side_effect = HelmError("not found")
        result = cli_runner.invoke(app, ["helm", "get-values", "rel"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.get_values.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["helm", "get-values", "rel"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmTemplate:
    """Tests for helm template command."""

    def test_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "template", "my-release", "bitnami/nginx"])
        assert result.exit_code == 0
        assert "apiVersion" in result.output
        mock_helm_manager.template.assert_called_once_with(
            "my-release",
            "bitnami/nginx",
            namespace=None,
            values_files=None,
            set_values=None,
            version=None,
        )

    def test_with_values(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "helm",
                "template",
                "my-release",
                "bitnami/nginx",
                "-f",
                "values.yaml",
                "--set",
                "replicaCount=2",
            ],
        )
        assert result.exit_code == 0
        mock_helm_manager.template.assert_called_once()

    def test_template_failure(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.template.return_value = HelmTemplateResult(
            rendered_yaml="",
            success=False,
            error="values validation failed",
        )
        result = cli_runner.invoke(app, ["helm", "template", "rel", "chart"])
        assert result.exit_code == 1
        assert "Template failed" in result.output

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.template.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "template", "rel", "chart"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.template.side_effect = HelmError("chart not found")
        result = cli_runner.invoke(app, ["helm", "template", "rel", "chart"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmSearch:
    """Tests for helm search command."""

    def test_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "search", "nginx"])
        assert result.exit_code == 0
        assert "nginx" in result.output
        mock_helm_manager.search_repo.assert_called_once_with(
            "nginx",
            version=None,
            all_versions=False,
        )

    def test_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.search_repo.return_value = []
        result = cli_runner.invoke(app, ["helm", "search", "nonexistent"])
        assert result.exit_code == 0
        assert "No charts found" in result.output

    def test_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "search", "nginx", "--output", "json"])
        assert result.exit_code == 0

    def test_all_versions(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "search", "nginx", "--versions"])
        assert result.exit_code == 0
        mock_helm_manager.search_repo.assert_called_once_with(
            "nginx",
            version=None,
            all_versions=True,
        )

    def test_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.search_repo.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "search", "nginx"])
        assert result.exit_code == 1

    def test_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.search_repo.side_effect = HelmError("no repos configured")
        result = cli_runner.invoke(app, ["helm", "search", "nginx"])
        assert result.exit_code == 1

    def test_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.search_repo.side_effect = KubernetesError(message="err")
        result = cli_runner.invoke(app, ["helm", "search", "nginx"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRepo:
    """Tests for helm repo subcommands."""

    def test_add_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app, ["helm", "repo", "add", "bitnami", "https://charts.bitnami.com/bitnami"]
        )
        assert result.exit_code == 0
        assert "added successfully" in result.output
        mock_helm_manager.repo_add.assert_called_once_with(
            "bitnami",
            "https://charts.bitnami.com/bitnami",
            force_update=False,
        )

    def test_add_force_update(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "helm",
                "repo",
                "add",
                "bitnami",
                "https://charts.bitnami.com/bitnami",
                "--force-update",
            ],
        )
        assert result.exit_code == 0
        mock_helm_manager.repo_add.assert_called_once_with(
            "bitnami",
            "https://charts.bitnami.com/bitnami",
            force_update=True,
        )

    def test_add_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_add.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "repo", "add", "r", "http://u"])
        assert result.exit_code == 1

    def test_add_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_add.side_effect = HelmError("already exists")
        result = cli_runner.invoke(app, ["helm", "repo", "add", "r", "http://u"])
        assert result.exit_code == 1

    def test_list_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "repo", "list"])
        assert result.exit_code == 0
        assert "bitnami" in result.output

    def test_list_no_repos(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_list.return_value = []
        result = cli_runner.invoke(app, ["helm", "repo", "list"])
        assert result.exit_code == 0
        assert "No repositories configured" in result.output

    def test_list_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "repo", "list", "--output", "json"])
        assert result.exit_code == 0

    def test_list_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_list.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "repo", "list"])
        assert result.exit_code == 1

    def test_update_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "repo", "update"])
        assert result.exit_code == 0
        assert "updated successfully" in result.output
        mock_helm_manager.repo_update.assert_called_once_with(None)

    def test_update_specific_repos(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "repo", "update", "bitnami", "stable"])
        assert result.exit_code == 0
        mock_helm_manager.repo_update.assert_called_once_with(["bitnami", "stable"])

    def test_update_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_update.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "repo", "update"])
        assert result.exit_code == 1

    def test_remove_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "repo", "remove", "bitnami"])
        assert result.exit_code == 0
        assert "removed" in result.output
        mock_helm_manager.repo_remove.assert_called_once_with("bitnami")

    def test_remove_binary_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_remove.side_effect = HelmBinaryNotFoundError()
        result = cli_runner.invoke(app, ["helm", "repo", "remove", "bitnami"])
        assert result.exit_code == 1

    def test_remove_helm_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        mock_helm_manager.repo_remove.side_effect = HelmError("repo not found")
        result = cli_runner.invoke(app, ["helm", "repo", "remove", "bitnami"])
        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmColorizeStatus:
    """Tests for _colorize_status helper via rendered table output."""

    def test_deployed_green(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 0
        assert "deployed" in result.output

    def test_failed_red(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        from system_operations_manager.integrations.kubernetes.models.helm import (
            HelmRelease,
        )

        mock_helm_manager.list_releases.return_value = [
            HelmRelease(
                name="bad",
                namespace="default",
                revision=1,
                status="failed",
                chart="app-1.0",
                app_version="1.0",
                updated="2024-01-01",
            ),
        ]
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 0
        assert "failed" in result.output

    def test_pending_yellow(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        from system_operations_manager.integrations.kubernetes.models.helm import (
            HelmRelease,
        )

        mock_helm_manager.list_releases.return_value = [
            HelmRelease(
                name="pending",
                namespace="default",
                revision=1,
                status="pending-install",
                chart="app-1.0",
                app_version="1.0",
                updated="2024-01-01",
            ),
        ]
        result = cli_runner.invoke(app, ["helm", "list"])
        assert result.exit_code == 0
        assert "pending-install" in result.output

    def test_superseded_dim(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_helm_manager: MagicMock,
    ) -> None:
        from system_operations_manager.integrations.kubernetes.models.helm import (
            HelmReleaseHistory,
        )

        mock_helm_manager.history.return_value = [
            HelmReleaseHistory(
                revision=1,
                status="superseded",
                chart="app-1.0",
                app_version="1.0",
                description="Superseded by 2",
                updated="2024-01-01",
            ),
        ]
        result = cli_runner.invoke(app, ["helm", "history", "my-release"])
        assert result.exit_code == 0
        assert "superseded" in result.output
