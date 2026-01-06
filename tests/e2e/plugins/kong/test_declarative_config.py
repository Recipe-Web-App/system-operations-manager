"""E2E tests for Kong declarative configuration workflows.

These tests verify the declarative config export/import cycle:
- Export current Kong state to YAML/JSON
- Validate configuration files
- Diff configuration against current state
- Apply configuration with dry-run and confirmation

Note: Kong runs in DB-less mode, so entities are created via config apply.
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
class TestConfigExport:
    """Test configuration export functionality."""

    def test_export_to_yaml(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Export current state to YAML file."""
        # First create some entities via config apply
        service_name = f"{unique_prefix}-export-svc"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
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
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to setup: {result.output}"

        # Export to YAML
        config_file = temp_config_dir / "kong.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0, f"Failed to export: {result.output}"
        assert config_file.exists()

        # Verify YAML is valid
        content = yaml.safe_load(config_file.read_text())
        assert "_format_version" in content
        assert "services" in content

        # Verify our service is in the export
        services = content.get("services", [])
        service_names = [s.get("name") for s in services]
        assert service_name in service_names

    def test_export_to_json(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Export current state to JSON file."""
        # Create a service via config apply
        service_name = f"{unique_prefix}-json-svc"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
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
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export to JSON
        config_file = temp_config_dir / "kong.json"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file), "--format", "json"],
        )
        assert result.exit_code == 0
        assert config_file.exists()

        # Verify JSON is valid
        import json

        content = json.loads(config_file.read_text())
        assert "_format_version" in content

    def test_export_with_only_filter(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Export only specific entity types."""
        # Create service and consumer via config apply
        service_name = f"{unique_prefix}-only-svc"
        username = f"{unique_prefix}-only-user"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "test.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "consumers": [{"username": username}],
        }
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export only services
        config_file = temp_config_dir / "services-only.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file), "--only", "services"],
        )
        assert result.exit_code == 0

        content = yaml.safe_load(config_file.read_text())
        # Services should be present
        assert "services" in content
        # Consumers should not be present (we only exported services)
        assert content.get("consumers", []) == [] or "consumers" not in content


