"""Unit tests for Kong service registry CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.service_registry import (
    DeploymentResult,
    ServiceAlreadyExistsError,
    ServiceDeployDiff,
    ServiceDeployResult,
    ServiceDeploySummary,
    ServiceNotFoundError,
    ServiceProtocol,
    ServiceRegistry,
    ServiceRegistryEntry,
)
from system_operations_manager.plugins.kong.commands.registry import (
    _display_deploy_results,
    _display_deploy_summary,
    _display_deployment_results,
    _display_target_results,
    register_registry_commands,
)


def _make_entry(
    name: str = "auth-service",
    host: str = "auth.local",
    port: int = 8080,
    protocol: ServiceProtocol = "http",
    *,
    openapi_spec: str | None = None,
    tags: list[str] | None = None,
    path: str | None = None,
    path_prefix: str | None = None,
) -> ServiceRegistryEntry:
    """Helper to create a ServiceRegistryEntry with sensible defaults."""
    return ServiceRegistryEntry(
        name=name,
        host=host,
        port=port,
        protocol=protocol,
        openapi_spec=openapi_spec,
        tags=tags,
        path=path,
        path_prefix=path_prefix,
    )


def _make_registry(*entries: ServiceRegistryEntry) -> ServiceRegistry:
    """Helper to create a ServiceRegistry with given entries."""
    return ServiceRegistry(services=list(entries))


class TestRegistryCommands:
    """Base class that sets up the app fixture used by all subclasses."""

    @pytest.fixture
    def app(
        self,
        mock_registry_manager: MagicMock,
        mock_service_manager: MagicMock,
        mock_openapi_sync_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with registry commands registered."""
        app = typer.Typer()
        register_registry_commands(
            app,
            lambda: mock_registry_manager,
            lambda: mock_service_manager,
            lambda: mock_openapi_sync_manager,
        )
        return app


# ---------------------------------------------------------------------------
# registry list
# ---------------------------------------------------------------------------


class TestRegistryList(TestRegistryCommands):
    """Tests for the registry list command."""

    @pytest.mark.unit
    def test_list_displays_services_in_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list should display registered services in a table."""
        entry = _make_entry("auth-service", "auth.local", 8080)
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list"])

        assert result.exit_code == 0
        mock_registry_manager.load.assert_called_once()
        assert "auth-service" in result.stdout
        assert "auth.local" in result.stdout

    @pytest.mark.unit
    def test_list_empty_registry_shows_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list should show a message when the registry is empty."""
        mock_registry_manager.load.return_value = _make_registry()
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list"])

        assert result.exit_code == 0
        assert "no services" in result.stdout.lower()

    @pytest.mark.unit
    def test_list_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list should support JSON output format."""
        entry = _make_entry("svc-a", "a.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list", "--output", "json"])

        assert result.exit_code == 0
        mock_registry_manager.load.assert_called_once()

    @pytest.mark.unit
    def test_list_yaml_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list should support YAML output format."""
        entry = _make_entry("svc-b", "b.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list", "--output", "yaml"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_list_shows_openapi_spec_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list table should show the OpenAPI spec filename."""
        entry = _make_entry("svc", "svc.local", openapi_spec="/path/to/spec.yaml")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list"])

        assert result.exit_code == 0
        assert "spec.yaml" in result.stdout

    @pytest.mark.unit
    def test_list_services_sorted_alphabetically(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry list should display services sorted by name."""
        entries = [
            _make_entry("zebra-svc", "z.local"),
            _make_entry("alpha-svc", "a.local"),
        ]
        mock_registry_manager.load.return_value = _make_registry(*entries)
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "list"])

        assert result.exit_code == 0
        alpha_pos = result.stdout.find("alpha-svc")
        zebra_pos = result.stdout.find("zebra-svc")
        assert alpha_pos < zebra_pos


# ---------------------------------------------------------------------------
# registry show
# ---------------------------------------------------------------------------


