"""E2E tests for certificate sync CLI commands.

These tests verify the CLI workflow for syncing certificate-related entity types
(certificates, SNIs, CA certificates, key sets, keys, vaults).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app
from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncSummary,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.mark.e2e
class TestSyncStatusEntityTypesE2E:
    """E2E tests for sync status with new entity types."""

    def test_sync_status_help_includes_all_entity_types(self, cli_runner: CliRunner) -> None:
        """Verify sync status help lists entity types option."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--help"])

        assert result.exit_code == 0
        assert "--type" in result.stdout or "-t" in result.stdout

    def test_sync_status_invalid_type_shows_error(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status rejects invalid entity types."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "invalid_type"])

        # Should fail with either "Invalid entity type" or "Konnect not configured"
        assert result.exit_code == 1
        assert "Invalid entity type" in result.stdout or "Konnect" in result.stdout

    def test_sync_status_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts certificates type (may fail on Konnect config)."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "certificates"])

        # Should NOT show "Invalid entity type" - may show Konnect not configured
        assert "Invalid entity type" not in result.stdout

    def test_sync_status_snis_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts snis type."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "snis"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_status_ca_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts ca_certificates type."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "ca_certificates"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_status_key_sets_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts key_sets type."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "key_sets"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_status_keys_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts keys type."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "keys"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_status_vaults_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync status accepts vaults type."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--type", "vaults"])

        assert "Invalid entity type" not in result.stdout


@pytest.mark.e2e
class TestSyncPushEntityTypesE2E:
    """E2E tests for sync push with new entity types."""

    def test_sync_push_help_includes_entity_types(self, cli_runner: CliRunner) -> None:
        """Verify sync push help mentions entity types."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert result.exit_code == 0
        assert "--type" in result.stdout or "-t" in result.stdout

    def test_sync_push_invalid_type_shows_error(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push rejects invalid entity types."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "push", "--type", "invalid_type", "--dry-run"]
        )

        assert result.exit_code == 1
        assert "Invalid entity type" in result.stdout or "Konnect" in result.stdout

    def test_sync_push_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts certificates type."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "push", "--type", "certificates", "--dry-run"]
        )

        assert "Invalid entity type" not in result.stdout

    def test_sync_push_snis_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts snis type."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--type", "snis", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_push_ca_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts ca_certificates type."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "push", "--type", "ca_certificates", "--dry-run"]
        )

        assert "Invalid entity type" not in result.stdout

    def test_sync_push_key_sets_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts key_sets type."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--type", "key_sets", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_push_keys_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts keys type."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--type", "keys", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_push_vaults_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync push accepts vaults type."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--type", "vaults", "--dry-run"])

        assert "Invalid entity type" not in result.stdout


@pytest.mark.e2e
class TestSyncPullEntityTypesE2E:
    """E2E tests for sync pull with new entity types."""

    def test_sync_pull_help_includes_entity_types(self, cli_runner: CliRunner) -> None:
        """Verify sync pull help mentions entity types."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--help"])

        assert result.exit_code == 0
        assert "--type" in result.stdout or "-t" in result.stdout

    def test_sync_pull_invalid_type_shows_error(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull rejects invalid entity types."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "pull", "--type", "invalid_type", "--dry-run"]
        )

        assert result.exit_code == 1
        assert "Invalid entity type" in result.stdout or "Konnect" in result.stdout

    def test_sync_pull_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts certificates type."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "pull", "--type", "certificates", "--dry-run"]
        )

        assert "Invalid entity type" not in result.stdout

    def test_sync_pull_snis_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts snis type."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--type", "snis", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_pull_ca_certificates_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts ca_certificates type."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "pull", "--type", "ca_certificates", "--dry-run"]
        )

        assert "Invalid entity type" not in result.stdout

    def test_sync_pull_key_sets_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts key_sets type."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--type", "key_sets", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_pull_keys_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts keys type."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--type", "keys", "--dry-run"])

        assert "Invalid entity type" not in result.stdout

    def test_sync_pull_vaults_type_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync pull accepts vaults type."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--type", "vaults", "--dry-run"])

        assert "Invalid entity type" not in result.stdout


@pytest.mark.e2e
class TestSyncHistoryEntityTypesE2E:
    """E2E tests for sync history with new entity types in audit."""

    def test_sync_history_shows_certificate_operations(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync history can show certificate sync operations."""
        mock_service = MagicMock()
        mock_service.list_syncs.return_value = [
            SyncSummary(
                sync_id="cert-sync-123",
                timestamp=datetime.now(UTC).isoformat(),
                operation="push",
                dry_run=False,
                created=1,
                updated=0,
                errors=0,
                entity_types=["certificates"],
            )
        ]
        mock_service.get_sync_details.return_value = [
            SyncAuditEntry(
                sync_id="cert-sync-123",
                timestamp=datetime.now(UTC).isoformat(),
                operation="push",
                dry_run=False,
                entity_type="certificates",
                entity_id="cert-1",
                entity_name="production-cert",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        ]

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(app, ["kong", "sync", "history"])

        assert result.exit_code == 0
        assert "Recent Sync Operations" in result.stdout or "push" in result.stdout

    def test_sync_history_entity_filter_with_certificates(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync history can filter by certificate entity type."""
        mock_service = MagicMock()
        mock_service.get_entity_history.return_value = [
            SyncAuditEntry(
                sync_id="cert-sync-123",
                timestamp=datetime.now(UTC).isoformat(),
                operation="push",
                dry_run=False,
                entity_type="certificates",
                entity_id="cert-1",
                entity_name="my-cert",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        ]

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(
                app,
                [
                    "kong",
                    "sync",
                    "history",
                    "--entity-type",
                    "certificates",
                    "--entity-name",
                    "my-cert",
                ],
            )

        assert result.exit_code == 0
        assert "certificates/my-cert" in result.stdout

    def test_sync_history_entity_filter_with_key_sets(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Verify sync history can filter by key_sets entity type."""
        mock_service = MagicMock()
        mock_service.get_entity_history.return_value = [
            SyncAuditEntry(
                sync_id="keyset-sync-456",
                timestamp=datetime.now(UTC).isoformat(),
                operation="push",
                dry_run=False,
                entity_type="key_sets",
                entity_id="keyset-1",
                entity_name="jwt-keys",
                action="create",
                source="gateway",
                target="konnect",
                status="success",
            )
        ]

        with patch(
            "system_operations_manager.services.kong.sync_audit.SyncAuditService"
        ) as mock_class:
            mock_class.return_value = mock_service
            result = cli_runner.invoke(
                app,
                [
                    "kong",
                    "sync",
                    "history",
                    "--entity-type",
                    "key_sets",
                    "--entity-name",
                    "jwt-keys",
                ],
            )

        assert result.exit_code == 0
        assert "key_sets/jwt-keys" in result.stdout
