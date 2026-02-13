"""Unit tests for HelmClient."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.helm_client import (
    HelmBinaryNotFoundError,
    HelmClient,
    HelmCommandError,
    HelmError,
)


@pytest.fixture
def helm_client() -> HelmClient:
    """Create a HelmClient with mocked binary detection."""
    with patch("shutil.which", return_value="/usr/local/bin/helm"):
        return HelmClient()


# ===========================================================================
# TestInit
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestInit:
    """Tests for HelmClient initialization."""

    def test_finds_binary_in_path(self) -> None:
        """Should find helm binary in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/helm"):
            client = HelmClient()
            assert client._binary == "/usr/local/bin/helm"

    def test_raises_when_binary_not_found(self) -> None:
        """Should raise HelmBinaryNotFoundError if not in PATH."""
        with patch("shutil.which", return_value=None), pytest.raises(HelmBinaryNotFoundError):
            HelmClient()

    def test_uses_explicit_binary_path(self, tmp_path: Path) -> None:
        """Should use explicit binary path when provided."""
        fake_binary = tmp_path / "helm"
        fake_binary.touch()

        client = HelmClient(binary_path=str(fake_binary))
        assert client._binary == str(fake_binary.resolve())

    def test_raises_when_explicit_path_not_found(self) -> None:
        """Should raise when explicit binary path does not exist."""
        with pytest.raises(HelmBinaryNotFoundError):
            HelmClient(binary_path="/nonexistent/helm")


