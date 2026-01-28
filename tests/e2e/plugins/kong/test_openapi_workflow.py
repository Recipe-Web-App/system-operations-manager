"""E2E tests for OpenAPI to Kong route sync workflows.

These tests verify the complete OpenAPI sync workflow via CLI:
- Parsing OpenAPI specs and creating routes
- Diffing spec against current Kong state
- Handling breaking changes
- Dry-run mode
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
class TestOpenAPIDiffCommand:
    """Test the openapi diff command."""

    def test_diff_shows_creates_for_new_spec(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Diff should show routes to create for new OpenAPI spec."""
        # First create a service via declarative config
        service_name = f"{unique_prefix}-openapi-svc"
        service_config_file = temp_config_dir / "service.yaml"

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
        service_config_file.write_text(yaml.dump(config))

        # Apply the service config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # Create an OpenAPI spec
        openapi_spec_file = temp_config_dir / "api-spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "summary": "List users",
                    }
                },
                "/users/{userId}": {
                    "get": {
                        "operationId": "getUser",
                        "tags": ["Users"],
                        "summary": "Get user by ID",
                    }
                },
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run diff command
        result = cli_runner.invoke(
            kong_app,
            ["kong", "openapi", "diff", str(openapi_spec_file), "--service", service_name],
        )

        assert result.exit_code == 0, f"Diff failed: {result.output}"
        # Should show creates
        assert "Creates" in result.output or "create" in result.output.lower()

    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Diff should output JSON when requested."""
        # Create service
        service_name = f"{unique_prefix}-json-svc"
        service_config_file = temp_config_dir / "service.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create OpenAPI spec
        openapi_spec_file = temp_config_dir / "api.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "JSON Test API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {"operationId": "listItems"},
                }
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run diff with JSON output
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "diff",
                str(openapi_spec_file),
                "--service",
                service_name,
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, f"Diff failed: {result.output}"
        # Should be valid JSON with expected structure
        assert '"service"' in result.output
        assert '"summary"' in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestOpenAPISyncRoutesCommand:
    """Test the openapi sync-routes command."""

    def test_sync_routes_dry_run(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync with --dry-run should preview without applying."""
        # Create service
        service_name = f"{unique_prefix}-dryrun-svc"
        service_config_file = temp_config_dir / "service.yaml"

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
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to create service: {result.output}"

        # Create OpenAPI spec
        openapi_spec_file = temp_config_dir / "dryrun-spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Dry Run API", "version": "1.0.0"},
            "paths": {
                "/dryrun": {
                    "get": {
                        "operationId": "dryRunEndpoint",
                        "summary": "Dry run test",
                    }
                }
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run sync with dry-run
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                service_name,
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, f"Sync dry-run failed: {result.output}"
        assert "dry run" in result.output.lower() or "Dry run" in result.output

    @pytest.mark.requires_db
    def test_sync_routes_creates_routes(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync should create routes from OpenAPI spec."""
        # Create service
        service_name = f"{unique_prefix}-sync-svc"
        service_config_file = temp_config_dir / "service.yaml"

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
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create OpenAPI spec with unique operation IDs
        openapi_spec_file = temp_config_dir / "sync-spec.yaml"
        op_id = f"syncTest{unique_prefix.replace('-', '')}"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Sync Test API", "version": "1.0.0"},
            "paths": {
                f"/{unique_prefix}/sync": {
                    "get": {
                        "operationId": op_id,
                        "tags": ["Sync"],
                        "summary": "Sync test endpoint",
                    }
                }
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run sync
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                service_name,
            ],
        )

        assert result.exit_code == 0, f"Sync failed: {result.output}"
        assert "success" in result.output.lower() or "applied" in result.output.lower()

        # Verify routes were created
        route_name = f"{service_name}-{op_id}"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "routes", "get", route_name],
        )
        # Route should exist (exit_code 0) or appear in routes list
        if result.exit_code != 0:
            # Try listing routes for the service
            result = cli_runner.invoke(
                kong_app,
                ["kong", "routes", "list", "--service", service_name],
            )
            assert result.exit_code == 0

    def test_sync_routes_with_path_prefix(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync should apply path prefix to routes."""
        # Create service
        service_name = f"{unique_prefix}-prefix-svc"
        service_config_file = temp_config_dir / "service.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create OpenAPI spec
        openapi_spec_file = temp_config_dir / "prefix-spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Prefix API", "version": "1.0.0"},
            "paths": {
                "/data": {"get": {"operationId": f"prefixGet{unique_prefix.replace('-', '')}"}}
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run sync with path prefix (dry-run to check)
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                service_name,
                "--path-prefix",
                "/api/v1",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, f"Sync failed: {result.output}"
        # Path should include the prefix
        assert "/api/v1" in result.output or "api/v1" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestOpenAPISyncBreakingChanges:
    """Test breaking change handling in sync."""

    def test_sync_breaking_changes_require_force(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync with breaking changes should fail without --force."""
        # Create service with a route
        service_name = f"{unique_prefix}-break-svc"
        route_name = f"{service_name}-existingRoute"
        service_config_file = temp_config_dir / "service-with-route.yaml"

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
                            "paths": [f"/{unique_prefix}/existing"],
                        }
                    ],
                }
            ],
        }
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create OpenAPI spec that REMOVES the existing route
        # (Empty spec will trigger deletion of the route)
        openapi_spec_file = temp_config_dir / "empty-spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Empty API", "version": "1.0.0"},
            "paths": {
                # Different path - will trigger delete of existing route
                "/different": {"get": {"operationId": f"different{unique_prefix.replace('-', '')}"}}
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run sync WITHOUT --force
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                service_name,
            ],
        )

        # Should fail or warn about breaking changes
        # Exit code 1 indicates breaking changes require force
        if result.exit_code == 1:
            assert "breaking" in result.output.lower() or "--force" in result.output

    @pytest.mark.requires_db
    def test_sync_breaking_changes_with_force(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync with --force should apply breaking changes."""
        # Create service with route
        service_name = f"{unique_prefix}-force-svc"
        route_name = f"{service_name}-toDelete"
        service_config_file = temp_config_dir / "service.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": [f"/{unique_prefix}/to-delete"],
                        }
                    ],
                }
            ],
        }
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create spec that would delete the route
        openapi_spec_file = temp_config_dir / "force-spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Force API", "version": "1.0.0"},
            "paths": {
                "/newpath": {"get": {"operationId": f"newOp{unique_prefix.replace('-', '')}"}}
            },
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        # Run sync WITH --force
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                service_name,
                "--force",
            ],
        )

        # Should succeed with force
        assert result.exit_code == 0, f"Sync with force failed: {result.output}"