@pytest.mark.e2e
@pytest.mark.kong
class TestConfigValidate:
    """Test configuration validation functionality."""

    def test_validate_exported_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Export config then validate it (should pass)."""
        # Create a service via config apply
        service_name = f"{unique_prefix}-validate-svc"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
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
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export
        config_file = temp_config_dir / "validate.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0

        # Validate
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "validate", str(config_file)],
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "error" not in result.output.lower()

    def test_validate_invalid_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
    ) -> None:
        """Validate an invalid config file (should fail)."""
        # Create an invalid config (route referencing non-existent service)
        config_file = temp_config_dir / "invalid.yaml"
        invalid_config = {
            "_format_version": "3.0",
            "services": [],
            "routes": [
                {
                    "name": "orphan-route",
                    "paths": ["/orphan"],
                    "service": {"name": "nonexistent-service"},
                }
            ],
        }
        config_file.write_text(yaml.dump(invalid_config))

        # Validate (should fail or show warnings)
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "validate", str(config_file)],
        )
        # Validation should report issues (exit code 1 or output contains error/warning)
        # The exact behavior depends on implementation
        assert (
            result.exit_code == 1
            or "error" in result.output.lower()
            or "warning" in result.output.lower()
        )


@pytest.mark.e2e
@pytest.mark.kong
class TestConfigDiff:
    """Test configuration diff functionality."""

    def test_diff_no_changes(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Diff exported config against current state (no changes)."""
        # Create a service via config apply
        service_name = f"{unique_prefix}-diff-svc"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
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
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export
        config_file = temp_config_dir / "diff.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0

        # Diff (should show no changes)
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "diff", str(config_file)],
        )
        assert result.exit_code == 0
        # Should indicate no changes (implementation may vary)
        assert (
            "no change" in result.output.lower()
            or "0 change" in result.output.lower()
            or "in sync" in result.output.lower()
        )

    def test_diff_with_new_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Diff config with a new service (should show create)."""
        # Export current (empty or minimal) state
        config_file = temp_config_dir / "diff-new.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0

        # Modify config to add a new service
        content = yaml.safe_load(config_file.read_text())
        if "services" not in content:
            content["services"] = []
        content["services"].append(
            {
                "name": f"{unique_prefix}-new-service",
                "host": "new-service.example.com",
                "port": 80,
                "protocol": "http",
            }
        )
        config_file.write_text(yaml.dump(content))

        # Diff (should show create)
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "diff", str(config_file)],
        )
        assert result.exit_code == 0
        # Should show some changes
        assert "create" in result.output.lower() or "1" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestConfigApply:
    """Test configuration apply functionality."""

    def test_apply_dry_run(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply with dry-run should not make changes."""
        # Create a config with a new service
        config_file = temp_config_dir / "apply-dry.yaml"
        service_name = f"{unique_prefix}-dryrun-svc"
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "dryrun.example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply with dry-run
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "would" in result.output.lower()

        # Verify service was NOT created
        result = cli_runner.invoke(
            kong_app,
            ["kong", "services", "get", service_name],
        )
        assert result.exit_code != 0  # Should not exist

    def test_apply_no_confirm(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply with --no-confirm should apply without prompting."""
        # Create a config with a new service
        config_file = temp_config_dir / "apply-noconfirm.yaml"
        service_name = f"{unique_prefix}-noconfirm-svc"
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "noconfirm.example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply with --no-confirm
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify service was created
        result = cli_runner.invoke(
            kong_app,
            ["kong", "services", "get", service_name],
        )
        assert result.exit_code == 0
        assert service_name in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestConfigExportImportCycle:
    """Test complete export-import cycle."""

    def test_export_modify_diff_apply_cycle(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Full cycle: export -> modify -> diff -> apply -> verify."""
        # 1. Create initial service via config apply
        initial_service = f"{unique_prefix}-initial-svc"
        setup_file = temp_config_dir / "setup.yaml"
        setup_config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": initial_service,
                    "host": "initial.example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
        }
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # 2. Export current state
        config_file = temp_config_dir / "cycle.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0

        # 3. Modify config - add another service
        content = yaml.safe_load(config_file.read_text())
        new_service = f"{unique_prefix}-added-svc"
        content["services"].append(
            {
                "name": new_service,
                "host": "added.example.com",
                "port": 80,
                "protocol": "http",
            }
        )
        config_file.write_text(yaml.dump(content))

        # 4. Diff to see changes
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "diff", str(config_file)],
        )
        assert result.exit_code == 0
        # Should show 1 create for the new service
        assert "create" in result.output.lower() or new_service in result.output

        # 5. Apply changes
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply: {result.output}"

        # 6. Verify both services exist
        result = cli_runner.invoke(kong_app, ["kong", "services", "list"])
        assert result.exit_code == 0
        # Check that both services are in the output
        # (names may be truncated in table display, so check for unique prefix)
        assert "Total: 2 entities" in result.output
        assert unique_prefix in result.output

    def test_export_contains_complete_state(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Verify export captures complete state (service, route, consumer)."""
        # Create complete setup via config apply
        service_name = f"{unique_prefix}-complete-svc"
        route_name = f"{unique_prefix}-complete-route"
        username = f"{unique_prefix}-complete-user"
        setup_file = temp_config_dir / "complete-setup.yaml"
        setup_config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "complete.example.com",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": ["/complete"],
                        }
                    ],
                }
            ],
            "consumers": [{"username": username}],
        }
        setup_file.write_text(yaml.dump(setup_config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(setup_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Export
        config_file = temp_config_dir / "complete.yaml"
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "export", str(config_file)],
        )
        assert result.exit_code == 0

        # Verify export contains all entities
        content = yaml.safe_load(config_file.read_text())

        # Check services
        services = content.get("services", [])
        service_names = [s.get("name") for s in services]
        assert service_name in service_names

        # Check routes
        routes = content.get("routes", [])
        route_names = [r.get("name") for r in routes]
        assert route_name in route_names

        # Check consumers
        consumers = content.get("consumers", [])
        consumer_names = [c.get("username") for c in consumers]
        assert username in consumer_names
