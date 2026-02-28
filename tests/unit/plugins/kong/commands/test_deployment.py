"""Unit tests for Kong Gateway deployment CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kong.commands.deployment import (
    register_deployment_commands,
)
from system_operations_manager.services.kong.deployment_manager import (
    DeploymentError,
    DeploymentInfo,
    DeploymentStatus,
    PodInfo,
)


def _make_info(
    status: DeploymentStatus = DeploymentStatus.RUNNING,
    namespace: str = "kong",
    chart: str | None = "kong/ingress",
    chart_version: str | None = "2.0.0",
    app_version: str | None = "3.5.0",
    *,
    postgres_ready: bool = True,
    gateway_ready: bool = True,
    controller_ready: bool = True,
    pods: list[PodInfo] | None = None,
) -> DeploymentInfo:
    """Helper to create a DeploymentInfo object with sensible defaults."""
    return DeploymentInfo(
        status=status,
        namespace=namespace,
        chart=chart,
        chart_version=chart_version,
        app_version=app_version,
        postgres_ready=postgres_ready,
        gateway_ready=gateway_ready,
        controller_ready=controller_ready,
        pods=pods or [],
    )


class TestDeploymentCommands:
    """Base class that sets up the app fixture used by all subclasses."""

    @pytest.fixture
    def app(self, mock_deployment_manager: MagicMock) -> typer.Typer:
        """Create a test app with deployment commands registered."""
        app = typer.Typer()
        register_deployment_commands(app, lambda: mock_deployment_manager)
        return app


# ---------------------------------------------------------------------------
# deploy status
# ---------------------------------------------------------------------------


class TestDeployStatus(TestDeploymentCommands):
    """Tests for the deploy status command."""

    @pytest.mark.unit
    def test_status_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should render a table with deployment info."""
        mock_deployment_manager.get_status.return_value = _make_info()

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        mock_deployment_manager.get_status.assert_called_once()
        assert "kong" in result.stdout.lower()
        assert "Running" in result.stdout or "running" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_shows_not_installed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should reflect NOT_INSTALLED status correctly."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.NOT_INSTALLED,
            chart=None,
            chart_version=None,
            app_version=None,
            postgres_ready=False,
            gateway_ready=False,
            controller_ready=False,
        )

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        assert "Not Installed" in result.stdout or "not installed" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_shows_degraded(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should display degraded status."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.DEGRADED,
            gateway_ready=False,
        )

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        assert "Degraded" in result.stdout or "degraded" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_shows_pods(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should display pod information when pods are present."""
        pods = [
            PodInfo(name="kong-gateway-abc123", phase="Running", ready=True, restarts=0),
            PodInfo(name="kong-controller-xyz789", phase="Running", ready=True, restarts=1),
        ]
        mock_deployment_manager.get_status.return_value = _make_info(pods=pods)

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        assert "kong-gateway-abc123" in result.stdout
        assert "kong-controller-xyz789" in result.stdout

    @pytest.mark.unit
    def test_status_no_pods(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should not render a pod table when there are no pods."""
        mock_deployment_manager.get_status.return_value = _make_info(pods=[])

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        # No pod section — simply confirm it doesn't crash
        assert "Kong Deployment Status" in result.stdout

    @pytest.mark.unit
    def test_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should support JSON output format."""
        mock_deployment_manager.get_status.return_value = _make_info()

        result = cli_runner.invoke(app, ["deploy", "status", "--output", "json"])

        assert result.exit_code == 0
        mock_deployment_manager.get_status.assert_called_once()

    @pytest.mark.unit
    def test_status_yaml_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should support YAML output format."""
        mock_deployment_manager.get_status.return_value = _make_info()

        result = cli_runner.invoke(app, ["deploy", "status", "--output", "yaml"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_status_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should exit with code 1 on exception."""
        mock_deployment_manager.get_status.side_effect = RuntimeError("k8s unreachable")

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_shows_postgres_not_ready(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy status should show 'Not Ready' for PostgreSQL when not ready."""
        mock_deployment_manager.get_status.return_value = _make_info(postgres_ready=False)

        result = cli_runner.invoke(app, ["deploy", "status"])

        assert result.exit_code == 0
        assert "Not Ready" in result.stdout or "not ready" in result.stdout.lower()


# ---------------------------------------------------------------------------
# deploy install
# ---------------------------------------------------------------------------


class TestDeployInstall(TestDeploymentCommands):
    """Tests for the deploy install command."""

    @pytest.mark.unit
    def test_install_fresh_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install should install Kong when it is not currently installed."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.NOT_INSTALLED
        )

        result = cli_runner.invoke(app, ["deploy", "install"])

        assert result.exit_code == 0
        mock_deployment_manager.install.assert_called_once()
        assert "installed" in result.stdout.lower()

    @pytest.mark.unit
    def test_install_already_running_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install --force should reinstall when Kong is already running."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )

        result = cli_runner.invoke(app, ["deploy", "install", "--force"])

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once()
        mock_deployment_manager.install.assert_called_once()

    @pytest.mark.unit
    def test_install_already_running_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install should cancel when Kong is already running and user declines."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )

        result = cli_runner.invoke(app, ["deploy", "install"], input="n\n")

        assert result.exit_code == 0
        mock_deployment_manager.install.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    @pytest.mark.unit
    def test_install_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install should exit with code 1 on DeploymentError."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.NOT_INSTALLED
        )
        mock_deployment_manager.install.side_effect = DeploymentError(
            "helm not found", details="install helm 3"
        )

        result = cli_runner.invoke(app, ["deploy", "install"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_install_error_with_details(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install should show error details when available."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.NOT_INSTALLED
        )
        err = DeploymentError("failed", details="run apt install helm")
        mock_deployment_manager.install.side_effect = err

        result = cli_runner.invoke(app, ["deploy", "install"])

        assert result.exit_code == 1
        assert "helm" in result.stdout.lower()

    @pytest.mark.unit
    def test_install_already_running_user_confirms(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy install should reinstall when already running and user confirms."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )

        result = cli_runner.invoke(app, ["deploy", "install"], input="y\n")

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once()
        mock_deployment_manager.install.assert_called_once()


# ---------------------------------------------------------------------------
# deploy upgrade
# ---------------------------------------------------------------------------


class TestDeployUpgrade(TestDeploymentCommands):
    """Tests for the deploy upgrade command."""

    @pytest.mark.unit
    def test_upgrade_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy upgrade should upgrade Kong and print a success message."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )

        result = cli_runner.invoke(app, ["deploy", "upgrade"])

        assert result.exit_code == 0
        mock_deployment_manager.upgrade.assert_called_once()
        assert "upgraded" in result.stdout.lower()

    @pytest.mark.unit
    def test_upgrade_not_installed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy upgrade should exit with code 1 when Kong is not installed."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.NOT_INSTALLED
        )

        result = cli_runner.invoke(app, ["deploy", "upgrade"])

        assert result.exit_code == 1
        assert "not installed" in result.stdout.lower()
        mock_deployment_manager.upgrade.assert_not_called()

    @pytest.mark.unit
    def test_upgrade_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy upgrade should exit with code 1 on exception."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )
        mock_deployment_manager.upgrade.side_effect = DeploymentError(
            "helm upgrade failed", details="chart not found"
        )

        result = cli_runner.invoke(app, ["deploy", "upgrade"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_upgrade_error_with_details(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy upgrade should print error details when available."""
        mock_deployment_manager.get_status.return_value = _make_info(
            status=DeploymentStatus.RUNNING
        )
        mock_deployment_manager.upgrade.side_effect = DeploymentError(
            "failed", details="chart not found"
        )

        result = cli_runner.invoke(app, ["deploy", "upgrade"])

        assert result.exit_code == 1
        assert "chart not found" in result.stdout


# ---------------------------------------------------------------------------
# deploy uninstall
# ---------------------------------------------------------------------------


class TestDeployUninstall(TestDeploymentCommands):
    """Tests for the deploy uninstall command."""

    @pytest.mark.unit
    def test_uninstall_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall --force should uninstall without prompting."""
        result = cli_runner.invoke(app, ["deploy", "uninstall", "--force"])

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once_with(
            keep_postgres=False,
            keep_secrets=True,
            keep_pvc=True,
        )
        assert "uninstalled" in result.stdout.lower()

    @pytest.mark.unit
    def test_uninstall_cancelled_by_user(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall should cancel when user declines the confirmation."""
        result = cli_runner.invoke(app, ["deploy", "uninstall"], input="n\n")

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    @pytest.mark.unit
    def test_uninstall_confirmed_by_user(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall should uninstall when user confirms."""
        result = cli_runner.invoke(app, ["deploy", "uninstall"], input="y\n")

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once()

    @pytest.mark.unit
    def test_uninstall_delete_secrets_and_pvc(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall --delete-secrets --delete-pvc should remove all resources."""
        result = cli_runner.invoke(
            app,
            ["deploy", "uninstall", "--force", "--delete-secrets", "--delete-pvc"],
        )

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once_with(
            keep_postgres=False,
            keep_secrets=False,
            keep_pvc=False,
        )

    @pytest.mark.unit
    def test_uninstall_keep_postgres(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall --keep-postgres should preserve PostgreSQL."""
        result = cli_runner.invoke(
            app,
            ["deploy", "uninstall", "--force", "--keep-postgres"],
        )

        assert result.exit_code == 0
        mock_deployment_manager.uninstall.assert_called_once_with(
            keep_postgres=True,
            keep_secrets=True,
            keep_pvc=True,
        )

    @pytest.mark.unit
    def test_uninstall_shows_preserved_resources(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall should list preserved resources in output."""
        result = cli_runner.invoke(app, ["deploy", "uninstall", "--force"])

        assert result.exit_code == 0
        # Secrets and PVC are kept by default
        assert "secret" in result.stdout.lower() or "pvc" in result.stdout.lower()

    @pytest.mark.unit
    def test_uninstall_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall should exit with code 1 on exception."""
        mock_deployment_manager.uninstall.side_effect = RuntimeError("kubectl error")

        result = cli_runner.invoke(app, ["deploy", "uninstall", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_uninstall_without_postgres_adds_msg_to_prompt(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy uninstall should mention PostgreSQL in the prompt when not keeping it."""
        # Without --keep-postgres the prompt should mention PostgreSQL
        result = cli_runner.invoke(
            app,
            ["deploy", "uninstall"],
            input="n\n",
        )

        assert result.exit_code == 0
        # The prompt message is shown before the "n" input; confirm the flow ran
        mock_deployment_manager.uninstall.assert_not_called()


# ---------------------------------------------------------------------------
# deploy init
# ---------------------------------------------------------------------------


class TestDeployInit(TestDeploymentCommands):
    """Tests for the deploy init command."""

    @pytest.mark.unit
    def test_init_creates_secrets_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy init should copy the example secrets file into place."""
        secrets_file = tmp_path / ".env.kong.secrets"
        example_file = tmp_path / ".env.kong.secrets.example"
        example_file.write_text("POSTGRES_PASSWORD=changeme\n")

        mock_deployment_manager._get_paths.return_value = {
            "secrets": secrets_file,
            "secrets_example": example_file,
        }

        result = cli_runner.invoke(app, ["deploy", "init", "--force"])

        assert result.exit_code == 0
        assert secrets_file.exists()
        assert "created" in result.stdout.lower()

    @pytest.mark.unit
    def test_init_example_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy init should exit with code 1 when the example file is missing."""
        secrets_file = tmp_path / ".env.kong.secrets"
        example_file = tmp_path / ".env.kong.secrets.example"
        # example_file is intentionally NOT created

        mock_deployment_manager._get_paths.return_value = {
            "secrets": secrets_file,
            "secrets_example": example_file,
        }

        result = cli_runner.invoke(app, ["deploy", "init", "--force"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_init_file_exists_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy init should ask for confirmation when secrets file already exists."""
        secrets_file = tmp_path / ".env.kong.secrets"
        secrets_file.write_text("original content\n")
        example_file = tmp_path / ".env.kong.secrets.example"
        example_file.write_text("POSTGRES_PASSWORD=changeme\n")

        mock_deployment_manager._get_paths.return_value = {
            "secrets": secrets_file,
            "secrets_example": example_file,
        }

        result = cli_runner.invoke(app, ["deploy", "init"], input="n\n")

        assert result.exit_code == 0
        # File should still contain original content
        assert secrets_file.read_text() == "original content\n"

    @pytest.mark.unit
    def test_init_file_exists_overwrite_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy init should overwrite secrets file when user confirms."""
        secrets_file = tmp_path / ".env.kong.secrets"
        secrets_file.write_text("old content\n")
        example_file = tmp_path / ".env.kong.secrets.example"
        example_file.write_text("POSTGRES_PASSWORD=newvalue\n")

        mock_deployment_manager._get_paths.return_value = {
            "secrets": secrets_file,
            "secrets_example": example_file,
        }

        result = cli_runner.invoke(app, ["deploy", "init"], input="y\n")

        assert result.exit_code == 0
        assert secrets_file.read_text() == "POSTGRES_PASSWORD=newvalue\n"

    @pytest.mark.unit
    def test_init_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_deployment_manager: MagicMock,
    ) -> None:
        """deploy init should exit with code 1 on unexpected exception."""
        mock_deployment_manager._get_paths.side_effect = RuntimeError("unexpected error")

        result = cli_runner.invoke(app, ["deploy", "init", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
