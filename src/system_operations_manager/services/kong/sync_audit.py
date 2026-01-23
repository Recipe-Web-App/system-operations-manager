"""Sync audit service for tracking Kong sync operations.

This module provides an audit log for sync operations between Kong Gateway
and Konnect control plane. It tracks each entity operation (create, update,
skip) and provides query capabilities for history review and future rollback.
"""

from __future__ import annotations

import fcntl
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Default audit file location following XDG spec
DEFAULT_AUDIT_FILE = Path.home() / ".local" / "state" / "ops" / "kong_sync_audit.jsonl"


class SyncAuditEntry(BaseModel):
    """A single audit entry for a sync operation.

    Each entry represents one entity operation (create, update, skip)
    within a larger sync run.
    """

    # Sync context
    sync_id: str = Field(description="UUID grouping all ops in one sync run")
    timestamp: str = Field(description="ISO 8601 timestamp")
    operation: str = Field(description="Sync operation: 'push' or 'pull'")
    dry_run: bool = Field(description="Whether this was a dry-run")

    # Entity context
    entity_type: str = Field(description="Entity type: services, routes, etc.")
    entity_id: str | None = Field(default=None, description="ID in source system")
    entity_name: str = Field(description="Human-readable identifier")

    # Operation details
    action: str = Field(description="Action: 'create', 'update', or 'skip'")
    source: str = Field(description="Source system: 'gateway' or 'konnect'")
    target: str = Field(description="Target system: 'gateway' or 'konnect'")
    status: str = Field(description="Status: 'success', 'failed', 'would_create', 'would_update'")

    # Optional details
    error: str | None = Field(default=None, description="Error message if failed")
    drift_fields: list[str] | None = Field(
        default=None, description="Fields that differed (for updates)"
    )

    # Snapshot for rollback (future)
    before_state: dict[str, Any] | None = Field(
        default=None, description="Entity state before change"
    )
    after_state: dict[str, Any] | None = Field(
        default=None, description="Entity state after change"
    )


class SyncSummary(BaseModel):
    """Summary of a sync operation.

    Aggregates all entries for a single sync run into summary statistics.
    """

    sync_id: str = Field(description="UUID of the sync run")
    timestamp: str = Field(description="Timestamp of the sync run")
    operation: str = Field(description="Sync operation: 'push' or 'pull'")
    dry_run: bool = Field(description="Whether this was a dry-run")

    # Counts
    created: int = Field(default=0, description="Number of entities created")
    updated: int = Field(default=0, description="Number of entities updated")
    errors: int = Field(default=0, description="Number of errors")
    skipped: int = Field(default=0, description="Number of entities skipped")

    # For display
    entity_types: list[str] = Field(default_factory=list, description="Entity types involved")


