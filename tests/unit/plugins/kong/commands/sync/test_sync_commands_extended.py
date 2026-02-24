"""Extended tests for sync push/pull/rollback commands covering manager building and options."""

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
from system_operations_manager.plugins.kong.commands.sync import register_sync_commands


def _summary_with_drift() -> dict[str, dict[str, int]]:
    """Return a sync summary with drift in services."""
    return {
        "services": {"gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 1, "total": 2},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


def _summary_with_gateway_only() -> dict[str, dict[str, int]]:
    """Return a sync summary with gateway-only services."""
    return {
        "services": {"gateway_only": 2, "konnect_only": 0, "synced": 0, "drift": 0, "total": 2},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


def _summary_with_konnect_only() -> dict[str, dict[str, int]]:
    """Return a sync summary with konnect-only services."""
    return {
        "services": {"gateway_only": 0, "konnect_only": 2, "synced": 0, "drift": 0, "total": 2},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


def _summary_with_gateway_only_and_drift() -> dict[str, dict[str, int]]:
    """Return a sync summary with both gateway-only and drift."""
    return {
        "services": {"gateway_only": 1, "konnect_only": 0, "synced": 0, "drift": 1, "total": 2},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


def _summary_with_upstreams() -> dict[str, dict[str, int]]:
    """Return a sync summary with upstream entities."""
    return {
        "services": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 1, "konnect_only": 0, "synced": 1, "drift": 0, "total": 2},
    }


def _summary_konnect_upstreams() -> dict[str, dict[str, int]]:
    """Return a sync summary with konnect-only upstream entities."""
    return {
        "services": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 1, "synced": 1, "drift": 0, "total": 2},
    }


def _empty_summary() -> dict[str, dict[str, int]]:
    """Return an empty sync summary."""
    return {
        "services": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


@pytest.fixture
def full_app(
    mock_unified_service: MagicMock,
    mock_konnect_service_manager: MagicMock,
    mock_konnect_route_manager: MagicMock,
    mock_konnect_consumer_manager: MagicMock,
    mock_konnect_plugin_manager: MagicMock,
    mock_konnect_upstream_manager: MagicMock,
    mock_gateway_upstream_manager: MagicMock,
) -> typer.Typer:
    """Create a test app with ALL manager factories (konnect + gateway + extended)."""
    mock_cert_mgr = MagicMock()
    mock_sni_mgr = MagicMock()
    mock_ca_cert_mgr = MagicMock()
    mock_key_set_mgr = MagicMock()
    mock_key_mgr = MagicMock()
    mock_vault_mgr = MagicMock()
    mock_gw_svc_mgr = MagicMock()
    mock_gw_route_mgr = MagicMock()
    mock_gw_consumer_mgr = MagicMock()
    mock_gw_plugin_mgr = MagicMock()
    mock_gw_cert_mgr = MagicMock()
    mock_gw_sni_mgr = MagicMock()
    mock_gw_ca_cert_mgr = MagicMock()
    mock_gw_key_set_mgr = MagicMock()
    mock_gw_key_mgr = MagicMock()
    mock_gw_vault_mgr = MagicMock()

    app = typer.Typer()
    register_sync_commands(
        app,
        lambda: mock_unified_service,
        # Konnect managers
        get_konnect_service_manager=lambda: mock_konnect_service_manager,
        get_konnect_route_manager=lambda: mock_konnect_route_manager,
        get_konnect_consumer_manager=lambda: mock_konnect_consumer_manager,
        get_konnect_plugin_manager=lambda: mock_konnect_plugin_manager,
        get_konnect_upstream_manager=lambda: mock_konnect_upstream_manager,
        get_konnect_certificate_manager=lambda: mock_cert_mgr,
        get_konnect_sni_manager=lambda: mock_sni_mgr,
        get_konnect_ca_certificate_manager=lambda: mock_ca_cert_mgr,
        get_konnect_key_set_manager=lambda: mock_key_set_mgr,
        get_konnect_key_manager=lambda: mock_key_mgr,
        get_konnect_vault_manager=lambda: mock_vault_mgr,
        # Gateway managers
        get_gateway_service_manager=lambda: mock_gw_svc_mgr,
        get_gateway_route_manager=lambda: mock_gw_route_mgr,
        get_gateway_consumer_manager=lambda: mock_gw_consumer_mgr,
        get_gateway_plugin_manager=lambda: mock_gw_plugin_mgr,
        get_gateway_upstream_manager=lambda: mock_gateway_upstream_manager,
        get_gateway_certificate_manager=lambda: mock_gw_cert_mgr,
        get_gateway_sni_manager=lambda: mock_gw_sni_mgr,
        get_gateway_ca_certificate_manager=lambda: mock_gw_ca_cert_mgr,
        get_gateway_key_set_manager=lambda: mock_gw_key_set_mgr,
        get_gateway_key_manager=lambda: mock_gw_key_mgr,
        get_gateway_vault_manager=lambda: mock_gw_vault_mgr,
    )
    return app


@pytest.fixture
def app_no_managers(mock_unified_service: MagicMock) -> typer.Typer:
    """Create a test app with unified service but NO manager factories."""
    app = typer.Typer()
    register_sync_commands(
        app,
        lambda: mock_unified_service,
        # No managers passed - all default to None
    )
    return app


class TestPushExtended:
    """Extended tests for sync push command options."""

    @pytest.mark.unit
    def test_push_skip_conflicts_nothing_to_push(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """push --skip-conflicts with only drift shows skip message."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        result = cli_runner.invoke(full_app, ["sync", "push", "--skip-conflicts", "--force"])

        assert result.exit_code == 0
        assert "conflict(s) skipped" in result.stdout

    @pytest.mark.unit
    def test_push_skip_conflicts_with_gateway_only(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push --skip-conflicts still creates gateway-only but skips drifted."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_gateway_only_and_drift()
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(full_app, ["sync", "push", "--skip-conflicts", "--force"])

        assert result.exit_code == 0
        assert "Skipping" in result.stdout
        assert "drift" in result.stdout

    @pytest.mark.unit
    def test_push_skip_conflicts_and_interactive_mutually_exclusive(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """push --skip-conflicts --interactive should error."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_gateway_only()
        result = cli_runner.invoke(
            full_app, ["sync", "push", "--skip-conflicts", "--interactive", "--force"]
        )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout

    @pytest.mark.unit
    def test_push_no_managers_available(
        self,
        cli_runner: CliRunner,
        app_no_managers: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """push with no konnect managers shows error."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_gateway_only()
        result = cli_runner.invoke(app_no_managers, ["sync", "push", "--force"])

        assert result.exit_code == 1
        assert "No Konnect managers" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_push_interactive_mode_applies_resolutions(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """push --interactive launches TUI and applies resolutions."""
        from system_operations_manager.services.kong.conflict_resolver import (
            Conflict,
            Resolution,
            ResolutionAction,
        )

        conflict = Conflict(
            entity_type="services",
            entity_id="svc-1",
            entity_name="my-api",
            direction="push",
            source_state={"host": "new-host.local"},
            target_state={"host": "old-host.local"},
            drift_fields=["host"],
        )
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.KEEP_SOURCE,
        )
        mock_tui.return_value = [resolution]
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(full_app, ["sync", "push", "--interactive"])

        assert result.exit_code == 0
        assert "Applying" in result.stdout
        assert "1 resolution" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_push_interactive_no_resolutions_cancels(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """push --interactive with empty resolutions cancels."""
        mock_tui.return_value = []
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()

        result = cli_runner.invoke(full_app, ["sync", "push", "--interactive"])

        assert result.exit_code == 0
        assert "No resolutions" in result.stdout or "Cancelled" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync.confirm_action")
    def test_push_confirmation_declined(
        self,
        mock_confirm: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_gateway_only_services: UnifiedEntityList[Service],
    ) -> None:
        """push without --force asks for confirmation; declining cancels."""
        mock_confirm.return_value = False
        mock_unified_service.get_sync_summary.return_value = _summary_with_gateway_only()
        mock_unified_service.list_services.return_value = sample_gateway_only_services

        result = cli_runner.invoke(full_app, ["sync", "push"])

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_push_interactive_record_skipped_resolutions(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """push --interactive records skipped resolutions in audit."""
        from system_operations_manager.services.kong.conflict_resolver import (
            Conflict,
            Resolution,
            ResolutionAction,
        )

        conflict = Conflict(
            entity_type="services",
            entity_id="svc-1",
            entity_name="my-api",
            direction="push",
            source_state={"host": "new-host.local"},
            target_state={"host": "old-host.local"},
            drift_fields=["host"],
        )
        # KEEP_TARGET = skip this entity
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.KEEP_TARGET,
        )
        mock_tui.return_value = [resolution]
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(full_app, ["sync", "push", "--interactive"])

        # With KEEP_TARGET only, total_to_update becomes 0 -> should apply 0 resolutions
        assert result.exit_code == 0

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_push_interactive_merge_resolution(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_service_manager: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """push --interactive with MERGE resolution includes merged_state."""
        from system_operations_manager.services.kong.conflict_resolver import (
            Conflict,
            Resolution,
            ResolutionAction,
        )

        conflict = Conflict(
            entity_type="services",
            entity_id="svc-1",
            entity_name="my-api",
            direction="push",
            source_state={"host": "new-host.local"},
            target_state={"host": "old-host.local"},
            drift_fields=["host"],
        )
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.MERGE,
            merged_state={"host": "merged-host.local"},
        )
        mock_tui.return_value = [resolution]
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(full_app, ["sync", "push", "--interactive"])

        assert result.exit_code == 0
        assert "Applying 1 resolution" in result.stdout

    @pytest.mark.unit
    def test_push_include_targets(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
        sample_upstreams: MagicMock,
        sample_gateway_only_targets: MagicMock,
    ) -> None:
        """push --include-targets pushes targets for upstream entities."""

        mock_unified_service.get_sync_summary.return_value = _summary_with_upstreams()
        mock_unified_service.list_upstreams.return_value = sample_upstreams
        mock_unified_service.list_targets_for_upstream.return_value = sample_gateway_only_targets

        result = cli_runner.invoke(
            full_app, ["sync", "push", "--type", "upstreams", "--include-targets", "--force"]
        )

        assert result.exit_code == 0
        assert "Targets" in result.stdout


class TestPullExtended:
    """Extended tests for sync pull command options."""

    @pytest.mark.unit
    def test_pull_skip_conflicts_nothing_to_pull(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull --skip-conflicts with only drift shows skip message."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        result = cli_runner.invoke(full_app, ["sync", "pull", "--skip-conflicts", "--force"])

        assert result.exit_code == 0
        assert "conflict(s) skipped" in result.stdout

    @pytest.mark.unit
    def test_pull_skip_conflicts_and_interactive_mutually_exclusive(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull --skip-conflicts --interactive should error."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_konnect_only()
        result = cli_runner.invoke(
            full_app, ["sync", "pull", "--skip-conflicts", "--interactive", "--force"]
        )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout

    @pytest.mark.unit
    def test_pull_no_managers_available(
        self,
        cli_runner: CliRunner,
        app_no_managers: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull with no gateway managers shows error."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_konnect_only()
        result = cli_runner.invoke(app_no_managers, ["sync", "pull", "--force"])

        assert result.exit_code == 1
        assert "No Gateway managers" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_pull_interactive_mode(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """pull --interactive launches TUI and applies resolutions."""
        from system_operations_manager.services.kong.conflict_resolver import (
            Conflict,
            Resolution,
            ResolutionAction,
        )

        conflict = Conflict(
            entity_type="services",
            entity_id="svc-1",
            entity_name="my-api",
            direction="pull",
            source_state={"host": "konnect-host.local"},
            target_state={"host": "gateway-host.local"},
            drift_fields=["host"],
        )
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.KEEP_SOURCE,
        )
        mock_tui.return_value = [resolution]
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(full_app, ["sync", "pull", "--interactive"])

        assert result.exit_code == 0
        assert "Applying 1 resolution" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_pull_interactive_no_resolutions_cancels(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull --interactive with empty resolutions cancels."""
        mock_tui.return_value = []
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()

        result = cli_runner.invoke(full_app, ["sync", "pull", "--interactive"])

        assert result.exit_code == 0
        assert "No resolutions" in result.stdout or "Cancelled" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync.confirm_action")
    def test_pull_confirmation_declined(
        self,
        mock_confirm: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull without --force asks for confirmation; declining cancels."""
        mock_confirm.return_value = False
        mock_unified_service.get_sync_summary.return_value = _summary_with_konnect_only()

        result = cli_runner.invoke(full_app, ["sync", "pull"])

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout

    @pytest.mark.unit
    def test_pull_skip_conflicts_with_konnect_only_and_drift(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull --skip-conflicts with konnect-only shows skip message and pulls new."""
        summary = {
            "services": {
                "gateway_only": 0,
                "konnect_only": 1,
                "synced": 0,
                "drift": 1,
                "total": 2,
            },
            "routes": {
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
            "plugins": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
            "upstreams": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 0,
            },
        }
        konnect_svc = Service(id="konnect-svc-1", name="konnect-api", host="konnect.local")
        konnect_only_entities = UnifiedEntityList(
            entities=[
                UnifiedEntity(
                    entity=konnect_svc,
                    source=EntitySource.KONNECT,
                    gateway_id=None,
                    konnect_id="konnect-svc-1",
                    has_drift=False,
                    konnect_entity=konnect_svc,
                ),
            ]
        )
        mock_unified_service.get_sync_summary.return_value = summary
        mock_unified_service.list_services.return_value = konnect_only_entities

        result = cli_runner.invoke(full_app, ["sync", "pull", "--skip-conflicts", "--force"])

        assert result.exit_code == 0
        assert "Skipping" in result.stdout

    @pytest.mark.unit
    def test_pull_include_targets(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        mock_gateway_upstream_manager: MagicMock,
        sample_upstreams: MagicMock,
        sample_konnect_only_targets: MagicMock,
    ) -> None:
        """pull --include-targets pulls targets for upstream entities."""
        mock_unified_service.get_sync_summary.return_value = _summary_konnect_upstreams()
        mock_unified_service.list_upstreams.return_value = sample_upstreams
        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets

        result = cli_runner.invoke(
            full_app, ["sync", "pull", "--type", "upstreams", "--include-targets", "--force"]
        )

        assert result.exit_code == 0
        assert "Targets" in result.stdout

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui")
    def test_pull_interactive_record_skipped_resolutions(
        self,
        mock_tui: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
    ) -> None:
        """pull --interactive records skipped resolutions."""
        from system_operations_manager.services.kong.conflict_resolver import (
            Conflict,
            Resolution,
            ResolutionAction,
        )

        conflict = Conflict(
            entity_type="services",
            entity_id="svc-1",
            entity_name="my-api",
            direction="pull",
            source_state={"host": "konnect-host.local"},
            target_state={"host": "gw-host.local"},
            drift_fields=["host"],
        )
        resolution = Resolution(conflict=conflict, action=ResolutionAction.SKIP)
        mock_tui.return_value = [resolution]
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()

        result = cli_runner.invoke(full_app, ["sync", "pull", "--interactive"])

        # Skip resolution -> 0 resolved -> applies 0
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_pull_with_drift_summary_line(
        self,
        cli_runner: CliRunner,
        full_app: typer.Typer,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """pull --with-drift shows 'Would update' in dry run summary."""
        mock_unified_service.get_sync_summary.return_value = _summary_with_drift()
        mock_unified_service.list_services.return_value = sample_drifted_services

        result = cli_runner.invoke(full_app, ["sync", "pull", "--with-drift", "--dry-run"])

        assert result.exit_code == 0
        assert "Would update" in result.stdout


class TestRollbackExtended:
    """Extended tests for sync rollback command covering manager building."""

    @pytest.mark.unit
    @patch("system_operations_manager.services.kong.sync_rollback.RollbackService")
    @patch("system_operations_manager.services.kong.sync_audit.SyncAuditService")
    @patch("system_operations_manager.plugins.kong.commands.sync.confirm_action")
    def test_rollback_confirmation_declined(
        self,
        mock_confirm: MagicMock,
        mock_audit_cls: MagicMock,
        mock_rollback_cls: MagicMock,
        cli_runner: CliRunner,
        full_app: typer.Typer,
    ) -> None:
        """rollback without --force asks for confirmation; declining cancels."""
        mock_audit = MagicMock()
        mock_audit_cls.return_value = mock_audit
        mock_rollback = MagicMock()
        mock_rollback_cls.return_value = mock_rollback

        preview = MagicMock()
        preview.can_rollback = True
        preview.operation = "push"
        preview.timestamp = "2024-01-01T00:00:00Z"
        preview.warnings = []
        action = MagicMock()
        action.entity_type = "services"
        action.entity_name = "test-api"
        action.rollback_action = "delete"
        action.target = "konnect"
        preview.actions = [action]
        mock_rollback.preview_rollback.return_value = preview
        mock_confirm.return_value = False

        result = cli_runner.invoke(full_app, ["sync", "rollback", "abc123"])

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout


class TestLaunchConflictResolutionTui:
    """Tests for _launch_conflict_resolution_tui helper."""

    @pytest.mark.unit
    @patch("system_operations_manager.plugins.kong.commands.sync.ConflictResolutionService")
    def test_no_conflicts_returns_empty(
        self,
        mock_conflict_cls: MagicMock,
        mock_unified_service: MagicMock,
    ) -> None:
        """Returns empty list when no conflicts found."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _launch_conflict_resolution_tui,
        )

        mock_conflict_svc = MagicMock()
        mock_conflict_cls.return_value = mock_conflict_svc
        mock_conflict_svc.collect_conflicts.return_value = []

        result = _launch_conflict_resolution_tui(mock_unified_service, ["services"], "push", False)

        assert result == []

    @pytest.mark.unit
    @patch("system_operations_manager.tui.apps.conflict_resolution.ConflictResolutionApp")
    @patch("system_operations_manager.plugins.kong.commands.sync.ConflictResolutionService")
    def test_launches_tui_with_conflicts(
        self,
        mock_conflict_cls: MagicMock,
        mock_app_cls: MagicMock,
        mock_unified_service: MagicMock,
    ) -> None:
        """Launches TUI when conflicts are found and returns resolutions."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _launch_conflict_resolution_tui,
        )

        mock_conflict_svc = MagicMock()
        mock_conflict_cls.return_value = mock_conflict_svc
        mock_conflict_svc.collect_conflicts.return_value = [MagicMock()]

        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        mock_resolution = MagicMock()
        mock_app.run_and_get_resolutions.return_value = [mock_resolution]

        result = _launch_conflict_resolution_tui(
            mock_unified_service, ["services", "routes"], "pull", True
        )

        assert len(result) == 1
        assert result[0] is mock_resolution
        mock_app_cls.assert_called_once_with(
            conflicts=[mock_conflict_svc.collect_conflicts.return_value[0]],
            direction="pull",
            dry_run=True,
        )


class TestPullTargetsForUpstreams:
    """Tests for _pull_targets_for_upstreams helper."""

    @pytest.mark.unit
    def test_pull_targets_error_handling(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Pull targets handles errors when fetching targets."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_targets_for_upstreams,
        )

        mock_unified_service.list_targets_for_upstream.side_effect = Exception("timeout")
        gateway_mgr = MagicMock()

        created, updated, errors = _pull_targets_for_upstreams(
            mock_unified_service, ["backend-upstream"], gateway_mgr, False
        )

        assert created == 0
        assert updated == 0
        assert errors == 0  # Error is printed, not counted

    @pytest.mark.unit
    def test_pull_targets_skips_none_entity(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Pull targets skips entries with None konnect_entity."""
        from system_operations_manager.integrations.kong.models.upstream import Target
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_targets_for_upstreams,
        )

        entity = UnifiedEntity(
            entity=Target(target="server:8080"),
            source=EntitySource.KONNECT,
            gateway_id=None,
            konnect_id="t-1",
            has_drift=False,
            konnect_entity=None,  # None entity
        )
        mock_unified_service.list_targets_for_upstream.return_value = UnifiedEntityList(
            entities=[entity]
        )
        gateway_mgr = MagicMock()

        created, _updated, _errors = _pull_targets_for_upstreams(
            mock_unified_service, ["backend"], gateway_mgr, False
        )

        assert created == 0
        gateway_mgr.add_target.assert_not_called()

    @pytest.mark.unit
    def test_pull_targets_dry_run(
        self,
        mock_unified_service: MagicMock,
        sample_konnect_only_targets: MagicMock,
    ) -> None:
        """Pull targets dry run counts but doesn't call manager."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_targets_for_upstreams,
        )

        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets
        gateway_mgr = MagicMock()

        created, _updated, _errors = _pull_targets_for_upstreams(
            mock_unified_service, ["backend"], gateway_mgr, dry_run=True
        )

        assert created == 2
        gateway_mgr.add_target.assert_not_called()

    @pytest.mark.unit
    def test_pull_targets_creates_successfully(
        self,
        mock_unified_service: MagicMock,
        sample_konnect_only_targets: MagicMock,
    ) -> None:
        """Pull targets creates via gateway manager."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_targets_for_upstreams,
        )

        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets
        gateway_mgr = MagicMock()

        created, _updated, _errors = _pull_targets_for_upstreams(
            mock_unified_service, ["backend"], gateway_mgr, dry_run=False
        )

        assert created == 2
        assert gateway_mgr.add_target.call_count == 2

    @pytest.mark.unit
    def test_pull_targets_create_error(
        self,
        mock_unified_service: MagicMock,
        sample_konnect_only_targets: MagicMock,
    ) -> None:
        """Pull targets handles create errors."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_targets_for_upstreams,
        )

        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets
        gateway_mgr = MagicMock()
        gateway_mgr.add_target.side_effect = Exception("create failed")

        created, _updated, errors = _pull_targets_for_upstreams(
            mock_unified_service, ["backend"], gateway_mgr, dry_run=False
        )

        assert created == 0
        assert errors == 2


class TestPullEntityTypeDrift:
    """Tests for _pull_entity_type with drift updates."""

    @pytest.mark.unit
    def test_pull_drift_dry_run(
        self,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """Pull entity with drift in dry_run mode shows would-update."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_unified_service.list_services.return_value = sample_drifted_services
        gw_mgr = MagicMock()

        _created, updated, _errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": gw_mgr},
            dry_run=True,
            with_drift=True,
        )

        assert updated == 1
        gw_mgr.update.assert_not_called()

    @pytest.mark.unit
    def test_pull_drift_skips_none_entity(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Pull entity with drift skips when konnect_entity is None."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        entity = UnifiedEntity(
            entity=Service(name="test", host="host"),
            source=EntitySource.BOTH,
            gateway_id="svc-1",
            konnect_id="k-svc-1",
            has_drift=True,
            drift_fields=["host"],
            gateway_entity=Service(name="test", host="old"),
            konnect_entity=None,  # None
        )
        mock_unified_service.list_services.return_value = UnifiedEntityList(entities=[entity])
        gw_mgr = MagicMock()

        _created, updated, _errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": gw_mgr},
            dry_run=False,
            with_drift=True,
        )

        assert updated == 0
        gw_mgr.update.assert_not_called()

    @pytest.mark.unit
    def test_pull_drift_interactive_skips_unresolved(
        self,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """Pull entity with drift in interactive skips entities not in resolved set."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_unified_service.list_services.return_value = sample_drifted_services
        gw_mgr = MagicMock()

        _created, updated, _errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": gw_mgr},
            dry_run=False,
            with_drift=True,
            resolved_entities=set(),  # Empty = skip all
        )

        assert updated == 0
        gw_mgr.update.assert_not_called()

    @pytest.mark.unit
    def test_pull_drift_update_error(
        self,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """Pull entity with drift handles update errors."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_unified_service.list_services.return_value = sample_drifted_services
        gw_mgr = MagicMock()
        gw_mgr.update.side_effect = Exception("update failed")

        _created, updated, errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": gw_mgr},
            dry_run=False,
            with_drift=True,
        )

        assert updated == 0
        assert errors == 1

    @pytest.mark.unit
    def test_pull_drift_update_with_audit(
        self,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """Pull entity with drift records audit entries."""
        from system_operations_manager.plugins.kong.commands.sync import _pull_entity_type

        mock_unified_service.list_services.return_value = sample_drifted_services
        gw_mgr = MagicMock()
        gw_mgr.update.return_value = Service(name="updated", host="host")
        audit = MagicMock()

        _created, updated, _errors = _pull_entity_type(
            "services",
            mock_unified_service,
            {"services": gw_mgr},
            dry_run=False,
            with_drift=True,
            audit_service=audit,
            sync_id="test-sync-id",
        )

        assert updated == 1
        audit.record.assert_called()


class TestDisplayStatusTableExtended:
    """Additional tests for _display_sync_status_table edge cases."""

    @pytest.mark.unit
    def test_status_table_konnect_only_truncation(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Status table truncates konnect-only entities at 5."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _display_sync_status_table,
        )

        # Create 7 konnect-only entities
        entities = []
        for i in range(7):
            svc = Service(id=f"k-svc-{i}", name=f"konnect-api-{i}", host="k.local")
            entities.append(
                UnifiedEntity(
                    entity=svc,
                    source=EntitySource.KONNECT,
                    gateway_id=None,
                    konnect_id=f"k-svc-{i}",
                    has_drift=False,
                    konnect_entity=svc,
                )
            )
        mock_unified_service.list_services.return_value = UnifiedEntityList(entities=entities)

        summary = {
            "services": {
                "gateway_only": 0,
                "konnect_only": 7,
                "synced": 0,
                "drift": 0,
                "total": 7,
            },
        }

        # Should not raise
        _display_sync_status_table(summary, ["services"], mock_unified_service)

    @pytest.mark.unit
    def test_status_table_drift_with_actual_entities(
        self,
        mock_unified_service: MagicMock,
        sample_drifted_services: UnifiedEntityList[Service],
    ) -> None:
        """Status table shows drift field details."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _display_sync_status_table,
        )

        mock_unified_service.list_services.return_value = sample_drifted_services

        summary = {
            "services": {
                "gateway_only": 0,
                "konnect_only": 0,
                "synced": 0,
                "drift": 1,
                "total": 1,
            },
        }

        # Should print drift fields without error
        _display_sync_status_table(summary, ["services"], mock_unified_service)

    @pytest.mark.unit
    def test_status_table_unknown_entity_type(
        self,
        mock_unified_service: MagicMock,
    ) -> None:
        """Status table handles unknown entity types gracefully."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _display_sync_status_table,
        )

        summary = {
            "unknown_type": {
                "gateway_only": 1,
                "konnect_only": 0,
                "synced": 0,
                "drift": 0,
                "total": 1,
            },
        }

        # Should not raise - returns empty entity list for unknown type
        _display_sync_status_table(summary, ["unknown_type"], mock_unified_service)
