"""Unit tests for Kong Routes CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.unified import (
    UnifiedEntityList,
)
from system_operations_manager.plugins.kong.commands.routes import (
    register_route_commands,
)

# ---------------------------------------------------------------------------
# DualWriteResult / DualDeleteResult stubs
# ---------------------------------------------------------------------------


@dataclass
class DualWriteResult:
    gateway_result: MagicMock
    konnect_result: MagicMock | None = None
    konnect_error: Exception | None = None
    konnect_skipped: bool = False
    konnect_not_configured: bool = False

    @property
    def is_fully_synced(self) -> bool:
        return (
            self.konnect_result is not None
            and self.konnect_error is None
            and not self.konnect_skipped
        )

    @property
    def partial_success(self) -> bool:
        return self.konnect_error is not None


@dataclass
class DualDeleteResult:
    konnect_deleted: bool = False
    konnect_error: Exception | None = None
    konnect_skipped: bool = False
    konnect_not_configured: bool = False

    @property
    def is_fully_synced(self) -> bool:
        return self.konnect_deleted and self.konnect_error is None and not self.konnect_skipped

    @property
    def partial_success(self) -> bool:
        return self.konnect_error is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_route(name: str = "my-route") -> MagicMock:
    m = MagicMock()
    m.name = name
    m.id = "route-id-123"
    return m


# ---------------------------------------------------------------------------
# Common app fixtures
# ---------------------------------------------------------------------------


class RoutesCommandsBase:
    """Base class providing shared app fixtures."""

    @pytest.fixture
    def app(
        self,
        mock_route_manager: MagicMock,
        mock_unified_query_service: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> typer.Typer:
        a = typer.Typer()
        register_route_commands(
            a,
            lambda: mock_route_manager,
            lambda: mock_unified_query_service,
            lambda: mock_dual_write_service,
        )
        return a

    @pytest.fixture
    def gateway_only_app(self, mock_route_manager: MagicMock) -> typer.Typer:
        a = typer.Typer()
        register_route_commands(a, lambda: mock_route_manager)
        return a


# ===========================================================================
# routes list
# ===========================================================================


@pytest.mark.unit
class TestListRoutes(RoutesCommandsBase):
    """Tests for the 'routes list' command."""

    def test_list_with_unified_query(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_routes.return_value = unified_result

        result = cli_runner.invoke(app, ["routes", "list"])

        assert result.exit_code == 0
        mock_unified_query_service.list_routes.assert_called_once()

    def test_list_with_source_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_routes.return_value = unified_result

        result = cli_runner.invoke(app, ["routes", "list", "--source", "gateway"])

        assert result.exit_code == 0

    def test_list_with_compare(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_routes.return_value = unified_result

        result = cli_runner.invoke(app, ["routes", "list", "--compare"])

        assert result.exit_code == 0

    def test_list_unified_failure_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_unified_query_service.list_routes.side_effect = RuntimeError("unavailable")
        mock_route_manager.list.return_value = ([_make_route()], None)

        result = cli_runner.invoke(app, ["routes", "list"])

        assert result.exit_code == 0
        mock_route_manager.list.assert_called_once()

    def test_list_konnect_source_without_unified(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(gateway_only_app, ["routes", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()

    def test_list_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.list.return_value = ([_make_route()], None)

        result = cli_runner.invoke(gateway_only_app, ["routes", "list"])

        assert result.exit_code == 0
        mock_route_manager.list.assert_called_once()

    def test_list_by_service(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.list_by_service.return_value = ([_make_route()], None)

        result = cli_runner.invoke(gateway_only_app, ["routes", "list", "--service", "my-svc"])

        assert result.exit_code == 0
        mock_route_manager.list_by_service.assert_called_once()

    def test_list_gateway_only_with_pagination(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.list.return_value = ([_make_route()], "next-page")

        result = cli_runner.invoke(gateway_only_app, ["routes", "list"])

        assert result.exit_code == 0
        assert "next-page" in result.stdout

    def test_list_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.list.side_effect = KongAPIError("fail", status_code=503)

        result = cli_runner.invoke(gateway_only_app, ["routes", "list"])

        assert result.exit_code == 1


# ===========================================================================
# routes get
# ===========================================================================


@pytest.mark.unit
class TestGetRoute(RoutesCommandsBase):
    """Tests for the 'routes get' command."""

    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("test-route")

        result = cli_runner.invoke(app, ["routes", "get", "test-route"])

        assert result.exit_code == 0
        mock_route_manager.get.assert_called_once_with("test-route")

    def test_get_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["routes", "get", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# routes create
# ===========================================================================


@pytest.mark.unit
class TestCreateRoute(RoutesCommandsBase):
    """Tests for the 'routes create' command."""

    def test_create_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("new-route")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_route("new-route")
        )

        result = cli_runner.invoke(
            app, ["routes", "create", "--service", "my-svc", "--path", "/api"]
        )

        assert result.exit_code == 0
        assert "created" in result.stdout.lower()
        assert "synced" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_create_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("new-route")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("timeout")
        )

        result = cli_runner.invoke(
            app, ["routes", "create", "--service", "my-svc", "--path", "/api"]
        )

        assert result.exit_code == 0

    def test_create_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("new-route")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app,
            ["routes", "create", "--service", "my-svc", "--path", "/api", "--data-plane-only"],
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_create_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("new-route")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(
            app, ["routes", "create", "--service", "my-svc", "--path", "/api"]
        )

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_create_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.create.return_value = _make_route("new-route")

        result = cli_runner.invoke(
            gateway_only_app, ["routes", "create", "--service", "my-svc", "--path", "/api"]
        )

        assert result.exit_code == 0
        mock_route_manager.create.assert_called_once()

    def test_create_no_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["routes", "create", "--path", "/api"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower()

    def test_create_no_matching_criteria(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["routes", "create", "--service", "my-svc"])

        assert result.exit_code == 1
        assert "at least one" in result.stdout.lower()

    def test_create_with_all_options(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.create.return_value = _make_route("full-route")

        result = cli_runner.invoke(
            gateway_only_app,
            [
                "routes",
                "create",
                "--service",
                "my-svc",
                "--name",
                "full-route",
                "--path",
                "/api",
                "--method",
                "GET",
                "--host",
                "api.example.com",
                "--protocol",
                "https",
                "--no-strip-path",
                "--preserve-host",
                "--regex-priority",
                "10",
                "--tag",
                "prod",
            ],
        )

        assert result.exit_code == 0

    def test_create_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.create.side_effect = KongAPIError("bad request", status_code=400)

        result = cli_runner.invoke(
            gateway_only_app, ["routes", "create", "--service", "svc", "--path", "/x"]
        )

        assert result.exit_code == 1


# ===========================================================================
# routes update
# ===========================================================================


@pytest.mark.unit
class TestUpdateRoute(RoutesCommandsBase):
    """Tests for the 'routes update' command."""

    def test_update_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("my-route")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_route("my-route")
        )

        result = cli_runner.invoke(app, ["routes", "update", "my-route", "--path", "/api/v2"])

        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()

    def test_update_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("my-route")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("fail")
        )

        result = cli_runner.invoke(app, ["routes", "update", "my-route", "--path", "/api/v2"])

        assert result.exit_code == 0

    def test_update_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("my-route")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app, ["routes", "update", "my-route", "--path", "/v2", "--data-plane-only"]
        )

        assert result.exit_code == 0

    def test_update_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_route("my-route")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(app, ["routes", "update", "my-route", "--path", "/v2"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_update_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.update.return_value = _make_route("my-route")

        result = cli_runner.invoke(
            gateway_only_app, ["routes", "update", "my-route", "--path", "/v2"]
        )

        assert result.exit_code == 0
        mock_route_manager.update.assert_called_once()

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["routes", "update", "my-route"])

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_update_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.update.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(gateway_only_app, ["routes", "update", "ghost", "--path", "/v2"])

        assert result.exit_code == 1


# ===========================================================================
# routes delete
# ===========================================================================


@pytest.mark.unit
class TestDeleteRoute(RoutesCommandsBase):
    """Tests for the 'routes delete' command."""

    def test_delete_force_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_deleted=True)

        result = cli_runner.invoke(app, ["routes", "delete", "del-route", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_delete_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")
        mock_dual_write_service.delete.return_value = DualDeleteResult(
            konnect_error=RuntimeError("503")
        )

        result = cli_runner.invoke(app, ["routes", "delete", "del-route", "--force"])

        assert result.exit_code == 0

    def test_delete_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_skipped=True)

        result = cli_runner.invoke(
            app, ["routes", "delete", "del-route", "--force", "--data-plane-only"]
        )

        assert result.exit_code == 0

    def test_delete_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_not_configured=True)

        result = cli_runner.invoke(app, ["routes", "delete", "del-route", "--force"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_delete_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")

        result = cli_runner.invoke(gateway_only_app, ["routes", "delete", "del-route", "--force"])

        assert result.exit_code == 0
        mock_route_manager.delete.assert_called_once_with("del-route")

    def test_delete_cancelled(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.get.return_value = _make_route("del-route")

        result = cli_runner.invoke(gateway_only_app, ["routes", "delete", "del-route"], input="n\n")

        assert result.exit_code == 0
        mock_route_manager.delete.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_delete_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        mock_route_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(gateway_only_app, ["routes", "delete", "ghost", "--force"])

        assert result.exit_code == 1
