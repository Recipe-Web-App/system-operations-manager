"""Unit tests for SyncAuditService.

Tests the sync audit logging functionality for tracking Kong sync operations.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
    SyncSummary,
    parse_since,
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
def sample_entry() -> SyncAuditEntry:
    """Create a sample audit entry."""
    return SyncAuditEntry(
        sync_id="test-sync-123",
        timestamp=datetime.now(UTC).isoformat(),
        operation="push",
        dry_run=False,
        entity_type="services",
        entity_id="svc-1",
        entity_name="api-service",
        action="create",
        source="gateway",
        target="konnect",
        status="success",
    )


class TestSyncAuditEntry:
    """Tests for SyncAuditEntry model."""

    @pytest.mark.unit
    def test_create_minimal_entry(self) -> None:
        """Entry can be created with required fields only."""
        entry = SyncAuditEntry(
            sync_id="abc-123",
            timestamp="2026-01-22T10:00:00Z",
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_name="test-service",
            action="create",
            source="gateway",
            target="konnect",
            status="success",
        )
        assert entry.sync_id == "abc-123"
        assert entry.entity_type == "services"
        assert entry.error is None
        assert entry.drift_fields is None

    @pytest.mark.unit
    def test_create_entry_with_all_fields(self) -> None:
        """Entry can be created with all optional fields."""
        entry = SyncAuditEntry(
            sync_id="abc-123",
            timestamp="2026-01-22T10:00:00Z",
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_id="svc-1",
            entity_name="test-service",
            action="update",
            source="gateway",
            target="konnect",
            status="success",
            error=None,
            drift_fields=["host", "port"],
            before_state={"host": "old.local"},
            after_state={"host": "new.local"},
        )
        assert entry.drift_fields == ["host", "port"]
        assert entry.before_state == {"host": "old.local"}

    @pytest.mark.unit
    def test_entry_serialization(self) -> None:
        """Entry can be serialized to JSON."""
        entry = SyncAuditEntry(
            sync_id="abc-123",
            timestamp="2026-01-22T10:00:00Z",
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_name="test-service",
            action="create",
            source="gateway",
            target="konnect",
            status="success",
        )
        json_str = entry.model_dump_json()
        assert "abc-123" in json_str
        assert "services" in json_str


class TestSyncSummary:
    """Tests for SyncSummary model."""

    @pytest.mark.unit
    def test_create_summary(self) -> None:
        """Summary can be created with required fields."""
        summary = SyncSummary(
            sync_id="abc-123",
            timestamp="2026-01-22T10:00:00Z",
            operation="push",
            dry_run=False,
            created=2,
            updated=1,
            errors=0,
        )
        assert summary.sync_id == "abc-123"
        assert summary.created == 2
        assert summary.updated == 1

    @pytest.mark.unit
    def test_summary_defaults(self) -> None:
        """Summary has sensible defaults."""
        summary = SyncSummary(
            sync_id="abc-123",
            timestamp="2026-01-22T10:00:00Z",
            operation="push",
            dry_run=False,
        )
        assert summary.created == 0
        assert summary.updated == 0
        assert summary.errors == 0
        assert summary.skipped == 0
        assert summary.entity_types == []


class TestSyncAuditServiceStartSync:
    """Tests for SyncAuditService.start_sync."""

    @pytest.mark.unit
    def test_start_sync_generates_unique_id(self, audit_service: SyncAuditService) -> None:
        """start_sync should generate unique IDs."""
        id1 = audit_service.start_sync("push", False)
        id2 = audit_service.start_sync("push", False)
        assert id1 != id2

    @pytest.mark.unit
    def test_start_sync_returns_uuid_format(self, audit_service: SyncAuditService) -> None:
        """start_sync should return a UUID string."""
        sync_id = audit_service.start_sync("push", False)
        # UUID format: 8-4-4-4-12 hex characters
        assert len(sync_id) == 36
        assert sync_id.count("-") == 4


class TestSyncAuditServiceRecord:
    """Tests for SyncAuditService.record."""

    @pytest.mark.unit
    def test_record_appends_to_file(
        self, audit_service: SyncAuditService, audit_file: Path, sample_entry: SyncAuditEntry
    ) -> None:
        """record should append entry to file."""
        audit_service.record(sample_entry)

        assert audit_file.exists()
        content = audit_file.read_text()
        assert "test-sync-123" in content
        assert "api-service" in content

    @pytest.mark.unit
    def test_record_multiple_entries(
        self, audit_service: SyncAuditService, audit_file: Path
    ) -> None:
        """record should append multiple entries."""
        for i in range(3):
            entry = SyncAuditEntry(
                sync_id=f"sync-{i}",
                timestamp=datetime.now(UTC).isoformat(),
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name=f"service-{i}",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
            audit_service.record(entry)

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 3

    @pytest.mark.unit
    def test_record_creates_parent_directory(self, tmp_path: Path) -> None:
        """record should create parent directory if it doesn't exist."""
        nested_file = tmp_path / "nested" / "dir" / "audit.jsonl"
        service = SyncAuditService(audit_file=nested_file)

        entry = SyncAuditEntry(
            sync_id="test",
            timestamp=datetime.now(UTC).isoformat(),
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_name="test",
            action="create",
            source="gateway",
            target="konnect",
            status="success",
        )
        service.record(entry)

        assert nested_file.exists()

    @pytest.mark.unit
    def test_concurrent_writes_are_safe(
        self, audit_service: SyncAuditService, audit_file: Path
    ) -> None:
        """record should be thread-safe."""
        num_threads = 10
        entries_per_thread = 5

        def write_entries(thread_id: int) -> None:
            for i in range(entries_per_thread):
                entry = SyncAuditEntry(
                    sync_id=f"sync-{thread_id}-{i}",
                    timestamp=datetime.now(UTC).isoformat(),
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name=f"service-{thread_id}-{i}",
                    action="create",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
                audit_service.record(entry)

        threads = [threading.Thread(target=write_entries, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == num_threads * entries_per_thread


class TestSyncAuditServiceListSyncs:
    """Tests for SyncAuditService.list_syncs."""

    @pytest.mark.unit
    def test_list_syncs_empty_file(self, audit_service: SyncAuditService) -> None:
        """list_syncs should return empty list for empty/missing file."""
        syncs = audit_service.list_syncs()
        assert syncs == []

    @pytest.mark.unit
    def test_list_syncs_aggregates_correctly(self, audit_service: SyncAuditService) -> None:
        """list_syncs should aggregate entries by sync_id."""
        sync_id = "sync-123"
        timestamp = datetime.now(UTC).isoformat()

        # Record multiple entries for same sync
        for i, (action, status) in enumerate(
            [
                ("create", "success"),
                ("create", "success"),
                ("update", "success"),
            ]
        ):
            entry = SyncAuditEntry(
                sync_id=sync_id,
                timestamp=timestamp,
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name=f"service-{i}",
                action=action,
                source="gateway",
                target="konnect",
                status=status,
            )
            audit_service.record(entry)

        syncs = audit_service.list_syncs()
        assert len(syncs) == 1
        assert syncs[0].sync_id == sync_id
        assert syncs[0].created == 2
        assert syncs[0].updated == 1

    @pytest.mark.unit
    def test_list_syncs_filters_by_since(self, audit_service: SyncAuditService) -> None:
        """list_syncs should filter by since parameter."""
        now = datetime.now(UTC)
        old_time = (now - timedelta(days=10)).isoformat()
        recent_time = (now - timedelta(hours=1)).isoformat()

        # Old entry
        audit_service.record(
            SyncAuditEntry(
                sync_id="old-sync",
                timestamp=old_time,
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name="old-service",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        )

        # Recent entry
        audit_service.record(
            SyncAuditEntry(
                sync_id="recent-sync",
                timestamp=recent_time,
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name="recent-service",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        )

        # Filter by last 7 days
        since = now - timedelta(days=7)
        syncs = audit_service.list_syncs(since=since)
        assert len(syncs) == 1
        assert syncs[0].sync_id == "recent-sync"

    @pytest.mark.unit
    def test_list_syncs_filters_by_operation(self, audit_service: SyncAuditService) -> None:
        """list_syncs should filter by operation type."""
        timestamp = datetime.now(UTC).isoformat()

        # Push entry
        audit_service.record(
            SyncAuditEntry(
                sync_id="push-sync",
                timestamp=timestamp,
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name="service",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        )

        # Pull entry
        audit_service.record(
            SyncAuditEntry(
                sync_id="pull-sync",
                timestamp=timestamp,
                operation="pull",
                dry_run=False,
                entity_type="services",
                entity_name="service",
                action="create",
                source="konnect",
                target="gateway",
                status="success",
            )
        )

        syncs = audit_service.list_syncs(operation="push")
        assert len(syncs) == 1
        assert syncs[0].sync_id == "push-sync"

    @pytest.mark.unit
    def test_list_syncs_respects_limit(self, audit_service: SyncAuditService) -> None:
        """list_syncs should respect the limit parameter."""
        for i in range(5):
            audit_service.record(
                SyncAuditEntry(
                    sync_id=f"sync-{i}",
                    timestamp=datetime.now(UTC).isoformat(),
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name=f"service-{i}",
                    action="create",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        syncs = audit_service.list_syncs(limit=3)
        assert len(syncs) == 3

    @pytest.mark.unit
    def test_list_syncs_sorts_by_timestamp_desc(self, audit_service: SyncAuditService) -> None:
        """list_syncs should sort by timestamp, most recent first."""
        now = datetime.now(UTC)

        for i in range(3):
            ts = (now - timedelta(hours=i)).isoformat()
            audit_service.record(
                SyncAuditEntry(
                    sync_id=f"sync-{i}",
                    timestamp=ts,
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name=f"service-{i}",
                    action="create",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        syncs = audit_service.list_syncs()
        # sync-0 should be first (most recent)
        assert syncs[0].sync_id == "sync-0"
        assert syncs[2].sync_id == "sync-2"


class TestSyncAuditServiceGetSyncDetails:
    """Tests for SyncAuditService.get_sync_details."""

    @pytest.mark.unit
    def test_get_sync_details_returns_all_entries(self, audit_service: SyncAuditService) -> None:
        """get_sync_details should return all entries for a sync."""
        sync_id = "target-sync"
        timestamp = datetime.now(UTC).isoformat()

        # Record entries for target sync
        for i in range(3):
            audit_service.record(
                SyncAuditEntry(
                    sync_id=sync_id,
                    timestamp=timestamp,
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name=f"service-{i}",
                    action="create",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        # Record entry for different sync
        audit_service.record(
            SyncAuditEntry(
                sync_id="other-sync",
                timestamp=timestamp,
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name="other-service",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        )

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 3
        assert all(e.sync_id == sync_id for e in entries)

    @pytest.mark.unit
    def test_get_sync_details_returns_empty_for_unknown_id(
        self, audit_service: SyncAuditService
    ) -> None:
        """get_sync_details should return empty list for unknown sync_id."""
        entries = audit_service.get_sync_details("nonexistent-sync")
        assert entries == []


class TestSyncAuditServiceGetEntityHistory:
    """Tests for SyncAuditService.get_entity_history."""

    @pytest.mark.unit
    def test_get_entity_history_filters_correctly(self, audit_service: SyncAuditService) -> None:
        """get_entity_history should filter by entity_type and entity_name."""
        now = datetime.now(UTC)

        # Record entries for target entity
        for i in range(3):
            ts = (now - timedelta(hours=i)).isoformat()
            audit_service.record(
                SyncAuditEntry(
                    sync_id=f"sync-{i}",
                    timestamp=ts,
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name="target-service",
                    action="update" if i > 0 else "create",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        # Record entry for different entity
        audit_service.record(
            SyncAuditEntry(
                sync_id="other-sync",
                timestamp=now.isoformat(),
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name="other-service",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        )

        entries = audit_service.get_entity_history("services", "target-service")
        assert len(entries) == 3
        assert all(e.entity_name == "target-service" for e in entries)

    @pytest.mark.unit
    def test_get_entity_history_respects_limit(self, audit_service: SyncAuditService) -> None:
        """get_entity_history should respect the limit parameter."""
        now = datetime.now(UTC)

        for i in range(10):
            ts = (now - timedelta(hours=i)).isoformat()
            audit_service.record(
                SyncAuditEntry(
                    sync_id=f"sync-{i}",
                    timestamp=ts,
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name="target-service",
                    action="update",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        entries = audit_service.get_entity_history("services", "target-service", limit=5)
        assert len(entries) == 5

    @pytest.mark.unit
    def test_get_entity_history_sorts_by_timestamp_desc(
        self, audit_service: SyncAuditService
    ) -> None:
        """get_entity_history should sort by timestamp, most recent first."""
        now = datetime.now(UTC)

        for i in range(3):
            ts = (now - timedelta(hours=i)).isoformat()
            audit_service.record(
                SyncAuditEntry(
                    sync_id=f"sync-{i}",
                    timestamp=ts,
                    operation="push",
                    dry_run=False,
                    entity_type="services",
                    entity_name="target-service",
                    action="update",
                    source="gateway",
                    target="konnect",
                    status="success",
                )
            )

        entries = audit_service.get_entity_history("services", "target-service")
        # sync-0 should be first (most recent)
        assert entries[0].sync_id == "sync-0"
        assert entries[2].sync_id == "sync-2"


class TestSyncAuditServiceEdgeCases:
    """Tests for edge cases in SyncAuditService."""

    @pytest.mark.unit
    def test_handles_empty_audit_file(self, audit_file: Path) -> None:
        """Service should handle empty audit file gracefully."""
        audit_file.write_text("")
        service = SyncAuditService(audit_file=audit_file)

        assert service.list_syncs() == []
        assert service.get_sync_details("any") == []
        assert service.get_entity_history("services", "any") == []

    @pytest.mark.unit
    def test_handles_missing_audit_file(self, audit_service: SyncAuditService) -> None:
        """Service should handle missing audit file gracefully."""
        # File doesn't exist yet
        assert audit_service.list_syncs() == []
        assert audit_service.get_sync_details("any") == []

    @pytest.mark.unit
    def test_handles_malformed_lines(self, audit_file: Path) -> None:
        """Service should skip malformed JSON lines."""
        # Write valid and invalid lines
        valid_entry = SyncAuditEntry(
            sync_id="valid-sync",
            timestamp=datetime.now(UTC).isoformat(),
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_name="valid-service",
            action="create",
            source="gateway",
            target="konnect",
            status="success",
        )

        with audit_file.open("w") as f:
            f.write("not valid json\n")
            f.write(valid_entry.model_dump_json() + "\n")
            f.write("{incomplete json\n")

        service = SyncAuditService(audit_file=audit_file)
        syncs = service.list_syncs()

        assert len(syncs) == 1
        assert syncs[0].sync_id == "valid-sync"


class TestParseSince:
    """Tests for parse_since helper function."""

    @pytest.mark.unit
    def test_parse_days(self) -> None:
        """parse_since should handle '7d' format."""
        result = parse_since("7d")
        expected = datetime.now(UTC) - timedelta(days=7)
        # Allow 1 second tolerance
        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.unit
    def test_parse_hours(self) -> None:
        """parse_since should handle '24h' format."""
        result = parse_since("24h")
        expected = datetime.now(UTC) - timedelta(hours=24)
        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.unit
    def test_parse_minutes(self) -> None:
        """parse_since should handle '30m' format."""
        result = parse_since("30m")
        expected = datetime.now(UTC) - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.unit
    def test_parse_iso_date(self) -> None:
        """parse_since should handle ISO date format."""
        result = parse_since("2026-01-15")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    @pytest.mark.unit
    def test_parse_iso_datetime(self) -> None:
        """parse_since should handle ISO datetime format."""
        result = parse_since("2026-01-15T10:30:00Z")
        assert result.year == 2026
        assert result.hour == 10
        assert result.minute == 30

    @pytest.mark.unit
    def test_parse_invalid_format(self) -> None:
        """parse_since should raise ValueError for invalid format."""
        with pytest.raises(ValueError) as exc_info:
            parse_since("invalid")
        assert "Invalid since format" in str(exc_info.value)

    @pytest.mark.unit
    def test_parse_case_insensitive(self) -> None:
        """parse_since should be case-insensitive for relative formats."""
        result_lower = parse_since("7d")
        result_upper = parse_since("7D")
        # Allow 1 second tolerance
        assert abs((result_lower - result_upper).total_seconds()) < 1
