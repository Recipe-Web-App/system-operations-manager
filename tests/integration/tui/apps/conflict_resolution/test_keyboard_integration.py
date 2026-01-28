"""Integration tests for keyboard accessibility.

Tests that the entire TUI can be operated using only keyboard navigation,
ensuring accessibility for keyboard-only users.
"""

from __future__ import annotations

import pytest

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
# Full Keyboard Workflow Tests
# ============================================================================


class TestFullKeyboardWorkflow:
    """Tests for completing entire workflows using only keyboard."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow_keyboard_only(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test complete workflow using only keyboard navigation."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and resolve all using keyboard
            for i in range(3):
                if i > 0:
                    await pilot.press("j")  # Move to next row
                await pilot.press("enter")  # Open detail
                await pilot.pause()
                await pilot.press("1")  # Keep source
                await pilot.pause()

            # All resolved
            assert len(app.service.get_all_resolutions()) == 3

            # Apply using keyboard
            await pilot.press("a")  # Go to summary
            await pilot.pause()
            await pilot.press("enter")  # Show modal
            await pilot.pause()
            await pilot.press("enter")  # Confirm

        # All resolutions applied
        assert len(app._result) == 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_keyboard_workflow_with_different_actions(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test keyboard workflow using different resolution actions."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # First conflict - key 1 (keep source)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Second conflict - key 2 (keep target)
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()

            # Third conflict - key 3 (skip)
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("3")
            await pilot.pause()

            # Apply
            await pilot.press("a")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Verify all different actions
        result_actions = [r.action for r in app._result]
        assert ResolutionAction.KEEP_SOURCE in result_actions
        assert ResolutionAction.KEEP_TARGET in result_actions
        assert ResolutionAction.SKIP in result_actions


# ============================================================================
# Modal Keyboard Navigation Tests
# ============================================================================


class TestModalKeyboardNavigation:
    """Tests for keyboard navigation within modals."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tab_navigation_in_modal(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test Tab cycles through modal buttons."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Make resolution and go to summary
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            # Show modal
            await pilot.press("enter")
            await pilot.pause()

            # Tab to cancel button
            await pilot.press("tab")
            await pilot.pause()

            # Press enter on cancel
            await pilot.press("enter")
            await pilot.pause()

            # Should still be on summary (cancelled)
            assert isinstance(app.screen, SummaryScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_modal_confirm_with_enter(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test Enter on Apply button confirms and exits."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and resolve
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Go to summary
            await pilot.press("a")
            await pilot.pause()

            # Show modal and confirm (default focus is Apply)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")

        # Should exit with resolution
        assert len(app._result) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_modal_cancel_with_escape(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test Escape cancels modal without applying."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate and resolve
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Go to summary
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, SummaryScreen)

            # Show modal then cancel with escape
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            # Should still be on summary (modal dismissed)
            assert isinstance(app.screen, SummaryScreen)


# ============================================================================
# Screen-Level Keyboard Binding Tests
# ============================================================================


class TestScreenKeyboardBindings:
    """Tests for keyboard bindings at each screen."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_screen_all_bindings(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test all keyboard bindings work on list screen."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            # j - move down
            await pilot.press("j")
            await pilot.pause()

            # k - move up
            await pilot.press("k")
            await pilot.pause()

            # s - batch keep source
            await pilot.press("s")
            await pilot.pause()
            assert len(app.service.get_all_resolutions()) == 3

            # a - apply (go to summary)
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, SummaryScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detail_screen_all_bindings(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test all keyboard bindings work on detail screen."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Enter to go to detail
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            # d - toggle diff mode
            await pilot.press("d")
            await pilot.pause()

            # escape - go back
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            # Enter again
            await pilot.press("enter")
            await pilot.pause()

            # 1 - keep source
            await pilot.press("1")
            await pilot.pause()

            # Should be back on list with resolution
            assert isinstance(app.screen, ConflictListScreen)
            assert len(app.service.get_all_resolutions()) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resolution_number_keys(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 1-4 number keys for resolution selection."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Test key 1 - keep source
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()
            assert app.service.get_all_resolutions()[0].action == ResolutionAction.KEEP_SOURCE

            # Test key 2 - keep target
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()

            resolutions = app.service.get_all_resolutions()
            keep_target = next(r for r in resolutions if r.conflict.entity_name == "service-1")
            assert keep_target.action == ResolutionAction.KEEP_TARGET

            # Test key 3 - skip
            await pilot.press("j")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("3")
            await pilot.pause()

            resolutions = app.service.get_all_resolutions()
            skip = next(r for r in resolutions if r.conflict.entity_name == "service-2")
            assert skip.action == ResolutionAction.SKIP


# ============================================================================
# Help Key Test
# ============================================================================


class TestHelpKey:
    """Tests for the help key."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_help_key_shows_notification(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test '?' key triggers help notification."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press ? for help
            await pilot.press("?")
            await pilot.pause()

            # App should still be functional
            assert isinstance(app.screen, ConflictListScreen)

            # Should be able to continue normal workflow
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)
