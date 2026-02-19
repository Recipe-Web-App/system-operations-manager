"""Unit tests for Kong Konnect CLI commands.

Tests for login, setup, status, list-control-planes commands and
helper functions _get_or_select_control_plane and _create_tls_secret.

Because these commands use lazy imports inside function bodies (e.g.
``from system_operations_manager.integrations.konnect import KonnectConfig``),
we patch at the *source* module rather than at the konnect command module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.konnect.exceptions import (
    KonnectAuthError,
    KonnectConfigError,
    KonnectNotFoundError,
)
from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    DataPlaneCertificate,
)
from system_operations_manager.plugins.kong.commands.konnect import (
    _create_tls_secret,
    _get_or_select_control_plane,
    register_konnect_commands,
)

# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------
# The commands do lazy imports inside the function body, e.g.
#   from system_operations_manager.integrations.konnect import KonnectConfig
# We must patch at the source module so the import binds to our mock.
_KONNECT_PKG = "system_operations_manager.integrations.konnect"
_KONNECT_CONFIG = f"{_KONNECT_PKG}.KonnectConfig"
_KONNECT_CLIENT = f"{_KONNECT_PKG}.KonnectClient"
_KONNECT_REGION = f"{_KONNECT_PKG}.KonnectRegion"
_KONNECT_AUTH_ERR = f"{_KONNECT_PKG}.exceptions.KonnectAuthError"
_KONNECT_CFG_ERR = f"{_KONNECT_PKG}.exceptions.KonnectConfigError"
_KONNECT_NOT_FOUND = f"{_KONNECT_PKG}.exceptions.KonnectNotFoundError"
_PYDANTIC_SECRET = "pydantic.SecretStr"
_RICH_CONFIRM = "system_operations_manager.plugins.kong.commands.konnect.Confirm"
_RICH_PROMPT = "system_operations_manager.plugins.kong.commands.konnect.Prompt"
_RICH_INT_PROMPT = "rich.prompt.IntPrompt"
_K8S_SERVICE = "system_operations_manager.services.kubernetes.KubernetesService"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_control_plane(
    name: str = "my-cp",
    cp_id: str = "cp-123",
    cluster_type: str | None = "CLUSTER_TYPE_HYBRID",
    control_plane_endpoint: str | None = "cp.konghq.com:443",
    telemetry_endpoint: str | None = "telemetry.konghq.com:443",
) -> ControlPlane:
    """Build a ControlPlane model with sensible defaults."""
    return ControlPlane(
        id=cp_id,
        name=name,
        cluster_type=cluster_type,
        control_plane_endpoint=control_plane_endpoint,
        telemetry_endpoint=telemetry_endpoint,
    )


def _make_cert(
    cert_id: str = "cert-abc",
    cert: str = "-----BEGIN CERTIFICATE-----\nMIIBx\n-----END CERTIFICATE-----\n",
    key: str | None = "MOCK_PRIVATE_KEY_DATA",
) -> DataPlaneCertificate:
    """Build a DataPlaneCertificate model with sensible defaults."""
    return DataPlaneCertificate(id=cert_id, cert=cert, key=key)


def _make_app() -> typer.Typer:
    """Create a Typer app with konnect commands registered."""
    app = typer.Typer()
    register_konnect_commands(app)
    return app


def _make_konnect_client(
    control_planes: list[Any] | None = None,
    validate_return: bool = True,
    validate_side_effect: Exception | None = None,
) -> MagicMock:
    """Build a mock KonnectClient context manager."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    if validate_side_effect is not None:
        client.validate_token.side_effect = validate_side_effect
    else:
        client.validate_token.return_value = validate_return
    client.list_control_planes.return_value = control_planes or []
    return client


