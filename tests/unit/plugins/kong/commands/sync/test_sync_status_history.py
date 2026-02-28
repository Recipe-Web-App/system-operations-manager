"""Unit tests for sync status, history, and rollback commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.plugins.kong.commands.sync import (
    _display_sync_status_table,
    register_sync_commands,
)

# ===========================================================================
# _display_sync_status_table
# ===========================================================================


@pytest.mark.unit
class TestDisplaySyncStatusTable:
    """Tests for the _display_sync_status_table helper function."""

    def test_all_synced_no_extra_sections(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When all entities are synced, no drift/gateway-only/konnect-only sections."""
        summary = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 5, "drift": 0, "total": 5},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 3, "drift": 0, "total": 3},
        }
        mock_unified = MagicMock()
        _display_sync_status_table(summary, ["services", "routes"], mock_unified)
        # Should not call any list methods since no drift/gateway_only/konnect_only
        mock_unified.list_services.assert_not_called()

    def test_drift_shows_drifted_entities(self) -> None:
        """When entities have drift, should display drift details."""
        summary = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 1, "total": 2},
        }
        mock_unified = MagicMock()
        gateway_svc = Service(id="svc-1", name="my-api", host="new.local")
        konnect_svc = Service(id="svc-1", name="my-api", host="old.local")
        drifted = UnifiedEntity(
            entity=gateway_svc,
            source=EntitySource.BOTH,
            gateway_id="svc-1",
            konnect_id="k-svc-1",
            has_drift=True,
            drift_fields=["host"],
            gateway_entity=gateway_svc,
            konnect_entity=konnect_svc,
        )
        entity_list = UnifiedEntityList(entities=[drifted])
        mock_unified.list_services.return_value = entity_list

        _display_sync_status_table(summary, ["services"], mock_unified)
        mock_unified.list_services.assert_called()

    def test_gateway_only_entities(self) -> None:
        """When entities exist only in gateway, should show gateway-only section."""
        summary = {
            "services": {"gateway_only": 1, "konnect_only": 0, "synced": 0, "drift": 0, "total": 1},
        }
        mock_unified = MagicMock()
        svc = Service(id="svc-1", name="gw-only-api", host="local")
        entity = UnifiedEntity(
            entity=svc,
            source=EntitySource.GATEWAY,
            gateway_id="svc-1",
            konnect_id=None,
            has_drift=False,
            gateway_entity=svc,
        )
        mock_unified.list_services.return_value = UnifiedEntityList(entities=[entity])

        _display_sync_status_table(summary, ["services"], mock_unified)
        mock_unified.list_services.assert_called()

    def test_konnect_only_entities(self) -> None:
        """When entities exist only in konnect, should show konnect-only section."""
        summary = {
            "services": {"gateway_only": 0, "konnect_only": 1, "synced": 0, "drift": 0, "total": 1},
        }
        mock_unified = MagicMock()
        svc = Service(id="svc-1", name="konnect-only-api", host="remote")
        entity = UnifiedEntity(
            entity=svc,
            source=EntitySource.KONNECT,
            gateway_id=None,
            konnect_id="k-svc-1",
            has_drift=False,
            konnect_entity=svc,
        )
        mock_unified.list_services.return_value = UnifiedEntityList(entities=[entity])

        _display_sync_status_table(summary, ["services"], mock_unified)
        mock_unified.list_services.assert_called()

    def test_unknown_entity_type_skipped(self) -> None:
        """Entity types not in summary should be skipped gracefully."""
        summary = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 0, "total": 1},
        }
        mock_unified = MagicMock()
        # Include "unknown_type" in entity_types but not in summary
        _display_sync_status_table(summary, ["services", "unknown_type"], mock_unified)

    def test_get_entities_routes(self) -> None:
        """Internal _get_entities should call list_routes for 'routes'."""
        summary = {
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
        }
        mock_unified = MagicMock()
        mock_unified.list_routes.return_value = UnifiedEntityList(entities=[])
        _display_sync_status_table(summary, ["routes"], mock_unified)
        mock_unified.list_routes.assert_called()

    def test_get_entities_consumers(self) -> None:
        summary = {
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 1,
                "total": 1,
            },
        }
        mock_unified = MagicMock()
        mock_unified.list_consumers.return_value = UnifiedEntityList(entities=[])
        _display_sync_status_table(summary, ["consumers"], mock_unified)
        mock_unified.list_consumers.assert_called()

    def test_get_entities_plugins_upstreams(self) -> None:
        summary = {
            "plugins": {"gateway_only": 1, "konnect_only": 0, "synced": 0, "drift": 0, "total": 1},
            "upstreams": {
                "gateway_only": 1,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 1,
            },
        }
        mock_unified = MagicMock()
        mock_unified.list_plugins.return_value = UnifiedEntityList(entities=[])
        mock_unified.list_upstreams.return_value = UnifiedEntityList(entities=[])
        _display_sync_status_table(summary, ["plugins", "upstreams"], mock_unified)
        mock_unified.list_plugins.assert_called()
        mock_unified.list_upstreams.assert_called()

    def test_get_entities_cert_types(self) -> None:
        """Test certificate, SNI, CA cert, key_set, key, vault entity types."""
        summary = {
            "certificates": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 1,
                "total": 1,
            },
            "snis": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
            "ca_certificates": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 1,
                "total": 1,
            },
            "key_sets": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
            "keys": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
            "vaults": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
        }
        mock_unified = MagicMock()
        for method in [
            "list_certificates",
            "list_snis",
            "list_ca_certificates",
            "list_key_sets",
            "list_keys",
            "list_vaults",
        ]:
            getattr(mock_unified, method).return_value = UnifiedEntityList(entities=[])

        entity_types = ["certificates", "snis", "ca_certificates", "key_sets", "keys", "vaults"]
        _display_sync_status_table(summary, entity_types, mock_unified)

        for method in [
            "list_certificates",
            "list_snis",
            "list_ca_certificates",
            "list_key_sets",
            "list_keys",
            "list_vaults",
        ]:
            getattr(mock_unified, method).assert_called()

    def test_gateway_only_truncation_at_five(self) -> None:
        """When >5 gateway-only entities, should show '... and N more'."""
        summary = {
            "services": {"gateway_only": 7, "konnect_only": 0, "synced": 0, "drift": 0, "total": 7},
        }
        mock_unified = MagicMock()
        entities = []
        for i in range(7):
            svc = Service(id=f"svc-{i}", name=f"api-{i}", host="local")
            entities.append(
                UnifiedEntity(
                    entity=svc,
                    source=EntitySource.GATEWAY,
                    gateway_id=f"svc-{i}",
                    konnect_id=None,
                    has_drift=False,
                    gateway_entity=svc,
                )
            )
        mock_unified.list_services.return_value = UnifiedEntityList(entities=entities)

        _display_sync_status_table(summary, ["services"], mock_unified)
        mock_unified.list_services.assert_called()


