"""Integration tests for sync audit logging.

Tests that sync push and pull operations correctly record audit entries.
These tests use mocked Kong/Konnect services to verify the audit integration
works correctly with the sync command helpers.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.services.kong.sync_audit import (
    SyncAuditService,
)


@pytest.fixture
def audit_file(tmp_path: Path) -> Path:
    """Create a temporary audit file."""
    return tmp_path / "kong_sync_audit.jsonl"


@pytest.fixture
def audit_service(audit_file: Path) -> SyncAuditService:
    """Create an audit service with temporary file."""
    return SyncAuditService(audit_file=audit_file)


@pytest.fixture
def mock_unified_service_gateway_only() -> MagicMock:
    """Create a mock UnifiedQueryService with gateway-only entities."""
    service = MagicMock()

    # Service only in Gateway
    gateway_svc = Service(id="gw-svc-1", name="api-service", host="api.local", port=8080)

    entity = UnifiedEntity(
        entity=gateway_svc,
        source=EntitySource.GATEWAY,
        gateway_id="gw-svc-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_svc,
    )

    entities = UnifiedEntityList(entities=[entity])
    service.list_services.return_value = entities
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_konnect_only() -> MagicMock:
    """Create a mock UnifiedQueryService with konnect-only entities."""
    service = MagicMock()

    # Service only in Konnect
    konnect_svc = Service(
        id="konnect-svc-1", name="konnect-service", host="konnect.local", port=443
    )

    entity = UnifiedEntity(
        entity=konnect_svc,
        source=EntitySource.KONNECT,
        gateway_id=None,
        konnect_id="konnect-svc-1",
        has_drift=False,
        konnect_entity=konnect_svc,
    )

    entities = UnifiedEntityList(entities=[entity])
    service.list_services.return_value = entities
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_with_drift() -> MagicMock:
    """Create a mock UnifiedQueryService with drifted entities."""
    service = MagicMock()

    # Service with drift
    gateway_svc = Service(id="svc-1", name="drift-service", host="new-host.local", port=8080)
    konnect_svc = Service(id="svc-1", name="drift-service", host="old-host.local", port=80)

    entity = UnifiedEntity(
        entity=gateway_svc,
        source=EntitySource.BOTH,
        gateway_id="svc-1",
        konnect_id="konnect-svc-1",
        has_drift=True,
        drift_fields=["host", "port"],
        gateway_entity=gateway_svc,
        konnect_entity=konnect_svc,
    )

    entities = UnifiedEntityList(entities=[entity])
    service.list_services.return_value = entities
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_konnect_service_manager() -> MagicMock:
    """Create a mock Konnect service manager."""
    manager = MagicMock()
    manager.create.return_value = Service(id="konnect-new", name="api-service", host="api.local")
    manager.update.return_value = Service(
        id="konnect-updated", name="drift-service", host="new-host.local"
    )
    return manager


@pytest.fixture
def mock_gateway_service_manager() -> MagicMock:
    """Create a mock Gateway service manager."""
    manager = MagicMock()
    manager.create.return_value = Service(id="gw-new", name="konnect-service", host="konnect.local")
    manager.update.return_value = Service(
        id="gw-updated", name="drift-service", host="new-host.local"
    )
    return manager


@pytest.mark.integration
class TestSyncPushAuditIntegration:
    """Integration tests for sync push with audit logging."""

    def test_push_records_create_audit_entries(
        self,
        audit_service: SyncAuditService,
        audit_file: Path,
        mock_unified_service_gateway_only: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify sync push creates audit entries for each created entity."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_gateway_only,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        # Verify audit entry was recorded
        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1

        entry = entries[0]
        assert entry.operation == "push"
        assert entry.entity_type == "services"
        assert entry.entity_name == "api-service"
        assert entry.action == "create"
        assert entry.status == "success"
        assert entry.dry_run is False

    def test_push_records_update_audit_entries(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_drift: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify sync push creates audit entries for drifted entities."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_with_drift,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 0
        assert updated == 1
        assert errors == 0

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1

        entry = entries[0]
        assert entry.action == "update"
        assert entry.status == "success"
        assert entry.drift_fields == ["host", "port"]

    def test_push_dry_run_records_would_create_status(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_gateway_only: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify dry-run push records 'would_create' status."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=True)

        created, _updated, _errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_gateway_only,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=True,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        mock_konnect_service_manager.create.assert_not_called()

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].status == "would_create"
        assert entries[0].dry_run is True

    def test_push_records_failed_operations_with_error(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_gateway_only: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify failed sync operations capture error details."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        mock_konnect_service_manager.create.side_effect = Exception("Konnect API error")
        sync_id = audit_service.start_sync("push", dry_run=False)

        created, _updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_gateway_only,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 0
        assert errors == 1

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].status == "failed"
        assert entries[0].error is not None
        assert "Konnect API error" in entries[0].error


@pytest.mark.integration
class TestSyncPullAuditIntegration:
    """Integration tests for sync pull with audit logging."""

    def test_pull_records_create_audit_entries(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_only: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify sync pull creates audit entries for each created entity."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        sync_id = audit_service.start_sync("pull", dry_run=False)

        created, updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_konnect_only,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=False,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1

        entry = entries[0]
        assert entry.operation == "pull"
        assert entry.entity_type == "services"
        assert entry.entity_name == "konnect-service"
        assert entry.action == "create"
        assert entry.status == "success"
        assert entry.source == "konnect"
        assert entry.target == "gateway"

    def test_pull_dry_run_records_would_create_status(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_only: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify dry-run pull records 'would_create' status."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        sync_id = audit_service.start_sync("pull", dry_run=True)

        created, _updated, _errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_konnect_only,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=True,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        mock_gateway_service_manager.create.assert_not_called()

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].status == "would_create"
        assert entries[0].dry_run is True

    def test_pull_records_failed_operations_with_error(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_only: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify failed sync operations capture error details."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        mock_gateway_service_manager.create.side_effect = Exception("Gateway API error")
        sync_id = audit_service.start_sync("pull", dry_run=False)

        created, _updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_konnect_only,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=False,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 0
        assert errors == 1

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].status == "failed"
        assert entries[0].error is not None
        assert "Gateway API error" in entries[0].error


@pytest.mark.integration
class TestSyncAuditMultipleOperations:
    """Integration tests for multiple sync operations."""

    def test_multiple_syncs_have_unique_ids(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_gateway_only: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify each sync run gets a unique sync_id."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_ids = []
        for _ in range(3):
            sync_id = audit_service.start_sync("push", dry_run=False)
            sync_ids.append(sync_id)

            _push_entity_type(
                entity_type="services",
                unified_service=mock_unified_service_gateway_only,
                konnect_managers={"services": mock_konnect_service_manager},
                dry_run=False,
                audit_service=audit_service,
                sync_id=sync_id,
            )

        # All sync_ids should be unique
        assert len(set(sync_ids)) == 3

        # Each should have exactly one entry
        for sid in sync_ids:
            entries = audit_service.get_sync_details(sid)
            assert len(entries) == 1

    def test_list_syncs_shows_recorded_operations(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_gateway_only: MagicMock,
        mock_unified_service_konnect_only: MagicMock,
        mock_konnect_service_manager: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify list_syncs shows all recorded sync operations."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
            _push_entity_type,
        )

        # Push operation
        push_sync_id = audit_service.start_sync("push", dry_run=False)
        _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_gateway_only,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=push_sync_id,
        )

        # Pull operation
        pull_sync_id = audit_service.start_sync("pull", dry_run=False)
        _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_konnect_only,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=False,
            with_drift=False,
            audit_service=audit_service,
            sync_id=pull_sync_id,
        )

        syncs = audit_service.list_syncs()
        assert len(syncs) == 2

        operations = {s.operation for s in syncs}
        assert "push" in operations
        assert "pull" in operations