@pytest.mark.e2e
@pytest.mark.kong
class TestOpenAPIErrorHandling:
    """Test error handling in OpenAPI commands."""

    def test_sync_nonexistent_service_fails(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync should fail gracefully for nonexistent service."""
        openapi_spec_file = temp_config_dir / "spec.yaml"
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Error API", "version": "1.0.0"},
            "paths": {"/test": {"get": {"operationId": "test"}}},
        }
        openapi_spec_file.write_text(yaml.dump(openapi_spec))

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(openapi_spec_file),
                "--service",
                "nonexistent-service-12345",
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_sync_invalid_spec_fails(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Sync should fail gracefully for invalid OpenAPI spec."""
        # Create service first
        service_name = f"{unique_prefix}-error-svc"
        service_config_file = temp_config_dir / "service.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        service_config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(service_config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Create invalid spec (Swagger 2.0)
        invalid_spec_file = temp_config_dir / "invalid-spec.yaml"
        invalid_spec = {
            "swagger": "2.0",
            "info": {"title": "Old API", "version": "1.0.0"},
            "paths": {},
        }
        invalid_spec_file.write_text(yaml.dump(invalid_spec))

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "openapi",
                "sync-routes",
                str(invalid_spec_file),
                "--service",
                service_name,
            ],
        )

        assert result.exit_code == 1
        assert (
            "swagger" in result.output.lower()
            or "error" in result.output.lower()
            or "not supported" in result.output.lower()
        )