# ---------------------------------------------------------------------------
# TestLogin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLogin:
    """Tests for the konnect login command."""

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Create a Typer app with konnect commands registered."""
        return _make_app()

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CliRunner."""
        return CliRunner()

    def test_login_with_token_success(self, runner: CliRunner, app: typer.Typer) -> None:
        """Providing --token directly validates and saves credentials."""
        mock_cp = _make_control_plane()
        mock_client = _make_konnect_client(control_planes=[mock_cp])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = mock_config_instance
        mock_config_cls.exists.return_value = False
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        mock_region_instance = MagicMock()
        mock_region_instance.value = "us"
        mock_region_cls = MagicMock(return_value=mock_region_instance)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "my-secret-token"])

        assert result.exit_code == 0, result.output
        mock_config_instance.save.assert_called_once()

    def test_login_token_prompt_when_not_provided(
        self, runner: CliRunner, app: typer.Typer
    ) -> None:
        """When no --token is given, the command prompts for one."""
        mock_cp = _make_control_plane()
        mock_client = _make_konnect_client(control_planes=[mock_cp])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = mock_config_instance
        mock_config_cls.exists.return_value = False
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        mock_region_instance = MagicMock()
        mock_region_instance.value = "us"
        mock_region_cls = MagicMock(return_value=mock_region_instance)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
            patch(_RICH_PROMPT) as mock_prompt_cls,
        ):
            mock_prompt_cls.ask.return_value = "prompted-token"
            result = runner.invoke(app, ["konnect", "login"])

        assert result.exit_code == 0, result.output
        mock_prompt_cls.ask.assert_called_once()

    def test_login_empty_token_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """An empty token after prompting should exit with code 1."""
        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_REGION, mock_region_cls),
            patch(_RICH_PROMPT) as mock_prompt_cls,
        ):
            mock_prompt_cls.ask.return_value = ""
            result = runner.invoke(app, ["konnect", "login"])

        assert result.exit_code == 1
        assert "Token is required" in result.output

    def test_login_invalid_region(self, runner: CliRunner, app: typer.Typer) -> None:
        """An invalid region string should exit with code 1."""
        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False

        mock_region_cls = MagicMock()
        mock_region_cls.side_effect = ValueError("invalid region")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(
                app,
                ["konnect", "login", "--token", "valid-token", "--region", "invalid-region"],
            )

        assert result.exit_code == 1
        assert "Invalid region" in result.output

    def test_login_auth_failure(self, runner: CliRunner, app: typer.Typer) -> None:
        """A KonnectAuthError from validate_token should exit with code 1."""
        mock_client = _make_konnect_client(
            validate_side_effect=KonnectAuthError("Invalid token", details=None)
        )
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False
        mock_config_cls.return_value = MagicMock()

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "bad-token"])

        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_login_auth_failure_with_details(self, runner: CliRunner, app: typer.Typer) -> None:
        """A KonnectAuthError with details should print both message and details."""
        mock_client = _make_konnect_client(
            validate_side_effect=KonnectAuthError("Invalid token", details="Please check your PAT")
        )
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False
        mock_config_cls.return_value = MagicMock()

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "bad-token"])

        assert result.exit_code == 1
        assert "Please check your PAT" in result.output

    def test_login_connection_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """A generic exception from KonnectClient should exit with code 1."""
        mock_client = _make_konnect_client(validate_side_effect=RuntimeError("connection refused"))
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False
        mock_config_cls.return_value = MagicMock()

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "my-token"])

        assert result.exit_code == 1
        assert "Connection error" in result.output

    def test_login_already_configured_cancel(self, runner: CliRunner, app: typer.Typer) -> None:
        """When already configured and user declines overwrite, exit with code 0."""
        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_REGION),
            patch(_RICH_CONFIRM) as mock_confirm_cls,
        ):
            mock_confirm_cls.ask.return_value = False
            result = runner.invoke(app, ["konnect", "login", "--token", "my-token"])

        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_login_already_configured_force(self, runner: CliRunner, app: typer.Typer) -> None:
        """--force skips the overwrite confirmation even when already configured."""
        mock_cp = _make_control_plane()
        mock_client = _make_konnect_client(control_planes=[mock_cp])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = mock_config_instance
        mock_config_cls.exists.return_value = True  # Already configured
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        mock_region_instance = MagicMock()
        mock_region_instance.value = "us"
        mock_region_cls = MagicMock(return_value=mock_region_instance)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
            patch(_RICH_CONFIRM) as mock_confirm_cls,
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "my-token", "--force"])

        assert result.exit_code == 0, result.output
        # Confirm.ask should NOT have been called because --force bypasses it
        mock_confirm_cls.ask.assert_not_called()
        mock_config_instance.save.assert_called_once()

    def test_login_shows_control_planes(self, runner: CliRunner, app: typer.Typer) -> None:
        """After successful login, available control planes should be displayed."""
        cp1 = _make_control_plane("prod-cp", "cp-001")
        cp2 = _make_control_plane("dev-cp", "cp-002", cluster_type=None)
        mock_client = _make_konnect_client(control_planes=[cp1, cp2])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = mock_config_instance
        mock_config_cls.exists.return_value = False
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "my-token"])

        assert result.exit_code == 0, result.output
        assert "prod-cp" in result.output
        assert "Available Control Planes" in result.output

    def test_login_no_control_planes(self, runner: CliRunner, app: typer.Typer) -> None:
        """After successful login with no CPs, show a warning message."""
        mock_client = _make_konnect_client(control_planes=[])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = mock_config_instance
        mock_config_cls.exists.return_value = False
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        mock_region_cls = MagicMock()
        mock_region_cls.return_value = MagicMock(value="us")

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(_KONNECT_REGION, mock_region_cls),
        ):
            result = runner.invoke(app, ["konnect", "login", "--token", "my-token"])

        assert result.exit_code == 0, result.output
        assert "No control planes found" in result.output


