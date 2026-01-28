"""Unit tests for RollbackService.

Tests the sync rollback functionality for reverting Kong sync operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
)
from system_operations_manager.services.kong.sync_rollback import (
    RollbackAction,
    RollbackPreview,
    RollbackResult,
    RollbackService,
)


@pytest.fixture
def audit_file(tmp_path: Path) -> Path:
    """Create a temporary audit file path."""
    return tmp_path / "test_audit.jsonl"


@pytest.fixture
def audit_service(audit_file: Path) -> SyncAuditService:
    """Create an audit service with a temporary file."""
    return SyncAuditService(audit_file=audit_file)


@pytest.fixture
def mock_gateway_manager() -> MagicMock:
    """Create a mock gateway manager."""
    manager = MagicMock()
    manager._model_class = MagicMock()
    manager._model_class.model_validate = MagicMock(return_value=MagicMock())
    return manager


@pytest.fixture
def mock_konnect_manager() -> MagicMock:
    """Create a mock Konnect manager."""
    manager = MagicMock()
    manager._model_class = MagicMock()
    manager._model_class.model_validate = MagicMock(return_value=MagicMock())
    return manager


@pytest.fixture
def gateway_managers(mock_gateway_manager: MagicMock) -> dict[str, Any]:
    """Create gateway managers dict."""
    return {"services": mock_gateway_manager, "routes": mock_gateway_manager}


@pytest.fixture
def konnect_managers(mock_konnect_manager: MagicMock) -> dict[str, Any]:
    """Create Konnect managers dict."""
    return {"services": mock_konnect_manager, "routes": mock_konnect_manager}


@pytest.fixture
def rollback_service(
    audit_service: SyncAuditService,
    gateway_managers: dict[str, Any],
    konnect_managers: dict[str, Any],
) -> RollbackService:
    """Create a rollback service."""
    return RollbackService(audit_service, gateway_managers, konnect_managers)


def make_audit_entry(
    sync_id: str,
    operation: str = "push",
    action: str = "create",
    entity_type: str = "services",
    entity_name: str = "test-service",
    status: str = "success",
    dry_run: bool = False,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
) -> SyncAuditEntry:
    """Helper to create audit entries."""
    source = "gateway" if operation == "push" else "konnect"
    target = "konnect" if operation == "push" else "gateway"
    return SyncAuditEntry(
        sync_id=sync_id,
        timestamp=datetime.now(UTC).isoformat(),
        operation=operation,
        dry_run=dry_run,
        entity_type=entity_type,
        entity_name=entity_name,
        action=action,
        source=source,
        target=target,
        status=status,
        before_state=before_state,
        after_state=after_state,
    )


class TestRollbackActionModel:
    """Tests for RollbackAction model."""

    @pytest.mark.unit
    def test_create_delete_action(self) -> None:
        """RollbackAction can represent a delete operation."""
        action = RollbackAction(
            entity_type="services",
            entity_id="svc-123",
            entity_name="api-service",
            original_action="create",
            rollback_action="delete",
            after_state={"id": "svc-123", "name": "api-service"},
            target="konnect",
        )
        assert action.rollback_action == "delete"
        assert action.entity_id == "svc-123"

    @pytest.mark.unit
    def test_create_restore_action(self) -> None:
        """RollbackAction can represent a restore operation."""
        action = RollbackAction(
            entity_type="services",
            entity_id="svc-123",
            entity_name="api-service",
            original_action="update",
            rollback_action="restore",
            before_state={"id": "svc-123", "host": "old.local"},
            after_state={"id": "svc-123", "host": "new.local"},
            target="konnect",
        )
        assert action.rollback_action == "restore"
        assert action.before_state == {"id": "svc-123", "host": "old.local"}


class TestRollbackPreviewModel:
    """Tests for RollbackPreview model."""

    @pytest.mark.unit
    def test_create_preview_with_actions(self) -> None:
        """RollbackPreview can contain multiple actions."""
        preview = RollbackPreview(
            sync_id="sync-123",
            operation="push",
            timestamp="2026-01-23T10:00:00Z",
            actions=[
                RollbackAction(
                    entity_type="services",
                    entity_id="svc-1",
                    entity_name="service-1",
                    original_action="create",
                    rollback_action="delete",
                    target="konnect",
                )
            ],
            warnings=[],
            can_rollback=True,
        )
        assert len(preview.actions) == 1
        assert preview.can_rollback is True

    @pytest.mark.unit
    def test_create_preview_with_warnings(self) -> None:
        """RollbackPreview can contain warnings."""
        preview = RollbackPreview(
            sync_id="sync-123",
            operation="push",
            timestamp="2026-01-23T10:00:00Z",
            actions=[],
            warnings=["Cannot rollback: missing state"],
            can_rollback=False,
        )
        assert len(preview.warnings) == 1
        assert preview.can_rollback is False


class TestRollbackResultModel:
    """Tests for RollbackResult model."""

    @pytest.mark.unit
    def test_create_success_result(self) -> None:
        """RollbackResult can represent success."""
        result = RollbackResult(
            sync_id="sync-123",
            success=True,
            rolled_back=3,
            failed=0,
            skipped=0,
            errors=[],
        )
        assert result.success is True
        assert result.rolled_back == 3

    @pytest.mark.unit
    def test_create_failure_result(self) -> None:
        """RollbackResult can represent failure."""
        result = RollbackResult(
            sync_id="sync-123",
            success=False,
            rolled_back=1,
            failed=2,
            skipped=0,
            errors=["Failed to delete service-1", "Failed to delete service-2"],
        )
        assert result.success is False
        assert result.failed == 2
        assert len(result.errors) == 2


class TestRollbackServicePreview:
    """Tests for RollbackService.preview_rollback."""

    @pytest.mark.unit
    def test_preview_not_found_sync(self, rollback_service: RollbackService) -> None:
        """preview_rollback returns error for unknown sync_id."""
        preview = rollback_service.preview_rollback("nonexistent-sync")

        assert preview.can_rollback is False
        assert "not found" in preview.warnings[0]

    @pytest.mark.unit
    def test_preview_dry_run_sync(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback rejects dry-run syncs."""
        entry = make_audit_entry(
            sync_id="dry-run-sync",
            dry_run=True,
            after_state={"id": "svc-1"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("dry-run-sync")

        assert preview.can_rollback is False
        assert "dry-run" in preview.warnings[0].lower()

    @pytest.mark.unit
    def test_preview_push_creates(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback generates delete actions for push creates."""
        entry = make_audit_entry(
            sync_id="push-sync",
            operation="push",
            action="create",
            entity_name="new-service",
            after_state={"id": "svc-123", "name": "new-service"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("push-sync")

        assert preview.can_rollback is True
        assert len(preview.actions) == 1
        assert preview.actions[0].rollback_action == "delete"
        assert preview.actions[0].entity_id == "svc-123"
        assert preview.actions[0].target == "konnect"

    @pytest.mark.unit
    def test_preview_push_updates(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback generates restore actions for push updates."""
        entry = make_audit_entry(
            sync_id="push-sync",
            operation="push",
            action="update",
            entity_name="updated-service",
            before_state={"id": "svc-123", "host": "old.local"},
            after_state={"id": "svc-123", "host": "new.local"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("push-sync")

        assert preview.can_rollback is True
        assert len(preview.actions) == 1
        assert preview.actions[0].rollback_action == "restore"
        assert preview.actions[0].before_state == {"id": "svc-123", "host": "old.local"}

    @pytest.mark.unit
    def test_preview_pull_creates(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback generates delete actions for pull creates."""
        entry = make_audit_entry(
            sync_id="pull-sync",
            operation="pull",
            action="create",
            entity_name="pulled-service",
            after_state={"id": "svc-456", "name": "pulled-service"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("pull-sync")

        assert preview.can_rollback is True
        assert len(preview.actions) == 1
        assert preview.actions[0].rollback_action == "delete"
        assert preview.actions[0].target == "gateway"

    @pytest.mark.unit
    def test_preview_filters_by_entity_type(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback filters by entity_types parameter."""
        # Create entries for services and routes
        for entity_type in ["services", "routes"]:
            entry = make_audit_entry(
                sync_id="mixed-sync",
                entity_type=entity_type,
                entity_name=f"{entity_type}-1",
                after_state={"id": f"{entity_type}-123"},
            )
            audit_service.record(entry)

        # Filter to services only
        preview = rollback_service.preview_rollback("mixed-sync", entity_types=["services"])

        assert len(preview.actions) == 1
        assert preview.actions[0].entity_type == "services"

    @pytest.mark.unit
    def test_preview_warns_on_missing_after_state_for_create(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback warns when create is missing after_state."""
        entry = make_audit_entry(
            sync_id="incomplete-sync",
            action="create",
            after_state=None,  # Missing!
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("incomplete-sync")

        assert len(preview.actions) == 0
        assert len(preview.warnings) == 1
        assert "missing after_state" in preview.warnings[0]

    @pytest.mark.unit
    def test_preview_warns_on_missing_before_state_for_update(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback warns when update is missing before_state."""
        entry = make_audit_entry(
            sync_id="incomplete-sync",
            action="update",
            before_state=None,  # Missing!
            after_state={"id": "svc-123"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("incomplete-sync")

        assert len(preview.actions) == 0
        assert len(preview.warnings) == 1
        assert "missing before_state" in preview.warnings[0]

    @pytest.mark.unit
    def test_preview_skips_failed_entries(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback skips entries with status='failed'."""
        entry = make_audit_entry(
            sync_id="partial-sync",
            status="failed",
            after_state={"id": "svc-123"},
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("partial-sync")

        assert len(preview.actions) == 0
        assert preview.can_rollback is False

    @pytest.mark.unit
    def test_preview_skips_skip_actions(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback skips entries with action='skip'."""
        entry = make_audit_entry(
            sync_id="skip-sync",
            action="skip",
            status="success",
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("skip-sync")

        assert len(preview.actions) == 0


class TestRollbackServiceRollback:
    """Tests for RollbackService.rollback."""

    @pytest.mark.unit
    def test_rollback_deletes_created_entities(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback deletes entities that were created in push."""
        entry = make_audit_entry(
            sync_id="push-sync",
            operation="push",
            action="create",
            after_state={"id": "svc-123"},
        )
        audit_service.record(entry)

        result = rollback_service.rollback("push-sync")

        assert result.success is True
        assert result.rolled_back == 1
        mock_konnect_manager.delete.assert_called_once_with("svc-123")

    @pytest.mark.unit
    def test_rollback_restores_updated_entities(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback restores before_state for updated entities."""
        entry = make_audit_entry(
            sync_id="push-sync",
            operation="push",
            action="update",
            before_state={"id": "svc-123", "host": "old.local"},
            after_state={"id": "svc-123", "host": "new.local"},
        )
        audit_service.record(entry)

        result = rollback_service.rollback("push-sync")

        assert result.success is True
        assert result.rolled_back == 1
        mock_konnect_manager.update.assert_called_once()

    @pytest.mark.unit
    def test_rollback_processes_in_reverse_order(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback processes actions in reverse order."""
        # First a service was created, then a route
        for i, entity_type in enumerate(["services", "routes"]):
            entry = make_audit_entry(
                sync_id="multi-sync",
                entity_type=entity_type,
                entity_name=f"{entity_type}-1",
                after_state={"id": f"{entity_type}-{i}"},
            )
            audit_service.record(entry)

        rollback_service.rollback("multi-sync")

        # Route should be deleted before service (reverse order)
        calls = mock_konnect_manager.delete.call_args_list
        assert len(calls) == 2
        # routes-1 should be deleted first (second entry, reversed)
        assert calls[0][0][0] == "routes-1"
        assert calls[1][0][0] == "services-0"

    @pytest.mark.unit
    def test_rollback_handles_partial_failures(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback handles failures gracefully with force=True."""
        # Create two entries
        for i in range(2):
            entry = make_audit_entry(
                sync_id="fail-sync",
                entity_name=f"service-{i}",
                after_state={"id": f"svc-{i}"},
            )
            audit_service.record(entry)

        # First delete fails, second succeeds
        mock_konnect_manager.delete.side_effect = [Exception("API error"), None]

        result = rollback_service.rollback("fail-sync", force=True)

        assert result.success is False
        assert result.rolled_back == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    @pytest.mark.unit
    def test_rollback_stops_on_error_without_force(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback stops on first error when force=False."""
        # Create two entries
        for i in range(2):
            entry = make_audit_entry(
                sync_id="fail-sync",
                entity_name=f"service-{i}",
                after_state={"id": f"svc-{i}"},
            )
            audit_service.record(entry)

        # First delete fails
        mock_konnect_manager.delete.side_effect = Exception("API error")

        result = rollback_service.rollback("fail-sync", force=False)

        assert result.success is False
        assert result.failed == 1
        # Should have only attempted one delete
        assert mock_konnect_manager.delete.call_count == 1

    @pytest.mark.unit
    def test_rollback_skips_on_missing_entity_id(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback skips when entity_id cannot be determined."""
        entry = make_audit_entry(
            sync_id="bad-sync",
            after_state={"name": "no-id-service"},  # No "id" field
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("bad-sync")

        assert len(preview.actions) == 0
        assert len(preview.warnings) == 1
        assert "no ID" in preview.warnings[0]

    @pytest.mark.unit
    def test_rollback_fails_when_not_rollbackable(self, rollback_service: RollbackService) -> None:
        """rollback returns failure for non-rollbackable syncs."""
        result = rollback_service.rollback("nonexistent-sync")

        assert result.success is False
        assert result.rolled_back == 0
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_rollback_respects_entity_type_filter(
        self,
        rollback_service: RollbackService,
        audit_service: SyncAuditService,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """rollback only processes specified entity types."""
        # Create entries for services and routes
        for entity_type in ["services", "routes"]:
            entry = make_audit_entry(
                sync_id="mixed-sync",
                entity_type=entity_type,
                entity_name=f"{entity_type}-1",
                after_state={"id": f"{entity_type}-123"},
            )
            audit_service.record(entry)

        result = rollback_service.rollback("mixed-sync", entity_types=["services"])

        assert result.success is True
        assert result.rolled_back == 1
        mock_konnect_manager.delete.assert_called_once_with("services-123")


class TestRollbackServiceEdgeCases:
    """Tests for edge cases in RollbackService."""

    @pytest.mark.unit
    def test_rollback_with_missing_manager(self, audit_service: SyncAuditService) -> None:
        """rollback raises error when manager is not available."""
        # Create service with no managers
        service = RollbackService(audit_service, {}, {})

        entry = make_audit_entry(
            sync_id="no-manager-sync",
            after_state={"id": "svc-123"},
        )
        audit_service.record(entry)

        result = service.rollback("no-manager-sync")

        assert result.success is False
        assert result.failed == 1
        assert "No manager available" in result.errors[0]

    @pytest.mark.unit
    def test_preview_empty_sync(
        self, rollback_service: RollbackService, audit_service: SyncAuditService
    ) -> None:
        """preview_rollback handles sync with only skipped entries."""
        entry = make_audit_entry(
            sync_id="empty-sync",
            action="skip",
            status="success",
        )
        audit_service.record(entry)

        preview = rollback_service.preview_rollback("empty-sync")

        assert len(preview.actions) == 0
        assert preview.can_rollback is False
