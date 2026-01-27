"""Integration tests for complete conflict resolution workflows.

Tests end-to-end user flows from conflict list through resolution and apply.
"""

from __future__ import annotations

import pytest
from textual.widgets import DataTable

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.screens import (
    ConflictDetailScreen,
    ConflictListScreen,
    SummaryScreen,
)
from tests.integration.tui.conftest import AppFactory

# ============================================================================
# Single Conflict Workflow Tests
# ============================================================================


class TestSingleConflictWorkflows:
    """Tests for resolving a single conflict through the full workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_single_conflict_keep_source_workflow(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test complete workflow: list -> detail -> keep source -> summary -> apply."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            # Verify starting on list screen
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            # Click on the table to give it focus, then select
            table = app.screen.query_one("#conflict-table", DataTable)
            await pilot.click(table)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            # Choose keep source (key 1)
            await pilot.press("1")
            await pilot.pause()

            # Should be back on list with resolution tracked
            assert isinstance(app.screen, ConflictListScreen)
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 1
            assert resolutions[0].action == ResolutionAction.KEEP_SOURCE

            # Apply all (key a)
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, SummaryScreen)

            # Press Enter to show confirmation modal
            await pilot.press("enter")
            await pilot.pause()

            # Press Enter again to confirm (Apply button)
            await pilot.press("enter")

        # Verify app exited with resolutions
        assert len(app._result) == 1
        assert app._result[0].action == ResolutionAction.KEEP_SOURCE
        assert app._result[0].conflict.entity_name == "simple-service"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_single_conflict_keep_target_workflow(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test complete workflow with keep target resolution."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to detail and resolve with keep target
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")  # Keep target
            await pilot.pause()

            # Verify resolution tracked correctly
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 1
            assert resolutions[0].action == ResolutionAction.KEEP_TARGET

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        assert len(app._result) == 1
        assert app._result[0].action == ResolutionAction.KEEP_TARGET

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_single_conflict_skip_workflow(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test complete workflow with skip resolution."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to detail and skip
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("3")  # Skip
            await pilot.pause()

            # Verify resolution tracked
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 1
            assert resolutions[0].action == ResolutionAction.SKIP

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        assert len(app._result) == 1
        assert app._result[0].action == ResolutionAction.SKIP


# ============================================================================
# Multi-Conflict Workflow Tests
# ============================================================================


class TestMultiConflictWorkflows:
    """Tests for resolving multiple conflicts in sequence."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_conflict_sequential_resolution(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test resolving 3 conflicts with different actions then apply."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Resolve first conflict - keep source
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")  # Keep source
            await pilot.pause()

            # Navigate to second conflict and resolve - keep target
            await pilot.press("j")  # Move cursor down
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")  # Keep target
            await pilot.pause()

            # Navigate to third conflict and resolve - skip
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("3")  # Skip
            await pilot.pause()

            # Verify all resolutions tracked
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # Verify each resolution matches expected action
            actions = {r.conflict.entity_name: r.action for r in resolutions}
            assert actions["service-0"] == ResolutionAction.KEEP_SOURCE
            assert actions["service-1"] == ResolutionAction.KEEP_TARGET
            assert actions["service-2"] == ResolutionAction.SKIP

            # Apply all
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Verify app exited with all resolutions
        assert len(app._result) == 3
        result_actions = {r.conflict.entity_name: r.action for r in app._result}
        assert result_actions["service-0"] == ResolutionAction.KEEP_SOURCE
        assert result_actions["service-1"] == ResolutionAction.KEEP_TARGET
        assert result_actions["service-2"] == ResolutionAction.SKIP

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_partial_resolution_then_apply(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test applying when only some conflicts are resolved."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Only resolve the first conflict
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")  # Keep source
            await pilot.pause()

            # Try to apply (only 1 of 3 resolved)
            await pilot.press("a")
            await pilot.pause()

            # Should show summary with 1 resolution
            assert isinstance(app.screen, SummaryScreen)
            assert len(app.screen.resolutions) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resolve_change_resolution_apply(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test changing a resolution before applying."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # First resolution - keep source
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            assert app.service.get_all_resolutions()[0].action == ResolutionAction.KEEP_SOURCE

            # Go back and change resolution to keep target
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()

            # Verify resolution was updated
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 1
            assert resolutions[0].action == ResolutionAction.KEEP_TARGET

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        assert app._result[0].action == ResolutionAction.KEEP_TARGET


# ============================================================================
# Direction-Specific Workflow Tests
# ============================================================================


class TestDirectionWorkflows:
    """Tests for workflows with different sync directions."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_push_direction_workflow(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test workflow with push direction."""
        app = app_factory([simple_conflict], direction="push")

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.direction == "push"

            # Complete a resolution
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        assert len(app._result) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pull_direction_workflow(
        self,
        app_factory: AppFactory,
    ) -> None:
        """Test workflow with pull direction."""
        conflict = Conflict(
            entity_type="services",
            entity_id="svc-pull",
            entity_name="pull-test-service",
            source_state={"host": "konnect.example.com"},
            target_state={"host": "gateway.example.com"},
            drift_fields=["host"],
            source_system_id="kn-svc-pull",
            target_system_id="gw-svc-pull",
            direction="pull",
        )
        app = app_factory([conflict], direction="pull")

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.direction == "pull"

            # Complete a resolution
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        assert len(app._result) == 1
        assert app._result[0].conflict.direction == "pull"


# ============================================================================
# Dry Run Workflow Tests
# ============================================================================


class TestDryRunWorkflows:
    """Tests for dry run (preview) workflows."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dry_run_workflow(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test workflow with dry_run=True."""
        app = app_factory([simple_conflict], dry_run=True)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.dry_run is True

            # Complete workflow
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()

            # Summary screen should indicate dry run
            assert isinstance(app.screen, SummaryScreen)
            assert app.screen.dry_run is True

            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Should still return resolutions even in dry run mode
        assert len(app._result) == 1