# ===========================================================================
# sync status command
# ===========================================================================


@pytest.mark.unit
class TestSyncStatusCommand:
    """Tests for the sync status command."""

    @pytest.fixture
    def app(self, mock_unified_service: MagicMock) -> typer.Typer:
        test_app = typer.Typer()
        register_sync_commands(test_app, lambda: mock_unified_service)
        return test_app

    @pytest.fixture
    def app_no_konnect(self) -> typer.Typer:
        test_app = typer.Typer()
        register_sync_commands(test_app, lambda: None)
        return test_app

    def test_status_not_configured(
        self,
        cli_runner: CliRunner,
        app_no_konnect: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app_no_konnect, ["sync", "status"])
        assert result.exit_code == 1
        assert "not configured" in result.stdout.lower() or "konnect" in result.stdout.lower()

    def test_status_success_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["sync", "status"])
        assert result.exit_code == 0

    def test_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["sync", "status", "--output", "json"])
        assert result.exit_code == 0

    def test_status_filter_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["sync", "status", "--type", "services"])
        assert result.exit_code == 0
        mock_unified_service.get_sync_summary.assert_called_once_with(["services"])

    def test_status_invalid_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["sync", "status", "--type", "bananas"])
        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()

    def test_status_all_types_by_default(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        result = cli_runner.invoke(app, ["sync", "status"])
        assert result.exit_code == 0
        call_args = mock_unified_service.get_sync_summary.call_args[0][0]
        assert "services" in call_args
        assert "routes" in call_args


# ===========================================================================
# sync history command
# ===========================================================================


def _make_sync_summary(
    sync_id: str = "sync-123",
    operation: str = "push",
    dry_run: bool = False,
    created: int = 1,
    updated: int = 0,
    errors: int = 0,
) -> MagicMock:
    """Create a mock SyncSummary."""
    summary = MagicMock()
    summary.sync_id = sync_id
    summary.timestamp = "2026-02-19T10:00:00Z"
    summary.operation = operation
    summary.dry_run = dry_run
    summary.created = created
    summary.updated = updated
    summary.errors = errors
    return summary


def _make_audit_entry(
    sync_id: str = "sync-123",
    entity_type: str = "services",
    entity_name: str = "my-api",
    action: str = "create",
    status: str = "success",
    drift_fields: list[str] | None = None,
    error: str | None = None,
    operation: str = "push",
    dry_run: bool = False,
) -> MagicMock:
    """Create a mock SyncAuditEntry."""
    entry = MagicMock()
    entry.sync_id = sync_id
    entry.timestamp = "2026-02-19T10:00:00Z"
    entry.operation = operation
    entry.entity_type = entity_type
    entry.entity_name = entity_name
    entry.action = action
    entry.status = status
    entry.drift_fields = drift_fields
    entry.error = error
    entry.dry_run = dry_run
    entry.model_dump.return_value = {
        "sync_id": sync_id,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "action": action,
        "status": status,
    }
    return entry


@pytest.mark.unit
class TestSyncHistoryCommand:
    """Tests for the sync history command."""

    @pytest.fixture
    def app(self, mock_unified_service: MagicMock) -> typer.Typer:
        test_app = typer.Typer()
        register_sync_commands(test_app, lambda: mock_unified_service)
        return test_app

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_no_syncs(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.list_syncs.return_value = []
        result = cli_runner.invoke(app, ["sync", "history"])
        assert result.exit_code == 0
        assert "no sync" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_list_syncs_table(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.list_syncs.return_value = [
            _make_sync_summary("sync-abc", "push", created=2),
        ]
        result = cli_runner.invoke(app, ["sync", "history"])
        assert result.exit_code == 0
        assert "sync-abc" in result.stdout[:100] or "sync" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_list_syncs_json(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        summary = _make_sync_summary()
        summary.model_dump.return_value = {"sync_id": "sync-123", "operation": "push"}
        mock_audit_cls.return_value.list_syncs.return_value = [summary]
        result = cli_runner.invoke(app, ["sync", "history", "--output", "json"])
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_entity_history_success(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_entity_history.return_value = [
            _make_audit_entry(entity_name="my-api", drift_fields=["host"]),
        ]
        result = cli_runner.invoke(
            app, ["sync", "history", "--entity-type", "services", "--entity-name", "my-api"]
        )
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_entity_history_no_results(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_entity_history.return_value = []
        result = cli_runner.invoke(
            app, ["sync", "history", "--entity-type", "services", "--entity-name", "nonexistent"]
        )
        assert result.exit_code == 0
        assert "no sync history" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_entity_history_json(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_entity_history.return_value = [
            _make_audit_entry(),
        ]
        result = cli_runner.invoke(
            app,
            [
                "sync",
                "history",
                "--entity-type",
                "services",
                "--entity-name",
                "my-api",
                "--output",
                "json",
            ],
        )
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_entity_history_with_error(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_entity_history.return_value = [
            _make_audit_entry(status="failed", error="connection timeout"),
        ]
        result = cli_runner.invoke(
            app, ["sync", "history", "--entity-type", "services", "--entity-name", "my-api"]
        )
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_sync_details_found(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        entries = [
            _make_audit_entry(action="create", status="success"),
            _make_audit_entry(entity_name="other-api", action="update", status="success"),
        ]
        mock_audit_cls.return_value.get_sync_details.return_value = entries
        result = cli_runner.invoke(app, ["sync", "history", "--sync-id", "sync-123"])
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_sync_details_not_found(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_sync_details.return_value = []
        result = cli_runner.invoke(app, ["sync", "history", "--sync-id", "nonexistent"])
        assert result.exit_code == 1

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_sync_details_json(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.get_sync_details.return_value = [
            _make_audit_entry(),
        ]
        result = cli_runner.invoke(
            app, ["sync", "history", "--sync-id", "sync-123", "--output", "json"]
        )
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_sync_details_pull_direction(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        entries = [_make_audit_entry(operation="pull")]
        mock_audit_cls.return_value.get_sync_details.return_value = entries
        result = cli_runner.invoke(app, ["sync", "history", "--sync-id", "sync-123"])
        assert result.exit_code == 0
        assert "gateway" in result.stdout.lower() or "konnect" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_sync_details_with_errors(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        entries = [
            _make_audit_entry(action="create", status="success"),
            _make_audit_entry(
                entity_name="bad-api", action="create", status="failed", error="timeout"
            ),
        ]
        mock_audit_cls.return_value.get_sync_details.return_value = entries
        result = cli_runner.invoke(app, ["sync", "history", "--sync-id", "sync-123"])
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_since_filter(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.list_syncs.return_value = [_make_sync_summary()]
        result = cli_runner.invoke(app, ["sync", "history", "--since", "7d"])
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_since_no_results_shows_filter_hint(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.list_syncs.return_value = []
        result = cli_runner.invoke(app, ["sync", "history", "--since", "1h"])
        assert result.exit_code == 0
        assert "since" in result.stdout.lower() or "no sync" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_history_with_errors_in_syncs(
        self,
        mock_audit_cls: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        mock_audit_cls.return_value.list_syncs.return_value = [
            _make_sync_summary(errors=3),
        ]
        result = cli_runner.invoke(app, ["sync", "history"])
        assert result.exit_code == 0


# ===========================================================================
# sync rollback command
# ===========================================================================


@pytest.mark.unit
class TestSyncRollbackCommand:
    """Tests for the sync rollback command."""

    @pytest.fixture
    def full_app(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        mock_konnect_route_manager: MagicMock,
        mock_konnect_consumer_manager: MagicMock,
        mock_konnect_plugin_manager: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
    ) -> typer.Typer:
        mock_gw_service = MagicMock()
        mock_gw_route = MagicMock()
        mock_gw_consumer = MagicMock()
        mock_gw_plugin = MagicMock()
        mock_gw_upstream = MagicMock()
        test_app = typer.Typer()
        register_sync_commands(
            test_app,
            lambda: mock_unified_service,
            get_konnect_service_manager=lambda: mock_konnect_service_manager,
            get_konnect_route_manager=lambda: mock_konnect_route_manager,
            get_konnect_consumer_manager=lambda: mock_konnect_consumer_manager,
            get_konnect_plugin_manager=lambda: mock_konnect_plugin_manager,
            get_konnect_upstream_manager=lambda: mock_konnect_upstream_manager,
            get_gateway_service_manager=lambda: mock_gw_service,
            get_gateway_route_manager=lambda: mock_gw_route,
            get_gateway_consumer_manager=lambda: mock_gw_consumer,
            get_gateway_plugin_manager=lambda: mock_gw_plugin,
            get_gateway_upstream_manager=lambda: mock_gw_upstream,
        )
        return test_app

    def _make_preview(
        self,
        can_rollback: bool = True,
        operation: str = "push",
        warnings: list[str] | None = None,
        num_actions: int = 2,
    ) -> MagicMock:
        preview = MagicMock()
        preview.can_rollback = can_rollback
        preview.operation = operation
        preview.timestamp = "2026-02-19T10:00:00Z"
        preview.warnings = warnings or []
        actions = []
        for i in range(num_actions):
            action = MagicMock()
            action.entity_type = "services"
            action.entity_name = f"api-{i}"
            action.rollback_action = "delete" if i == 0 else "update"
            action.target = "konnect"
            actions.append(action)
        preview.actions = actions
        return preview

    def _make_rollback_result(
        self,
        success: bool = True,
        rolled_back: int = 2,
        skipped: int = 0,
        failed: int = 0,
        errors: list[str] | None = None,
    ) -> MagicMock:
        result = MagicMock()
        result.success = success
        result.rolled_back = rolled_back
        result.skipped = skipped
        result.failed = failed
        result.errors = errors or []
        return result

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_dry_run(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview()
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123", "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_cannot_rollback(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview(
            can_rollback=False, warnings=["Sync already rolled back"]
        )
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123"])
        assert result.exit_code == 1
        assert "cannot" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_force_success(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview()
        mock_rollback_cls.return_value.rollback.return_value = self._make_rollback_result()
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123", "--force"])
        assert result.exit_code == 0
        assert "complete" in result.stdout.lower()

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_force_with_errors(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview()
        mock_rollback_cls.return_value.rollback.return_value = self._make_rollback_result(
            success=False, failed=1, errors=["Failed to delete service api-0"]
        )
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123", "--force"])
        assert result.exit_code == 1

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_type_filter(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview()
        mock_rollback_cls.return_value.rollback.return_value = self._make_rollback_result()
        result = cli_runner.invoke(
            full_app, ["sync", "rollback", "sync-123", "--force", "--type", "services"]
        )
        assert result.exit_code == 0
        # Verify entity_types filter was passed
        mock_rollback_cls.return_value.preview_rollback.assert_called_once_with(
            "sync-123", ["services"]
        )

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_with_warnings(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview(
            warnings=["Some entities may have changed since the sync"]
        )
        mock_rollback_cls.return_value.rollback.return_value = self._make_rollback_result()
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123", "--force"])
        assert result.exit_code == 0

    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    def test_rollback_with_skipped(
        self,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        mock_rollback_cls.return_value.preview_rollback.return_value = self._make_preview()
        mock_rollback_cls.return_value.rollback.return_value = self._make_rollback_result(skipped=1)
        result = cli_runner.invoke(full_app, ["sync", "rollback", "sync-123", "--force"])
        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower()
