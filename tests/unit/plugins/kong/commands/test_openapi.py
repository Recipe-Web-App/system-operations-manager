"""Unit tests for OpenAPI sync CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongNotFoundError,
)
from system_operations_manager.integrations.kong.models.openapi import (
    OpenAPISpec,
    SyncApplyResult,
    SyncChange,
    SyncOperationResult,
    SyncResult,
)
from system_operations_manager.plugins.kong.commands.openapi import (
    register_openapi_commands,
)
from system_operations_manager.services.kong.openapi_sync_manager import (
    BreakingChangeError,
    OpenAPIParseError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    title: str = "Test API",
    version: str = "1.0.0",
    operations: int = 2,
) -> OpenAPISpec:
    """Create a minimal OpenAPISpec for testing."""
    from system_operations_manager.integrations.kong.models.openapi import OpenAPIOperation

    ops = [
        OpenAPIOperation(path=f"/path{i}", method="GET", operation_id=f"op{i}")
        for i in range(operations)
    ]
    return OpenAPISpec(title=title, version=version, operations=ops)


def _make_sync_result(
    service_name: str = "auth-service",
    *,
    creates: list[SyncChange] | None = None,
    updates: list[SyncChange] | None = None,
    deletes: list[SyncChange] | None = None,
) -> SyncResult:
    """Create a SyncResult with optional change lists."""
    return SyncResult(
        service_name=service_name,
        creates=creates or [],
        updates=updates or [],
        deletes=deletes or [],
    )


def _make_change(
    operation: str = "create",
    route_name: str = "auth-service-getUsers",
    path: str = "/users",
    methods: list[str] | None = None,
    *,
    is_breaking: bool = False,
    breaking_reason: str | None = None,
    field_changes: dict[str, tuple[Any, Any]] | None = None,
) -> SyncChange:
    """Create a SyncChange for testing."""
    return SyncChange(
        operation=operation,  # type: ignore[arg-type]
        route_name=route_name,
        path=path,
        methods=methods or ["GET"],
        is_breaking=is_breaking,
        breaking_reason=breaking_reason,
        field_changes=field_changes,
    )


def _make_apply_result(
    service_name: str = "auth-service",
    *,
    succeeded: list[str] | None = None,
    failed: list[tuple[str, str]] | None = None,
) -> SyncApplyResult:
    """Create a SyncApplyResult with succeeded / failed operations."""
    ops: list[SyncOperationResult] = []
    for name in succeeded or []:
        ops.append(SyncOperationResult(operation="create", route_name=name, result="success"))
    for name, error in failed or []:
        ops.append(
            SyncOperationResult(operation="create", route_name=name, result="failed", error=error)
        )
    return SyncApplyResult(service_name=service_name, operations=ops)


class TestOpenAPICommands:
    """Base class that sets up the app fixture used by all subclasses."""

    @pytest.fixture
    def app(
        self,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
        mock_route_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with OpenAPI commands registered."""
        app = typer.Typer()
        register_openapi_commands(
            app,
            lambda: mock_openapi_sync_manager,
            lambda: mock_service_manager,
            lambda: mock_route_manager,
        )
        return app

    @pytest.fixture
    def spec_file(self, tmp_path: Path) -> Path:
        """Create a minimal YAML spec file on disk for tests that need an actual path."""
        f = tmp_path / "api-spec.yaml"
        f.write_text("openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'\npaths: {}\n")
        return f


# ---------------------------------------------------------------------------
# openapi sync-routes
# ---------------------------------------------------------------------------


