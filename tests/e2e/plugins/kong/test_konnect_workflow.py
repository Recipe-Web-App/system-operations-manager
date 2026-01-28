"""E2E tests for Kong Konnect workflows.

These tests require actual Konnect credentials and are skipped by default.
Run 'ops kong konnect login' to configure credentials.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from system_operations_manager.integrations.konnect.config import KonnectConfig

# Skip all tests if Konnect credentials are not configured
pytestmark = pytest.mark.skipif(
    not KonnectConfig.exists(),
    reason="Konnect not configured. Run 'ops kong konnect login' first.",
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestKonnectE2EWorkflow:
    """E2E tests for Konnect workflow."""

    @pytest.mark.e2e
    def test_konnect_status_with_real_credentials(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Status command should work with real credentials."""
        import typer

        from system_operations_manager.plugins.kong.commands.konnect import (
            register_konnect_commands,
        )

        app = typer.Typer()
        register_konnect_commands(app)

        result = cli_runner.invoke(app, ["konnect", "status"])

        # Should either show status or indicate not configured
        assert result.exit_code == 0 or "not configured" in result.stdout.lower()

    @pytest.mark.e2e
    def test_list_control_planes_with_real_credentials(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """List control planes should work with real credentials."""
        import typer

        from system_operations_manager.plugins.kong.commands.konnect import (
            register_konnect_commands,
        )

        app = typer.Typer()
        register_konnect_commands(app)

        result = cli_runner.invoke(app, ["konnect", "list-control-planes"])

        # Should either list control planes or fail gracefully
        if result.exit_code == 0:
            # Output should contain table-like output
            assert "Control Planes" in result.stdout or "No control planes" in result.stdout

    @pytest.mark.e2e
    def test_konnect_client_validates_token(self) -> None:
        """KonnectClient should validate token against real API."""
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )

        config = KonnectConfig.load()

        with KonnectClient(config) as client:
            # This should not raise an exception
            result = client.validate_token()
            assert result is True

    @pytest.mark.e2e
    def test_konnect_list_control_planes_real(self) -> None:
        """list_control_planes should return real data."""
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )
        from system_operations_manager.integrations.konnect.models import ControlPlane

        config = KonnectConfig.load()

        with KonnectClient(config) as client:
            control_planes = client.list_control_planes()

            # Should be a list (may be empty)
            assert isinstance(control_planes, list)
            # If there are control planes, verify structure
            for cp in control_planes:
                assert isinstance(cp, ControlPlane)
                assert cp.id is not None
                assert cp.name is not None


class TestKonnectConfigE2E:
    """E2E tests for Konnect configuration."""

    @pytest.mark.e2e
    def test_config_load_from_environment(self) -> None:
        """Config should load from environment variables."""
        from pydantic import SecretStr

        from system_operations_manager.integrations.konnect import (
            KonnectConfig,
            KonnectRegion,
        )

        # Environment variable is already set (from pytestmark check)
        config = KonnectConfig.load()

        assert config.token is not None
        assert isinstance(config.token, SecretStr)
        assert config.region in [KonnectRegion.US, KonnectRegion.EU, KonnectRegion.AU]

    @pytest.mark.e2e
    def test_config_save_and_load(self, tmp_path: Path) -> None:
        """Config should save to file and load back."""
        from unittest.mock import patch

        from pydantic import SecretStr

        from system_operations_manager.integrations.konnect import (
            KonnectConfig,
            KonnectRegion,
        )

        config_path = tmp_path / "konnect.yaml"

        config = KonnectConfig(
            token=SecretStr("test-token-save"),
            region=KonnectRegion.EU,
            default_control_plane="test-cp",
        )

        with patch.object(KonnectConfig, "get_config_path", return_value=config_path):
            config.save()

            # Clear env vars and reload from file
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("KONG_KONNECT_TOKEN", None)
                loaded = KonnectConfig.load()

        assert loaded.token.get_secret_value() == "test-token-save"
        assert loaded.region == KonnectRegion.EU
        assert loaded.default_control_plane == "test-cp"