# ---------------------------------------------------------------------------
# TestSetup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetup:
    """Tests for the konnect setup command."""

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Create a Typer app with konnect commands registered."""
        return _make_app()

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CliRunner."""
        return CliRunner()

    def _make_setup_client(
        self,
        cp: ControlPlane | None = None,
        existing_certs: list[Any] | None = None,
        created_cert: DataPlaneCertificate | None = None,
    ) -> tuple[MagicMock, MagicMock]:
        """Return (mock_client_instance, mock_client_cls) for setup tests."""
        if cp is None:
            cp = _make_control_plane()
        if existing_certs is None:
            existing_certs = []
        if created_cert is None:
            created_cert = _make_cert()

        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        client.find_control_plane.return_value = cp
        client.list_control_planes.return_value = [cp]
        client.list_dp_certificates.return_value = existing_certs
        client.create_dp_certificate.return_value = created_cert
        return client, MagicMock(return_value=client)

    def _base_setup_patches(
        self,
        mock_config_cls: MagicMock,
        mock_client_cls: MagicMock,
    ) -> tuple[Any, ...]:
        """Build the common patch context for setup command tests."""
        return (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
            patch(
                f"{_KONNECT_PKG}.exceptions.KonnectConfigError",
                KonnectConfigError,
            ),
        )

    def test_setup_success_with_cp_name(self, runner: CliRunner, app: typer.Typer) -> None:
        """Full happy-path: provide --control-plane, creates cert and K8s secret."""
        cp = _make_control_plane()
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ) as mock_create_secret,
        ):
            result = runner.invoke(app, ["konnect", "setup", "--control-plane", "my-cp"])

        assert result.exit_code == 0, result.output
        mock_create_secret.assert_called_once()

    def test_setup_config_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """A KonnectConfigError on load exits with code 1."""
        mock_config_cls = MagicMock()
        mock_config_cls.load.side_effect = KonnectConfigError(
            "Not configured", details="Run login first"
        )

        with patch(_KONNECT_CONFIG, mock_config_cls):
            result = runner.invoke(app, ["konnect", "setup"])

        assert result.exit_code == 1
        assert "Not configured" in result.output

    def test_setup_config_error_with_details(self, runner: CliRunner, app: typer.Typer) -> None:
        """A KonnectConfigError with details prints both message and details."""
        mock_config_cls = MagicMock()
        mock_config_cls.load.side_effect = KonnectConfigError(
            "Not configured", details="Config file missing"
        )

        with patch(_KONNECT_CONFIG, mock_config_cls):
            result = runner.invoke(app, ["konnect", "setup"])

        assert result.exit_code == 1
        assert "Config file missing" in result.output

    def test_setup_default_control_plane(self, runner: CliRunner, app: typer.Typer) -> None:
        """When no --control-plane provided, uses config.default_control_plane."""
        cp = _make_control_plane("default-cp")
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = "default-cp"
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ),
        ):
            result = runner.invoke(app, ["konnect", "setup"])

        assert result.exit_code == 0, result.output
        assert "default-cp" in result.output

    def test_setup_existing_certs_no_force_decline(
        self, runner: CliRunner, app: typer.Typer
    ) -> None:
        """Existing certs and user declines creating new one exits with code 1."""
        cp = _make_control_plane()
        existing_cert = _make_cert("old-cert")
        _client, client_cls = self._make_setup_client(cp=cp, existing_certs=[existing_cert])

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(_RICH_CONFIRM) as mock_confirm_cls,
        ):
            mock_confirm_cls.ask.return_value = False
            result = runner.invoke(app, ["konnect", "setup", "--control-plane", "my-cp"])

        assert result.exit_code == 1

    def test_setup_existing_certs_force(self, runner: CliRunner, app: typer.Typer) -> None:
        """--force bypasses the confirmation for existing certs."""
        cp = _make_control_plane()
        existing_cert = _make_cert("old-cert")
        new_cert = _make_cert("new-cert")
        _client, client_cls = self._make_setup_client(
            cp=cp, existing_certs=[existing_cert], created_cert=new_cert
        )

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ) as mock_create_secret,
            patch(_RICH_CONFIRM) as mock_confirm_cls,
        ):
            result = runner.invoke(app, ["konnect", "setup", "--control-plane", "my-cp", "--force"])

        assert result.exit_code == 0, result.output
        mock_confirm_cls.ask.assert_not_called()
        mock_create_secret.assert_called_once()

    def test_setup_no_private_key(self, runner: CliRunner, app: typer.Typer) -> None:
        """cert.key is None means no private key returned - exit with code 1."""
        cp = _make_control_plane()
        cert_no_key = _make_cert(key=None)
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert_no_key)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
        ):
            result = runner.invoke(app, ["konnect", "setup", "--control-plane", "my-cp"])

        assert result.exit_code == 1
        assert "no private key" in result.output.lower()

    def test_setup_k8s_secret_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """Exception in _create_tls_secret exits with code 1."""
        cp = _make_control_plane()
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
                side_effect=RuntimeError("kubectl not available"),
            ),
        ):
            result = runner.invoke(app, ["konnect", "setup", "--control-plane", "my-cp"])

        assert result.exit_code == 1
        assert "Failed to create secret" in result.output

    def test_setup_update_values(self, runner: CliRunner, app: typer.Typer) -> None:
        """--update-values flag triggers _update_values_file."""
        cp = _make_control_plane()
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._update_values_file",
            ) as mock_update_values,
        ):
            result = runner.invoke(
                app,
                ["konnect", "setup", "--control-plane", "my-cp", "--update-values"],
            )

        assert result.exit_code == 0, result.output
        mock_update_values.assert_called_once()

    def test_setup_update_values_no_endpoints(self, runner: CliRunner, app: typer.Typer) -> None:
        """--update-values with missing endpoints shows a warning but succeeds."""
        cp_no_endpoints = _make_control_plane(control_plane_endpoint=None, telemetry_endpoint=None)
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp_no_endpoints, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp_no_endpoints,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._update_values_file",
            ) as mock_update_values,
        ):
            result = runner.invoke(
                app,
                ["konnect", "setup", "--control-plane", "my-cp", "--update-values"],
            )

        assert result.exit_code == 0, result.output
        assert "Cannot update values file" in result.output
        mock_update_values.assert_not_called()

    def test_setup_update_values_file_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """Exception in _update_values_file exits with code 1."""
        cp = _make_control_plane()
        cert = _make_cert()
        _client, client_cls = self._make_setup_client(cp=cp, created_cert=cert)

        mock_config_instance = MagicMock()
        mock_config_instance.default_control_plane = None
        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = mock_config_instance

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, client_cls),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._get_or_select_control_plane",
                return_value=cp,
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._create_tls_secret",
            ),
            patch(
                "system_operations_manager.plugins.kong.commands.konnect._update_values_file",
                side_effect=OSError("file not writable"),
            ),
        ):
            result = runner.invoke(
                app,
                ["konnect", "setup", "--control-plane", "my-cp", "--update-values"],
            )

        assert result.exit_code == 1
        assert "Failed to update values file" in result.output


