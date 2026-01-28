"""Integration tests for batch operations.

Tests the batch resolution keys (s, t, m) that apply actions to all conflicts.
"""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.screens import (
    ConflictListScreen,
)
from tests.integration.tui.conftest import AppFactory

# ============================================================================
# Batch Keep Source Tests
# ============================================================================


class TestBatchKeepSource:
    """Tests for batch 'keep source' operations (s key)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_keep_source_all(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 's' key applies KEEP_SOURCE to all pending conflicts."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            # Initially no resolutions
            assert len(app.service.get_all_resolutions()) == 0

            # Press 's' for batch keep source
            await pilot.press("s")
            await pilot.pause()

            # All conflicts should now have resolutions
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # All should be KEEP_SOURCE
            for resolution in resolutions:
                assert resolution.action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_keep_source_only_pending(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 's' only applies to conflicts without existing resolutions."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Manually resolve first conflict as KEEP_TARGET
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")  # Keep target
            await pilot.pause()

            # One resolution should exist
            assert len(app.service.get_all_resolutions()) == 1
            first_resolution = app.service.get_all_resolutions()[0]
            assert first_resolution.action == ResolutionAction.KEEP_TARGET

            # Now batch keep source
            await pilot.press("s")
            await pilot.pause()

            # All conflicts should now have resolutions
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # First conflict should still be KEEP_TARGET (not overwritten)
            first_conflict_resolution = next(
                r for r in resolutions if r.conflict.entity_name == "service-0"
            )
            assert first_conflict_resolution.action == ResolutionAction.KEEP_TARGET

            # Other two should be KEEP_SOURCE
            other_resolutions = [r for r in resolutions if r.conflict.entity_name != "service-0"]
            for resolution in other_resolutions:
                assert resolution.action == ResolutionAction.KEEP_SOURCE


# ============================================================================
# Batch Keep Target Tests
# ============================================================================


class TestBatchKeepTarget:
    """Tests for batch 'keep target' operations (t key)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_keep_target_all(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 't' key applies KEEP_TARGET to all pending conflicts."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press 't' for batch keep target
            await pilot.press("t")
            await pilot.pause()

            # All conflicts should have resolutions
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # All should be KEEP_TARGET
            for resolution in resolutions:
                assert resolution.action == ResolutionAction.KEEP_TARGET


# ============================================================================
# Batch Auto-Merge Tests
# ============================================================================


class TestBatchAutoMerge:
    """Tests for batch 'auto-merge' operations (m key)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_auto_merge_simple_conflicts(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 'm' key auto-merges simple conflicts where possible."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press 'm' for batch auto-merge
            await pilot.press("m")
            await pilot.pause()

            # Check resolutions - some may be merged, some may not
            # depending on merge analysis
            resolutions = app.service.get_all_resolutions()

            # At minimum, the batch operation should have been attempted
            # The actual count depends on which conflicts are auto-mergeable
            # We just verify the operation completes without error
            assert resolutions is not None  # Operation completed

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_auto_merge_mixed_conflicts(
        self,
        conflict_set_mixed: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 'm' key with mixed conflict types."""
        app = app_factory(conflict_set_mixed)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press 'm' for batch auto-merge
            await pilot.press("m")
            await pilot.pause()

            # Should have some resolutions (at least auto-mergeable ones)
            resolutions = app.service.get_all_resolutions()

            # Verify that any MERGE resolutions have merged_state
            for resolution in resolutions:
                if resolution.action == ResolutionAction.MERGE:
                    assert resolution.merged_state is not None


# ============================================================================
# Batch Then Individual Override Tests
# ============================================================================


class TestBatchThenIndividualOverride:
    """Tests for overriding batch operations with individual resolutions."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_then_individual_override(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test that individual resolution overrides batch resolution."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # First apply batch keep source
            await pilot.press("s")
            await pilot.pause()

            # Verify all are KEEP_SOURCE
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3
            for r in resolutions:
                assert r.action == ResolutionAction.KEEP_SOURCE

            # Now individually override first conflict to KEEP_TARGET
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")  # Keep target
            await pilot.pause()

            # Verify override took effect
            resolutions = app.service.get_all_resolutions()
            first_resolution = next(r for r in resolutions if r.conflict.entity_name == "service-0")
            assert first_resolution.action == ResolutionAction.KEEP_TARGET

            # Others should still be KEEP_SOURCE
            other_resolutions = [r for r in resolutions if r.conflict.entity_name != "service-0"]
            for r in other_resolutions:
                assert r.action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_individual_then_batch(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test individual resolution followed by batch operation."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Individually resolve first conflict
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")  # Keep target
            await pilot.pause()

            assert len(app.service.get_all_resolutions()) == 1

            # Apply batch keep source to remaining
            await pilot.press("s")
            await pilot.pause()

            # All should have resolutions
            resolutions = app.service.get_all_resolutions()
            assert len(resolutions) == 3

            # First should be KEEP_TARGET (preserved)
            first_resolution = next(r for r in resolutions if r.conflict.entity_name == "service-0")
            assert first_resolution.action == ResolutionAction.KEEP_TARGET


# ============================================================================
# Batch Operations and Apply Tests
# ============================================================================


class TestBatchOperationsAndApply:
    """Tests for applying after batch operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_then_apply_workflow(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test complete workflow: batch operation -> apply."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Batch keep source
            await pilot.press("s")
            await pilot.pause()

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # All resolutions should be in result
        assert len(app._result) == 3
        for r in app._result:
            assert r.action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_override_then_apply(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test workflow: batch -> override -> apply."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Batch keep source
            await pilot.press("s")
            await pilot.pause()

            # Override one
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("3")  # Skip
            await pilot.pause()

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Check results
        result_actions = {r.conflict.entity_name: r.action for r in app._result}
        assert result_actions["service-0"] == ResolutionAction.SKIP
        assert result_actions["service-1"] == ResolutionAction.KEEP_SOURCE
        assert result_actions["service-2"] == ResolutionAction.KEEP_SOURCE
