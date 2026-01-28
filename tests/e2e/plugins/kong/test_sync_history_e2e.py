"""E2E tests for sync history CLI command.

These tests verify the CLI workflow for sync history command.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app
from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
    SyncSummary,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_audit_file(tmp_path: Path) -> Path:
    """Create a temporary audit file."""
    return tmp_path / "kong_sync_audit.jsonl"


def create_mock_audit_service(entries: list[SyncAuditEntry]) -> MagicMock:
    """Create a mock audit service with specified entries."""
    mock_service = MagicMock(spec=SyncAuditService)

    # Group entries by sync_id for list_syncs
    syncs_by_id: dict[str, list[SyncAuditEntry]] = {}
    for entry in entries:
        if entry.sync_id not in syncs_by_id:
            syncs_by_id[entry.sync_id] = []
        syncs_by_id[entry.sync_id].append(entry)

    # Create summaries
    summaries = []
    for sync_id, sync_entries in syncs_by_id.items():
        first = sync_entries[0]
        created = sum(1 for e in sync_entries if e.action == "create")
        updated = sum(1 for e in sync_entries if e.action == "update")
        errors = sum(1 for e in sync_entries if e.status == "failed")
        entity_types = list(set(e.entity_type for e in sync_entries))

        summaries.append(
            SyncSummary(
                sync_id=sync_id,
                timestamp=first.timestamp,
                operation=first.operation,
                dry_run=first.dry_run,
                created=created,
                updated=updated,
                errors=errors,
                entity_types=entity_types,
            )
        )

    mock_service.list_syncs.return_value = summaries

    def get_sync_details(sync_id: str) -> list[SyncAuditEntry]:
        return [e for e in entries if e.sync_id == sync_id]

    mock_service.get_sync_details.side_effect = get_sync_details

    def get_entity_history(
        entity_type: str, entity_name: str, limit: int = 10
    ) -> list[SyncAuditEntry]:
        return [
            e for e in entries if e.entity_type == entity_type and e.entity_name == entity_name
        ][:limit]

    mock_service.get_entity_history.side_effect = get_entity_history

    return mock_service


@pytest.fixture
def sample_entries() -> list[SyncAuditEntry]:
    """Create sample audit entries."""
    now = datetime.now(UTC)

    return [
        SyncAuditEntry(
            sync_id="test-push-123",
            timestamp=now.isoformat(),
            operation="push",
            dry_run=False,
            entity_type="services",
            entity_id="svc-1",
            entity_name="test-service",
            action="create",
            source="gateway",
            target="konnect",
            status="success",
        ),
        SyncAuditEntry(
            sync_id="test-pull-456",
            timestamp=now.isoformat(),
            operation="pull",
            dry_run=True,
            entity_type="routes",
            entity_id="rt-1",
            entity_name="test-route",
            action="create",
            source="konnect",
            target="gateway",
            status="would_create",
        ),
    ]


@pytest.fixture
def mock_audit_service(sample_entries: list[SyncAuditEntry]) -> MagicMock:
    """Create a mock audit service with pre-populated entries."""
    return create_mock_audit_service(sample_entries)


@pytest.mark.e2e
class TestSyncHistoryE2E:
    """E2E tests for sync history command."""

    def test_sync_history_command_exists(self, cli_runner: CliRunner) -> None:
        """Verify sync history command is registered."""
        result = cli_runner.invoke(app, ["kong", "sync", "history", "--help"])

        # Command should be found and show help
        assert result.exit_code == 0
        assert "Show sync operation history" in result.stdout

    def test_sync_history_help_shows_options(self, cli_runner: CliRunner) -> None:
        """Verify help shows all available options."""
        result = cli_runner.invoke(app, ["kong", "sync", "history", "--help"])

        assert "--sync-id" in result.stdout
        assert "--entity-type" in result.stdout
        assert "--entity-name" in result.stdout
        assert "--limit" in result.stdout
        assert "--since" in result.stdout
        assert "--output" in result.stdout

    def test_sync_history_help_shows_examples(self, cli_runner: CliRunner) -> None:
        """Verify help shows usage examples."""
        result = cli_runner.invoke(app, ["kong", "sync", "history", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.stdout
        assert "ops kong sync history" in result.stdout

    def test_sync_history_shows_empty_initially(self, cli_runner: CliRunner) -> None:
        """Verify history command works with no prior syncs."""
        mock_service = create_mock_audit_service([])

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(app, ["kong", "sync", "history"])

        assert result.exit_code == 0
        assert "No sync operations found" in result.stdout

    def test_sync_history_shows_recorded_syncs(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify history command shows recorded sync operations."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(app, ["kong", "sync", "history"])

        assert result.exit_code == 0
        assert "Recent Sync Operations" in result.stdout
        # Should show push in output
        assert "push" in result.stdout.lower()

    def test_sync_history_with_sync_id_shows_details(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify --sync-id shows detailed view."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(
                app, ["kong", "sync", "history", "--sync-id", "test-push-123"]
            )

        assert result.exit_code == 0
        assert "Sync Operation:" in result.stdout
        assert "Operations:" in result.stdout
        assert "test-service" in result.stdout

    def test_sync_history_unknown_sync_id_shows_error(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify unknown --sync-id shows appropriate message."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(
                app, ["kong", "sync", "history", "--sync-id", "nonexistent-sync"]
            )

        assert result.exit_code == 1
        assert "No sync found with ID" in result.stdout

    def test_sync_history_filters_by_entity(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify --entity-type and --entity-name filter correctly."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(
                app,
                [
                    "kong",
                    "sync",
                    "history",
                    "--entity-type",
                    "services",
                    "--entity-name",
                    "test-service",
                ],
            )

        assert result.exit_code == 0
        assert "Sync History for services/test-service" in result.stdout

    def test_sync_history_entity_filter_no_results(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify entity filter shows message when no results."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(
                app,
                [
                    "kong",
                    "sync",
                    "history",
                    "--entity-type",
                    "consumers",
                    "--entity-name",
                    "nonexistent",
                ],
            )

        assert result.exit_code == 0
        assert "No sync history found" in result.stdout

    def test_sync_history_since_option(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify --since flag filters results."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(app, ["kong", "sync", "history", "--since", "7d"])

        # Should not error
        assert result.exit_code == 0

    def test_sync_history_invalid_since_shows_error(self, cli_runner: CliRunner) -> None:
        """Verify invalid --since format shows error."""
        mock_service = create_mock_audit_service([])

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(app, ["kong", "sync", "history", "--since", "invalid"])

        assert result.exit_code == 1
        assert "Invalid since format" in result.stdout

    def test_sync_history_output_json(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify --output json produces valid JSON."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(app, ["kong", "sync", "history", "--output", "json"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 2  # Two syncs recorded

    def test_sync_history_output_json_with_sync_id(
        self,
        cli_runner: CliRunner,
        mock_audit_service: MagicMock,
    ) -> None:
        """Verify --output json with --sync-id produces valid JSON."""
        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_audit_service
            result = cli_runner.invoke(
                app,
                [
                    "kong",
                    "sync",
                    "history",
                    "--sync-id",
                    "test-push-123",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["sync_id"] == "test-push-123"

    def test_sync_history_limit_option(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify --limit option restricts results."""
        # Create entries for 10 different syncs
        now = datetime.now(UTC)
        entries = [
            SyncAuditEntry(
                sync_id=f"sync-{i}",
                timestamp=now.isoformat(),
                operation="push",
                dry_run=False,
                entity_type="services",
                entity_name=f"service-{i}",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
            for i in range(10)
        ]

        mock_service = create_mock_audit_service(entries)
        # Override list_syncs to respect limit
        original_summaries: list[SyncSummary] = mock_service.list_syncs.return_value

        def list_syncs_with_limit(limit: int = 20, **kwargs: object) -> list[SyncSummary]:
            return list(original_summaries[:limit])

        mock_service.list_syncs.side_effect = list_syncs_with_limit

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(
                app, ["kong", "sync", "history", "--limit", "3", "--output", "json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 3

    def test_sync_subcommand_shows_history(self, cli_runner: CliRunner) -> None:
        """Verify sync subcommand help shows history command."""
        result = cli_runner.invoke(app, ["kong", "sync", "--help"])

        assert result.exit_code == 0
        assert "history" in result.stdout
        assert "status" in result.stdout
        assert "push" in result.stdout
        assert "pull" in result.stdout
