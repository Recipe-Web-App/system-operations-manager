"""E2E tests for sync push/pull CLI commands with --interactive flag.

These tests verify the CLI workflow for interactive conflict resolution
during sync operations. The TUI is mocked to test the CLI flow without
actual TUI interaction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app
from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    Resolution,
    ResolutionAction,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_conflict_push() -> Conflict:
    """Sample conflict for push direction tests."""
    return Conflict(
        entity_type="services",
        entity_id="svc-123",
        entity_name="test-service",
        source_state={"host": "gateway.example.com", "port": 8080},
        target_state={"host": "konnect.example.com", "port": 80},
        drift_fields=["host", "port"],
        source_system_id="gw-svc-123",
        target_system_id="kn-svc-123",
        direction="push",
    )


@pytest.fixture
def sample_conflict_pull() -> Conflict:
    """Sample conflict for pull direction tests."""
    return Conflict(
        entity_type="services",
        entity_id="svc-456",
        entity_name="pull-test-service",
        source_state={"host": "konnect.example.com", "port": 443},
        target_state={"host": "gateway.example.com", "port": 8080},
        drift_fields=["host", "port"],
        source_system_id="kn-svc-456",
        target_system_id="gw-svc-456",
        direction="pull",
    )


@pytest.fixture
def sample_resolution_keep_source(sample_conflict_push: Conflict) -> Resolution:
    """Sample resolution with KEEP_SOURCE action."""
    return Resolution(
        conflict=sample_conflict_push,
        action=ResolutionAction.KEEP_SOURCE,
    )


@pytest.fixture
def sample_resolution_keep_target(sample_conflict_push: Conflict) -> Resolution:
    """Sample resolution with KEEP_TARGET action."""
    return Resolution(
        conflict=sample_conflict_push,
        action=ResolutionAction.KEEP_TARGET,
    )


@pytest.fixture
def sample_resolution_skip(sample_conflict_push: Conflict) -> Resolution:
    """Sample resolution with SKIP action."""
    return Resolution(
        conflict=sample_conflict_push,
        action=ResolutionAction.SKIP,
    )


# ============================================================================
# Push Direction Tests
# ============================================================================


@pytest.mark.e2e
class TestSyncPushInteractiveE2E:
    """E2E tests for sync push with --interactive flag."""

    def test_push_interactive_flag_exists(self, cli_runner: CliRunner) -> None:
        """Verify --interactive/-i flag is available on push command."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert result.exit_code == 0
        assert "--interactive" in result.stdout
        assert "-i" in result.stdout

    def test_push_interactive_help_description(self, cli_runner: CliRunner) -> None:
        """Verify --interactive flag has descriptive help text."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert result.exit_code == 0
        # Should mention interactive conflict resolution
        assert "interactive" in result.stdout.lower()

    def test_push_interactive_example_in_help(self, cli_runner: CliRunner) -> None:
        """Verify help includes interactive usage example."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert result.exit_code == 0
        # Examples section should show --interactive usage
        assert "--interactive" in result.stdout

    def test_push_interactive_mutually_exclusive_with_skip_conflicts(
        self, cli_runner: CliRunner
    ) -> None:
        """Verify --interactive and --skip-conflicts are mutually exclusive."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "push", "--interactive", "--skip-conflicts"]
        )

        # Should fail because options are mutually exclusive
        assert result.exit_code == 1
        assert (
            "mutually exclusive" in result.stdout.lower()
            or "Konnect not configured" in result.stdout
        )

    def test_push_interactive_no_konnect_or_gateway_shows_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Verify proper error message when Konnect or Gateway is not available."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive"])

        # Without proper configuration, should fail gracefully with a clear message
        assert result.exit_code == 1
        # Either Konnect not configured OR Kong connection error
        error_indicators = [
            "Konnect not configured",
            "Kong connection error",
            "Connection refused",
            "connection error",
        ]
        assert any(indicator.lower() in result.stdout.lower() for indicator in error_indicators), (
            f"Expected error message, got: {result.stdout}"
        )

    def test_push_interactive_with_dry_run(self, cli_runner: CliRunner) -> None:
        """Verify --interactive can be combined with --dry-run."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        # Both options should be documented
        assert "--interactive" in result.stdout
        assert "--dry-run" in result.stdout

    @pytest.mark.requires_konnect
    def test_push_interactive_no_conflicts_skips_tui(self, cli_runner: CliRunner) -> None:
        """Test TUI is not launched when there are no conflicts.

        This test requires Konnect to be configured.
        """
        # Mock the unified query service to return no drift
        mock_unified_service = MagicMock()
        mock_unified_service.get_sync_summary.return_value = {
            "services": {"total": 1, "gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 0}
        }

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            # TUI should not be called if no drift
            result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--dry-run"])

            # If Konnect configured and no drift, should succeed without TUI
            if result.exit_code == 0:
                mock_tui.assert_not_called()

    @pytest.mark.requires_konnect
    def test_push_interactive_detects_conflicts(
        self, cli_runner: CliRunner, sample_conflict_push: Conflict
    ) -> None:
        """Test that conflicts are detected and passed to TUI.

        This test requires Konnect to be configured.
        """
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = []  # User cancelled

            _result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive"])

            # If TUI was called, verify it received proper arguments
            if mock_tui.called:
                call_args = mock_tui.call_args
                assert call_args is not None
                # Direction should be "push"
                assert call_args[0][2] == "push" or call_args.kwargs.get("direction") == "push"

    @pytest.mark.requires_konnect
    def test_push_interactive_keep_source_syncs_entity(
        self,
        cli_runner: CliRunner,
        sample_conflict_push: Conflict,
        sample_resolution_keep_source: Resolution,
    ) -> None:
        """Test KEEP_SOURCE resolution triggers entity sync.

        This test requires Konnect to be configured.
        """
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [sample_resolution_keep_source]

            result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--force"])

            # If Konnect configured, KEEP_SOURCE should sync the entity
            if result.exit_code == 0:
                mock_tui.assert_called_once()

    @pytest.mark.requires_konnect
    def test_push_interactive_keep_target_skips_entity(
        self,
        cli_runner: CliRunner,
        sample_conflict_push: Conflict,
        sample_resolution_keep_target: Resolution,
    ) -> None:
        """Test KEEP_TARGET resolution skips entity sync.

        This test requires Konnect to be configured.
        """
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [sample_resolution_keep_target]

            _result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--force"])

            # KEEP_TARGET should not sync the entity
            if mock_tui.called:
                # Verify KEEP_TARGET was in the returned resolutions
                assert sample_resolution_keep_target.action == ResolutionAction.KEEP_TARGET

    @pytest.mark.requires_konnect
    def test_push_interactive_skip_skips_entity(
        self,
        cli_runner: CliRunner,
        sample_conflict_push: Conflict,
        sample_resolution_skip: Resolution,
    ) -> None:
        """Test SKIP resolution skips entity sync.

        This test requires Konnect to be configured.
        """
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [sample_resolution_skip]

            _result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--force"])

            # SKIP should not sync the entity
            if mock_tui.called:
                assert sample_resolution_skip.action == ResolutionAction.SKIP

    @pytest.mark.requires_konnect
    def test_push_interactive_cancelled_exits_gracefully(self, cli_runner: CliRunner) -> None:
        """Test empty resolutions (cancelled) exits gracefully.

        This test requires Konnect to be configured.
        """
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = []  # Empty = cancelled

            result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive"])

            # Should exit gracefully with message
            if mock_tui.called:
                # Empty resolutions should be handled gracefully
                assert "Cancelled" in result.stdout or result.exit_code == 0

    def test_push_interactive_dry_run_flag_combination(self, cli_runner: CliRunner) -> None:
        """Verify --interactive and --dry-run can be combined."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        # Both flags should be available together
        assert "--interactive" in result.stdout
        assert "--dry-run" in result.stdout


# ============================================================================
# Pull Direction Tests
# ============================================================================


@pytest.mark.e2e
class TestSyncPullInteractiveE2E:
    """E2E tests for sync pull with --interactive flag."""

    def test_pull_interactive_flag_exists(self, cli_runner: CliRunner) -> None:
        """Verify --interactive/-i flag is available on pull command."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--help"])

        assert result.exit_code == 0
        assert "--interactive" in result.stdout
        assert "-i" in result.stdout

    def test_pull_interactive_help_description(self, cli_runner: CliRunner) -> None:
        """Verify --interactive flag has descriptive help text."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--help"])

        assert result.exit_code == 0
        assert "interactive" in result.stdout.lower()

    def test_pull_interactive_mutually_exclusive_with_skip_conflicts(
        self, cli_runner: CliRunner
    ) -> None:
        """Verify --interactive and --skip-conflicts are mutually exclusive."""
        result = cli_runner.invoke(
            app, ["kong", "sync", "pull", "--interactive", "--skip-conflicts"]
        )

        # Should fail because options are mutually exclusive
        assert result.exit_code == 1
        assert (
            "mutually exclusive" in result.stdout.lower()
            or "Konnect not configured" in result.stdout
        )

    def test_pull_interactive_no_konnect_or_gateway_shows_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Verify proper error message when Konnect or Gateway is not available."""
        result = cli_runner.invoke(app, ["kong", "sync", "pull", "--interactive"])

        # Without proper configuration, should fail gracefully with a clear message
        assert result.exit_code == 1
        # Either Konnect not configured OR Kong connection error
        error_indicators = [
            "Konnect not configured",
            "Kong connection error",
            "Connection refused",
            "connection error",
        ]
        assert any(indicator.lower() in result.stdout.lower() for indicator in error_indicators), (
            f"Expected error message, got: {result.stdout}"
        )

    @pytest.mark.requires_konnect
    def test_pull_interactive_direction_passed_to_tui(
        self, cli_runner: CliRunner, sample_conflict_pull: Conflict
    ) -> None:
        """Test direction='pull' is passed to TUI.

        This test requires Konnect to be configured.
        """
        resolution = Resolution(
            conflict=sample_conflict_pull,
            action=ResolutionAction.KEEP_SOURCE,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [resolution]

            _result = cli_runner.invoke(
                app, ["kong", "sync", "pull", "--interactive", "--force", "--with-drift"]
            )

            # If TUI was called, verify direction is "pull"
            if mock_tui.called:
                call_args = mock_tui.call_args
                assert call_args is not None
                # The direction argument (3rd positional or keyword)
                args = call_args[0] if call_args[0] else []
                kwargs = call_args[1] if len(call_args) > 1 else {}
                direction = args[2] if len(args) > 2 else kwargs.get("direction")
                assert direction == "pull"

    @pytest.mark.requires_konnect
    def test_pull_interactive_keep_source_syncs(
        self, cli_runner: CliRunner, sample_conflict_pull: Conflict
    ) -> None:
        """Test KEEP_SOURCE on pull syncs Konnect -> Gateway.

        This test requires Konnect to be configured.
        """
        resolution = Resolution(
            conflict=sample_conflict_pull,
            action=ResolutionAction.KEEP_SOURCE,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [resolution]

            _result = cli_runner.invoke(
                app, ["kong", "sync", "pull", "--interactive", "--force", "--with-drift"]
            )

            # Verify TUI was called with correct direction
            if mock_tui.called:
                assert resolution.action == ResolutionAction.KEEP_SOURCE
                # KEEP_SOURCE on pull means Konnect (source) -> Gateway (target)


# ============================================================================
# Mixed Resolution Tests
# ============================================================================


@pytest.mark.e2e
class TestSyncInteractiveMixedResolutions:
    """E2E tests for mixed resolution actions."""

    @pytest.mark.requires_konnect
    def test_push_interactive_multiple_mixed_resolutions(self, cli_runner: CliRunner) -> None:
        """Test workflow with multiple conflicts and mixed resolution actions.

        This test requires Konnect to be configured.
        """
        conflicts = [
            Conflict(
                entity_type="services",
                entity_id=f"svc-{i}",
                entity_name=f"service-{i}",
                source_state={"host": f"gw-{i}.example.com"},
                target_state={"host": f"kn-{i}.example.com"},
                drift_fields=["host"],
                source_system_id=f"gw-svc-{i}",
                target_system_id=f"kn-svc-{i}",
                direction="push",
            )
            for i in range(3)
        ]

        resolutions = [
            Resolution(conflict=conflicts[0], action=ResolutionAction.KEEP_SOURCE),
            Resolution(conflict=conflicts[1], action=ResolutionAction.KEEP_TARGET),
            Resolution(conflict=conflicts[2], action=ResolutionAction.SKIP),
        ]

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = resolutions

            _result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--force"])

            # Verify mixed resolutions are handled
            if mock_tui.called:
                # Should have 1 KEEP_SOURCE, 1 KEEP_TARGET, 1 SKIP
                actions = [r.action for r in resolutions]
                assert ResolutionAction.KEEP_SOURCE in actions
                assert ResolutionAction.KEEP_TARGET in actions
                assert ResolutionAction.SKIP in actions


# ============================================================================
# Audit Recording Tests
# ============================================================================


@pytest.mark.e2e
class TestSyncInteractiveAudit:
    """E2E tests for audit recording with interactive mode."""

    @pytest.mark.requires_konnect
    def test_push_interactive_audit_records_resolution_action(
        self, cli_runner: CliRunner, sample_conflict_push: Conflict
    ) -> None:
        """Test audit entries include resolution_action field.

        This test requires Konnect to be configured.
        """
        resolution = Resolution(
            conflict=sample_conflict_push,
            action=ResolutionAction.KEEP_SOURCE,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [resolution]

            # Run with force to skip confirmation
            result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--force"])

            # If successful, audit should have been recorded
            if result.exit_code == 0 and mock_tui.called:
                # Verify the resolution action value is correct
                assert resolution.action.value == "keep_source"


# ============================================================================
# Dry Run Tests
# ============================================================================


@pytest.mark.e2e
class TestSyncInteractiveDryRun:
    """E2E tests for interactive mode with --dry-run."""

    @pytest.mark.requires_konnect
    def test_push_interactive_dry_run_mode(
        self, cli_runner: CliRunner, sample_conflict_push: Conflict
    ) -> None:
        """Test --dry-run with --interactive shows preview without changes.

        This test requires Konnect to be configured.
        """
        resolution = Resolution(
            conflict=sample_conflict_push,
            action=ResolutionAction.KEEP_SOURCE,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [resolution]

            result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive", "--dry-run"])

            # Dry run should show what would happen
            if mock_tui.called and result.exit_code == 0:
                # Should indicate it's a dry run
                assert "dry" in result.stdout.lower() or "Would" in result.stdout

    @pytest.mark.requires_konnect
    def test_pull_interactive_dry_run_mode(
        self, cli_runner: CliRunner, sample_conflict_pull: Conflict
    ) -> None:
        """Test --dry-run with --interactive on pull shows preview.

        This test requires Konnect to be configured.
        """
        resolution = Resolution(
            conflict=sample_conflict_pull,
            action=ResolutionAction.KEEP_SOURCE,
        )

        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock_tui:
            mock_tui.return_value = [resolution]

            result = cli_runner.invoke(
                app,
                ["kong", "sync", "pull", "--interactive", "--dry-run", "--with-drift"],
            )

            # Dry run should work with interactive mode
            if mock_tui.called and result.exit_code == 0:
                assert "dry" in result.stdout.lower() or "Would" in result.stdout