# ===========================================================================
# TestGetVersion
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetVersion:
    """Tests for HelmClient.get_version."""

    @patch("subprocess.run")
    def test_parses_version_string(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse version from helm output."""
        mock_run.return_value = MagicMock(stdout="v3.17.0+g301108e\n", returncode=0)

        version = helm_client.get_version()

        assert version == "v3.17.0"

    @patch("subprocess.run")
    def test_handles_clean_version_string(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should handle version without build metadata."""
        mock_run.return_value = MagicMock(stdout="v3.17.0\n", returncode=0)

        version = helm_client.get_version()

        assert version == "v3.17.0"

    @patch("subprocess.run")
    def test_raises_on_failure(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should raise HelmCommandError on command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["helm", "version"], stderr="error"
        )

        with pytest.raises(HelmCommandError):
            helm_client.get_version()

    @patch("subprocess.run")
    def test_raises_on_timeout(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should raise HelmError on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["helm"], timeout=10)

        with pytest.raises(HelmError, match="timed out"):
            helm_client.get_version()


# ===========================================================================
# TestInstall
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestInstall:
    """Tests for HelmClient.install."""

    @patch("subprocess.run")
    def test_install_basic(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should run basic install command."""
        mock_run.return_value = MagicMock(stdout="NAME: my-release\n", stderr="", returncode=0)

        result = helm_client.install("my-release", "bitnami/nginx")

        assert result.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd[1:3] == ["install", "my-release"]
        assert "bitnami/nginx" in cmd

    @patch("subprocess.run")
    def test_install_with_namespace(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --namespace flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install("my-release", "bitnami/nginx", namespace="production")

        cmd = mock_run.call_args[0][0]
        assert "--namespace" in cmd
        ns_idx = cmd.index("--namespace")
        assert cmd[ns_idx + 1] == "production"

    @patch("subprocess.run")
    def test_install_with_values_files(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --values flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install(
            "my-release", "bitnami/nginx", values_files=["values.yaml", "values-prod.yaml"]
        )

        cmd = mock_run.call_args[0][0]
        values_indices = [i for i, v in enumerate(cmd) if v == "--values"]
        assert len(values_indices) == 2

    @patch("subprocess.run")
    def test_install_with_set_values(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --set flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install("my-release", "bitnami/nginx", set_values=["key1=val1", "key2=val2"])

        cmd = mock_run.call_args[0][0]
        set_indices = [i for i, v in enumerate(cmd) if v == "--set"]
        assert len(set_indices) == 2

    @patch("subprocess.run")
    def test_install_with_create_namespace(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should pass --create-namespace flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install("my-release", "bitnami/nginx", create_namespace=True)

        cmd = mock_run.call_args[0][0]
        assert "--create-namespace" in cmd

    @patch("subprocess.run")
    def test_install_with_dry_run(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --dry-run flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install("my-release", "bitnami/nginx", dry_run=True)

        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd

    @patch("subprocess.run")
    def test_install_with_wait_and_timeout(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should pass --wait and --timeout flags."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.install("my-release", "bitnami/nginx", wait=True, timeout="5m0s")

        cmd = mock_run.call_args[0][0]
        assert "--wait" in cmd
        assert "--timeout" in cmd
        timeout_idx = cmd.index("--timeout")
        assert cmd[timeout_idx + 1] == "5m0s"

    @patch("subprocess.run")
    def test_install_failure(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should raise HelmCommandError on install failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["helm", "install"],
            stderr="Error: cannot re-use a name that is still in use",
        )

        with pytest.raises(HelmCommandError, match="cannot re-use"):
            helm_client.install("my-release", "bitnami/nginx")


# ===========================================================================
# TestUpgrade
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestUpgrade:
    """Tests for HelmClient.upgrade."""

    @patch("subprocess.run")
    def test_upgrade_basic(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should run basic upgrade command."""
        mock_run.return_value = MagicMock(stdout="Release upgraded\n", stderr="", returncode=0)

        result = helm_client.upgrade("my-release", "bitnami/nginx")

        assert result.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd[1:3] == ["upgrade", "my-release"]

    @patch("subprocess.run")
    def test_upgrade_with_install(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --install flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.upgrade("my-release", "bitnami/nginx", install=True)

        cmd = mock_run.call_args[0][0]
        assert "--install" in cmd

    @patch("subprocess.run")
    def test_upgrade_with_reuse_values(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --reuse-values flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.upgrade("my-release", "bitnami/nginx", reuse_values=True)

        cmd = mock_run.call_args[0][0]
        assert "--reuse-values" in cmd

    @patch("subprocess.run")
    def test_upgrade_with_reset_values(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --reset-values flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.upgrade("my-release", "bitnami/nginx", reset_values=True)

        cmd = mock_run.call_args[0][0]
        assert "--reset-values" in cmd


# ===========================================================================
# TestRollback
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRollback:
    """Tests for HelmClient.rollback."""

    @patch("subprocess.run")
    def test_rollback_to_previous(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should rollback without specifying revision."""
        mock_run.return_value = MagicMock(
            stdout="Rollback was a success!\n", stderr="", returncode=0
        )

        result = helm_client.rollback("my-release")

        assert result.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd[1:3] == ["rollback", "my-release"]

    @patch("subprocess.run")
    def test_rollback_to_specific_revision(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should rollback to a specific revision."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.rollback("my-release", 3, namespace="production")

        cmd = mock_run.call_args[0][0]
        assert "3" in cmd
        assert "--namespace" in cmd


# ===========================================================================
# TestUninstall
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestUninstall:
    """Tests for HelmClient.uninstall."""

    @patch("subprocess.run")
    def test_uninstall_basic(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should run basic uninstall command."""
        mock_run.return_value = MagicMock(
            stdout='release "my-release" uninstalled\n', stderr="", returncode=0
        )

        result = helm_client.uninstall("my-release")

        assert result.success is True

    @patch("subprocess.run")
    def test_uninstall_with_keep_history(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should pass --keep-history flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.uninstall("my-release", keep_history=True)

        cmd = mock_run.call_args[0][0]
        assert "--keep-history" in cmd


# ===========================================================================
# TestListReleases
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestListReleases:
    """Tests for HelmClient.list_releases."""

    @patch("subprocess.run")
    def test_list_releases(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse release list from JSON output."""
        releases_json = json.dumps(
            [
                {
                    "name": "my-release",
                    "namespace": "default",
                    "revision": "1",
                    "status": "deployed",
                    "chart": "nginx-18.0.0",
                    "app_version": "1.25.0",
                    "updated": "2026-01-01 00:00:00",
                },
            ]
        )
        mock_run.return_value = MagicMock(stdout=releases_json, returncode=0)

        releases = helm_client.list_releases()

        assert len(releases) == 1
        assert releases[0].name == "my-release"
        assert releases[0].status == "deployed"

    @patch("subprocess.run")
    def test_list_releases_all_namespaces(
        self, mock_run: MagicMock, helm_client: HelmClient
    ) -> None:
        """Should pass --all-namespaces flag."""
        mock_run.return_value = MagicMock(stdout="[]", returncode=0)

        helm_client.list_releases(all_namespaces=True)

        cmd = mock_run.call_args[0][0]
        assert "--all-namespaces" in cmd

    @patch("subprocess.run")
    def test_list_releases_with_filter(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --filter flag."""
        mock_run.return_value = MagicMock(stdout="[]", returncode=0)

        helm_client.list_releases(filter_pattern="my-*")

        cmd = mock_run.call_args[0][0]
        assert "--filter" in cmd
        filter_idx = cmd.index("--filter")
        assert cmd[filter_idx + 1] == "my-*"

    @patch("subprocess.run")
    def test_list_releases_empty(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should return empty list when no releases."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        releases = helm_client.list_releases()

        assert releases == []


# ===========================================================================
# TestHistory
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHistory:
    """Tests for HelmClient.history."""

    @patch("subprocess.run")
    def test_history_returns_entries(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse history entries from JSON output."""
        history_json = json.dumps(
            [
                {
                    "revision": 1,
                    "status": "superseded",
                    "chart": "nginx-18.0.0",
                    "app_version": "1.25.0",
                    "description": "Install complete",
                    "updated": "2026-01-01 00:00:00",
                },
                {
                    "revision": 2,
                    "status": "deployed",
                    "chart": "nginx-18.1.0",
                    "app_version": "1.25.1",
                    "description": "Upgrade complete",
                    "updated": "2026-01-02 00:00:00",
                },
            ]
        )
        mock_run.return_value = MagicMock(stdout=history_json, returncode=0)

        entries = helm_client.history("my-release")

        assert len(entries) == 2
        assert entries[0].revision == 1
        assert entries[1].status == "deployed"

    @patch("subprocess.run")
    def test_history_with_max(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --max flag."""
        mock_run.return_value = MagicMock(stdout="[]", returncode=0)

        helm_client.history("my-release", max_revisions=5)

        cmd = mock_run.call_args[0][0]
        assert "--max" in cmd
        max_idx = cmd.index("--max")
        assert cmd[max_idx + 1] == "5"


# ===========================================================================
# TestStatus
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatus:
    """Tests for HelmClient.status."""

    @patch("subprocess.run")
    def test_status_returns_details(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse status details from JSON output."""
        status_json = json.dumps(
            {
                "name": "my-release",
                "namespace": "default",
                "version": 2,
                "info": {
                    "status": "deployed",
                    "description": "Upgrade complete",
                    "notes": "Access the application at http://localhost:8080",
                },
            }
        )
        mock_run.return_value = MagicMock(stdout=status_json, returncode=0)

        status = helm_client.status("my-release")

        assert status.name == "my-release"
        assert status.revision == 2
        assert status.status == "deployed"
        assert "localhost" in status.notes


# ===========================================================================
# TestGetValues
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetValues:
    """Tests for HelmClient.get_values."""

    @patch("subprocess.run")
    def test_get_values(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should return YAML values string."""
        mock_run.return_value = MagicMock(
            stdout="replicaCount: 2\nimage:\n  tag: latest\n", returncode=0
        )

        values = helm_client.get_values("my-release")

        assert "replicaCount: 2" in values

    @patch("subprocess.run")
    def test_get_values_all(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --all flag."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        helm_client.get_values("my-release", all_values=True)

        cmd = mock_run.call_args[0][0]
        assert "--all" in cmd


# ===========================================================================
# TestRepoManagement
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRepoManagement:
    """Tests for Helm repository management."""

    @patch("subprocess.run")
    def test_repo_add(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should add a repository."""
        mock_run.return_value = MagicMock(
            stdout='"bitnami" has been added\n', stderr="", returncode=0
        )

        result = helm_client.repo_add("bitnami", "https://charts.bitnami.com/bitnami")

        assert result.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd[1:4] == ["repo", "add", "bitnami"]

    @patch("subprocess.run")
    def test_repo_add_force_update(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --force-update flag."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.repo_add("bitnami", "https://charts.bitnami.com/bitnami", force_update=True)

        cmd = mock_run.call_args[0][0]
        assert "--force-update" in cmd

    @patch("subprocess.run")
    def test_repo_list(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse repo list from JSON output."""
        repos_json = json.dumps(
            [
                {"name": "bitnami", "url": "https://charts.bitnami.com/bitnami"},
                {"name": "stable", "url": "https://charts.helm.sh/stable"},
            ]
        )
        mock_run.return_value = MagicMock(stdout=repos_json, returncode=0)

        repos = helm_client.repo_list()

        assert len(repos) == 2
        assert repos[0].name == "bitnami"
        assert repos[1].url == "https://charts.helm.sh/stable"

    @patch("subprocess.run")
    def test_repo_update(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should update all repos."""
        mock_run.return_value = MagicMock(stdout="Update Complete.\n", stderr="", returncode=0)

        result = helm_client.repo_update()

        assert result.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd[1:3] == ["repo", "update"]

    @patch("subprocess.run")
    def test_repo_update_specific(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should update specific repos."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        helm_client.repo_update(names=["bitnami"])

        cmd = mock_run.call_args[0][0]
        assert "bitnami" in cmd

    @patch("subprocess.run")
    def test_repo_remove(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should remove a repository."""
        mock_run.return_value = MagicMock(
            stdout='"bitnami" has been removed\n', stderr="", returncode=0
        )

        result = helm_client.repo_remove("bitnami")

        assert result.success is True


# ===========================================================================
# TestTemplate
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestTemplate:
    """Tests for HelmClient.template."""

    @patch("subprocess.run")
    def test_template_success(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should return rendered YAML."""
        rendered = "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-release-nginx\n"
        mock_run.return_value = MagicMock(stdout=rendered, returncode=0)

        result = helm_client.template("my-release", "bitnami/nginx")

        assert result.success is True
        assert "Service" in result.rendered_yaml

    @patch("subprocess.run")
    def test_template_failure(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should return error result on failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["helm", "template"], stderr="Error: chart not found"
        )

        result = helm_client.template("my-release", "nonexistent/chart")

        assert result.success is False
        assert result.error is not None

    @patch("subprocess.run")
    def test_template_with_values(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass values and set flags."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        helm_client.template(
            "my-release",
            "bitnami/nginx",
            namespace="production",
            values_files=["values.yaml"],
            set_values=["key=val"],
            version="18.0.0",
        )

        cmd = mock_run.call_args[0][0]
        assert "--namespace" in cmd
        assert "--values" in cmd
        assert "--set" in cmd
        assert "--version" in cmd


# ===========================================================================
# TestSearchRepo
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSearchRepo:
    """Tests for HelmClient.search_repo."""

    @patch("subprocess.run")
    def test_search_returns_charts(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should parse search results."""
        charts_json = json.dumps(
            [
                {
                    "name": "bitnami/nginx",
                    "version": "18.0.0",
                    "app_version": "1.25.0",
                    "description": "NGINX Open Source web server",
                },
            ]
        )
        mock_run.return_value = MagicMock(stdout=charts_json, returncode=0)

        charts = helm_client.search_repo("nginx")

        assert len(charts) == 1
        assert charts[0].name == "bitnami/nginx"
        assert charts[0].chart_version == "18.0.0"

    @patch("subprocess.run")
    def test_search_all_versions(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should pass --versions flag."""
        mock_run.return_value = MagicMock(stdout="[]", returncode=0)

        helm_client.search_repo("nginx", all_versions=True)

        cmd = mock_run.call_args[0][0]
        assert "--versions" in cmd

    @patch("subprocess.run")
    def test_search_empty_results(self, mock_run: MagicMock, helm_client: HelmClient) -> None:
        """Should return empty list when no matches."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        charts = helm_client.search_repo("nonexistent")

        assert charts == []
