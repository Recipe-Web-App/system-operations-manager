"""Integration tests for TUI navigation flows.

Tests screen navigation, screen stack management, keyboard navigation,
and back/escape flows.
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
from system_operations_manager.tui.components.diff_viewer import DiffViewer
from tests.integration.tui.conftest import AppFactory

# ============================================================================
# List Navigation Tests
# ============================================================================


class TestListNavigation:
    """Tests for j/k navigation in the conflict list."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_navigation_j_key_moves_down(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 'j' key moves cursor down in the table."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#conflict-table", DataTable)

            # Initial cursor position
            assert table.cursor_row == 0

            # Press j to move down
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == 1

            # Press j again
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_navigation_k_key_moves_up(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test 'k' key moves cursor up in the table."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#conflict-table", DataTable)

            # Move down first
            await pilot.press("j")
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == 2

            # Press k to move up
            await pilot.press("k")
            await pilot.pause()
            assert table.cursor_row == 1

            # Press k again
            await pilot.press("k")
            await pilot.pause()
            assert table.cursor_row == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_navigation_jk_combination(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test combined j/k navigation."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.screen.query_one("#conflict-table", DataTable)

            # Navigate: down, down, up, down
            await pilot.press("j")
            await pilot.press("j")
            await pilot.press("k")
            await pilot.press("j")
            await pilot.pause()

            # Should be at row 2 (0 -> 1 -> 2 -> 1 -> 2)
            assert table.cursor_row == 2


# ============================================================================
# Screen Stack Tests
# ============================================================================


class TestScreenStackNavigation:
    """Tests for screen stack management."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_enter_pushes_detail_screen(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test that Enter from list pushes detail screen."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()
            initial_stack = len(app.screen_stack)
            assert isinstance(app.screen, ConflictListScreen)

            # Press Enter to go to detail
            await pilot.press("enter")
            await pilot.pause()

            # Screen stack should grow
            assert len(app.screen_stack) == initial_stack + 1
            assert isinstance(app.screen, ConflictDetailScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_escape_pops_detail_screen(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test that Escape from detail pops back to list."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()
            initial_stack = len(app.screen_stack)

            # Go to detail
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            # Press escape to go back
            await pilot.press("escape")
            await pilot.pause()

            # Should be back on list
            assert len(app.screen_stack) == initial_stack
            assert isinstance(app.screen, ConflictListScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_apply_pushes_summary_screen(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test that 'a' from list with resolutions pushes summary."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # First make a resolution
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            initial_stack = len(app.screen_stack)

            # Press 'a' to go to summary
            await pilot.press("a")
            await pilot.pause()

            # Should be on summary
            assert len(app.screen_stack) == initial_stack + 1
            assert isinstance(app.screen, SummaryScreen)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_escape_from_summary_returns_to_list(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test that Escape from summary returns to list."""
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

            assert isinstance(app.screen, SummaryScreen)

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Should be back on list
            assert isinstance(app.screen, ConflictListScreen)


# ============================================================================
# Back Navigation State Preservation Tests
# ============================================================================


class TestBackNavigationStatePreservation:
    """Tests that navigation preserves state correctly."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_back_from_detail_preserves_resolution(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test that resolution is preserved when navigating back."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Make a resolution
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")  # Keep source
            await pilot.pause()

            # Resolution should be tracked
            assert len(app.service.get_all_resolutions()) == 1

            # Go back to detail (re-enter the conflict)
            await pilot.press("enter")
            await pilot.pause()

            # Resolution should still be tracked
            assert len(app.service.get_all_resolutions()) == 1
            assert app.service.get_all_resolutions()[0].action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_escape_from_summary_preserves_resolutions(
        self,
        conflict_set_small: list[Conflict],
        app_factory: AppFactory,
    ) -> None:
        """Test that escaping from summary preserves all resolutions."""
        app = app_factory(conflict_set_small)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Resolve all conflicts
            for i in range(3):
                if i > 0:
                    await pilot.press("j")
                await pilot.press("enter")
                await pilot.pause()
                await pilot.press("1")
                await pilot.pause()

            assert len(app.service.get_all_resolutions()) == 3

            # Go to summary
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, SummaryScreen)

            # Escape back to list
            await pilot.press("escape")
            await pilot.pause()

            # All resolutions should still be there
            assert len(app.service.get_all_resolutions()) == 3


# ============================================================================
# Diff Mode Toggle Tests
# ============================================================================


class TestDiffModeToggle:
    """Tests for diff mode toggling on detail screen."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_d_key_toggles_diff_mode(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test 'd' key toggles diff mode between side_by_side and unified."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to detail screen
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            # Get diff viewer
            diff_viewer = app.screen.query_one("#diff-viewer", DiffViewer)
            initial_mode = diff_viewer.mode
            assert initial_mode == "side_by_side"

            # Press 'd' to toggle
            await pilot.press("d")
            await pilot.pause()
            assert diff_viewer.mode == "unified"

            # Press 'd' again to toggle back
            await pilot.press("d")
            await pilot.pause()
            toggled_back_mode: str = diff_viewer.mode
            assert toggled_back_mode == "side_by_side"


# ============================================================================
# Quit and Cancel Tests
# ============================================================================


class TestQuitAndCancel:
    """Tests for quit and cancel flows."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quit_without_applying(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test 'q' exits app with empty result."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Make a resolution
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Resolution exists
            assert len(app.service.get_all_resolutions()) == 1

            # Quit without applying
            await pilot.press("q")

        # Result should be empty (quit discards resolutions)
        assert app._result == []

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quit_from_list_screen(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test quitting directly from list screen."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            await pilot.press("q")

        assert app._result == []

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_quit_from_detail_screen(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test quitting from detail screen."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to detail
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConflictDetailScreen)

            await pilot.press("q")

        assert app._result == []

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_escape_navigation(
        self,
        simple_conflict: Conflict,
        app_factory: AppFactory,
    ) -> None:
        """Test multiple escapes navigate back correctly."""
        app = app_factory([simple_conflict])

        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to detail, make resolution, go to summary
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            assert isinstance(app.screen, SummaryScreen)

            # First escape: summary -> list
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, ConflictListScreen)

            # Second escape from list screen pops back to default screen
            # (the app allows back navigation as long as screen_stack > 1)
            await pilot.press("escape")
            await pilot.pause()

            # Now on default screen, one more escape won't reduce stack further
            final_stack_size = len(app.screen_stack)
            await pilot.press("escape")
            await pilot.pause()

            # Stack should remain at 1 (can't pop the default screen)
            assert len(app.screen_stack) == final_stack_size
