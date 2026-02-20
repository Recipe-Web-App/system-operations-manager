"""Unit tests for Kong Consumers CLI commands."""

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
from system_operations_manager.plugins.kong.commands.consumers import (
    register_consumer_commands,
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
# Helpers
# ---------------------------------------------------------------------------


def _make_consumer(username: str = "my-user", custom_id: str | None = None) -> MagicMock:
    m = MagicMock()
    m.username = username
    m.custom_id = custom_id
    m.id = "consumer-id-123"
    return m


# ---------------------------------------------------------------------------
# Common app fixtures
# ---------------------------------------------------------------------------


class ConsumersCommandsBase:
    """Base class providing shared app fixtures for all consumer command tests."""

    @pytest.fixture
    def app(
        self,
        mock_consumer_manager: MagicMock,
        mock_unified_query_service: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> typer.Typer:
        a = typer.Typer()
        register_consumer_commands(
            a,
            lambda: mock_consumer_manager,
            lambda: mock_unified_query_service,
            lambda: mock_dual_write_service,
        )
        return a

    @pytest.fixture
    def gateway_only_app(self, mock_consumer_manager: MagicMock) -> typer.Typer:
        a = typer.Typer()
        register_consumer_commands(a, lambda: mock_consumer_manager)
        return a


# ===========================================================================
# consumers list
# ===========================================================================


@pytest.mark.unit
class TestListConsumers(ConsumersCommandsBase):
    """Tests for the 'consumers list' command."""

    def test_list_with_unified_query(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_consumers.return_value = unified_result

        result = cli_runner.invoke(app, ["consumers", "list"])

        assert result.exit_code == 0
        mock_unified_query_service.list_consumers.assert_called_once()

    def test_list_with_source_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_consumers.return_value = unified_result

        result = cli_runner.invoke(app, ["consumers", "list", "--source", "gateway"])

        assert result.exit_code == 0
        mock_unified_query_service.list_consumers.assert_called_once()

    def test_list_with_compare(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
    ) -> None:
        unified_result: UnifiedEntityList[Any] = UnifiedEntityList(entities=[])
        mock_unified_query_service.list_consumers.return_value = unified_result

        result = cli_runner.invoke(app, ["consumers", "list", "--compare"])

        assert result.exit_code == 0

    def test_list_unified_failure_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_query_service: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_unified_query_service.list_consumers.side_effect = RuntimeError("unavailable")
        mock_consumer_manager.list.return_value = ([_make_consumer()], None)

        result = cli_runner.invoke(app, ["consumers", "list"])

        assert result.exit_code == 0
        mock_consumer_manager.list.assert_called_once()

    def test_list_konnect_source_without_unified(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(gateway_only_app, ["consumers", "list", "--source", "konnect"])

        assert result.exit_code == 1
        assert "konnect" in result.stdout.lower()

    def test_list_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list.return_value = ([_make_consumer()], None)

        result = cli_runner.invoke(gateway_only_app, ["consumers", "list"])

        assert result.exit_code == 0
        mock_consumer_manager.list.assert_called_once()

    def test_list_gateway_only_with_pagination(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list.return_value = ([_make_consumer()], "next-page")

        result = cli_runner.invoke(gateway_only_app, ["consumers", "list"])

        assert result.exit_code == 0
        assert "next-page" in result.stdout

    def test_list_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list.side_effect = KongAPIError("fail", status_code=503)

        result = cli_runner.invoke(gateway_only_app, ["consumers", "list"])

        assert result.exit_code == 1


# ===========================================================================
# consumers get
# ===========================================================================


@pytest.mark.unit
class TestGetConsumer(ConsumersCommandsBase):
    """Tests for the 'consumers get' command."""

    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("test-user")

        result = cli_runner.invoke(app, ["consumers", "get", "test-user"])

        assert result.exit_code == 0
        mock_consumer_manager.get.assert_called_once_with("test-user")

    def test_get_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(app, ["consumers", "get", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# consumers create
# ===========================================================================


@pytest.mark.unit
class TestCreateConsumer(ConsumersCommandsBase):
    """Tests for the 'consumers create' command."""

    def test_create_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("new-user")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_consumer("new-user")
        )

        result = cli_runner.invoke(app, ["consumers", "create", "--username", "new-user"])

        assert result.exit_code == 0
        assert "created" in result.stdout.lower()
        assert "synced" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_create_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("new-user")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("timeout")
        )

        result = cli_runner.invoke(app, ["consumers", "create", "--username", "new-user"])

        assert result.exit_code == 0
        assert "sync failed" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_create_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("new-user")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app, ["consumers", "create", "--username", "new-user", "--data-plane-only"]
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_create_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("new-user")
        mock_dual_write_service.create.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(app, ["consumers", "create", "--username", "new-user"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_create_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.create.return_value = _make_consumer("new-user")

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "create", "--username", "new-user"]
        )

        assert result.exit_code == 0
        mock_consumer_manager.create.assert_called_once()
        assert "created" in result.stdout.lower()

    def test_create_no_username_or_custom_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["consumers", "create"])

        assert result.exit_code == 1
        assert "at least one" in result.stdout.lower()

    def test_create_with_custom_id(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.create.return_value = _make_consumer("", custom_id="cust-123")

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "create", "--custom-id", "cust-123"]
        )

        assert result.exit_code == 0
        mock_consumer_manager.create.assert_called_once()

    def test_create_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.create.side_effect = KongAPIError("duplicate", status_code=409)

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "create", "--username", "existing"]
        )

        assert result.exit_code == 1


# ===========================================================================
# consumers update
# ===========================================================================


@pytest.mark.unit
class TestUpdateConsumer(ConsumersCommandsBase):
    """Tests for the 'consumers update' command."""

    def test_update_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("updated-user")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_result=_make_consumer("updated-user")
        )

        result = cli_runner.invoke(
            app, ["consumers", "update", "my-user", "--username", "updated-user"]
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
        gw = _make_consumer("my-user")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_error=RuntimeError("fail")
        )

        result = cli_runner.invoke(
            app, ["consumers", "update", "my-user", "--username", "new-name"]
        )

        assert result.exit_code == 0
        assert "sync failed" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_update_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("my-user")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_skipped=True
        )

        result = cli_runner.invoke(
            app,
            ["consumers", "update", "my-user", "--username", "new", "--data-plane-only"],
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_update_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_dual_write_service: MagicMock,
    ) -> None:
        gw = _make_consumer("my-user")
        mock_dual_write_service.update.return_value = DualWriteResult(
            gateway_result=gw, konnect_not_configured=True
        )

        result = cli_runner.invoke(app, ["consumers", "update", "my-user", "--custom-id", "new-id"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_update_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.update.return_value = _make_consumer("my-user")

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "update", "my-user", "--username", "new"]
        )

        assert result.exit_code == 0
        mock_consumer_manager.update.assert_called_once()

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["consumers", "update", "my-user"])

        assert result.exit_code == 0
        assert "no updates" in result.stdout.lower()

    def test_update_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.update.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "update", "ghost", "--username", "new"]
        )

        assert result.exit_code == 1


