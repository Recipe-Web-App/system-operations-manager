"""E2E tests for Kong API management workflows.

These tests verify complete workflows for setting up APIs via CLI:
- Service and route creation via declarative config
- Full service-route-plugin chains
- Upstream and target management
- Consumer and credential management

Note: Kong runs in DB-less mode, so entities are created via declarative config apply.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner


@pytest.mark.e2e
@pytest.mark.kong
class TestServiceWorkflow:
    """Test service management workflows via declarative config."""

    def test_create_service_via_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a service via declarative config and verify it exists."""
        service_name = f"{unique_prefix}-service"
        config_file = temp_config_dir / "service.yaml"

        # Create declarative config with service
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify service exists via get
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_list_services(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create services via config and verify they appear in list."""
        service1 = f"{unique_prefix}-svc1"
        service2 = f"{unique_prefix}-svc2"
        config_file = temp_config_dir / "services.yaml"

        # Create declarative config with two services
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service1,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                },
                {
                    "name": service2,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                },
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # List services
        result = cli_runner.invoke(kong_app, ["kong", "services", "list"])
        assert result.exit_code == 0
        # Check that the output shows 2 services (names may be truncated in table display)
        assert "Total: 2 entities" in result.output or "2 entities" in result.output
        # Check for partial name match (table may truncate names)
        assert unique_prefix in result.output

    def test_export_after_apply(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply config and verify export contains the entities."""
        service_name = f"{unique_prefix}-export-svc"
        config_file = temp_config_dir / "apply.yaml"
        export_file = temp_config_dir / "export.yaml"

        # Create and apply config
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "export.example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export current state
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(export_file)],
        )
        assert result.exit_code == 0

        # Verify export contains service
        exported = yaml.safe_load(export_file.read_text())
        services = exported.get("services", [])
        service_names = [s.get("name") for s in services]
        assert service_name in service_names


@pytest.mark.e2e
@pytest.mark.kong
class TestServiceRouteWorkflow:
    """Test service and route creation workflows via declarative config."""

    def test_create_service_and_route(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a service and route via declarative config."""
        service_name = f"{unique_prefix}-api"
        route_name = f"{unique_prefix}-route"
        config_file = temp_config_dir / "service-route.yaml"

        # Create declarative config with service and route
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": [f"/{unique_prefix}"],
                        }
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify route via get
        result = cli_runner.invoke(kong_app, ["kong", "routes", "get", route_name])
        assert result.exit_code == 0
        assert route_name in result.output

        # Verify route is linked to service
        result = cli_runner.invoke(kong_app, ["kong", "services", "routes", service_name])
        assert result.exit_code == 0
        assert route_name in result.output

    def test_multiple_routes_per_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a service with multiple routes via config."""
        service_name = f"{unique_prefix}-multi-route-api"
        route1 = f"{unique_prefix}-v1-route"
        route2 = f"{unique_prefix}-v2-route"
        config_file = temp_config_dir / "multi-route.yaml"

        # Create declarative config with service and multiple routes
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "api.example.com",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {"name": route1, "paths": ["/v1"]},
                        {"name": route2, "paths": ["/v2"]},
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Verify both routes exist
        result = cli_runner.invoke(kong_app, ["kong", "services", "routes", service_name])
        assert result.exit_code == 0
        assert route1 in result.output
        assert route2 in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestConsumerWorkflow:
    """Test consumer management workflows via declarative config."""

    def test_create_consumer(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer via declarative config."""
        username = f"{unique_prefix}-user"
        config_file = temp_config_dir / "consumer.yaml"

        # Create declarative config with consumer
        config = {
            "_format_version": "3.0",
            "consumers": [{"username": username}],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output

    def test_consumer_with_custom_id(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer with a custom ID via config."""
        username = f"{unique_prefix}-custom-user"
        custom_id = f"custom-{unique_prefix}"
        config_file = temp_config_dir / "consumer-custom.yaml"

        # Create declarative config with consumer with custom ID
        config = {
            "_format_version": "3.0",
            "consumers": [{"username": username, "custom_id": custom_id}],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Verify consumer has custom ID
        result = cli_runner.invoke(
            kong_app, ["kong", "consumers", "get", username, "--output", "json"]
        )
        assert result.exit_code == 0
        assert custom_id in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestUpstreamWorkflow:
    """Test upstream and target management workflows via declarative config."""

    def test_create_upstream(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create an upstream via declarative config."""
        upstream_name = f"{unique_prefix}-upstream"
        config_file = temp_config_dir / "upstream.yaml"

        # Create declarative config with upstream
        config = {
            "_format_version": "3.0",
            "upstreams": [{"name": upstream_name}],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify upstream exists
        result = cli_runner.invoke(kong_app, ["kong", "upstreams", "get", upstream_name])
        assert result.exit_code == 0
        assert upstream_name in result.output

    def test_upstream_with_targets(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create an upstream with targets via declarative config."""
        upstream_name = f"{unique_prefix}-lb-upstream"
        config_file = temp_config_dir / "upstream-targets.yaml"

        # Create declarative config with upstream and targets
        config = {
            "_format_version": "3.0",
            "upstreams": [
                {
                    "name": upstream_name,
                    "algorithm": "round-robin",
                    "targets": [
                        {"target": "server1.example.com:8080", "weight": 100},
                        {"target": "server2.example.com:8080", "weight": 100},
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # List targets
        result = cli_runner.invoke(
            kong_app, ["kong", "upstreams", "targets", "list", upstream_name]
        )
        assert result.exit_code == 0
        assert "server1.example.com:8080" in result.output
        assert "server2.example.com:8080" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestPluginWorkflow:
    """Test plugin management workflows."""

    def test_list_available_plugins(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
    ) -> None:
        """List available Kong plugins."""
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "available"])
        assert result.exit_code == 0
        # Common plugins should be available
        assert "rate-limiting" in result.output or "key-auth" in result.output

    def test_enable_plugin_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable a plugin on a service via declarative config."""
        service_name = f"{unique_prefix}-plugin-svc"
        config_file = temp_config_dir / "plugin-service.yaml"

        # Create declarative config with service and plugin
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "correlation-id",
                    "service": service_name,
                    "config": {"header_name": "X-Request-ID"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # List plugins for service
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "correlation-id" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestFullAPISetupWorkflow:
    """Test complete API setup workflow via declarative config."""

    def test_full_api_setup(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Complete workflow: service -> route -> plugin via config."""
        service_name = f"{unique_prefix}-full-api"
        route_name = f"{unique_prefix}-full-route"
        config_file = temp_config_dir / "full-api.yaml"

        # Create comprehensive declarative config
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "url": "http://httpbin.org:80/anything",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": [f"/api/{unique_prefix}"],
                            "methods": ["GET", "POST"],
                        }
                    ],
                }
            ],
            "plugins": [
                {
                    "name": "correlation-id",
                    "service": service_name,
                    "config": {"header_name": "X-Correlation-ID"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify the complete setup
        # Check service
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

        # Check route
        result = cli_runner.invoke(kong_app, ["kong", "routes", "get", route_name])
        assert result.exit_code == 0
        assert route_name in result.output

        # Check plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "correlation-id" in result.output