# ---------------------------------------------------------------------------
# TestStatus
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStatus:
    """Tests for the konnect status command."""

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Create a Typer app with konnect commands registered."""
        return _make_app()

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CliRunner."""
        return CliRunner()

    def test_status_not_configured(self, runner: CliRunner, app: typer.Typer) -> None:
        """When not configured, show warning and exit with code 0."""
        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = False

        with patch(_KONNECT_CONFIG, mock_config_cls):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0
        assert "not configured" in result.output.lower()

    def test_status_config_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """KonnectConfigError on load exits with code 1."""
        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True
        mock_config_cls.load.side_effect = KonnectConfigError("Bad config file")

        with patch(_KONNECT_CONFIG, mock_config_cls):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 1
        assert "Bad config file" in result.output

    def test_status_success(self, runner: CliRunner, app: typer.Typer) -> None:
        """Full happy path shows configuration and connection OK."""
        mock_cps = [_make_control_plane()]
        mock_client = _make_konnect_client(control_planes=mock_cps)
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_instance.region.value = "us"
        mock_config_instance.api_url = "https://us.api.konghq.com"
        mock_config_instance.default_control_plane = "my-cp"

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True
        mock_config_cls.load.return_value = mock_config_instance
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0, result.output
        assert "Connection OK" in result.output
        assert "us" in result.output

    def test_status_success_with_default_cp(self, runner: CliRunner, app: typer.Typer) -> None:
        """Status shows default control plane when configured."""
        mock_cps = [_make_control_plane()]
        mock_client = _make_konnect_client(control_planes=mock_cps)
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_instance.region.value = "eu"
        mock_config_instance.api_url = "https://eu.api.konghq.com"
        mock_config_instance.default_control_plane = "prod-cp"

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True
        mock_config_cls.load.return_value = mock_config_instance
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0, result.output
        assert "prod-cp" in result.output

    def test_status_no_default_cp(self, runner: CliRunner, app: typer.Typer) -> None:
        """Status without default CP still succeeds."""
        mock_client = _make_konnect_client(control_planes=[])
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_instance.region.value = "us"
        mock_config_instance.api_url = "https://us.api.konghq.com"
        mock_config_instance.default_control_plane = None

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True
        mock_config_cls.load.return_value = mock_config_instance
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 0, result.output

    def test_status_connection_failure(self, runner: CliRunner, app: typer.Typer) -> None:
        """Exception during validate_token exits with code 1."""
        mock_client = _make_konnect_client(validate_side_effect=RuntimeError("Network unreachable"))
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_config_instance = MagicMock()
        mock_config_instance.region.value = "us"
        mock_config_instance.api_url = "https://us.api.konghq.com"
        mock_config_instance.default_control_plane = None

        mock_config_cls = MagicMock()
        mock_config_cls.exists.return_value = True
        mock_config_cls.load.return_value = mock_config_instance
        mock_config_cls.get_config_path.return_value = "/home/user/.config/ops/konnect.yaml"

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "status"])

        assert result.exit_code == 1
        assert "Connection failed" in result.output