# ===========================================================================
# consumers delete
# ===========================================================================


@pytest.mark.unit
class TestDeleteConsumer(ConsumersCommandsBase):
    """Tests for the 'consumers delete' command."""

    def test_delete_force_dual_write_synced(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_deleted=True)

        result = cli_runner.invoke(app, ["consumers", "delete", "del-user", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()
        assert "konnect" in result.stdout.lower()

    def test_delete_dual_write_partial(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")
        mock_dual_write_service.delete.return_value = DualDeleteResult(
            konnect_error=RuntimeError("503")
        )

        result = cli_runner.invoke(app, ["consumers", "delete", "del-user", "--force"])

        assert result.exit_code == 0
        assert "delete failed" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_delete_dual_write_skipped(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_skipped=True)

        result = cli_runner.invoke(
            app, ["consumers", "delete", "del-user", "--force", "--data-plane-only"]
        )

        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "data-plane-only" in result.stdout.lower()

    def test_delete_dual_write_not_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
        mock_dual_write_service: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")
        mock_dual_write_service.delete.return_value = DualDeleteResult(konnect_not_configured=True)

        result = cli_runner.invoke(app, ["consumers", "delete", "del-user", "--force"])

        assert result.exit_code == 0
        assert "not configured" in result.stdout.lower()

    def test_delete_gateway_only(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")

        result = cli_runner.invoke(gateway_only_app, ["consumers", "delete", "del-user", "--force"])

        assert result.exit_code == 0
        mock_consumer_manager.delete.assert_called_once_with("del-user")

    def test_delete_cancelled(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.get.return_value = _make_consumer("del-user")

        result = cli_runner.invoke(
            gateway_only_app, ["consumers", "delete", "del-user"], input="n\n"
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_delete_kong_api_error(
        self,
        cli_runner: CliRunner,
        gateway_only_app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.get.side_effect = KongAPIError("not found", status_code=404)

        result = cli_runner.invoke(gateway_only_app, ["consumers", "delete", "ghost", "--force"])

        assert result.exit_code == 1


# ===========================================================================
# consumers credentials list
# ===========================================================================


@pytest.mark.unit
class TestListCredentials(ConsumersCommandsBase):
    """Tests for the 'consumers credentials list' command."""

    def test_list_credentials_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        cred = MagicMock()
        cred.id = "cred-1"
        cred.key = "my-key"
        mock_consumer_manager.list_credentials.return_value = [cred]

        result = cli_runner.invoke(app, ["consumers", "credentials", "list", "my-user"])

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "key-auth")

    def test_list_credentials_jwt_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list_credentials.return_value = []

        result = cli_runner.invoke(
            app, ["consumers", "credentials", "list", "my-user", "--type", "jwt"]
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "jwt")

    def test_list_credentials_value_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list_credentials.side_effect = ValueError("unsupported type")

        result = cli_runner.invoke(
            app, ["consumers", "credentials", "list", "my-user", "--type", "bad-type"]
        )

        assert result.exit_code == 1

    def test_list_credentials_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list_credentials.side_effect = KongAPIError(
            "not found", status_code=404
        )

        result = cli_runner.invoke(app, ["consumers", "credentials", "list", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# consumers credentials add
# ===========================================================================


@pytest.mark.unit
class TestAddCredential(ConsumersCommandsBase):
    """Tests for the 'consumers credentials add' command."""

    def test_add_credential_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        cred = MagicMock()
        cred.name = "key-auth"
        mock_consumer_manager.add_credential.return_value = cred

        result = cli_runner.invoke(
            app,
            ["consumers", "credentials", "add", "my-user", "--config", "key=my-api-key"],
        )

        assert result.exit_code == 0
        assert "created" in result.stdout.lower()

    def test_add_credential_config_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        cred = MagicMock()
        cred.name = "jwt"
        mock_consumer_manager.add_credential.return_value = cred

        result = cli_runner.invoke(
            app,
            [
                "consumers",
                "credentials",
                "add",
                "my-user",
                "--type",
                "jwt",
                "--config-json",
                '{"key": "my-key", "algorithm": "RS256"}',
            ],
        )

        assert result.exit_code == 0

    def test_add_credential_invalid_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(
            app,
            [
                "consumers",
                "credentials",
                "add",
                "my-user",
                "--config-json",
                "not-json",
            ],
        )

        assert result.exit_code == 1

    def test_add_credential_value_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.add_credential.side_effect = ValueError("unsupported")

        result = cli_runner.invoke(
            app, ["consumers", "credentials", "add", "my-user", "--type", "bad"]
        )

        assert result.exit_code == 1

    def test_add_credential_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.add_credential.side_effect = KongAPIError(
            "consumer not found", status_code=404
        )

        result = cli_runner.invoke(app, ["consumers", "credentials", "add", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# consumers credentials delete
# ===========================================================================


@pytest.mark.unit
class TestDeleteCredential(ConsumersCommandsBase):
    """Tests for the 'consumers credentials delete' command."""

    def test_delete_credential_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            ["consumers", "credentials", "delete", "my-user", "cred-123", "--force"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_called_once_with(
            "my-user", "key-auth", "cred-123"
        )
        assert "deleted" in result.stdout.lower()

    def test_delete_credential_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            ["consumers", "credentials", "delete", "my-user", "cred-123"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_delete_credential_value_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.delete_credential.side_effect = ValueError("bad type")

        result = cli_runner.invoke(
            app,
            ["consumers", "credentials", "delete", "my-user", "cred-123", "--force"],
        )

        assert result.exit_code == 1

    def test_delete_credential_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.delete_credential.side_effect = KongAPIError(
            "not found", status_code=404
        )

        result = cli_runner.invoke(
            app,
            ["consumers", "credentials", "delete", "my-user", "ghost-cred", "--force"],
        )

        assert result.exit_code == 1


# ===========================================================================
# consumers acls list
# ===========================================================================


@pytest.mark.unit
class TestListAclGroups(ConsumersCommandsBase):
    """Tests for the 'consumers acls list' command."""

    def test_list_acl_groups_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        acl = MagicMock()
        acl.id = "acl-1"
        acl.group = "admin"
        mock_consumer_manager.list_acl_groups.return_value = [acl]

        result = cli_runner.invoke(app, ["consumers", "acls", "list", "my-user"])

        assert result.exit_code == 0
        mock_consumer_manager.list_acl_groups.assert_called_once_with("my-user")

    def test_list_acl_groups_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.list_acl_groups.side_effect = KongAPIError(
            "not found", status_code=404
        )

        result = cli_runner.invoke(app, ["consumers", "acls", "list", "ghost"])

        assert result.exit_code == 1


# ===========================================================================
# consumers acls add
# ===========================================================================


@pytest.mark.unit
class TestAddToAclGroup(ConsumersCommandsBase):
    """Tests for the 'consumers acls add' command."""

    def test_add_to_acl_group_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        acl = MagicMock()
        acl.group = "admin"
        mock_consumer_manager.add_to_acl_group.return_value = acl

        result = cli_runner.invoke(app, ["consumers", "acls", "add", "my-user", "admin"])

        assert result.exit_code == 0
        assert "added to group" in result.stdout.lower()

    def test_add_to_acl_group_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        acl = MagicMock()
        acl.group = "readers"
        mock_consumer_manager.add_to_acl_group.return_value = acl

        result = cli_runner.invoke(
            app, ["consumers", "acls", "add", "my-user", "readers", "--tag", "prod"]
        )

        assert result.exit_code == 0

    def test_add_to_acl_group_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.add_to_acl_group.side_effect = KongAPIError(
            "consumer not found", status_code=404
        )

        result = cli_runner.invoke(app, ["consumers", "acls", "add", "ghost", "admin"])

        assert result.exit_code == 1


# ===========================================================================
# consumers acls remove
# ===========================================================================


@pytest.mark.unit
class TestRemoveFromAclGroup(ConsumersCommandsBase):
    """Tests for the 'consumers acls remove' command."""

    def test_remove_from_acl_group_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app, ["consumers", "acls", "remove", "my-user", "acl-123", "--force"]
        )

        assert result.exit_code == 0
        mock_consumer_manager.remove_from_acl_group.assert_called_once_with("my-user", "acl-123")
        assert "removed" in result.stdout.lower()

    def test_remove_from_acl_group_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        result = cli_runner.invoke(
            app,
            ["consumers", "acls", "remove", "my-user", "acl-123"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.remove_from_acl_group.assert_not_called()
        assert "cancelled" in result.stdout.lower()

    def test_remove_from_acl_group_kong_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        mock_consumer_manager.remove_from_acl_group.side_effect = KongAPIError(
            "not found", status_code=404
        )

        result = cli_runner.invoke(
            app, ["consumers", "acls", "remove", "my-user", "ghost-acl", "--force"]
        )

        assert result.exit_code == 1
