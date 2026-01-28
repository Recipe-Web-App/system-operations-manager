"""E2E tests for Kong Service Registry workflows.

These tests verify complete workflows for managing services via the registry:
- Adding and removing services from the registry
- Listing and showing service details
- Importing services from YAML files
- Deploying services to Kong (in DB-less mode, uses config apply pattern)
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
class TestRegistryManagement:
    """Test registry CRUD operations via CLI."""

    def test_add_service_to_registry(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Add a service to the registry and verify it appears in list."""
        # Set up temp config dir
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add a service
        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "registry",
                "add",
                "test-api",
                "--host",
                "api.example.com",
                "--port",
                "8080",
            ],
        )
        assert result.exit_code == 0, f"Failed to add service: {result.output}"
        assert "Added service" in result.output or "test-api" in result.output

        # Verify via list
        result = cli_runner.invoke(kong_app, ["kong", "registry", "list"])
        assert result.exit_code == 0
        assert "test-api" in result.output
        assert "api.example.com" in result.output

    def test_add_service_with_tags(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Add a service with tags and verify they're stored."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        result = cli_runner.invoke(
            kong_app,
            [
                "kong",
                "registry",
                "add",
                "tagged-api",
                "--host",
                "api.local",
                "--tag",
                "production",
                "--tag",
                "api",
            ],
        )
        assert result.exit_code == 0

        # Verify tags in show output
        result = cli_runner.invoke(kong_app, ["kong", "registry", "show", "tagged-api"])
        assert result.exit_code == 0
        assert "production" in result.output or "api" in result.output

    def test_show_service_details(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Show detailed info for a single service."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add service
        cli_runner.invoke(
            kong_app,
            [
                "kong",
                "registry",
                "add",
                "detailed-api",
                "--host",
                "detailed.local",
                "--port",
                "9090",
                "--protocol",
                "https",
            ],
        )

        # Show details
        result = cli_runner.invoke(kong_app, ["kong", "registry", "show", "detailed-api"])
        assert result.exit_code == 0
        assert "detailed-api" in result.output
        assert "detailed.local" in result.output
        assert "9090" in result.output
        assert "https" in result.output

    def test_remove_service_from_registry(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Remove a service and verify it's gone."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add then remove
        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "to-remove", "--host", "remove.local"],
        )

        result = cli_runner.invoke(
            kong_app,
            ["kong", "registry", "remove", "to-remove", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed" in result.output

        # Verify gone
        result = cli_runner.invoke(kong_app, ["kong", "registry", "list"])
        assert "to-remove" not in result.output

    def test_show_nonexistent_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Show should fail for non-existent service."""
        monkeypatch.setenv("HOME", str(temp_config_dir))

        result = cli_runner.invoke(kong_app, ["kong", "registry", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


@pytest.mark.e2e
@pytest.mark.kong
class TestRegistryImport:
    """Test registry import from YAML files."""

    def test_import_services_from_yaml(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Import multiple services from a YAML file."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Create import file
        import_file = temp_config_dir / "import.yaml"
        import_data = {
            "services": [
                {"name": "imported-api-1", "host": "api1.local", "port": 8080},
                {"name": "imported-api-2", "host": "api2.local", "port": 8081},
                {"name": "imported-api-3", "host": "api3.local", "port": 8082},
            ]
        }
        import_file.write_text(yaml.dump(import_data))

        # Import
        result = cli_runner.invoke(kong_app, ["kong", "registry", "import", str(import_file)])
        assert result.exit_code == 0
        assert "Imported" in result.output or "3" in result.output

        # Verify all imported
        result = cli_runner.invoke(kong_app, ["kong", "registry", "list"])
        assert "imported-api-1" in result.output
        assert "imported-api-2" in result.output
        assert "imported-api-3" in result.output

    def test_import_updates_existing(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Import should update existing services."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add initial service
        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "update-me", "--host", "old.local", "--port", "80"],
        )

        # Import with updated values
        import_file = temp_config_dir / "update.yaml"
        import_data = {
            "services": [
                {"name": "update-me", "host": "new.local", "port": 9090},
            ]
        }
        import_file.write_text(yaml.dump(import_data))

        cli_runner.invoke(kong_app, ["kong", "registry", "import", str(import_file)])

        # Verify updated
        result = cli_runner.invoke(kong_app, ["kong", "registry", "show", "update-me"])
        assert "new.local" in result.output
        assert "9090" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestRegistryDeploy:
    """Test registry deployment workflows."""

    def test_deploy_dry_run(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Deploy --dry-run should show changes without applying."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add services to registry
        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "dry-run-api", "--host", "dryrun.local"],
        )

        # Dry run deploy
        result = cli_runner.invoke(kong_app, ["kong", "registry", "deploy", "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower() or "Dry run" in result.output

    def test_deploy_single_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Deploy should support filtering to single service."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        # Add multiple services
        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "deploy-a", "--host", "a.local"],
        )
        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "deploy-b", "--host", "b.local"],
        )

        # Deploy only one
        result = cli_runner.invoke(
            kong_app,
            ["kong", "registry", "deploy", "--service", "deploy-a", "--dry-run"],
        )
        assert result.exit_code == 0
        # Should only show deploy-a in the diff
        assert "deploy-a" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestRegistryOutputFormats:
    """Test different output formats for registry commands."""

    def test_list_json_output(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """List should support JSON output."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "json-test", "--host", "json.local"],
        )

        result = cli_runner.invoke(kong_app, ["kong", "registry", "list", "--output", "json"])
        assert result.exit_code == 0
        # Should be valid JSON-ish output
        assert "json-test" in result.output
        assert "json.local" in result.output

    def test_list_yaml_output(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """List should support YAML output."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        cli_runner.invoke(
            kong_app,
            ["kong", "registry", "add", "yaml-test", "--host", "yaml.local"],
        )

        result = cli_runner.invoke(kong_app, ["kong", "registry", "list", "--output", "yaml"])
        assert result.exit_code == 0
        assert "yaml-test" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestRegistryIdempotency:
    """Test that registry operations are idempotent."""

    def test_import_twice_same_result(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Importing the same file twice should produce same result."""
        registry_dir = temp_config_dir / "ops" / "kong"
        registry_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(temp_config_dir))

        import_file = temp_config_dir / "idempotent.yaml"
        import_data = {
            "services": [
                {"name": "idem-api", "host": "idem.local", "port": 8080},
            ]
        }
        import_file.write_text(yaml.dump(import_data))

        # Import twice
        cli_runner.invoke(kong_app, ["kong", "registry", "import", str(import_file)])
        cli_runner.invoke(kong_app, ["kong", "registry", "import", str(import_file)])

        # List should show exactly one service
        result = cli_runner.invoke(kong_app, ["kong", "registry", "list"])
        assert result.output.count("idem-api") == 1  # Name appears once in table