# ---------------------------------------------------------------------------
# TestListControlPlanes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListControlPlanes:
    """Tests for the konnect list-control-planes command."""

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Create a Typer app with konnect commands registered."""
        return _make_app()

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CliRunner."""
        return CliRunner()

    def test_list_control_planes_success(self, runner: CliRunner, app: typer.Typer) -> None:
        """Shows a table of control planes when they exist."""
        cps = [
            _make_control_plane("prod", "cp-001"),
            _make_control_plane("staging", "cp-002", cluster_type=None),
        ]
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_control_planes.return_value = cps

        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "list-control-planes"])

        assert result.exit_code == 0, result.output
        assert "prod" in result.output
        assert "staging" in result.output

    def test_list_control_planes_empty(self, runner: CliRunner, app: typer.Typer) -> None:
        """When no CPs exist, show a 'No control planes found' message."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_control_planes.return_value = []

        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "list-control-planes"])

        assert result.exit_code == 0, result.output
        assert "No control planes found" in result.output

    def test_list_control_planes_config_error(self, runner: CliRunner, app: typer.Typer) -> None:
        """KonnectConfigError on load exits with code 1."""
        mock_config_cls = MagicMock()
        mock_config_cls.load.side_effect = KonnectConfigError("Run login first")

        with patch(_KONNECT_CONFIG, mock_config_cls):
            result = runner.invoke(app, ["konnect", "list-control-planes"])

        assert result.exit_code == 1
        assert "Run login first" in result.output

    def test_list_control_planes_shows_endpoint(self, runner: CliRunner, app: typer.Typer) -> None:
        """The table should include endpoint information for each CP."""
        cp = _make_control_plane("prod", control_plane_endpoint="prod.konghq.com:443")

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.list_control_planes.return_value = [cp]

        mock_config_cls = MagicMock()
        mock_config_cls.load.return_value = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client)

        with (
            patch(_KONNECT_CONFIG, mock_config_cls),
            patch(_KONNECT_CLIENT, mock_client_cls),
        ):
            result = runner.invoke(app, ["konnect", "list-control-planes"])

        assert result.exit_code == 0, result.output
        assert "prod.konghq.com:443" in result.output


# ---------------------------------------------------------------------------
# TestGetOrSelectControlPlane
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetOrSelectControlPlane:
    """Tests for the _get_or_select_control_plane helper."""

    def test_find_by_name(self) -> None:
        """When name_or_id is provided, find_control_plane is called."""
        cp = _make_control_plane("my-cp")
        mock_client = MagicMock()
        mock_client.find_control_plane.return_value = cp

        result = _get_or_select_control_plane(mock_client, "my-cp")

        assert result.name == "my-cp"
        mock_client.find_control_plane.assert_called_once_with("my-cp")

    def test_not_found(self) -> None:
        """KonnectNotFoundError from find_control_plane exits with typer.Exit."""
        import click

        mock_client = MagicMock()
        mock_client.find_control_plane.side_effect = KonnectNotFoundError(
            "not found", status_code=404
        )

        with pytest.raises((SystemExit, click.exceptions.Exit)):
            _get_or_select_control_plane(mock_client, "missing-cp")

    def test_interactive_no_cps(self) -> None:
        """When no CPs are available for selection, exits with typer.Exit."""
        import click

        mock_client = MagicMock()
        mock_client.list_control_planes.return_value = []

        with pytest.raises((SystemExit, click.exceptions.Exit)):
            _get_or_select_control_plane(mock_client, None)

    def test_interactive_selection(self) -> None:
        """User can select a CP interactively by number."""
        cp1 = _make_control_plane("first-cp", "cp-001")
        cp2 = _make_control_plane("second-cp", "cp-002")
        mock_client = MagicMock()
        mock_client.list_control_planes.return_value = [cp1, cp2]

        with patch(_RICH_INT_PROMPT) as mock_int_prompt_cls:
            mock_int_prompt_cls.ask.return_value = 2
            result = _get_or_select_control_plane(mock_client, None)

        assert result.name == "second-cp"

    def test_interactive_selection_first(self) -> None:
        """User selects the first CP from a list."""
        cp1 = _make_control_plane("first-cp", "cp-001")
        cp2 = _make_control_plane("second-cp", "cp-002")
        mock_client = MagicMock()
        mock_client.list_control_planes.return_value = [cp1, cp2]

        with patch(_RICH_INT_PROMPT) as mock_int_prompt_cls:
            mock_int_prompt_cls.ask.return_value = 1
            result = _get_or_select_control_plane(mock_client, None)

        assert result.name == "first-cp"


# ---------------------------------------------------------------------------
# TestCreateTlsSecret
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateTlsSecret:
    """Tests for the _create_tls_secret helper."""

    def test_create_secret_success(self) -> None:
        """Happy path: KubernetesService is created and methods are called."""
        mock_k8s = MagicMock()
        mock_k8s_cls = MagicMock(return_value=mock_k8s)

        with patch(_K8S_SERVICE, mock_k8s_cls):
            _create_tls_secret(
                namespace="kong",
                secret_name="konnect-client-tls",
                cert_pem="---CERT---",
                key_pem="---KEY---",
                force=False,
            )

        mock_k8s.ensure_namespace.assert_called_once_with("kong")
        mock_k8s.create_tls_secret.assert_called_once_with(
            namespace="kong",
            name="konnect-client-tls",
            cert_pem="---CERT---",
            key_pem="---KEY---",
            force=False,
        )

    def test_create_secret_success_with_force(self) -> None:
        """force=True is passed through to create_tls_secret."""
        mock_k8s = MagicMock()
        mock_k8s_cls = MagicMock(return_value=mock_k8s)

        with patch(_K8S_SERVICE, mock_k8s_cls):
            _create_tls_secret(
                namespace="custom-ns",
                secret_name="my-secret",
                cert_pem="---CERT---",
                key_pem="---KEY---",
                force=True,
            )

        mock_k8s.create_tls_secret.assert_called_once_with(
            namespace="custom-ns",
            name="my-secret",
            cert_pem="---CERT---",
            key_pem="---KEY---",
            force=True,
        )

    def test_import_error(self) -> None:
        """ImportError on KubernetesService import is re-raised as RuntimeError."""
        import sys

        # Temporarily remove the kubernetes service module from sys.modules
        # to simulate an ImportError when the function tries to import it.
        k8s_mod = "system_operations_manager.services.kubernetes"
        original = sys.modules.get(k8s_mod)
        sys.modules[k8s_mod] = None  # type: ignore[assignment]
        try:
            with pytest.raises((RuntimeError, ImportError)):
                _create_tls_secret(
                    namespace="kong",
                    secret_name="test-secret",
                    cert_pem="---CERT---",
                    key_pem="---KEY---",
                )
        finally:
            if original is None:
                del sys.modules[k8s_mod]
            else:
                sys.modules[k8s_mod] = original
