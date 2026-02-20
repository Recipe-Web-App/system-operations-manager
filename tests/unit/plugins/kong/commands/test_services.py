"""Unit tests for Kong Services CLI commands."""

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
from system_operations_manager.plugins.kong.commands.services import (
    register_service_commands,
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


def _make_service(name: str = "my-service") -> MagicMock:
    m = MagicMock()
    m.name = name
    m.id = "svc-id-123"
    return m


def _make_route(name: str = "my-route") -> MagicMock:
    m = MagicMock()
    m.name = name
    m.id = "route-id-123"
    return m


# ---------------------------------------------------------------------------
# Common app fixtures
# ---------------------------------------------------------------------------


class ServicesCommandsBase:
    """Base class providing shared app fixtures."""

    @pytest.fixture
    def app(
        self,
        mock_service_manager: MagicMock,
        mock_unified_query_service: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> typer.Typer:
        a = typer.Typer()
        register_service_commands(
            a,
            lambda: mock_service_manager,
            lambda: mock_unified_query_service,
            lambda: mock_dual_write_service,
        )
        return a

    @pytest.fixture
    def gateway_only_app(self, mock_service_manager: MagicMock) -> typer.Typer:
        a = typer.Typer()
        register_service_commands(a, lambda: mock_service_manager)
        return a


# ===========================================================================
# services list
# ===========================================================================


@pytest.mark.unit
class TestListServices(ServicesCommandsBase):
    """Tests for the 'services list' command."""

    def test_list_with_unified_query(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_services.return_value = unified_result

        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 0
        mock_unified_query_service.list_services.assert_called_once()

    def test_list_with_source_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_services.return_value = unified_result

        result = cli_runner.invoke(app, ["services", "list", "--source", "gateway"])

        assert result.exit_code == 0

    def test_list_with_compare(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_services.return_value = unified_result

        result = cli_runner.invoke(app, ["services", "list", "--compare"])

        assert result.exit_code == 0

    def test_list_unified_failure_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_unified_query_service.list_services.side_effect = RuntimeError("unavailable")
        mock_service_manager.list.return_value = ([_make_service()], None)

        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 0
        mock_service_manager.list.assert_called_once()

    def test_list_konnect_source_without_unified(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(gateway_only_app, ["services", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()

    def test_list_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.list.return_value = ([_make_service()], None)

        result = cli_runner.invoke(gateway_only_app, ["services", "list"])

        assert result.exit_code == 0
        mock_service_manager.list.assert_called_once()

    def test_list_gateway_only_with_pagination(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.list.return_value = ([_make_service()], "next-page")

        result = cli_runner.invoke(gateway_only_app, ["services", "list"])

        assert result.exit_code == 0
        assert "next-page" in result.stdout

    def test_list_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.list.side_effect = KongAPIError("fail", status_code=503)

        result = cli_runner.invoke(gateway_only_app, ["services", "list"])

        assert result.exit_code == 1


# ===========================================================================
# services get
# ===========================================================================


@pytest.mark.unit
class TestGetService(ServicesCommandsBase):
    """Tests for the 'services get' command."""

    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("test-svc")

        result = cli_runner.invoke(app, ["services", "get", "test-svc"])

        assert result.exit_code == 0
        mock_service_manager.get.assert_called_once_with("test-svc")

    def test_get_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["services", "get", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# services create
# ===========================================================================


@pytest.mark.unit
class TestCreateService(ServicesCommandsBase):
    """Tests for the 'services create' command."""

    def test_create_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("new-svc")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_service("new-svc")
        )

        result = cli_runner.invoke(
            app, ["services", "create", "--name", "new-svc", "--host", "api.example.com"]
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
        gw = _make_service("new-svc")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("timeout")
        )

        result = cli_runner.invoke(app, ["services", "create", "--host", "api.example.com"])

        assert result.exit_code == 0

    def test_create_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("new-svc")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app,
            ["services", "create", "--host", "api.example.com", "--data-plane-only"],
        )

        assert result.exit_code == 0

    def test_create_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("new-svc")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(app, ["services", "create", "--host", "api.example.com"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_create_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.create.return_value = _make_service("new-svc")

        result = cli_runner.invoke(
            gateway_only_app, ["services", "create", "--host", "api.example.com"]
        )

        assert result.exit_code == 0
        mock_service_manager.create.assert_called_once()

    def test_create_no_host_or_url(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["services", "create", "--name", "no-host"])

        assert result.exit_code == 1
        assert "host" in result.stdout.lower() or "url" in result.stdout.lower()

    def test_create_with_url(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.create.return_value = _make_service("url-svc")

        result = cli_runner.invoke(
            gateway_only_app,
            ["services", "create", "--url", "http://api.example.com:8080/v1"],
        )

        assert result.exit_code == 0

    def test_create_with_all_options(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.create.return_value = _make_service("full-svc")

        result = cli_runner.invoke(
            gateway_only_app,
            [
                "services",
                "create",
                "--name",
                "full-svc",
                "--host",
                "api.example.com",
                "--port",
                "8080",
                "--protocol",
                "https",
                "--path",
                "/v1",
                "--retries",
                "3",
                "--connect-timeout",
                "5000",
                "--write-timeout",
                "10000",
                "--read-timeout",
                "10000",
                "--tag",
                "prod",
            ],
        )

        assert result.exit_code == 0

    def test_create_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.create.side_effect = KongAPIError("duplicate", status_code=409)

        result = cli_runner.invoke(
            gateway_only_app, ["services", "create", "--host", "api.example.com"]
        )

        assert result.exit_code == 1


# ===========================================================================
# services update
# ===========================================================================


@pytest.mark.unit
class TestUpdateService(ServicesCommandsBase):
    """Tests for the 'services update' command."""

    def test_update_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("my-svc")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_service("my-svc")
        )

        result = cli_runner.invoke(
            app, ["services", "update", "my-svc", "--host", "new.example.com"]
        )

        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()

    def test_update_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("my-svc")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("fail")
        )

        result = cli_runner.invoke(app, ["services", "update", "my-svc", "--port", "8080"])

        assert result.exit_code == 0

    def test_update_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("my-svc")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app, ["services", "update", "my-svc", "--port", "8080", "--data-plane-only"]
        )

        assert result.exit_code == 0

    def test_update_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_service("my-svc")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(app, ["services", "update", "my-svc", "--port", "8080"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_update_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.update.return_value = _make_service("my-svc")

        result = cli_runner.invoke(
            gateway_only_app, ["services", "update", "my-svc", "--host", "new.example.com"]
        )

        assert result.exit_code == 0
        mock_service_manager.update.assert_called_once()

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["services", "update", "my-svc"])

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_update_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.update.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(
            gateway_only_app, ["services", "update", "ghost", "--host", "new.example.com"]
        )

        assert result.exit_code == 1


# ===========================================================================
# services delete
# ===========================================================================


@pytest.mark.unit
class TestDeleteService(ServicesCommandsBase):
    """Tests for the 'services delete' command."""

    def test_delete_force_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_deleted=True)

        result = cli_runner.invoke(app, ["services", "delete", "del-svc", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_delete_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")
        mock_dual_write_service.delete.return_value = DualDeleteResult(
            konnect_error=RuntimeError("503")
        )

        result = cli_runner.invoke(app, ["services", "delete", "del-svc", "--force"])

        assert result.exit_code == 0

    def test_delete_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_skipped=True)

        result = cli_runner.invoke(
            app, ["services", "delete", "del-svc", "--force", "--data-plane-only"]
        )

        assert result.exit_code == 0

    def test_delete_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_not_configured=True)

        result = cli_runner.invoke(app, ["services", "delete", "del-svc", "--force"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_delete_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")

        result = cli_runner.invoke(gateway_only_app, ["services", "delete", "del-svc", "--force"])

        assert result.exit_code == 0
        mock_service_manager.delete.assert_called_once_with("del-svc")

    def test_delete_cancelled(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get.return_value = _make_service("del-svc")

        result = cli_runner.invoke(gateway_only_app, ["services", "delete", "del-svc"], input="n\n")

        assert result.exit_code == 0
        mock_service_manager.delete.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_delete_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(gateway_only_app, ["services", "delete", "ghost", "--force"])

        assert result.exit_code == 1


# ===========================================================================
# services routes
# ===========================================================================


@pytest.mark.unit
class TestListServiceRoutes(ServicesCommandsBase):
    """Tests for the 'services routes' command."""

    def test_list_service_routes_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get_routes.return_value = [_make_route()]

        result = cli_runner.invoke(app, ["services", "routes", "my-svc"])

        assert result.exit_code == 0
        mock_service_manager.get_routes.assert_called_once_with("my-svc")

    def test_list_service_routes_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.get_routes.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["services", "routes", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# services enable
# ===========================================================================


@pytest.mark.unit
class TestEnableService(ServicesCommandsBase):
    """Tests for the 'services enable' command."""

    def test_enable_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.enable.return_value = _make_service("my-svc")

        result = cli_runner.invoke(app, ["services", "enable", "my-svc"])

        assert result.exit_code == 0
        mock_service_manager.enable.assert_called_once_with("my-svc")
        assert "enabled" in result.stdout.lower()

    def test_enable_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.enable.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["services", "enable", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# services disable
# ===========================================================================


@pytest.mark.unit
class TestDisableService(ServicesCommandsBase):
    """Tests for the 'services disable' command."""

    def test_disable_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.disable.return_value = _make_service("my-svc")

        result = cli_runner.invoke(app, ["services", "disable", "my-svc"])

        assert result.exit_code == 0
        mock_service_manager.disable.assert_called_once_with("my-svc")
        assert "disabled" in result.stdout.lower()

    def test_disable_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        mock_service_manager.disable.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["services", "disable", "ghost"])

        assert result.exit_code == 1