class TestSyncRoutes(TestOpenAPICommands):
    """Tests for the openapi sync-routes command."""

    @pytest.mark.unit
    def test_sync_routes_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should report 'no changes' when routes are already in sync."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 0
        assert "no changes" in result.stdout.lower() or "in sync" in result.stdout.lower()
        mock_openapi_sync_manager.apply_sync.assert_not_called()

    @pytest.mark.unit
    def test_sync_routes_success_creates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should apply creates and report success."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change("create", "auth-service-getUsers")]
        )
        mock_openapi_sync_manager.apply_sync.return_value = _make_apply_result(
            succeeded=["auth-service-getUsers"]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service", "--force"],
        )

        assert result.exit_code == 0
        mock_openapi_sync_manager.apply_sync.assert_called_once()
        assert "successfully applied" in result.stdout.lower() or "1" in result.stdout

    @pytest.mark.unit
    def test_sync_routes_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes --dry-run should preview changes without applying them."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change()]
        )

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "dry run" in result.stdout.lower()
        mock_openapi_sync_manager.apply_sync.assert_not_called()

    @pytest.mark.unit
    def test_sync_routes_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should exit 1 when the target service does not exist in Kong."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_service_manager.get.side_effect = KongNotFoundError("service not found")

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "missing-service"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_sync_routes_breaking_change_without_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should exit 1 with breaking changes when --force is not used."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            deletes=[
                _make_change(
                    "delete",
                    "auth-service-deleteAll",
                    is_breaking=True,
                    breaking_reason="route removed",
                )
            ]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1
        assert "breaking" in result.stdout.lower() or "force" in result.stdout.lower()
        mock_openapi_sync_manager.apply_sync.assert_not_called()

    @pytest.mark.unit
    def test_sync_routes_breaking_change_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes --force should apply breaking changes."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            deletes=[_make_change("delete", is_breaking=True, breaking_reason="removed")]
        )
        mock_openapi_sync_manager.apply_sync.return_value = _make_apply_result(
            succeeded=["auth-service-getUsers"]
        )

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--force",
            ],
        )

        assert result.exit_code == 0
        mock_openapi_sync_manager.apply_sync.assert_called_once()

    @pytest.mark.unit
    def test_sync_routes_parse_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
    ) -> None:
        """sync-routes should exit 1 on OpenAPIParseError."""
        mock_openapi_sync_manager.parse_openapi.side_effect = OpenAPIParseError(
            "invalid spec", parse_error="missing info section"
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_sync_routes_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should handle KongAPIError gracefully."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.side_effect = KongAPIError(
            "gateway error", status_code=502
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_sync_routes_partial_failure(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should exit 1 when some operations fail."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[
                _make_change("create", "auth-service-getUsers"),
                _make_change("create", "auth-service-postUsers", "/users", ["POST"]),
            ]
        )
        mock_openapi_sync_manager.apply_sync.return_value = _make_apply_result(
            succeeded=["auth-service-getUsers"],
            failed=[("auth-service-postUsers", "conflict")],
        )

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--force",
            ],
        )

        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()

    @pytest.mark.unit
    def test_sync_routes_with_path_prefix(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes --path-prefix should pass prefix to generate_route_mappings."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--path-prefix",
                "/v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_openapi_sync_manager.generate_route_mappings.call_args
        assert call_kwargs.kwargs.get("path_prefix") == "/v2" or "/v2" in str(call_kwargs)

    @pytest.mark.unit
    def test_sync_routes_breaking_change_error_exception(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes should handle BreakingChangeError raised from apply_sync."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change()]
        )
        mock_openapi_sync_manager.apply_sync.side_effect = BreakingChangeError(
            [_make_change(is_breaking=True, breaking_reason="field removed")]
        )

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--force",
            ],
        )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_sync_routes_no_strip_path(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """sync-routes --no-strip-path should pass strip_path=False to the manager."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "sync-routes",
                str(spec_file),
                "--service",
                "auth-service",
                "--no-strip-path",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_openapi_sync_manager.generate_route_mappings.call_args
        assert call_kwargs.kwargs.get("strip_path") is False or "False" in str(call_kwargs)

    @pytest.mark.unit
    def test_sync_routes_parse_error_with_detail(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
    ) -> None:
        """sync-routes should print parse_error detail when present in OpenAPIParseError."""
        err = OpenAPIParseError("bad spec", parse_error="YAML syntax error on line 3")
        mock_openapi_sync_manager.parse_openapi.side_effect = err

        result = cli_runner.invoke(
            app,
            ["openapi", "sync-routes", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1
        assert "yaml syntax error" in result.stdout.lower() or "line 3" in result.stdout


# ---------------------------------------------------------------------------
# openapi diff
# ---------------------------------------------------------------------------


class TestDiffRoutes(TestOpenAPICommands):
    """Tests for the openapi diff command."""

    @pytest.mark.unit
    def test_diff_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should report 'no changes' when routes are in sync."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 0
        assert "no changes" in result.stdout.lower() or "in sync" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_shows_creates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should display routes to be created."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change("create", "auth-service-getUsers")]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 0
        assert "auth-service-getUsers" in result.stdout or "creates" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_shows_updates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should display routes to be updated."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        update_change = _make_change(
            "update",
            "auth-service-getUsers",
            field_changes={"methods": (["GET"], ["GET", "HEAD"])},
        )
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            updates=[update_change]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 0
        assert "auth-service-getUsers" in result.stdout or "updates" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_shows_deletes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should display routes to be deleted."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            deletes=[_make_change("delete", "auth-service-old", is_breaking=True)]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 0
        assert (
            "auth-service-old" in result.stdout
            or "deletes" in result.stdout.lower()
            or "breaking" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_diff_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should exit 1 when the target service does not exist in Kong."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_service_manager.get.side_effect = KongNotFoundError("service not found")

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "missing-service"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_parse_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
    ) -> None:
        """openapi diff should exit 1 on OpenAPIParseError."""
        mock_openapi_sync_manager.parse_openapi.side_effect = OpenAPIParseError("cannot parse spec")

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should handle KongAPIError gracefully."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.side_effect = KongAPIError(
            "admin api down", status_code=503
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service"],
        )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should support JSON output format."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change()]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service", "--output", "json"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_diff_yaml_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff should support YAML output format."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(
            creates=[_make_change()]
        )

        result = cli_runner.invoke(
            app,
            ["openapi", "diff", str(spec_file), "--service", "auth-service", "--output", "yaml"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_diff_verbose_shows_field_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff --verbose should display field-level changes for updates."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = [MagicMock()]
        update = _make_change(
            "update",
            field_changes={"strip_path": (True, False)},
        )
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result(updates=[update])

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(spec_file),
                "--service",
                "auth-service",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        # verbose mode shows "field: old -> new" format
        assert "strip_path" in result.stdout or "true" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_with_path_prefix(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff --path-prefix should pass the prefix to generate_route_mappings."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(spec_file),
                "--service",
                "auth-service",
                "--path-prefix",
                "/api/v1",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_openapi_sync_manager.generate_route_mappings.call_args
        assert call_kwargs.kwargs.get("path_prefix") == "/api/v1" or "/api/v1" in str(call_kwargs)

    @pytest.mark.unit
    def test_diff_no_changes_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        spec_file: Path,
        mock_openapi_sync_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """openapi diff with JSON output and no changes should still produce output."""
        mock_openapi_sync_manager.parse_openapi.return_value = _make_spec()
        mock_openapi_sync_manager.generate_route_mappings.return_value = []
        mock_openapi_sync_manager.calculate_diff.return_value = _make_sync_result()

        result = cli_runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(spec_file),
                "--service",
                "auth-service",
                "--output",
                "json",
            ],
        )

        # JSON/YAML path always runs the formatter, even with no changes
        assert result.exit_code == 0
