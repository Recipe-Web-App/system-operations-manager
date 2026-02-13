"""Unit tests for HelmManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.helm import (
    HelmChart,
    HelmCommandResult,
    HelmReleaseHistory,
    HelmReleaseStatus,
    HelmRepo,
    HelmTemplateResult,
)
from system_operations_manager.services.kubernetes.helm_manager import HelmManager


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def mock_helm_client() -> MagicMock:
    """Create a mock HelmClient."""
    return MagicMock()


@pytest.fixture
def helm_manager(
    mock_k8s_client: MagicMock,
    mock_helm_client: MagicMock,
) -> HelmManager:
    """Create a HelmManager with mocked clients."""
    return HelmManager(mock_k8s_client, mock_helm_client)


# ===========================================================================
# TestInstall
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestInstall:
    """Tests for HelmManager.install."""

    def test_install_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate install to HelmClient."""
        mock_helm_client.install.return_value = HelmCommandResult(
            success=True, stdout="Installed", stderr=""
        )

        result = helm_manager.install("my-release", "bitnami/nginx")

        assert result.success is True
        mock_helm_client.install.assert_called_once()

    def test_install_resolves_namespace(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should resolve namespace to default when not specified."""
        mock_helm_client.install.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.install("my-release", "bitnami/nginx")

        call_kwargs = mock_helm_client.install.call_args.kwargs
        assert call_kwargs["namespace"] == "default"

    def test_install_uses_explicit_namespace(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should use explicit namespace when provided."""
        mock_helm_client.install.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.install("my-release", "bitnami/nginx", namespace="production")

        call_kwargs = mock_helm_client.install.call_args.kwargs
        assert call_kwargs["namespace"] == "production"

    def test_install_passes_all_options(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass all options to client."""
        mock_helm_client.install.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.install(
            "my-release",
            "bitnami/nginx",
            namespace="prod",
            values_files=["values.yaml"],
            set_values=["key=val"],
            version="18.0.0",
            create_namespace=True,
            wait=True,
            timeout="5m0s",
            dry_run=True,
        )

        call_kwargs = mock_helm_client.install.call_args.kwargs
        assert call_kwargs["values_files"] == ["values.yaml"]
        assert call_kwargs["set_values"] == ["key=val"]
        assert call_kwargs["version"] == "18.0.0"
        assert call_kwargs["create_namespace"] is True
        assert call_kwargs["wait"] is True
        assert call_kwargs["timeout"] == "5m0s"
        assert call_kwargs["dry_run"] is True


# ===========================================================================
# TestUpgrade
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestUpgrade:
    """Tests for HelmManager.upgrade."""

    def test_upgrade_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate upgrade to HelmClient."""
        mock_helm_client.upgrade.return_value = HelmCommandResult(
            success=True, stdout="Upgraded", stderr=""
        )

        result = helm_manager.upgrade("my-release", "bitnami/nginx")

        assert result.success is True
        mock_helm_client.upgrade.assert_called_once()

    def test_upgrade_passes_install_flag(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass install flag to client."""
        mock_helm_client.upgrade.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.upgrade("my-release", "bitnami/nginx", install=True)

        call_kwargs = mock_helm_client.upgrade.call_args.kwargs
        assert call_kwargs["install"] is True

    def test_upgrade_passes_reuse_values(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass reuse_values flag to client."""
        mock_helm_client.upgrade.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.upgrade("my-release", "bitnami/nginx", reuse_values=True)

        call_kwargs = mock_helm_client.upgrade.call_args.kwargs
        assert call_kwargs["reuse_values"] is True


# ===========================================================================
# TestRollback
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRollback:
    """Tests for HelmManager.rollback."""

    def test_rollback_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate rollback to HelmClient."""
        mock_helm_client.rollback.return_value = HelmCommandResult(
            success=True, stdout="Rollback was a success!", stderr=""
        )

        result = helm_manager.rollback("my-release", 3)

        assert result.success is True
        mock_helm_client.rollback.assert_called_once_with(
            "my-release",
            3,
            namespace="default",
            wait=False,
            timeout=None,
            dry_run=False,
        )


# ===========================================================================
# TestUninstall
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestUninstall:
    """Tests for HelmManager.uninstall."""

    def test_uninstall_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate uninstall to HelmClient."""
        mock_helm_client.uninstall.return_value = HelmCommandResult(
            success=True, stdout="release uninstalled", stderr=""
        )

        result = helm_manager.uninstall("my-release")

        assert result.success is True
        mock_helm_client.uninstall.assert_called_once()

    def test_uninstall_passes_keep_history(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass keep_history to client."""
        mock_helm_client.uninstall.return_value = HelmCommandResult(
            success=True, stdout="", stderr=""
        )

        helm_manager.uninstall("my-release", keep_history=True)

        call_kwargs = mock_helm_client.uninstall.call_args.kwargs
        assert call_kwargs["keep_history"] is True


# ===========================================================================
# TestListReleases
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestListReleases:
    """Tests for HelmManager.list_releases."""

    def test_list_releases_resolves_namespace(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should resolve namespace for listing."""
        mock_helm_client.list_releases.return_value = []

        helm_manager.list_releases()

        call_kwargs = mock_helm_client.list_releases.call_args.kwargs
        assert call_kwargs["namespace"] == "default"

    def test_list_releases_all_namespaces_skips_resolve(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should not resolve namespace when all_namespaces=True."""
        mock_helm_client.list_releases.return_value = []

        helm_manager.list_releases(all_namespaces=True)

        call_kwargs = mock_helm_client.list_releases.call_args.kwargs
        assert call_kwargs["namespace"] is None
        assert call_kwargs["all_namespaces"] is True

    def test_list_releases_passes_filter(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass filter_pattern to client."""
        mock_helm_client.list_releases.return_value = []

        helm_manager.list_releases(filter_pattern="my-*")

        call_kwargs = mock_helm_client.list_releases.call_args.kwargs
        assert call_kwargs["filter_pattern"] == "my-*"


# ===========================================================================
# TestHistory
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHistory:
    """Tests for HelmManager.history."""

    def test_history_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate history to HelmClient."""
        mock_helm_client.history.return_value = [
            HelmReleaseHistory(
                revision=1,
                status="deployed",
                chart="nginx-18.0.0",
                app_version="1.25.0",
                description="Install complete",
                updated="2026-01-01",
            ),
        ]

        entries = helm_manager.history("my-release")

        assert len(entries) == 1
        assert entries[0].revision == 1
        mock_helm_client.history.assert_called_once()


# ===========================================================================
# TestStatus
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatus:
    """Tests for HelmManager.status."""

    def test_status_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate status to HelmClient."""
        mock_helm_client.status.return_value = HelmReleaseStatus(
            name="my-release",
            namespace="default",
            revision=1,
            status="deployed",
            description="Install complete",
        )

        status = helm_manager.status("my-release")

        assert status.name == "my-release"
        assert status.status == "deployed"


# ===========================================================================
# TestGetValues
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetValues:
    """Tests for HelmManager.get_values."""

    def test_get_values_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate get_values to HelmClient."""
        mock_helm_client.get_values.return_value = "replicaCount: 2\n"

        values = helm_manager.get_values("my-release")

        assert "replicaCount: 2" in values

    def test_get_values_passes_all_values(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should pass all_values flag to client."""
        mock_helm_client.get_values.return_value = ""

        helm_manager.get_values("my-release", all_values=True)

        call_kwargs = mock_helm_client.get_values.call_args.kwargs
        assert call_kwargs["all_values"] is True


# ===========================================================================
# TestRepoManagement
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRepoManagement:
    """Tests for HelmManager repository operations."""

    def test_repo_add(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate repo_add to HelmClient."""
        mock_helm_client.repo_add.return_value = HelmCommandResult(
            success=True, stdout="added", stderr=""
        )

        result = helm_manager.repo_add("bitnami", "https://charts.bitnami.com/bitnami")

        assert result.success is True
        mock_helm_client.repo_add.assert_called_once()

    def test_repo_list(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate repo_list to HelmClient."""
        mock_helm_client.repo_list.return_value = [
            HelmRepo(name="bitnami", url="https://charts.bitnami.com/bitnami"),
        ]

        repos = helm_manager.repo_list()

        assert len(repos) == 1
        assert repos[0].name == "bitnami"

    def test_repo_update(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate repo_update to HelmClient."""
        mock_helm_client.repo_update.return_value = HelmCommandResult(
            success=True, stdout="updated", stderr=""
        )

        result = helm_manager.repo_update()

        assert result.success is True

    def test_repo_remove(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate repo_remove to HelmClient."""
        mock_helm_client.repo_remove.return_value = HelmCommandResult(
            success=True, stdout="removed", stderr=""
        )

        result = helm_manager.repo_remove("bitnami")

        assert result.success is True


# ===========================================================================
# TestTemplate
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestTemplate:
    """Tests for HelmManager.template."""

    def test_template_resolves_namespace(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should resolve namespace for template rendering."""
        mock_helm_client.template.return_value = HelmTemplateResult(
            rendered_yaml="apiVersion: v1\n", success=True
        )

        helm_manager.template("my-release", "bitnami/nginx")

        call_kwargs = mock_helm_client.template.call_args.kwargs
        assert call_kwargs["namespace"] == "default"


# ===========================================================================
# TestSearchRepo
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSearchRepo:
    """Tests for HelmManager.search_repo."""

    def test_search_delegates_to_client(
        self,
        helm_manager: HelmManager,
        mock_helm_client: MagicMock,
    ) -> None:
        """Should delegate search to HelmClient."""
        mock_helm_client.search_repo.return_value = [
            HelmChart(
                name="bitnami/nginx",
                chart_version="18.0.0",
                app_version="1.25.0",
                description="NGINX",
            ),
        ]

        charts = helm_manager.search_repo("nginx")

        assert len(charts) == 1
        assert charts[0].name == "bitnami/nginx"