class SyncAuditService:
    """Service for recording and querying sync audit logs.

    This service provides:
    - Append-only audit logging for sync operations
    - Query capabilities for reviewing sync history
    - Entity-level history tracking
    - Thread-safe file writes

    The audit log is stored in JSONL format (one JSON object per line)
    for efficient append operations and streaming reads.
    """

    def __init__(self, audit_file: Path | None = None) -> None:
        """Initialize the audit service.

        Args:
            audit_file: Path to the audit file. Defaults to
                ~/.local/state/ops/kong_sync_audit.jsonl
        """
        self._audit_file = audit_file or DEFAULT_AUDIT_FILE
        self._audit_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def audit_file(self) -> Path:
        """Get the audit file path."""
        return self._audit_file

    def start_sync(self, operation: str, dry_run: bool) -> str:
        """Start a new sync operation.

        Args:
            operation: The sync operation type ('push' or 'pull')
            dry_run: Whether this is a dry-run

        Returns:
            A unique sync_id for this operation
        """
        return str(uuid.uuid4())

    def record(self, entry: SyncAuditEntry) -> None:
        """Record an audit entry to the log.

        Appends the entry to the JSONL file with file locking
        to ensure thread-safety.

        Args:
            entry: The audit entry to record
        """
        with self._audit_file.open("a") as f:
            # Use file locking for concurrent writes
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(entry.model_dump_json() + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def list_syncs(
        self,
        *,
        limit: int = 20,
        since: datetime | None = None,
        operation: str | None = None,
    ) -> list[SyncSummary]:
        """List sync operations with aggregated stats.

        Args:
            limit: Maximum number of syncs to return
            since: Only include syncs after this time
            operation: Filter by operation type ('push' or 'pull')

        Returns:
            List of SyncSummary objects, most recent first
        """
        if not self._audit_file.exists():
            return []

        # Group entries by sync_id
        syncs: dict[str, list[SyncAuditEntry]] = {}
        with self._audit_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = SyncAuditEntry.model_validate_json(line)

                    # Apply filters
                    if operation and entry.operation != operation:
                        continue

                    if since:
                        entry_time = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
                        if entry_time < since:
                            continue

                    if entry.sync_id not in syncs:
                        syncs[entry.sync_id] = []
                    syncs[entry.sync_id].append(entry)
                except Exception:
                    # Skip malformed entries
                    continue

        # Convert to summaries
        summaries: list[SyncSummary] = []
        for sync_id, entries in syncs.items():
            if not entries:
                continue

            first_entry = entries[0]
            entity_types = set()
            created = updated = errors = skipped = 0

            for entry in entries:
                entity_types.add(entry.entity_type)
                if entry.status in ("success", "would_create") and entry.action == "create":
                    created += 1
                elif entry.status in ("success", "would_update") and entry.action == "update":
                    updated += 1
                elif entry.status == "failed":
                    errors += 1
                elif entry.action == "skip":
                    skipped += 1

            summaries.append(
                SyncSummary(
                    sync_id=sync_id,
                    timestamp=first_entry.timestamp,
                    operation=first_entry.operation,
                    dry_run=first_entry.dry_run,
                    created=created,
                    updated=updated,
                    errors=errors,
                    skipped=skipped,
                    entity_types=sorted(entity_types),
                )
            )

        # Sort by timestamp, most recent first
        summaries.sort(key=lambda s: s.timestamp, reverse=True)

        return summaries[:limit]

    def get_sync_details(self, sync_id: str) -> list[SyncAuditEntry]:
        """Get all entries for a specific sync operation.

        Args:
            sync_id: The sync operation ID

        Returns:
            List of all audit entries for this sync, empty if not found
        """
        if not self._audit_file.exists():
            return []

        entries: list[SyncAuditEntry] = []
        with self._audit_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = SyncAuditEntry.model_validate_json(line)
                    if entry.sync_id == sync_id:
                        entries.append(entry)
                except Exception:
                    continue

        return entries

    def get_entity_history(
        self,
        entity_type: str,
        entity_name: str,
        limit: int = 10,
    ) -> list[SyncAuditEntry]:
        """Get sync history for a specific entity.

        Args:
            entity_type: The entity type (services, routes, etc.)
            entity_name: The entity name/identifier
            limit: Maximum number of entries to return

        Returns:
            List of audit entries for this entity, most recent first
        """
        if not self._audit_file.exists():
            return []

        entries: list[SyncAuditEntry] = []
        with self._audit_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = SyncAuditEntry.model_validate_json(line)
                    if entry.entity_type == entity_type and entry.entity_name == entity_name:
                        entries.append(entry)
                except Exception:
                    continue

        # Sort by timestamp, most recent first
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]


def parse_since(since_str: str) -> datetime:
    """Parse a since string into a datetime.

    Supports formats:
    - "7d" - 7 days ago
    - "24h" - 24 hours ago
    - "30m" - 30 minutes ago
    - ISO 8601 date/datetime strings

    Args:
        since_str: The since string to parse

    Returns:
        datetime object

    Raises:
        ValueError: If the string cannot be parsed
    """
    # Check for relative time format
    match = re.match(r"^(\d+)([dhm])$", since_str.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        now = datetime.now(UTC)
        if unit == "d":
            return now - timedelta(days=value)
        elif unit == "h":
            return now - timedelta(hours=value)
        elif unit == "m":
            return now - timedelta(minutes=value)

    # Try ISO 8601 format
    try:
        # Handle date-only format
        if len(since_str) == 10:
            return datetime.fromisoformat(since_str + "T00:00:00+00:00")
        # Handle full datetime
        return datetime.fromisoformat(since_str.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            f"Invalid since format: {since_str}. Use '7d', '24h', '30m' or ISO 8601 date/datetime."
        ) from e
