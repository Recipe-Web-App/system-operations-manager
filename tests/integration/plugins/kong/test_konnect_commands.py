"""Integration tests for Kong Konnect CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
import typer
from pydantic import SecretStr
from typer.testing import CliRunner

from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    DataPlaneCertificate,
)
from system_operations_manager.plugins.kong.commands.konnect import (
    register_konnect_commands,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def app() -> typer.Typer:
    """Create a test app with konnect commands."""
    app = typer.Typer()
    register_konnect_commands(app)
    return app


@pytest.fixture
def mock_konnect_config() -> KonnectConfig:
    """Create a mock Konnect config."""
    return KonnectConfig(
        token=SecretStr("test-token"),
        region=KonnectRegion.US,
    )


@pytest.fixture
def mock_control_planes() -> list[ControlPlane]:
    """Create mock control planes."""
    return [
        ControlPlane(
            id="cp-1",
            name="test-control-plane",
            cluster_type="CLUSTER_TYPE_K8S_INGRESS_CONTROLLER",
            control_plane_endpoint="https://test.cp0.konghq.com",
            telemetry_endpoint="https://test.tp0.konghq.com",
        ),
        ControlPlane(
            id="cp-2",
            name="second-control-plane",
            cluster_type="CLUSTER_TYPE_CONTROL_PLANE",
            control_plane_endpoint="https://second.cp0.konghq.com",
            telemetry_endpoint="https://second.tp0.konghq.com",
        ),
    ]


@pytest.fixture
def mock_certificate() -> DataPlaneCertificate:
    """Create a mock certificate."""
    return DataPlaneCertificate(
        id="cert-123",
        cert="-----BEGIN CERTIFICATE-----\ntest-cert\n-----END CERTIFICATE-----",
        key="-----BEGIN TEST KEY-----\ntest-key\n-----END TEST KEY-----",
    )


class TestKonnectLoginCommand:
    """Tests for the konnect login command."""

    @pytest.mark.integration
    def test_login_help(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Login command should show help."""
        result = cli_runner.invoke(app, ["konnect", "login", "--help"])

        assert result.exit_code == 0
        assert "Configure Konnect credentials" in result.stdout

    @pytest.mark.integration
    def test_login_with_invalid_region(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Login should reject invalid region."""
        with patch.object(KonnectConfig, "exists", return_value=False):
            result = cli_runner.invoke(
                app,
                ["konnect", "login", "--token", "test", "--region", "invalid"],
            )

        assert result.exit_code == 1
        assert "Invalid region" in result.stdout


class TestKonnectStatusCommand:
    """Tests for the konnect status command."""

    @pytest.mark.integration
    def test_status_help(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Status command should show help."""
        result = cli_runner.invoke(app, ["konnect", "status", "--help"])

        assert result.exit_code == 0
        assert "Show Konnect configuration status" in result.stdout

    @pytest.mark.integration
    def test_status_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Status should indicate when not configured."""
        with patch.object(KonnectConfig, "exists", return_value=False):
            result = cli_runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout

    @pytest.mark.integration
    def test_status_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_konnect_config: KonnectConfig,
        mock_control_planes: list[ControlPlane],
    ) -> None:
        """Status should show configuration when configured."""
        mock_client = MagicMock()
        mock_client.validate_token.return_value = True
        mock_client.list_control_planes.return_value = mock_control_planes
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(KonnectConfig, "exists", return_value=True),
            patch.object(KonnectConfig, "load", return_value=mock_konnect_config),
            patch(
                "system_operations_manager.integrations.konnect.KonnectClient",
                return_value=mock_client,
            ),
        ):
            result = cli_runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0
        assert "Connection OK" in result.stdout


class TestKonnectListControlPlanesCommand:
    """Tests for the konnect list-control-planes command."""

    @pytest.mark.integration
    def test_list_control_planes_help(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """List control planes command should show help."""
        result = cli_runner.invoke(app, ["konnect", "list-control-planes", "--help"])

        assert result.exit_code == 0
        assert "List available control planes" in result.stdout

    @pytest.mark.integration
    def test_list_control_planes_shows_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_konnect_config: KonnectConfig,
        mock_control_planes: list[ControlPlane],
    ) -> None:
        """List control planes should display table."""
        mock_client = MagicMock()
        mock_client.list_control_planes.return_value = mock_control_planes
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(KonnectConfig, "load", return_value=mock_konnect_config),
            patch(
                "system_operations_manager.integrations.konnect.KonnectClient",
                return_value=mock_client,
            ),
        ):
            result = cli_runner.invoke(app, ["konnect", "list-control-planes"])

        assert result.exit_code == 0
        assert "test-control-plane" in result.stdout
        assert "second-control-plane" in result.stdout


class TestKonnectSetupCommand:
    """Tests for the konnect setup command."""

    @pytest.mark.integration
    def test_setup_help(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Setup command should show help."""
        result = cli_runner.invoke(app, ["konnect", "setup", "--help"])

        assert result.exit_code == 0
        assert "Set up Konnect data plane connection" in result.stdout
        assert "--control-plane" in result.stdout
        assert "--namespace" in result.stdout

    @pytest.mark.integration
    def test_setup_with_control_plane_option(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_konnect_config: KonnectConfig,
        mock_control_planes: list[ControlPlane],
        mock_certificate: DataPlaneCertificate,
    ) -> None:
        """Setup should use --control-plane option."""
        mock_client = MagicMock()
        mock_client.find_control_plane.return_value = mock_control_planes[0]
        mock_client.list_dp_certificates.return_value = []
        mock_client.create_dp_certificate.return_value = mock_certificate
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(KonnectConfig, "load", return_value=mock_konnect_config),
            patch(
                "system_operations_manager.integrations.konnect.KonnectClient",
                return_value=mock_client,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ) as mock_create_secret,
        ):
            result = cli_runner.invoke(
                app,
                [
                    "konnect",
                    "setup",
                    "--control-plane",
                    "test-control-plane",
                    "--namespace",
                    "kong",
                ],
            )

        assert result.exit_code == 0
        assert "Konnect setup complete" in result.stdout
        mock_client.find_control_plane.assert_called_once_with("test-control-plane")
        mock_create_secret.assert_called_once()

    @pytest.mark.integration
    def test_setup_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Setup should fail when not configured."""
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectConfigError,
        )

        with patch.object(
            KonnectConfig,
            "load",
            side_effect=KonnectConfigError("Not configured"),
        ):
            result = cli_runner.invoke(
                app,
                ["konnect", "setup", "--control-plane", "test", "--namespace", "kong"],
            )

        assert result.exit_code == 1
        assert "Not configured" in result.stdout


class TestHelperFunctions:
    """Tests for helper functions."""

    @pytest.mark.integration
    def test_get_or_select_control_plane_with_name(
        self,
        mock_control_planes: list[ControlPlane],
    ) -> None:
        """_get_or_select_control_plane should find by name."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _get_or_select_control_plane,
        )

        mock_client = MagicMock()
        mock_client.find_control_plane.return_value = mock_control_planes[0]

        result = _get_or_select_control_plane(mock_client, "test-control-plane")

        assert result.name == "test-control-plane"
        mock_client.find_control_plane.assert_called_once_with("test-control-plane")

    @pytest.mark.integration
    def test_get_or_select_control_plane_not_found(self) -> None:
        """_get_or_select_control_plane should exit when not found."""
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectNotFoundError,
        )
        from system_operations_manager.plugins.kong.commands.konnect import (
            _get_or_select_control_plane,
        )

        mock_client = MagicMock()
        mock_client.find_control_plane.side_effect = KonnectNotFoundError("Not found")

        with pytest.raises(click.exceptions.Exit):
            _get_or_select_control_plane(mock_client, "nonexistent")
