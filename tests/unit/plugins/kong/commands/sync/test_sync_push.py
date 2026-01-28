"""Unit tests for sync push command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.plugins.kong.commands.sync import register_sync_commands


class TestSyncPushCommand:
    """Tests for sync push command."""

    @pytest.fixture
    def app(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        mock_konnect_route_manager: MagicMock,
        mock_konnect_consumer_manager: MagicMock,
        mock_konnect_plugin_manager: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with sync commands."""
        app = typer.Typer()
        register_sync_commands(
            app,
            lambda: mock_unified_service,
            lambda: mock_konnect_service_manager,
            lambda: mock_konnect_route_manager,
            lambda: mock_konnect_consumer_manager,
            lambda: mock_konnect_plugin_manager,
            lambda: mock_konnect_upstream_manager,
        )
        return app

    @pytest.fixture
    def app_no_konnect(self) -> typer.Typer:
        """Create a test app with sync commands but no Konnect configured."""
        app = typer.Typer()
        register_sync_commands(
            app,
            lambda: None,  # No unified service
        )
        return app

    @pytest.mark.unit
    def test_push_nothing_to_sync(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """push should show message when Gateway and Konnect are in sync."""
        # Default mock returns no changes
        result = cli_runner.invoke(app, ["sync", "push"])

        assert result.exit_code == 0
        assert "Nothing to push" in result.stdout or "in sync" in result.stdout

    @pytest.mark.unit
    def test_push_dry_run_shows_preview(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
        sync_summary_with_changes: dict[str, dict[str, int]],
    ) -> None:
        """push --dry-run should show what would be pushed."""
        mock_unified_service.get_sync_summary.return_value = sync_summary_with_changes
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(app, ["sync", "push", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.stdout.lower()
        assert "Would create:" in result.stdout

    @pytest.mark.unit
    def test_push_creates_gateway_only_entities(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push should create entities that only exist in Gateway."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(app, ["sync", "push", "--force"])

        assert result.exit_code == 0
        assert mock_konnect_service_manager.create.call_count == 2
        assert "Created:" in result.stdout

    @pytest.mark.unit
    def test_push_updates_entities_with_drift(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """push should update entities with drift."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(app, ["sync", "push", "--force"])

        assert result.exit_code == 0
        assert mock_konnect_service_manager.update.call_count == 1
        assert "Updated:" in result.stdout

    @pytest.mark.unit
    def test_push_dry_run_makes_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push --dry-run should not call create/update."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(app, ["sync", "push", "--dry-run"])

        assert result.exit_code == 0
        mock_konnect_service_manager.create.assert_not_called()
        mock_konnect_service_manager.update.assert_not_called()

    @pytest.mark.unit
    def test_push_handles_konnect_errors(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push should handle and report Konnect API errors."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = sample_gateway_only_services
        mock_konnect_service_manager.create.side_effect = Exception("Connection timeout")

        result = cli_runner.invoke(app, ["sync", "push", "--force"])

        assert result.exit_code == 0  # Command completes with errors reported
        assert "Failed to create:" in result.stdout
        assert "Errors:" in result.stdout

    @pytest.mark.unit
    def test_push_single_entity_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        mock_konnect_route_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push --type services should only push services."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
        }
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(app, ["sync", "push", "--type", "services", "--force"])

        assert result.exit_code == 0
        assert mock_konnect_service_manager.create.call_count == 2
        mock_konnect_route_manager.create.assert_not_called()

    @pytest.mark.unit
    def test_push_skipped_when_konnect_not_configured(
        self,
        cli_runner: CliRunner,
        app_no_konnect: typer.Typer,
    ) -> None:
        """push should show error when Konnect is not configured."""
        result = cli_runner.invoke(app_no_konnect, ["sync", "push"])

        assert result.exit_code == 1
        assert "Konnect not configured" in result.stdout

    @pytest.mark.unit
    def test_push_force_skips_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push --force should not prompt for confirmation."""
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        # Force flag should allow command to proceed without confirmation input
        result = cli_runner.invoke(app, ["sync", "push", "--force"])

        assert result.exit_code == 0
        assert mock_konnect_service_manager.create.call_count == 2

    @pytest.mark.unit
    def test_push_invalid_entity_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """push --type with invalid type should show error."""
        result = cli_runner.invoke(app, ["sync", "push", "--type", "invalid"])

        assert result.exit_code == 1
        assert "Invalid entity type" in result.stdout

    @pytest.mark.unit
    def test_push_summary_shows_counts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """push should show summary with correct counts."""
        # Combine gateway_only and drifted services
        combined = UnifiedEntityList(
            entities=sample_gateway_only_services.entities + sample_drifted_services.entities
        )
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 1, "total": 3},
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        mock_unified_service.list_services.return_value = combined

        result = cli_runner.invoke(app, ["sync", "push", "--force"])

        assert result.exit_code == 0
        assert "Summary" in result.stdout
        assert "Created: 2" in result.stdout
        assert "Updated: 1" in result.stdout


class TestPushEntityTypeHelper:
    """Tests for _push_entity_type helper function."""

    @pytest.mark.unit
    def test_push_entity_type_skips_none_entity(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Helper should skip entities where gateway_entity is None."""
        from system_operations_manager.plugins.kong.commands.sync import _push_entity_type

        # Create entity with None gateway_entity
        entity = UnifiedEntity(
            entity=Service(name="test"),
            source=EntitySource.GATEWAY,
            gateway_id="svc-1",
            konnect_id=None,
            has_drift=False,
            gateway_entity=None,  # Explicitly None
        )
        mock_unified_service.list_services.return_value = UnifiedEntityList(entities=[entity])

        created, updated, errors = _push_entity_type(
            "services",
            mock_unified_service,
            {"services": mock_konnect_service_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0
        mock_konnect_service_manager.create.assert_not_called()

    @pytest.mark.unit
    def test_push_entity_type_skips_unknown_type(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Helper should return zeros for unknown entity type."""
        from system_operations_manager.plugins.kong.commands.sync import _push_entity_type

        created, updated, errors = _push_entity_type(
            "unknown",
            mock_unified_service,
            {"services": mock_konnect_service_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0

    @pytest.mark.unit
    def test_push_entity_type_skips_missing_manager(
        self,
        mock_unified_service: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """Helper should skip if manager not in dict."""
        from system_operations_manager.plugins.kong.commands.sync import _push_entity_type

        mock_unified_service.list_services.return_value = sample_gateway_only_services

        created, updated, errors = _push_entity_type(
            "services",
            mock_unified_service,
            {},  # No managers
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0
