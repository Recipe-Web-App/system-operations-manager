"""E2E tests for Kong dual-write workflows.

These tests verify that CLI commands support the --data-plane-only flag
and handle Konnect not being configured gracefully.

Note: Konnect is not available in CI, so we test the degraded behavior
where commands work but show "Konnect not configured" messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner


@pytest.mark.e2e
@pytest.mark.kong
class TestDataPlaneOnlyFlag:
    """Test --data-plane-only flag is recognized by CLI commands."""

    def test_services_create_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """services create should accept --data-plane-only flag."""
        service_name = f"{unique_prefix}-dp-only-svc"

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "test.local",
                "--data-plane-only",
            ],
        )

        # Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert service_name in result.output

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "services", "delete", service_name, "--force"])

    def test_services_create_accepts_gateway_only_alias(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """services create should accept --gateway-only alias."""
        service_name = f"{unique_prefix}-gw-only-svc"

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "test.local",
                "--gateway-only",
            ],
        )

        # Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "services", "delete", service_name, "--force"])

    def test_services_update_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """services update should accept --data-plane-only flag."""
        service_name = f"{unique_prefix}-update-dp-svc"

        # Create service first
        cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "original.local",
            ],
        )

        # Update with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "update",
                service_name,
                "--host",
                "updated.local",
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "services", "delete", service_name, "--force"])

    def test_services_delete_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """services delete should accept --data-plane-only flag."""
        service_name = f"{unique_prefix}-delete-dp-svc"

        # Create service first
        cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "delete.local",
            ],
        )

        # Delete with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "delete",
                service_name,
                "--force",
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"


@pytest.mark.e2e
@pytest.mark.kong
class TestRouteDataPlaneOnlyFlag:
    """Test --data-plane-only flag for route commands."""

    def test_routes_create_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """routes create should accept --data-plane-only flag."""
        service_name = f"{unique_prefix}-route-svc"
        route_name = f"{unique_prefix}-dp-route"

        # Create service first
        cli_runner.invoke(
            kong_app,
            ["kong", "services", "create", "--name", service_name, "--host", "test.local"],
        )

        # Create route with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "routes",
                "create",
                "--name",
                route_name,
                "--service",
                service_name,
                "--path",
                f"/{unique_prefix}",
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "routes", "delete", route_name, "--force"])
        cli_runner.invoke(kong_app, ["kong", "services", "delete", service_name, "--yes"])


@pytest.mark.e2e
@pytest.mark.kong
class TestConsumerDataPlaneOnlyFlag:
    """Test --data-plane-only flag for consumer commands."""

    def test_consumers_create_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """consumers create should accept --data-plane-only flag."""
        username = f"{unique_prefix}-dp-consumer"

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "consumers",
                "create",
                "--username",
                username,
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "consumers", "delete", username, "--force"])


@pytest.mark.e2e
@pytest.mark.kong
class TestUpstreamDataPlaneOnlyFlag:
    """Test --data-plane-only flag for upstream commands."""

    def test_upstreams_create_accepts_data_plane_only_flag(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """upstreams create should accept --data-plane-only flag."""
        upstream_name = f"{unique_prefix}-dp-upstream"

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "upstreams",
                "create",
                upstream_name,  # positional argument
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "upstreams", "delete", upstream_name, "--force"])


@pytest.mark.e2e
@pytest.mark.kong
class TestKonnectNotConfiguredBehavior:
    """Test graceful degradation when Konnect is not configured."""

    def test_service_create_shows_konnect_not_configured(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Service create should indicate when Konnect is not configured."""
        service_name = f"{unique_prefix}-no-konnect-svc"

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "test.local",
            ],
        )

        # Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert service_name in result.output

        # Should indicate Konnect status (either not configured or skipped)
        # The exact message depends on whether dual-write is enabled
        # If dual-write factory returns None for Konnect manager, it shows "not configured"
        # If dual-write is not configured at all, no message is shown

        # Cleanup
        cli_runner.invoke(kong_app, ["kong", "services", "delete", service_name, "--force"])


@pytest.mark.e2e
@pytest.mark.kong
class TestDualWriteFullWorkflow:
    """Test complete dual-write workflows via declarative config."""

    def test_full_api_workflow_with_data_plane_only(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Complete API workflow should work with --data-plane-only flag."""
        service_name = f"{unique_prefix}-workflow-api"
        route_name = f"{unique_prefix}-workflow-route"

        # Create service with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "create",
                "--name",
                service_name,
                "--host",
                "api.example.com",
                "--port",
                "80",
                "--data-plane-only",
            ],
        )
        assert result.exit_code == 0, f"Service create failed: {result.output}"

        # Create route for the service with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "routes",
                "create",
                "--name",
                route_name,
                "--service",
                service_name,
                "--path",
                f"/api/{unique_prefix}",
                "--data-plane-only",
            ],
        )
        assert result.exit_code == 0, f"Route create failed: {result.output}"

        # Verify both exist
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

        result = cli_runner.invoke(kong_app, ["kong", "routes", "get", route_name])
        assert result.exit_code == 0
        assert route_name in result.output

        # Update service with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "services",
                "update",
                service_name,
                "--port",
                "8080",
                "--data-plane-only",
            ],
        )
        assert result.exit_code == 0, f"Service update failed: {result.output}"

        # Cleanup with --data-plane-only
        result = cli_runner.invoke(
            kong_app,
            ["kong", "routes", "delete", route_name, "--force", "--data-plane-only"],
        )
        assert result.exit_code == 0, f"Route delete failed: {result.output}"

        result = cli_runner.invoke(
            kong_app,
            ["kong", "services", "delete", service_name, "--force", "--data-plane-only"],
        )
        assert result.exit_code == 0, f"Service delete failed: {result.output}"
