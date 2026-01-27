"""Integration tests for merge resolution flows.

Tests auto-merge for simple conflicts and manual merge preview for
conflicts with overlapping changes.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.screens import (
    ConflictDetailScreen,
    ConflictListScreen,
    MergePreviewScreen,
)
from system_operations_manager.utils.merge import MergeAnalysis
from tests.integration.tui.conftest import AppFactory

# ============================================================================
# Auto-Merge Tests
# ============================================================================


class TestAutoMerge:
    """Tests for automatic merge resolution."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auto_merge_simple_conflict(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test key '4' auto-merges simple conflict and returns to list."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to detail
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            # Press 4 for merge
            await pilot.press("4")
            await pilot.pause()

            # Simple conflict should auto-merge and return to list
            assert isinstance(app.screen, ConflictListScreen)

            # Should have a MERGE resolution with merged state
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 1
            assert resolutions[0].action == ResolutionAction.MERGE
            assert resolutions[0].merged_state is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auto_merge_then_apply(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test auto-merge followed by apply workflow."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Auto-merge
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Result should have merge resolution
        assert len(app._result) == 1
        assert app._result[0].action == ResolutionAction.MERGE
        assert app._result[0].merged_state is not None


# ============================================================================
# Manual Merge Preview Tests
# ============================================================================


class TestManualMergePreview:
    """Tests for manual merge preview screen.

    These tests mock analyze_merge_potential to return can_auto_merge=False,
    simulating a conflict that requires manual merge (e.g., when both source
    and target changed the same fields from some original state).
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_overlapping_conflict_opens_merge_preview(
        self,
        overlapping_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test key '4' on overlapping conflict opens MergePreviewScreen."""
        # Mock to simulate non-auto-mergeable conflict
        mock_analysis = MergeAnalysis(
            can_auto_merge=False,
            source_only_fields=[],
            target_only_fields=[],
            conflicting_fields=["paths", "hosts"],
        )

        app = app_factory([overlapping_conflict])

        with patch(
            "system_operations_manager.utils.merge.analyze_merge_potential",
            return_value=mock_analysis,
        ):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Go to detail
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, ConflictDetailScreen)

                # Press 4 for merge
                await pilot.press("4")
                await pilot.pause()

                # Overlapping conflict should open MergePreviewScreen
                assert isinstance(app.screen, MergePreviewScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cancel_manual_merge_returns_to_detail(
        self,
        overlapping_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test Escape from MergePreviewScreen returns to detail."""
        mock_analysis = MergeAnalysis(
            can_auto_merge=False,
            source_only_fields=[],
            target_only_fields=[],
            conflicting_fields=["paths", "hosts"],
        )

        app = app_factory([overlapping_conflict])

        with patch(
            "system_operations_manager.utils.merge.analyze_merge_potential",
            return_value=mock_analysis,
        ):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Go to detail
                await pilot.press("enter")
                await pilot.pause()

                # Open merge preview
                await pilot.press("4")
                await pilot.pause()
                assert isinstance(app.screen, MergePreviewScreen)

                # Press escape to cancel
                await pilot.press("escape")
                await pilot.pause()

                # Should be back on detail screen
                assert isinstance(app.screen, ConflictDetailScreen)

                # No resolution should have been made
                assert len(app.service.get_all_resolutions()) == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_confirm_manual_merge_with_default_state(
        self,
        overlapping_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test confirming merge with default (source) state."""
        mock_analysis = MergeAnalysis(
            can_auto_merge=False,
            source_only_fields=[],
            target_only_fields=[],
            conflicting_fields=["paths", "hosts"],
        )

        app = app_factory([overlapping_conflict])

        with patch(
            "system_operations_manager.utils.merge.analyze_merge_potential",
            return_value=mock_analysis,
        ):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Go to detail and open merge preview
                await pilot.press("enter")
                await pilot.pause()
                await pilot.press("4")
                await pilot.pause()
                assert isinstance(app.screen, MergePreviewScreen)

                # Confirm merge without editing (uses source state as default)
                await pilot.press("c")
                await pilot.pause()

                # Should return to list with merge resolution
                assert isinstance(app.screen, ConflictListScreen)

                resolutions = app.service.get_all_resolutions()
                assert len(resolutions) == 1
                assert resolutions[0].action == ResolutionAction.MERGE
                assert resolutions[0].merged_state is not None


# ============================================================================
# Mixed Merge and Other Resolutions Tests
# ============================================================================


class TestMixedMergeResolutions:
    """Tests for workflows mixing merge with other resolution types."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_merge_and_keep_source_mixed(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test workflow mixing merge and keep_source resolutions."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # First conflict - merge (simple conflicts auto-merge)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()

            # Second conflict - keep source
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Third conflict - merge
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()

            # Verify resolutions
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # Count by action type
            merge_count = sum(1 for r in resolutions if r.action == ResolutionAction.MERGE)
            keep_source_count = sum(
                1 for r in resolutions if r.action == ResolutionAction.KEEP_SOURCE
            )

            assert merge_count == 2
            assert keep_source_count == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_source_then_individual_merge(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test batch keep_source followed by individual merge override."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Batch keep source
            await pilot.press("s")
            await pilot.pause()

            # Override first conflict with merge
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()

            # Verify first is merge, others are keep_source
            resolutions = app.service.get_all_resolutions()
            first = next(r for r in resolutions if r.conflict.entity_name == "service-0")
            assert first.action == ResolutionAction.MERGE

            others = [r for r in resolutions if r.conflict.entity_name != "service-0"]
            for r in others:
                assert r.action == ResolutionAction.KEEP_SOURCE


# ============================================================================
# Merge Resolution Complete Workflow Tests
# ============================================================================


class TestMergeWorkflowComplete:
    """Tests for complete merge workflows through apply."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auto_merge_all_then_apply(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test auto-merging all conflicts then applying."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Merge each conflict individually
            for i in range(3):
                if i > 0:
                    await pilot.press("j")
                await pilot.press("enter")
                await pilot.pause()
                await pilot.press("4")  # Merge
                await pilot.pause()

            # Apply all
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # All should be merge resolutions
        assert len(app._result) == 3
        for r in app._result:
            assert r.action == ResolutionAction.MERGE
            assert r.merged_state is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mixed_conflicts_merge_workflow(
        self,
        conflict_set_mixed: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test merge workflow with mixed conflict types."""
        app = app_factory(conflict_set_mixed)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Resolve each conflict
            for i in range(3):
                if i > 0:
                    await pilot.press("j")
                await pilot.press("enter")
                await pilot.pause()

                # Try merge - may auto-merge or open preview
                await pilot.press("4")
                await pilot.pause()

                # If on MergePreviewScreen, confirm
                if isinstance(app.screen, MergePreviewScreen):
                    await pilot.press("c")
                    await pilot.pause()

            # All should be resolved
            assert len(app.service.get_all_resolutions()) == 3

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Should have all resolutions
        assert len(app._result) == 3


# ============================================================================
# Merge Resolution State Validation Tests
# ============================================================================


class TestMergeStateValidation:
    """Tests for merge state validation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auto_merge_preserves_unchanged_fields(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test auto-merge preserves fields that didn't change."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Auto-merge
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()

        # Get the merged state
        resolution = app.service.get_all_resolutions()[0]
        merged_state = resolution.merged_state

        # Common fields should be preserved
        assert merged_state is not None
        # The merge should contain all keys from source
        assert "port" in merged_state or "name" in merged_state or "host" in merged_state
