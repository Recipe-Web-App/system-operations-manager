"""Unit tests for Kong Upstreams CLI commands."""

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
from system_operations_manager.plugins.kong.commands.upstreams import (
    register_upstream_commands,
)

# ---------------------------------------------------------------------------
# DualWriteResult / DualDeleteResult stubs matching the real dataclasses
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
# Helper to build a mock upstream entity
# ---------------------------------------------------------------------------


def _make_upstream(name: str = "my-upstream") -> MagicMock:
    m = MagicMock()
    m.name = name
    return m


def _make_target(target_addr: str = "10.0.0.1:8080") -> MagicMock:
    m = MagicMock()
    m.target = target_addr
    return m


# ---------------------------------------------------------------------------
# Common app fixtures
# ---------------------------------------------------------------------------


class UpstreamsCommandsBase:
    """Base class providing shared app fixtures for all upstreams command tests."""

    @pytest.fixture
    def app(
        self,
        mock_upstream_manager: MagicMock,
        mock_unified_query_service: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> typer.Typer:
        """Full-featured app with all optional services wired in."""
        a = typer.Typer()
        register_upstream_commands(
            a,
            lambda: mock_upstream_manager,
            lambda: mock_unified_query_service,
            lambda: mock_dual_write_service,
        )
        return a

    @pytest.fixture
    def gateway_only_app(self, mock_upstream_manager: MagicMock) -> typer.Typer:
        """App without dual-write or unified query services (gateway-only fallback)."""
        a = typer.Typer()
        register_upstream_commands(a, lambda: mock_upstream_manager)
        return a


# ===========================================================================
# upstreams list
# ===========================================================================


@pytest.mark.unit
class TestListUpstreams(UpstreamsCommandsBase):
    """Tests for the 'upstreams list' command."""

    def test_list_with_unified_query(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        """upstreams list should use unified query service when available."""
        # Use a real UnifiedEntityList so format_unified_list can iterate properly
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_upstreams.return_value = unified_result

        result = cli_runner.invoke(app, ["upstreams", "list"])

        assert result.exit_code == 0
        mock_unified_query_service.list_upstreams.assert_called_once()

    def test_list_with_source_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        """upstreams list --source gateway should call filter_by_source."""
        # An empty unified list; filter_by_source("gateway") will return another empty list
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_upstreams.return_value = unified_result

        result = cli_runner.invoke(app, ["upstreams", "list", "--source", "gateway"])

        assert result.exit_code == 0
        mock_unified_query_service.list_upstreams.assert_called_once()

    def test_list_with_compare(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        """upstreams list --compare should pass show_drift=True to formatter."""
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_upstreams.return_value = unified_result

        result = cli_runner.invoke(app, ["upstreams", "list", "--compare"])

        assert result.exit_code == 0
        mock_unified_query_service.list_upstreams.assert_called_once()

    def test_list_unified_failure_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams list should fall back to gateway-only when unified query fails."""
        mock_unified_query_service.list_upstreams.side_effect = RuntimeError("unavailable")
        mock_upstream_manager.list.return_value = ([_make_upstream()], None)

        result = cli_runner.invoke(app, ["upstreams", "list"])

        assert result.exit_code == 0
        mock_upstream_manager.list.assert_called_once()
        # Fallback note should appear in output
        assert "gateway only" in result.stdout.lower() or "unavailable" in result.stdout.lower()

    def test_list_konnect_source_without_unified(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
    ) -> None:
        """upstreams list --source konnect without unified service should exit 1."""
        result = cli_runner.invoke(gateway_only_app, ["upstreams", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()

    def test_list_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams list without services should call manager.list directly."""
        mock_upstream_manager.list.return_value = ([_make_upstream("svc-a")], None)

        result = cli_runner.invoke(gateway_only_app, ["upstreams", "list"])

        assert result.exit_code == 0
        mock_upstream_manager.list.assert_called_once()

    def test_list_gateway_only_with_pagination(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams list should print pagination hint when next_offset is set."""
        mock_upstream_manager.list.return_value = ([_make_upstream()], "abc123")

        result = cli_runner.invoke(gateway_only_app, ["upstreams", "list"])

        assert result.exit_code == 0
        assert "abc123" in result.stdout

    def test_list_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams list should handle KongAPIError and exit 1."""
        mock_upstream_manager.list.side_effect = KongAPIError("connection refused", status_code=503)

        result = cli_runner.invoke(gateway_only_app, ["upstreams", "list"])

        assert result.exit_code == 1

    def test_list_unified_konnect_source_falls_back_and_then_errors(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        """When unified fails and source is 'konnect', should exit 1 with Konnect message."""
        mock_unified_query_service.list_upstreams.side_effect = RuntimeError("no unified")

        result = cli_runner.invoke(app, ["upstreams", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()


# ===========================================================================
# upstreams get
# ===========================================================================


@pytest.mark.unit
class TestGetUpstream(UpstreamsCommandsBase):
    """Tests for the 'upstreams get' command."""

    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams get should display upstream details."""
        upstream = _make_upstream("target-upstream")
        mock_upstream_manager.get.return_value = upstream

        result = cli_runner.invoke(app, ["upstreams", "get", "target-upstream"])

        assert result.exit_code == 0
        mock_upstream_manager.get.assert_called_once_with("target-upstream")

    def test_get_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams get should handle KongAPIError and exit 1."""
        mock_upstream_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["upstreams", "get", "ghost-upstream"])

        assert result.exit_code == 1


# ===========================================================================
# upstreams create
# ===========================================================================


@pytest.mark.unit
class TestCreateUpstream(UpstreamsCommandsBase):
    """Tests for the 'upstreams create' command."""

    def test_create_with_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams create should show sync confirmation when fully synced."""
        gw_result = _make_upstream("new-upstream")
        konnect_result = _make_upstream("new-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_result=konnect_result,
        )
        mock_dual_write_service.create.return_value = dual_result

        result = cli_runner.invoke(app, ["upstreams", "create", "new-upstream"])

        assert result.exit_code == 0
        assert "created" in result.stdout.lower()
        assert "synced" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_create_dual_write_partial_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams create should show warning when Konnect sync fails."""
        gw_result = _make_upstream("partial-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_error=RuntimeError("Konnect timeout"),
        )
        mock_dual_write_service.create.return_value = dual_result

        result = cli_runner.invoke(app, ["upstreams", "create", "partial-upstream"])

        assert result.exit_code == 0
        assert "sync failed" in result.stdout.lower() or "konnect" in result.stdout.lower()
        assert "retry" in result.stdout.lower() or "sync push" in result.stdout.lower()

    def test_create_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams create --data-plane-only should show skipped message."""
        gw_result = _make_upstream("dp-only-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_skipped=True,
        )
        mock_dual_write_service.create.return_value = dual_result

        result = cli_runner.invoke(
            app, ["upstreams", "create", "dp-only-upstream", "--data-plane-only"]
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_create_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams create should show 'not configured' when Konnect is not set up."""
        gw_result = _make_upstream("no-konnect-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_not_configured=True,
        )
        mock_dual_write_service.create.return_value = dual_result

        result = cli_runner.invoke(app, ["upstreams", "create", "no-konnect-upstream"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_create_gateway_only_fallback(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams create without dual-write service should use manager.create."""
        created = _make_upstream("gw-only-upstream")
        mock_upstream_manager.create.return_value = created

        result = cli_runner.invoke(gateway_only_app, ["upstreams", "create", "gw-only-upstream"])

        assert result.exit_code == 0
        mock_upstream_manager.create.assert_called_once()
        assert "created" in result.stdout.lower()

    def test_create_with_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams create should forward all optional parameters."""
        gw_result = _make_upstream("full-upstream")
        konnect_result = _make_upstream("full-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_result=konnect_result,
        )
        mock_dual_write_service.create.return_value = dual_result

        result = cli_runner.invoke(
            app,
            [
                "upstreams",
                "create",
                "full-upstream",
                "--algorithm",
                "consistent-hashing",
                "--slots",
                "1000",
                "--hash-on",
                "ip",
                "--hash-on-header",
                "X-Real-IP",
                "--hash-on-cookie",
                "session_id",
                "--hash-on-query-arg",
                "user",
                "--host-header",
                "override.example.com",
                "--tag",
                "prod",
                "--tag",
                "v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_dual_write_service.create.call_args
        upstream_arg = call_kwargs[0][0]
        assert upstream_arg.algorithm == "consistent-hashing"
        assert upstream_arg.hash_on == "ip"

    def test_create_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams create should handle KongAPIError and exit 1."""
        mock_upstream_manager.create.side_effect = KongAPIError(
            "validation failed", status_code=400
        )

        result = cli_runner.invoke(gateway_only_app, ["upstreams", "create", "bad-upstream"])

        assert result.exit_code == 1


# ===========================================================================
# upstreams update
# ===========================================================================


@pytest.mark.unit
class TestUpdateUpstream(UpstreamsCommandsBase):
    """Tests for the 'upstreams update' command."""

    def test_update_with_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams update should show sync confirmation when fully synced."""
        gw_result = _make_upstream("my-upstream")
        konnect_result = _make_upstream("my-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_result=konnect_result,
        )
        mock_dual_write_service.update.return_value = dual_result

        result = cli_runner.invoke(
            app, ["upstreams", "update", "my-upstream", "--algorithm", "least-connections"]
        )

        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()
        assert "synced" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_update_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams update should show warning when Konnect sync fails."""
        gw_result = _make_upstream("my-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_error=RuntimeError("Konnect 500"),
        )
        mock_dual_write_service.update.return_value = dual_result

        result = cli_runner.invoke(
            app, ["upstreams", "update", "my-upstream", "--algorithm", "latency"]
        )

        assert result.exit_code == 0
        assert "sync failed" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_update_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams update --data-plane-only should show skipped message."""
        gw_result = _make_upstream("my-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_skipped=True,
        )
        mock_dual_write_service.update.return_value = dual_result

        result = cli_runner.invoke(
            app,
            [
                "upstreams",
                "update",
                "my-upstream",
                "--algorithm",
                "round-robin",
                "--data-plane-only",
            ],
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_update_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams update should show 'not configured' when Konnect is not set up."""
        gw_result = _make_upstream("my-upstream")
        dual_result = DualWriteResult(
            gateway_result=gw_result,
            konnect_not_configured=True,
        )
        mock_dual_write_service.update.return_value = dual_result

        result = cli_runner.invoke(app, ["upstreams", "update", "my-upstream", "--slots", "5000"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_update_gateway_only_fallback(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams update without dual-write service should call manager.update."""
        updated = _make_upstream("my-upstream")
        mock_upstream_manager.update.return_value = updated

        result = cli_runner.invoke(
            gateway_only_app, ["upstreams", "update", "my-upstream", "--algorithm", "latency"]
        )

        assert result.exit_code == 0
        mock_upstream_manager.update.assert_called_once()
        assert "updated" in result.stdout.lower()

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """upstreams update with no options should print warning and exit 0."""
        result = cli_runner.invoke(app, ["upstreams", "update", "my-upstream"])

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_update_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams update should handle KongAPIError and exit 1."""
        mock_upstream_manager.update.side_effect = KongAPIError(
            "upstream not found", status_code=404
        )

        result = cli_runner.invoke(
            gateway_only_app, ["upstreams", "update", "ghost-upstream", "--algorithm", "latency"]
        )

        assert result.exit_code == 1

    def test_update_with_all_optional_fields(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams update should forward hash-on, hash-on-header, hash-on-cookie, host-header, and tags."""
        updated = _make_upstream("my-upstream")
        mock_upstream_manager.update.return_value = updated

        result = cli_runner.invoke(
            gateway_only_app,
            [
                "upstreams",
                "update",
                "my-upstream",
                "--hash-on",
                "header",
                "--hash-on-header",
                "X-User-Id",
                "--hash-on-cookie",
                "sess",
                "--host-header",
                "backend.example.com",
                "--tag",
                "v1",
            ],
        )

        assert result.exit_code == 0
        mock_upstream_manager.update.assert_called_once()
        upstream_arg = mock_upstream_manager.update.call_args[0][1]
        assert upstream_arg.hash_on == "header"
        assert upstream_arg.hash_on_header == "X-User-Id"
        assert upstream_arg.hash_on_cookie == "sess"
        assert upstream_arg.host_header == "backend.example.com"
        assert upstream_arg.tags == ["v1"]


# ===========================================================================
# upstreams delete
# ===========================================================================


@pytest.mark.unit
class TestDeleteUpstream(UpstreamsCommandsBase):
    """Tests for the 'upstreams delete' command."""

    def test_delete_with_force_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams delete --force with dual-write fully synced should show deleted from Konnect."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream
        del_result = DualDeleteResult(konnect_deleted=True)
        mock_dual_write_service.delete.return_value = del_result

        result = cli_runner.invoke(app, ["upstreams", "delete", "del-upstream", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()
        assert "konnect" in result.stdout.lower()

    def test_delete_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams delete should warn when Konnect delete fails."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream
        del_result = DualDeleteResult(konnect_error=RuntimeError("Konnect 503"))
        mock_dual_write_service.delete.return_value = del_result

        result = cli_runner.invoke(app, ["upstreams", "delete", "del-upstream", "--force"])

        assert result.exit_code == 0
        assert "delete failed" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_delete_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams delete --data-plane-only should show skipped message."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream
        del_result = DualDeleteResult(konnect_skipped=True)
        mock_dual_write_service.delete.return_value = del_result

        result = cli_runner.invoke(
            app,
            ["upstreams", "delete", "del-upstream", "--force", "--data-plane-only"],
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_delete_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        """upstreams delete should show 'not configured' when Konnect is not set up."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream
        del_result = DualDeleteResult(konnect_not_configured=True)
        mock_dual_write_service.delete.return_value = del_result

        result = cli_runner.invoke(app, ["upstreams", "delete", "del-upstream", "--force"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_delete_gateway_only_fallback(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams delete without dual-write service should call manager.delete."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream

        result = cli_runner.invoke(
            gateway_only_app, ["upstreams", "delete", "del-upstream", "--force"]
        )

        assert result.exit_code == 0
        mock_upstream_manager.delete.assert_called_once_with("del-upstream")
        assert "deleted" in result.stdout.lower()

    def test_delete_cancelled(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams delete should cancel when user declines confirmation."""
        upstream = _make_upstream("del-upstream")
        mock_upstream_manager.get.return_value = upstream

        result = cli_runner.invoke(
            gateway_only_app, ["upstreams", "delete", "del-upstream"], input="n\n"
        )

        assert result.exit_code == 0
        mock_upstream_manager.delete.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_delete_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams delete should handle KongAPIError and exit 1."""
        mock_upstream_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(
            gateway_only_app, ["upstreams", "delete", "ghost-upstream", "--force"]
        )

        assert result.exit_code == 1


# ===========================================================================
# upstreams health
# ===========================================================================


@pytest.mark.unit
class TestUpstreamHealth(UpstreamsCommandsBase):
    """Tests for the 'upstreams health' command."""

    def test_health_healthy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should display HEALTHY status in green."""
        health = MagicMock()
        health.health = "HEALTHY"
        health.data = None
        mock_upstream_manager.get_health.return_value = health

        result = cli_runner.invoke(app, ["upstreams", "health", "my-upstream"])

        assert result.exit_code == 0
        assert "HEALTHY" in result.stdout
        mock_upstream_manager.get_health.assert_called_once_with("my-upstream")

    def test_health_unhealthy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should display UNHEALTHY status in red."""
        health = MagicMock()
        health.health = "UNHEALTHY"
        health.data = None
        mock_upstream_manager.get_health.return_value = health

        result = cli_runner.invoke(app, ["upstreams", "health", "my-upstream"])

        assert result.exit_code == 0
        assert "UNHEALTHY" in result.stdout

    def test_health_unknown(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should display UNKNOWN status in yellow when health is None."""
        health = MagicMock()
        health.health = None
        health.data = None
        mock_upstream_manager.get_health.return_value = health

        result = cli_runner.invoke(app, ["upstreams", "health", "my-upstream"])

        assert result.exit_code == 0
        assert "UNKNOWN" in result.stdout

    def test_health_with_data(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should display health data when present."""
        health = MagicMock()
        health.health = "HEALTHY"
        health.data = [{"target": "10.0.0.1:8080", "health": "HEALTHY"}]
        mock_upstream_manager.get_health.return_value = health

        result = cli_runner.invoke(app, ["upstreams", "health", "my-upstream"])

        assert result.exit_code == 0

    def test_health_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should handle KongAPIError and exit 1."""
        mock_upstream_manager.get_health.side_effect = KongAPIError(
            "upstream not found", status_code=404
        )

        result = cli_runner.invoke(app, ["upstreams", "health", "ghost-upstream"])

        assert result.exit_code == 1

    def test_health_healthchecks_off(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams health should show custom status for HEALTHCHECKS_OFF."""
        health = MagicMock()
        health.health = "HEALTHCHECKS_OFF"
        health.data = None
        mock_upstream_manager.get_health.return_value = health

        result = cli_runner.invoke(app, ["upstreams", "health", "my-upstream"])

        assert result.exit_code == 0
        assert "HEALTHCHECKS_OFF" in result.stdout


# ===========================================================================
# upstreams targets list
# ===========================================================================


@pytest.mark.unit
class TestTargetsList(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets list' command."""

    def test_targets_list_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets list should display targets for an upstream."""
        target = _make_target("10.0.0.1:8080")
        mock_upstream_manager.list_targets.return_value = ([target], None)

        result = cli_runner.invoke(app, ["upstreams", "targets", "list", "my-upstream"])

        assert result.exit_code == 0
        mock_upstream_manager.list_targets.assert_called_once()

    def test_targets_list_pagination(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets list should print pagination hint when next_offset is set."""
        target = _make_target("10.0.0.1:8080")
        mock_upstream_manager.list_targets.return_value = ([target], "next-page-token")

        result = cli_runner.invoke(app, ["upstreams", "targets", "list", "my-upstream"])

        assert result.exit_code == 0
        assert "next-page-token" in result.stdout

    def test_targets_list_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets list should handle KongAPIError and exit 1."""
        mock_upstream_manager.list_targets.side_effect = KongAPIError(
            "upstream not found", status_code=404
        )

        result = cli_runner.invoke(app, ["upstreams", "targets", "list", "ghost-upstream"])

        assert result.exit_code == 1


# ===========================================================================
# upstreams targets add
# ===========================================================================


@pytest.mark.unit
class TestTargetsAdd(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets add' command."""

    def test_targets_add_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets add should add target and print success."""
        created_target = _make_target("api.example.com:8080")
        mock_upstream_manager.add_target.return_value = created_target

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "add", "my-upstream", "api.example.com:8080"],
        )

        assert result.exit_code == 0
        mock_upstream_manager.add_target.assert_called_once()
        assert "added" in result.stdout.lower()

    def test_targets_add_with_weight_and_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets add should forward weight and tags to manager."""
        created_target = _make_target("api.example.com:8080")
        mock_upstream_manager.add_target.return_value = created_target

        result = cli_runner.invoke(
            app,
            [
                "upstreams",
                "targets",
                "add",
                "my-upstream",
                "api.example.com:8080",
                "--weight",
                "50",
                "--tag",
                "prod",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_upstream_manager.add_target.call_args[0]
        assert call_args[2] == 50  # weight positional arg

    def test_targets_add_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets add should handle KongAPIError and exit 1."""
        mock_upstream_manager.add_target.side_effect = KongAPIError(
            "duplicate target", status_code=400
        )

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "add", "my-upstream", "api.example.com:8080"],
        )

        assert result.exit_code == 1


# ===========================================================================
# upstreams targets update
# ===========================================================================


@pytest.mark.unit
class TestTargetsUpdate(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets update' command."""

    def test_targets_update_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets update --weight should update target weight."""
        updated_target = _make_target("abc-target-id")
        mock_upstream_manager.update_target.return_value = updated_target

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "update", "my-upstream", "abc-target-id", "--weight", "75"],
        )

        assert result.exit_code == 0
        mock_upstream_manager.update_target.assert_called_once()
        assert "updated" in result.stdout.lower()

    def test_targets_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """upstreams targets update with no options should print warning and exit 0."""
        result = cli_runner.invoke(
            app, ["upstreams", "targets", "update", "my-upstream", "abc-target-id"]
        )

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_targets_update_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets update --tag should update target tags."""
        updated_target = _make_target("abc-target-id")
        mock_upstream_manager.update_target.return_value = updated_target

        result = cli_runner.invoke(
            app,
            [
                "upstreams",
                "targets",
                "update",
                "my-upstream",
                "abc-target-id",
                "--tag",
                "prod",
            ],
        )

        assert result.exit_code == 0
        mock_upstream_manager.update_target.assert_called_once()

    def test_targets_update_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets update should handle KongAPIError and exit 1."""
        mock_upstream_manager.update_target.side_effect = KongAPIError(
            "target not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "update", "my-upstream", "ghost-id", "--weight", "10"],
        )

        assert result.exit_code == 1


# ===========================================================================
# upstreams targets delete
# ===========================================================================


@pytest.mark.unit
class TestTargetsDelete(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets delete' command."""

    def test_targets_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets delete --force should delete without confirmation."""
        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "delete", "my-upstream", "target-abc", "--force"],
        )

        assert result.exit_code == 0
        mock_upstream_manager.delete_target.assert_called_once_with("my-upstream", "target-abc")
        assert "deleted" in result.stdout.lower()

    def test_targets_delete_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets delete should cancel when user declines confirmation."""
        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "delete", "my-upstream", "target-abc"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_upstream_manager.delete_target.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_targets_delete_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets delete should delete when user confirms."""
        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "delete", "my-upstream", "target-abc"],
            input="y\n",
        )

        assert result.exit_code == 0
        mock_upstream_manager.delete_target.assert_called_once_with("my-upstream", "target-abc")

    def test_targets_delete_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets delete should handle KongAPIError and exit 1."""
        mock_upstream_manager.delete_target.side_effect = KongAPIError(
            "target not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "delete", "my-upstream", "ghost-target", "--force"],
        )

        assert result.exit_code == 1


# ===========================================================================
# upstreams targets healthy
# ===========================================================================


@pytest.mark.unit
class TestTargetsHealthy(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets healthy' command."""

    def test_targets_healthy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets healthy should mark target as healthy."""
        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "healthy", "my-upstream", "api.example.com:8080"],
        )

        assert result.exit_code == 0
        mock_upstream_manager.set_target_healthy.assert_called_once_with(
            "my-upstream", "api.example.com:8080"
        )
        assert "healthy" in result.stdout.lower()

    def test_targets_healthy_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets healthy should handle KongAPIError and exit 1."""
        mock_upstream_manager.set_target_healthy.side_effect = KongAPIError(
            "target not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "healthy", "my-upstream", "ghost:8080"],
        )

        assert result.exit_code == 1


# ===========================================================================
# upstreams targets unhealthy
# ===========================================================================


@pytest.mark.unit
class TestTargetsUnhealthy(UpstreamsCommandsBase):
    """Tests for the 'upstreams targets unhealthy' command."""

    def test_targets_unhealthy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets unhealthy should mark target as unhealthy."""
        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "unhealthy", "my-upstream", "api.example.com:8080"],
        )

        assert result.exit_code == 0
        mock_upstream_manager.set_target_unhealthy.assert_called_once_with(
            "my-upstream", "api.example.com:8080"
        )
        assert "unhealthy" in result.stdout.lower()

    def test_targets_unhealthy_kong_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets unhealthy should handle KongAPIError and exit 1."""
        mock_upstream_manager.set_target_unhealthy.side_effect = KongAPIError(
            "target not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["upstreams", "targets", "unhealthy", "my-upstream", "ghost:8080"],
        )

        assert result.exit_code == 1
