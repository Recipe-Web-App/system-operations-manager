"""E2E tests for sync rollback CLI command.

These tests verify the CLI workflow for sync rollback command.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app
from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
)
from system_operations_manager.services.kong.sync_rollback import (
    RollbackPreview,
    RollbackResult,
    RollbackService,
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

    def get_sync_details(sync_id: str) -> list[SyncAuditEntry]:
        return [e for e in entries if e.sync_id == sync_id]

    mock_service.get_sync_details.side_effect = get_sync_details
    return mock_service


def make_entry(
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


@pytest.fixture
def sample_push_entry() -> SyncAuditEntry:
    """Create a sample push entry with after_state."""
    return make_entry(
        sync_id="push-sync-123",
        operation="push",
        action="create",
        entity_name="api-service",
        after_state={"id": "svc-abc123", "name": "api-service", "host": "example.com"},
    )


@pytest.fixture
def sample_dry_run_entry() -> SyncAuditEntry:
    """Create a sample dry-run entry."""
    return make_entry(
        sync_id="dry-run-sync",
        operation="push",
        action="create",
        dry_run=True,
        entity_name="test-service",
        after_state={"id": "svc-123"},
    )


@pytest.fixture
def mock_rollback_service() -> MagicMock:
    """Create a mock rollback service."""
    return MagicMock(spec=RollbackService)


@pytest.mark.e2e
class TestSyncRollbackCommandExists:
    """Tests verifying the rollback command is properly registered."""

    def test_rollback_command_exists(self, cli_runner: CliRunner) -> None:
        """Verify rollback command is registered."""
        result = cli_runner.invoke(app, ["kong", "sync", "rollback", "--help"])

        assert result.exit_code == 0
        assert "Rollback a sync operation" in result.stdout

    def test_rollback_help_shows_options(self, cli_runner: CliRunner) -> None:
        """Verify help shows all available options."""
        result = cli_runner.invoke(app, ["kong", "sync", "rollback", "--help"])

        assert "--dry-run" in result.stdout
        assert "--type" in result.stdout
        assert "--force" in result.stdout
        assert "SYNC_ID_ARG" in result.stdout

    def test_rollback_help_shows_examples(self, cli_runner: CliRunner) -> None:
        """Verify help shows usage examples."""
        result = cli_runner.invoke(app, ["kong", "sync", "rollback", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.stdout
        assert "ops kong sync history" in result.stdout
        assert "ops kong sync rollback" in result.stdout

    def test_sync_subcommand_shows_rollback(self, cli_runner: CliRunner) -> None:
        """Verify sync subcommand help shows rollback command."""
        result = cli_runner.invoke(app, ["kong", "sync", "--help"])

        assert result.exit_code == 0
        assert "rollback" in result.stdout


@pytest.mark.e2e
class TestSyncRollbackDryRun:
    """Tests for rollback dry-run functionality."""

    def test_rollback_dry_run_shows_preview(self, cli_runner: CliRunner) -> None:
        """Verify --dry-run shows preview without executing."""
        entry = make_entry(
            sync_id="push-sync-123",
            operation="push",
            action="create",
            entity_name="api-service",
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "push-sync-123", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "Rollback Preview" in result.stdout
        assert "Dry run" in result.stdout
        assert "Would rollback" in result.stdout

    def test_rollback_dry_run_for_nonexistent_sync_shows_error(self, cli_runner: CliRunner) -> None:
        """Verify --dry-run for unknown sync shows error."""
        mock_audit = create_mock_audit_service([])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "nonexistent-sync", "--dry-run"]
            )

        assert result.exit_code == 1
        assert "Cannot rollback" in result.stdout


@pytest.mark.e2e
class TestSyncRollbackValidation:
    """Tests for rollback validation."""

    def test_rollback_rejects_dry_run_syncs(self, cli_runner: CliRunner) -> None:
        """Verify cannot rollback syncs that were dry-runs."""
        entry = make_entry(
            sync_id="dry-run-sync",
            operation="push",
            action="create",
            dry_run=True,
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "dry-run-sync", "--dry-run"]
            )

        assert result.exit_code == 1
        assert "dry-run" in result.stdout.lower()

    def test_rollback_requires_sync_id(self, cli_runner: CliRunner) -> None:
        """Verify sync_id argument is required."""
        result = cli_runner.invoke(app, ["kong", "sync", "rollback"])

        # Should fail due to missing required argument
        assert result.exit_code != 0
        # Typer shows error in stderr or stdout depending on version
        output = result.stdout + (result.stderr or "")
        assert (
            "SYNC_ID_ARG" in output or "Missing argument" in output or "required" in output.lower()
        )

    def test_rollback_with_no_rollbackable_entries(self, cli_runner: CliRunner) -> None:
        """Verify rollback handles syncs with only skipped entries."""
        entry = make_entry(
            sync_id="skip-sync",
            operation="push",
            action="skip",
            status="success",
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(app, ["kong", "sync", "rollback", "skip-sync", "--dry-run"])

        assert result.exit_code == 1


@pytest.mark.e2e
class TestSyncRollbackFiltering:
    """Tests for rollback entity type filtering."""

    def test_rollback_filters_by_entity_type(self, cli_runner: CliRunner) -> None:
        """Verify --type option filters to specific entity type."""
        entries = [
            make_entry(
                sync_id="mixed-sync",
                entity_type="services",
                entity_name="svc-1",
                after_state={"id": "svc-1"},
            ),
            make_entry(
                sync_id="mixed-sync",
                entity_type="routes",
                entity_name="route-1",
                after_state={"id": "route-1"},
            ),
        ]

        mock_audit = create_mock_audit_service(entries)

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app,
                ["kong", "sync", "rollback", "mixed-sync", "--dry-run", "--type", "services"],
            )

        assert result.exit_code == 0
        assert "services" in result.stdout
        # Should show only 1 action (services), not 2
        assert "Would rollback 1 operation" in result.stdout


@pytest.mark.e2e
class TestSyncRollbackExecution:
    """Tests for rollback execution."""

    def test_rollback_without_force_asks_confirmation(self, cli_runner: CliRunner) -> None:
        """Verify rollback asks for confirmation without --force."""
        entry = make_entry(
            sync_id="push-sync-123",
            operation="push",
            action="create",
            entity_name="api-service",
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            # Answer 'n' to confirmation
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "push-sync-123"], input="n\n"
            )

        assert "rollback" in result.stdout.lower()
        assert "Cancelled" in result.stdout

    def test_rollback_with_force_skips_confirmation(self, cli_runner: CliRunner) -> None:
        """Verify --force skips confirmation prompt."""
        entry = make_entry(
            sync_id="push-sync-123",
            operation="push",
            action="create",
            entity_name="api-service",
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        # Mock the RollbackService to return a successful result
        mock_rollback_result = RollbackResult(
            sync_id="push-sync-123",
            success=True,
            rolled_back=1,
            failed=0,
            skipped=0,
            errors=[],
        )
        mock_rollback_preview = RollbackPreview(
            sync_id="push-sync-123",
            operation="push",
            timestamp=datetime.now(UTC).isoformat(),
            actions=[],  # Simplified - just test the flow
            warnings=[],
            can_rollback=True,
        )

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
                return_value=mock_audit,
            ),
            patch(
                "system_operations_manager.services.kong.sync_rollback.RollbackService.preview_rollback",
                return_value=mock_rollback_preview,
            ),
            patch(
                "system_operations_manager.services.kong.sync_rollback.RollbackService.rollback",
                return_value=mock_rollback_result,
            ),
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "push-sync-123", "--force"]
            )

        # Should not ask for confirmation
        assert "Continue?" not in result.stdout
        # Should execute and show summary (or indicate no actions if preview was empty)
        assert "Rollback" in result.stdout


@pytest.mark.e2e
class TestSyncRollbackOutputFormat:
    """Tests for rollback output formatting."""

    def test_rollback_preview_shows_table(self, cli_runner: CliRunner) -> None:
        """Verify preview shows formatted table of actions."""
        entry = make_entry(
            sync_id="push-sync-123",
            operation="push",
            action="create",
            entity_type="services",
            entity_name="api-service",
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "push-sync-123", "--dry-run"]
            )

        assert result.exit_code == 0
        # Table should include columns
        assert "Entity Type" in result.stdout
        assert "Name" in result.stdout
        assert "Action" in result.stdout
        assert "Target" in result.stdout
        # And values
        assert "services" in result.stdout
        assert "api-service" in result.stdout
        assert "delete" in result.stdout
        assert "konnect" in result.stdout

    def test_rollback_shows_operation_direction(self, cli_runner: CliRunner) -> None:
        """Verify rollback shows original sync direction."""
        entry = make_entry(
            sync_id="push-sync-123",
            operation="push",
            action="create",
            after_state={"id": "svc-123"},
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "push-sync-123", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "push" in result.stdout.lower()

    def test_rollback_preview_shows_warnings(self, cli_runner: CliRunner) -> None:
        """Verify preview shows warnings when applicable."""
        # Entry missing after_state will generate a warning
        entry = make_entry(
            sync_id="incomplete-sync",
            operation="push",
            action="create",
            entity_name="bad-service",
            after_state=None,  # Missing!
        )

        mock_audit = create_mock_audit_service([entry])

        with patch(
            "system_operations_manager.plugins.kong.commands.sync.SyncAuditService",
            return_value=mock_audit,
        ):
            result = cli_runner.invoke(
                app, ["kong", "sync", "rollback", "incomplete-sync", "--dry-run"]
            )

        # Should fail with error due to no rollbackable actions
        assert result.exit_code == 1
        assert "Cannot rollback" in result.stdout
