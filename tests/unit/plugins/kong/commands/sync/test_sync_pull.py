"""Unit tests for sync pull command."""

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


class TestSyncPullCommand:
    """Tests for sync pull command."""

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
        """Create a test app with sync commands including Gateway managers."""
        app = typer.Typer()

        # Create mock Gateway managers
        mock_gateway_service_manager = MagicMock()
        mock_gateway_service_manager.create.return_value = Service(
            name="created-service", host="localhost"
        )
        mock_gateway_service_manager.update.return_value = Service(
            name="updated-service", host="localhost"
        )

        mock_gateway_route_manager = MagicMock()
        mock_gateway_consumer_manager = MagicMock()
        mock_gateway_plugin_manager = MagicMock()
        mock_gateway_upstream_manager = MagicMock()

        register_sync_commands(
            app,
            lambda: mock_unified_service,
            lambda: mock_konnect_service_manager,
            lambda: mock_konnect_route_manager,
            lambda: mock_konnect_consumer_manager,
            lambda: mock_konnect_plugin_manager,
            lambda: mock_konnect_upstream_manager,
            # Gateway managers for pull
            get_gateway_service_manager=lambda: mock_gateway_service_manager,
            get_gateway_route_manager=lambda: mock_gateway_route_manager,
            get_gateway_consumer_manager=lambda: mock_gateway_consumer_manager,
            get_gateway_plugin_manager=lambda: mock_gateway_plugin_manager,
            get_gateway_upstream_manager=lambda: mock_gateway_upstream_manager,
        )
        return app

    @pytest.fixture
    def app_with_gateway_managers(
        self,
        mock_unified_service: MagicMock,
    ) -> tuple[typer.Typer, MagicMock]:
        """Create a test app with sync commands and return the Gateway service manager."""
        app = typer.Typer()

        mock_gateway_service_manager = MagicMock()
        mock_gateway_service_manager.create.return_value = Service(
            name="created-service", host="localhost"
        )
        mock_gateway_service_manager.update.return_value = Service(
            name="updated-service", host="localhost"
        )

        register_sync_commands(
            app,
            lambda: mock_unified_service,
            get_gateway_service_manager=lambda: mock_gateway_service_manager,
            get_gateway_route_manager=MagicMock,
            get_gateway_consumer_manager=MagicMock,
            get_gateway_plugin_manager=MagicMock,
            get_gateway_upstream_manager=MagicMock,
        )
        return app, mock_gateway_service_manager

    @pytest.fixture
    def app_no_konnect(self) -> typer.Typer:
        """Create a test app with sync commands but no Konnect configured."""
        app = typer.Typer()
        register_sync_commands(
            app,
            lambda: None,  # No unified service
        )
        return app

    @pytest.fixture
    def sample_konnect_only_services(self) -> UnifiedEntityList[Service]:
        """Sample services that exist only in Konnect."""
        service1 = Service(id="svc-1", name="konnect-api", host="api.konnect.local")
        service2 = Service(id="svc-2", name="konnect-backend", host="backend.konnect.local")

        entities = [
            UnifiedEntity(
                entity=service1,
                source=EntitySource.KONNECT,
                gateway_id=None,
                konnect_id="svc-1",
                has_drift=False,
                konnect_entity=service1,
            ),
            UnifiedEntity(
                entity=service2,
                source=EntitySource.KONNECT,
                gateway_id=None,
                konnect_id="svc-2",
                has_drift=False,
                konnect_entity=service2,
            ),
        ]
        return UnifiedEntityList(entities=entities)

    @pytest.fixture
    def sample_drifted_services_for_pull(self) -> UnifiedEntityList[Service]:
        """Sample services with drift for testing pull with --with-drift."""
        gateway_svc = Service(id="svc-1", name="my-api", host="old-host.local", port=80)
        konnect_svc = Service(id="svc-1", name="my-api", host="new-host.local", port=8080)

        entities = [
            UnifiedEntity(
                entity=konnect_svc,  # Use Konnect version as primary for pull
                source=EntitySource.BOTH,
                gateway_id="gateway-svc-1",
                konnect_id="konnect-svc-1",
                has_drift=True,
                drift_fields=["host", "port"],
                gateway_entity=gateway_svc,
                konnect_entity=konnect_svc,
            ),
        ]
        return UnifiedEntityList(entities=entities)

    @pytest.fixture
    def sync_summary_with_konnect_only(self) -> dict[str, dict[str, int]]:
        """Sample sync summary with entities only in Konnect."""
        return {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 1, "drift": 0, "total": 3},
            "routes": {"gateway_only": 0, "konnect_only": 1, "synced": 0, "drift": 0, "total": 1},
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

    @pytest.mark.unit
    def test_pull_nothing_to_sync(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull should show message when Gateway and Konnect are in sync."""
        # Default mock returns no changes (everything synced)
        result = cli_runner.invoke(app, ["sync", "pull"])

        assert result.exit_code == 0
        assert "Nothing to pull" in result.stdout or "in sync" in result.stdout

    @pytest.mark.unit
    def test_pull_dry_run_shows_preview(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
        sync_summary_with_konnect_only: dict[str, dict[str, int]],
    ) -> None:
        """pull --dry-run should show what would be pulled."""
        mock_unified_service.get_sync_summary.return_value = sync_summary_with_konnect_only
        mock_unified_service.list_services.return_value = sample_konnect_only_services

        result = cli_runner.invoke(app, ["sync", "pull", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.stdout.lower()
        assert "Would create:" in result.stdout

    @pytest.mark.unit
    def test_pull_creates_konnect_only_entities(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """pull should create entities that only exist in Konnect."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        }
        mock_unified_service.list_services.return_value = sample_konnect_only_services

        result = cli_runner.invoke(app, ["sync", "pull", "--force"])

        assert result.exit_code == 0
        assert mock_gateway_service_manager.create.call_count == 2
        assert "Created:" in result.stdout

    @pytest.mark.unit
    def test_pull_with_drift_updates_entities(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_drifted_services_for_pull: UnifiedEntityList[Service],
    ) -> None:
        """pull --with-drift should update entities with drift."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 1, "total": 1},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        }
        mock_unified_service.list_services.return_value = sample_drifted_services_for_pull

        result = cli_runner.invoke(app, ["sync", "pull", "--with-drift", "--force"])

        assert result.exit_code == 0
        assert mock_gateway_service_manager.update.call_count == 1
        assert "Updated:" in result.stdout

    @pytest.mark.unit
    def test_pull_dry_run_makes_no_changes(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """pull --dry-run should not call create/update."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        }
        mock_unified_service.list_services.return_value = sample_konnect_only_services

        result = cli_runner.invoke(app, ["sync", "pull", "--dry-run"])

        assert result.exit_code == 0
        mock_gateway_service_manager.create.assert_not_called()
        mock_gateway_service_manager.update.assert_not_called()

    @pytest.mark.unit
    def test_pull_handles_gateway_errors(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """pull should handle and report Gateway API errors."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        }
        mock_unified_service.list_services.return_value = sample_konnect_only_services
        mock_gateway_service_manager.create.side_effect = Exception("Connection timeout")

        result = cli_runner.invoke(app, ["sync", "pull", "--force"])

        assert result.exit_code == 0  # Command completes with errors reported
        assert "Failed to create:" in result.stdout

    @pytest.mark.unit
    def test_pull_single_entity_type(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """pull --type services should only pull services."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
        }
        mock_unified_service.list_services.return_value = sample_konnect_only_services

        result = cli_runner.invoke(app, ["sync", "pull", "--type", "services", "--force"])

        assert result.exit_code == 0
        assert mock_gateway_service_manager.create.call_count == 2

    @pytest.mark.unit
    def test_pull_skipped_when_konnect_not_configured(
        self,
        cli_runner: CliRunner,
        app_no_konnect: typer.Typer,
    ) -> None:
        """pull should show error when Konnect is not configured."""
        result = cli_runner.invoke(app_no_konnect, ["sync", "pull"])

        assert result.exit_code == 1
        assert "Konnect not configured" in result.stdout

    @pytest.mark.unit
    def test_pull_force_skips_confirmation(
        self,
        cli_runner: CliRunner,
        app_with_gateway_managers: tuple[typer.Typer, MagicMock],
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """pull --force should not prompt for confirmation."""
        app, mock_gateway_service_manager = app_with_gateway_managers
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "consumers": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
            "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        }
        mock_unified_service.list_services.return_value = sample_konnect_only_services

        # Force flag should allow command to proceed without confirmation input
        result = cli_runner.invoke(app, ["sync", "pull", "--force"])

        assert result.exit_code == 0
        assert mock_gateway_service_manager.create.call_count == 2

    @pytest.mark.unit
    def test_pull_invalid_entity_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """pull --type with invalid type should show error."""
        result = cli_runner.invoke(app, ["sync", "pull", "--type", "invalid"])

        assert result.exit_code == 1
        assert "Invalid entity type" in result.stdout

    @pytest.mark.unit
    def test_pull_shows_drift_hint_when_not_using_with_drift(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull without --with-drift should show hint about drifted entities."""
        # No konnect_only but has drift
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 2, "total": 3},
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

        result = cli_runner.invoke(app, ["sync", "pull"])

        assert result.exit_code == 0
        assert "Nothing to pull" in result.stdout
        assert "--with-drift" in result.stdout


class TestPullEntityTypeHelper:
    """Tests for _pull_entity_type helper function."""

    @pytest.mark.unit
    def test_pull_entity_type_skips_none_entity(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Helper should skip entities where konnect_entity is None."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_gateway_manager = MagicMock()

        # Create entity with None konnect_entity
        entity = UnifiedEntity(
            entity=Service(name="test"),
            source=EntitySource.KONNECT,
            gateway_id=None,
            konnect_id="svc-1",
            has_drift=False,
            konnect_entity=None,  # Explicitly None
        )
        mock_unified_service.list_services.return_value = UnifiedEntityList(entities=[entity])

        created, updated, errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": mock_gateway_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0
        mock_gateway_manager.create.assert_not_called()

    @pytest.mark.unit
    def test_pull_entity_type_skips_unknown_type(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Helper should return zeros for unknown entity type."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_gateway_manager = MagicMock()

        created, updated, errors = _pull_entity_type(
            "unknown",
            mock_unified_service,
            {"services": mock_gateway_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0

    @pytest.mark.unit
    def test_pull_entity_type_skips_missing_manager(
        self,
        mock_unified_service: MagicMock,
        sample_konnect_only_services: UnifiedEntityList[Service],
    ) -> None:
        """Helper should skip if manager not in dict."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_unified_service.list_services.return_value = sample_konnect_only_services

        created, updated, errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {},  # No managers
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0

    @pytest.fixture
    def sample_konnect_only_services(self) -> UnifiedEntityList[Service]:
        """Sample services that exist only in Konnect."""
        service1 = Service(id="svc-1", name="konnect-api", host="api.konnect.local")

        entities = [
            UnifiedEntity(
                entity=service1,
                source=EntitySource.KONNECT,
                gateway_id=None,
                konnect_id="svc-1",
                has_drift=False,
                konnect_entity=service1,
            ),
        ]
        return UnifiedEntityList(entities=entities)