class TestRegistryShow(TestRegistryCommands):
    """Tests for the registry show command."""

    @pytest.mark.unit
    def test_show_displays_service_details(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry show should display details for a specific service."""
        entry = _make_entry("auth-service", "auth.local", 8080)
        mock_registry_manager.get_service.return_value = entry

        result = cli_runner.invoke(app, ["registry", "show", "auth-service"])

        assert result.exit_code == 0
        mock_registry_manager.get_service.assert_called_once_with("auth-service")
        assert "auth-service" in result.stdout
        assert "auth.local" in result.stdout
        assert "8080" in result.stdout

    @pytest.mark.unit
    def test_show_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry show should exit with code 1 when service is not found."""
        mock_registry_manager.get_service.return_value = None

        result = cli_runner.invoke(app, ["registry", "show", "missing-service"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_show_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry show should support JSON output."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.get_service.return_value = entry

        result = cli_runner.invoke(app, ["registry", "show", "auth-service", "--output", "json"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_show_displays_optional_fields(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry show should display optional fields when present."""
        entry = _make_entry(
            "svc",
            "svc.local",
            tags=["prod", "api"],
            openapi_spec="/path/to/spec.yaml",
            path="/api",
            path_prefix="/v1",
        )
        mock_registry_manager.get_service.return_value = entry

        result = cli_runner.invoke(app, ["registry", "show", "svc"])

        assert result.exit_code == 0
        assert "prod" in result.stdout
        assert "/api" in result.stdout


# ---------------------------------------------------------------------------
# registry add
# ---------------------------------------------------------------------------


class TestRegistryAdd(TestRegistryCommands):
    """Tests for the registry add command."""

    @pytest.mark.unit
    def test_add_service_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should add a service and print a success message."""
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(
            app,
            ["registry", "add", "new-service", "--host", "new.local", "--port", "9090"],
        )

        assert result.exit_code == 0
        mock_registry_manager.add_service.assert_called_once()
        assert "added" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_service_already_exists(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should exit with code 1 when the service already exists."""
        mock_registry_manager.add_service.side_effect = ServiceAlreadyExistsError("dupe-service")

        result = cli_runner.invoke(
            app,
            ["registry", "add", "dupe-service", "--host", "dupe.local"],
        )

        assert result.exit_code == 1
        assert "already exists" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_service_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should accept multiple --tag options."""
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(
            app,
            [
                "registry",
                "add",
                "tagged-svc",
                "--host",
                "tagged.local",
                "--tag",
                "prod",
                "--tag",
                "api",
            ],
        )

        assert result.exit_code == 0
        called_entry: ServiceRegistryEntry = mock_registry_manager.add_service.call_args[0][0]
        assert called_entry.tags is not None
        assert "prod" in called_entry.tags
        assert "api" in called_entry.tags

    @pytest.mark.unit
    def test_add_service_with_openapi_spec(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should accept --openapi-spec option."""
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(
            app,
            [
                "registry",
                "add",
                "spec-svc",
                "--host",
                "spec.local",
                "--openapi-spec",
                "/path/to/spec.yaml",
            ],
        )

        assert result.exit_code == 0
        called_entry: ServiceRegistryEntry = mock_registry_manager.add_service.call_args[0][0]
        assert called_entry.openapi_spec is not None

    @pytest.mark.unit
    def test_add_service_invalid_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should exit with code 1 for an invalid service name."""
        result = cli_runner.invoke(
            app,
            ["registry", "add", "invalid name!", "--host", "h.local"],
        )

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_service_with_protocol(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should accept --protocol option."""
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(
            app,
            ["registry", "add", "https-svc", "--host", "https.local", "--protocol", "https"],
        )

        assert result.exit_code == 0
        called_entry: ServiceRegistryEntry = mock_registry_manager.add_service.call_args[0][0]
        assert called_entry.protocol == "https"

    @pytest.mark.unit
    def test_add_service_strip_path_flag(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry add should accept --strip-path flag."""
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(
            app,
            ["registry", "add", "strip-svc", "--host", "strip.local", "--strip-path"],
        )

        assert result.exit_code == 0
        called_entry: ServiceRegistryEntry = mock_registry_manager.add_service.call_args[0][0]
        assert called_entry.strip_path is True


# ---------------------------------------------------------------------------
# registry edit
# ---------------------------------------------------------------------------


class TestRegistryEdit(TestRegistryCommands):
    """Tests for the registry edit command."""

    @pytest.mark.unit
    def test_edit_service_host(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should update the host for an existing service."""
        existing = _make_entry("auth-service", "old-host.local", 8080)
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "auth-service", "--host", "new-host.local"],
        )

        assert result.exit_code == 0
        mock_registry_manager.update_service.assert_called_once()
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.host == "new-host.local"

    @pytest.mark.unit
    def test_edit_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should exit with code 1 when the service is not found."""
        mock_registry_manager.get_service.return_value = None

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "missing-service", "--port", "9090"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_edit_service_port(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should update the port when specified."""
        existing = _make_entry("auth-service", "auth.local", 8080)
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "auth-service", "--port", "9090"],
        )

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.port == 9090

    @pytest.mark.unit
    def test_edit_service_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should replace tags when --tag is specified."""
        existing = _make_entry("auth-service", "auth.local", tags=["old-tag"])
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "auth-service", "--tag", "new-tag"],
        )

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.tags == ["new-tag"]

    @pytest.mark.unit
    def test_edit_service_openapi_spec(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should update the openapi_spec path."""
        existing = _make_entry("auth-service", "auth.local")
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "auth-service", "--openapi-spec", "/new/spec.yaml"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_edit_preserves_unchanged_fields(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should not change fields that were not specified."""
        existing = _make_entry("auth-service", "auth.local", port=8080, tags=["keep-me"])
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(
            app,
            ["registry", "edit", "auth-service", "--host", "new-host.local"],
        )

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.port == 8080
        assert updated.tags == ["keep-me"]


# ---------------------------------------------------------------------------
# registry remove
# ---------------------------------------------------------------------------


class TestRegistryRemove(TestRegistryCommands):
    """Tests for the registry remove command."""

    @pytest.mark.unit
    def test_remove_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry remove --force should remove the service without prompting."""
        result = cli_runner.invoke(
            app,
            ["registry", "remove", "auth-service", "--force"],
        )

        assert result.exit_code == 0
        mock_registry_manager.remove_service.assert_called_once_with("auth-service")
        assert "removed" in result.stdout.lower()

    @pytest.mark.unit
    def test_remove_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry remove should exit with code 1 when the service is not found."""
        mock_registry_manager.remove_service.side_effect = ServiceNotFoundError("ghost-svc")

        result = cli_runner.invoke(
            app,
            ["registry", "remove", "ghost-svc", "--force"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_remove_cancelled_by_user(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry remove should exit cleanly when user declines the confirmation."""
        result = cli_runner.invoke(
            app,
            ["registry", "remove", "auth-service"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_registry_manager.remove_service.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    @pytest.mark.unit
    def test_remove_confirmed_by_user(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry remove should remove the service when user confirms."""
        result = cli_runner.invoke(
            app,
            ["registry", "remove", "auth-service"],
            input="y\n",
        )

        assert result.exit_code == 0
        mock_registry_manager.remove_service.assert_called_once_with("auth-service")


# ---------------------------------------------------------------------------
# registry import
# ---------------------------------------------------------------------------


class TestRegistryImport(TestRegistryCommands):
    """Tests for the registry import command."""

    @pytest.mark.unit
    def test_import_from_file_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """registry import should import services from a YAML file."""
        services_file = tmp_path / "services.yaml"
        services_file.write_text("services:\n  - name: svc\n    host: svc.local\n")
        mock_registry_manager.import_from_file.return_value = 1
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "import", str(services_file)])

        assert result.exit_code == 0
        mock_registry_manager.import_from_file.assert_called_once()
        assert "imported" in result.stdout.lower()
        assert "1" in result.stdout

    @pytest.mark.unit
    def test_import_generic_exception(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """registry import should exit with code 1 on a generic exception."""
        services_file = tmp_path / "services.yaml"
        services_file.write_text("invalid content")
        mock_registry_manager.import_from_file.side_effect = RuntimeError("read error")

        result = cli_runner.invoke(app, ["registry", "import", str(services_file)])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_import_multiple_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """registry import should report the correct count when importing many services."""
        services_file = tmp_path / "services.yaml"
        services_file.write_text("services: []")
        mock_registry_manager.import_from_file.return_value = 5
        mock_registry_manager.config_path = Path("/config/services.yaml")

        result = cli_runner.invoke(app, ["registry", "import", str(services_file)])

        assert result.exit_code == 0
        assert "5" in result.stdout


# ---------------------------------------------------------------------------
# registry deploy
# ---------------------------------------------------------------------------


def _make_deploy_result(
    name: str,
    status: Literal["created", "updated", "unchanged", "failed"] = "created",
    *,
    routes_synced: int = 0,
    routes_status: Literal["synced", "skipped", "failed", "no_spec"] = "no_spec",
    error: str | None = None,
) -> ServiceDeployResult:
    """Helper to create a ServiceDeployResult."""
    return ServiceDeployResult(
        service_name=name,
        service_status=status,
        routes_synced=routes_synced,
        routes_status=routes_status,
        error=error,
    )


def _make_summary(
    *,
    creates: int = 1,
    updates: int = 0,
    unchanged: int = 0,
    diffs: list[ServiceDeployDiff] | None = None,
) -> ServiceDeploySummary:
    """Helper to create a ServiceDeploySummary."""
    if diffs is None:
        diffs = [
            ServiceDeployDiff(
                service_name="auth-service",
                operation="create",
                desired={"host": "auth.local", "port": 8080, "protocol": "http"},
            )
        ] * creates
    return ServiceDeploySummary(
        total_services=creates + updates + unchanged,
        creates=creates,
        updates=updates,
        unchanged=unchanged,
        diffs=diffs,
    )


class TestRegistryDeploy(TestRegistryCommands):
    """Tests for the registry deploy command."""

    @pytest.mark.unit
    def test_deploy_empty_registry(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should exit cleanly when the registry is empty."""
        mock_registry_manager.load.return_value = _make_registry()

        result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert "no services" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy --dry-run should show changes but not apply them."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(app, ["registry", "deploy", "--dry-run", "--gateway-only"])

        assert result.exit_code == 0
        assert "dry run" in result.stdout.lower()
        mock_registry_manager.deploy.assert_not_called()

    @pytest.mark.unit
    def test_deploy_no_changes_needed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should exit cleanly when all services are already in sync."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = ServiceDeploySummary(
            total_services=1,
            creates=0,
            updates=0,
            unchanged=1,
            diffs=[
                ServiceDeployDiff(
                    service_name="auth-service",
                    operation="unchanged",
                )
            ],
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(
                app,
                ["registry", "deploy", "--gateway-only", "--no-confirm"],
            )

        assert result.exit_code == 0
        assert "in sync" in result.stdout.lower() or "no changes" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_cancelled_by_user(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should exit cleanly when user cancels the confirmation."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(
                app,
                ["registry", "deploy", "--gateway-only"],
                input="n\n",
            )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_registry_manager.deploy.assert_not_called()

    @pytest.mark.unit
    def test_deploy_gateway_only_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
        mock_service_manager: MagicMock,
        mock_openapi_sync_manager: MagicMock,
    ) -> None:
        """registry deploy --gateway-only should deploy to Gateway only."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--gateway-only", "--no-confirm"],
        )

        assert result.exit_code == 0
        mock_registry_manager.deploy.assert_called_once()
        assert "successful" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_specific_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy --service should exit 1 when service is not in registry."""
        entry = _make_entry("existing-service", "existing.local")
        registry = _make_registry(entry)
        mock_registry_manager.load.return_value = registry

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--service", "ghost-service", "--no-confirm"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should handle KongAPIError gracefully."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.side_effect = KongAPIError(
            "connection refused", status_code=503
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(
                app,
                ["registry", "deploy", "--gateway-only", "--no-confirm"],
            )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_deploy_with_failed_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should exit 1 when gateway has failed service deployments."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "failed", error="timeout")],
            konnect_skipped=True,
        )

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--gateway-only", "--no-confirm"],
        )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_deploy_konnect_skipped_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy --gateway-only should show Konnect skipped message."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--gateway-only", "--no-confirm"],
        )

        assert result.exit_code == 0
        assert "gateway-only" in result.stdout.lower() or "skipped" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_with_routes_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should show routes synced count when applicable."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[
                _make_deploy_result(
                    "auth-service",
                    "created",
                    routes_synced=3,
                    routes_status="synced",
                )
            ],
            konnect_skipped=True,
        )

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--gateway-only", "--no-confirm"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_deploy_konnect_error_in_result(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry deploy should exit 1 when konnect_error is set in result."""
        entry = _make_entry("auth-service", "auth.local")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_error="Konnect API timeout",
        )

        result = cli_runner.invoke(
            app,
            ["registry", "deploy", "--gateway-only", "--no-confirm"],
        )

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower() or "error" in result.stdout.lower()


# ---------------------------------------------------------------------------
# registry edit - additional field-update paths
# ---------------------------------------------------------------------------


class TestRegistryEditAdditional(TestRegistryCommands):
    """Tests for uncovered edit-command field updates and validation error."""

    @pytest.mark.unit
    def test_edit_service_protocol(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit --protocol should update the protocol."""
        existing = _make_entry("svc", "svc.local")
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(app, ["registry", "edit", "svc", "--protocol", "https"])

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.protocol == "https"

    @pytest.mark.unit
    def test_edit_service_path(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit --path should update the service path."""
        existing = _make_entry("svc", "svc.local")
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(app, ["registry", "edit", "svc", "--path", "/api/v2"])

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.path == "/api/v2"

    @pytest.mark.unit
    def test_edit_service_path_prefix(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit --path-prefix should update the path prefix."""
        existing = _make_entry("svc", "svc.local")
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(app, ["registry", "edit", "svc", "--path-prefix", "/prefix"])

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.path_prefix == "/prefix"

    @pytest.mark.unit
    def test_edit_service_strip_path(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit --strip-path should update the strip_path flag."""
        existing = _make_entry("svc", "svc.local")
        mock_registry_manager.get_service.return_value = existing

        result = cli_runner.invoke(app, ["registry", "edit", "svc", "--strip-path"])

        assert result.exit_code == 0
        updated: ServiceRegistryEntry = mock_registry_manager.update_service.call_args[0][0]
        assert updated.strip_path is True

    @pytest.mark.unit
    def test_edit_validation_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """registry edit should show validation errors when data is invalid."""
        from pydantic import ValidationError as PydanticValidationError

        existing = _make_entry("svc", "svc.local")
        mock_registry_manager.get_service.return_value = existing

        # Patch so ServiceRegistryEntry(**updated_data) raises the error
        with patch(
            "system_operations_manager.plugins.kong.commands.registry.ServiceRegistryEntry",
            side_effect=PydanticValidationError.from_exception_data(
                title="ServiceRegistryEntry",
                line_errors=[
                    {
                        "type": "value_error",
                        "loc": ("port",),
                        "input": -1,
                        "ctx": {"error": ValueError("invalid port")},
                    }
                ],
            ),
        ):
            result = cli_runner.invoke(app, ["registry", "edit", "svc", "--port", "99999"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


# ---------------------------------------------------------------------------
# registry import - validation error path
# ---------------------------------------------------------------------------


class TestRegistryImportValidation(TestRegistryCommands):
    """Tests for the import PydanticValidationError path."""

    @pytest.mark.unit
    def test_import_pydantic_validation_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """registry import should show field-level errors on PydanticValidationError."""
        from pydantic import ValidationError as PydanticValidationError

        services_file = tmp_path / "bad.yaml"
        services_file.write_text("services:\n  - name: bad\n")
        mock_registry_manager.import_from_file.side_effect = (
            PydanticValidationError.from_exception_data(
                title="ServiceRegistryEntry",
                line_errors=[
                    {
                        "type": "missing",
                        "loc": ("host",),
                        "input": {},
                    }
                ],
            )
        )

        result = cli_runner.invoke(app, ["registry", "import", str(services_file)])

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()


# ---------------------------------------------------------------------------
# registry deploy - Konnect integration paths
# ---------------------------------------------------------------------------


class TestRegistryDeployKonnect(TestRegistryCommands):
    """Tests for deploy command Konnect integration paths."""

    def _setup_deploy(
        self,
        mock_registry_manager: MagicMock,
        *,
        has_openapi: bool = False,
    ) -> None:
        """Common setup for deploy tests with a single service entry."""
        entry = _make_entry(
            "auth-service",
            "auth.local",
            openapi_spec="/spec.yaml" if has_openapi else None,
        )
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=False,
            konnect=[_make_deploy_result("auth-service", "created")],
        )

    @pytest.mark.unit
    def test_deploy_with_konnect_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should resolve Konnect CP and display its name."""
        self._setup_deploy(mock_registry_manager)

        mock_cp = MagicMock()
        mock_cp.id = "cp-123"
        mock_cp.name = "my-control-plane"

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
            ) as mock_cfg_cls,
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectClient"
            ) as mock_client_cls,
        ):
            mock_config = MagicMock()
            mock_config.default_control_plane = "my-control-plane"
            mock_cfg_cls.load.return_value = mock_config

            mock_client = MagicMock()
            mock_client.find_control_plane.return_value = mock_cp
            mock_client_cls.return_value = mock_client

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert "my-control-plane" in result.stdout

    @pytest.mark.unit
    def test_deploy_konnect_no_cp_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should warn when no control plane is configured."""
        self._setup_deploy(mock_registry_manager)
        # Make deploy return gateway-only result since no CP
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
            ) as mock_cfg_cls,
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectClient"
            ) as mock_client_cls,
        ):
            mock_config = MagicMock()
            mock_config.default_control_plane = None
            mock_cfg_cls.load.return_value = mock_config
            mock_client_cls.return_value = MagicMock()

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert (
            "no control plane" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_deploy_konnect_config_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should warn and fall back to gateway-only on KonnectConfigError."""
        self._setup_deploy(mock_registry_manager)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg_cls:
            from system_operations_manager.integrations.konnect.exceptions import (
                KonnectConfigError,
            )

            mock_cfg_cls.load.side_effect = KonnectConfigError("not configured")

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower() or "konnect" in result.stdout.lower()

    @pytest.mark.unit
    def test_deploy_konnect_generic_exception(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should warn and fall back to gateway-only on a generic exception."""
        self._setup_deploy(mock_registry_manager)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg_cls:
            mock_cfg_cls.load.side_effect = ConnectionError("connection refused")

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert (
            "could not connect" in result.stdout.lower()
            or "deploying to gateway" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_deploy_konnect_client_close_called(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should close the Konnect client in the finally block."""
        self._setup_deploy(mock_registry_manager)

        mock_cp = MagicMock()
        mock_cp.id = "cp-123"
        mock_cp.name = "test-cp"

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
            ) as mock_cfg_cls,
            patch(
                "system_operations_manager.plugins.kong.commands.registry.KonnectClient"
            ) as mock_client_cls,
        ):
            mock_config = MagicMock()
            mock_config.default_control_plane = "test-cp"
            mock_cfg_cls.load.return_value = mock_config

            mock_client = MagicMock()
            mock_client.find_control_plane.return_value = mock_cp
            mock_client_cls.return_value = mock_client

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        mock_client.close.assert_called_once()

    @pytest.mark.unit
    def test_deploy_not_configured_message_in_targets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should show 'not configured' in deployment targets when no Konnect."""
        self._setup_deploy(mock_registry_manager)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[_make_deploy_result("auth-service", "created")],
            konnect_skipped=True,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg_cls:
            mock_cfg_cls.load.side_effect = Exception("no config")

            result = cli_runner.invoke(app, ["registry", "deploy", "--no-confirm"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower() or "skipped" in result.stdout.lower()


# ---------------------------------------------------------------------------
# registry deploy - OpenAPI route sync messages
# ---------------------------------------------------------------------------


class TestRegistryDeployOpenAPI(TestRegistryCommands):
    """Tests for deploy OpenAPI route sync messaging paths."""

    @pytest.mark.unit
    def test_deploy_with_openapi_specs_shows_route_sync_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should show OpenAPI route sync message when specs exist."""
        entry = _make_entry("api-svc", "api.local", openapi_spec="/spec.yaml")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = _make_summary(creates=1)
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[
                _make_deploy_result("api-svc", "created", routes_synced=3, routes_status="synced")
            ],
            konnect_skipped=True,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(
                app, ["registry", "deploy", "--gateway-only", "--no-confirm"]
            )

        assert result.exit_code == 0
        assert (
            "openapi" in result.stdout.lower() or "routes will be synced" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_deploy_openapi_no_changes_but_has_routes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_registry_manager: MagicMock,
    ) -> None:
        """Deploy should sync routes even when services are in sync if specs exist."""
        entry = _make_entry("api-svc", "api.local", openapi_spec="/spec.yaml")
        mock_registry_manager.load.return_value = _make_registry(entry)
        mock_registry_manager.calculate_diff.return_value = ServiceDeploySummary(
            total_services=1,
            creates=0,
            updates=0,
            unchanged=1,
            diffs=[ServiceDeployDiff(service_name="api-svc", operation="unchanged")],
        )
        mock_registry_manager.deploy.return_value = DeploymentResult(
            gateway=[
                _make_deploy_result("api-svc", "unchanged", routes_synced=2, routes_status="synced")
            ],
            konnect_skipped=True,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.KonnectConfig"
        ) as mock_cfg:
            mock_cfg.load.side_effect = Exception("no konnect")
            result = cli_runner.invoke(
                app, ["registry", "deploy", "--gateway-only", "--no-confirm"]
            )

        assert result.exit_code == 0
        assert (
            "routes will be synced" in result.stdout.lower() or "openapi" in result.stdout.lower()
        )


# ---------------------------------------------------------------------------
# _display_deploy_summary - helper function tests
# ---------------------------------------------------------------------------


class TestDisplayDeploySummary:
    """Tests for _display_deploy_summary helper."""

    @pytest.mark.unit
    def test_summary_non_table_output(self) -> None:
        """Non-table output should use formatter.format_dict."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        summary = _make_summary(creates=1, updates=1)
        with patch(
            "system_operations_manager.plugins.kong.commands.registry.get_formatter"
        ) as mock_get_fmt:
            mock_formatter = MagicMock()
            mock_get_fmt.return_value = mock_formatter
            _display_deploy_summary(summary, OutputFormat.JSON)

        mock_get_fmt.assert_called_once()
        mock_formatter.format_dict.assert_called_once()

    @pytest.mark.unit
    def test_summary_with_updates_table(self) -> None:
        """Table output should render updates table when updates exist."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        diffs = [
            ServiceDeployDiff(
                service_name="create-svc",
                operation="create",
                desired={"host": "c.local", "port": 80, "protocol": "http"},
            ),
            ServiceDeployDiff(
                service_name="update-svc",
                operation="update",
                changes={"host": ("old.local", "new.local")},
            ),
        ]
        summary = ServiceDeploySummary(
            total_services=2, creates=1, updates=1, unchanged=0, diffs=diffs
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_deploy_summary(summary, OutputFormat.TABLE)

        # Should have printed Panel, creates table, and updates table
        assert mock_console.print.call_count >= 3


# ---------------------------------------------------------------------------
# _display_deploy_results - helper function tests
# ---------------------------------------------------------------------------


class TestDisplayDeployResults:
    """Tests for _display_deploy_results helper."""

    @pytest.mark.unit
    def test_results_non_table_output(self) -> None:
        """Non-table output should use formatter."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        results = [_make_deploy_result("svc1", "created")]
        with patch(
            "system_operations_manager.plugins.kong.commands.registry.get_formatter"
        ) as mock_get_fmt:
            mock_formatter = MagicMock()
            mock_get_fmt.return_value = mock_formatter
            _display_deploy_results(results, OutputFormat.JSON)

        mock_formatter.format_dict.assert_called_once()

    @pytest.mark.unit
    def test_results_with_failures(self) -> None:
        """Failed deployments should print error table and raise typer.Exit(1)."""
        from click.exceptions import Exit as ClickExit

        from system_operations_manager.plugins.kong.formatters import OutputFormat

        results = [
            _make_deploy_result("ok-svc", "created"),
            _make_deploy_result("bad-svc", "failed", error="timeout"),
        ]

        with pytest.raises(ClickExit):
            _display_deploy_results(results, OutputFormat.TABLE)

    @pytest.mark.unit
    def test_results_all_successful(self) -> None:
        """Successful deployments should show summary without raising."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        results = [
            _make_deploy_result("svc1", "created", routes_synced=2, routes_status="synced"),
            _make_deploy_result("svc2", "updated"),
            _make_deploy_result("svc3", "unchanged"),
        ]

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_deploy_results(results, OutputFormat.TABLE)

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "successful" in output.lower() or "created" in output.lower()


# ---------------------------------------------------------------------------
# _display_deployment_results - helper function tests
# ---------------------------------------------------------------------------


class TestDisplayDeploymentResults:
    """Tests for _display_deployment_results helper."""

    @pytest.mark.unit
    def test_deployment_results_non_table_output(self) -> None:
        """Non-table output should use formatter for deployment results."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        deployment = DeploymentResult(
            gateway=[_make_deploy_result("svc", "created")],
            konnect=[_make_deploy_result("svc", "created")],
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.get_formatter"
        ) as mock_get_fmt:
            mock_formatter = MagicMock()
            mock_get_fmt.return_value = mock_formatter
            _display_deployment_results(deployment, "test-cp", OutputFormat.JSON)

        mock_formatter.format_dict.assert_called_once()

    @pytest.mark.unit
    def test_deployment_results_with_konnect(self) -> None:
        """Table output should display Konnect results section."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        deployment = DeploymentResult(
            gateway=[_make_deploy_result("svc", "created")],
            konnect=[_make_deploy_result("svc", "created")],
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_deployment_results(deployment, "my-cp", OutputFormat.TABLE)

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "my-cp" in output

    @pytest.mark.unit
    def test_deployment_results_konnect_summary(self) -> None:
        """Konnect summary line should show created/updated/unchanged/failed counts."""
        from system_operations_manager.plugins.kong.formatters import OutputFormat

        deployment = DeploymentResult(
            gateway=[_make_deploy_result("svc", "created")],
            konnect=[
                _make_deploy_result("svc1", "created"),
                _make_deploy_result("svc2", "updated"),
            ],
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_deployment_results(deployment, "cp-name", OutputFormat.TABLE)

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "konnect" in output.lower()


# ---------------------------------------------------------------------------
# _display_target_results - helper function tests
# ---------------------------------------------------------------------------


class TestDisplayTargetResults:
    """Tests for _display_target_results helper, route status variants."""

    @pytest.mark.unit
    def test_routes_status_skipped(self) -> None:
        """Target results should show 'skipped' for routes_status=skipped."""
        results = [_make_deploy_result("svc", "created", routes_status="skipped")]

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_target_results(results, "Gateway")

        mock_console.print.assert_called_once()

    @pytest.mark.unit
    def test_routes_status_failed(self) -> None:
        """Target results should show 'failed' for routes_status=failed."""
        results = [_make_deploy_result("svc", "created", routes_status="failed")]

        with patch(
            "system_operations_manager.plugins.kong.commands.registry.console"
        ) as mock_console:
            _display_target_results(results, "Gateway")

        mock_console.print.assert_called_once()
