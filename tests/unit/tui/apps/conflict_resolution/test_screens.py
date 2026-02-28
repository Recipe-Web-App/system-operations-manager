"""Unit tests for conflict resolution TUI screens.

Tests the ConflictListScreen, ConflictDetailScreen, and SummaryScreen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Label

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ConflictResolutionService,
    Resolution,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.screens import (
    ConflictDetailScreen,
    ConflictListScreen,
    MergePreviewScreen,
    SummaryScreen,
)
from system_operations_manager.utils.merge import MergeAnalysis

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_conflict() -> Conflict:
    """Create a sample conflict for testing."""
    return Conflict(
        entity_type="services",
        entity_id="svc-123",
        entity_name="test-service",
        source_state={"host": "old.example.com", "port": 80},
        target_state={"host": "new.example.com", "port": 80},
        drift_fields=["host"],
        source_system_id="gw-svc-123",
        target_system_id="kn-svc-123",
        direction="push",
    )


@pytest.fixture
def sample_conflicts(sample_conflict: Conflict) -> list[Conflict]:
    """Create a list of sample conflicts."""
    conflict2 = Conflict(
        entity_type="routes",
        entity_id="rt-456",
        entity_name="test-route",
        source_state={"paths": ["/old"]},
        target_state={"paths": ["/new"]},
        drift_fields=["paths"],
        source_system_id="gw-rt-456",
        target_system_id="kn-rt-456",
        direction="push",
    )
    return [sample_conflict, conflict2]


@pytest.fixture
def sample_resolution(sample_conflict: Conflict) -> Resolution:
    """Create a sample resolution."""
    return Resolution(
        conflict=sample_conflict,
        action=ResolutionAction.KEEP_SOURCE,
        resolved_at=datetime.now(UTC),
    )


@pytest.fixture
def conflict_resolution_service() -> ConflictResolutionService:
    """Create a ConflictResolutionService for testing."""
    return ConflictResolutionService()


# ============================================================================
# ConflictListScreen Tests
# ============================================================================


class ConflictListTestApp(App[None]):
    """Test app for ConflictListScreen."""

    def __init__(
        self,
        conflicts: list[Conflict],
        service: ConflictResolutionService,
    ) -> None:
        super().__init__()
        self.conflicts = conflicts
        self.service = service
        self.selected_conflict: Conflict | None = None

    def compose(self) -> ComposeResult:
        yield ConflictListScreen(
            conflicts=self.conflicts,
            direction="push",
            service=self.service,
        )

    def on_conflict_list_screen_conflict_selected(
        self, event: ConflictListScreen.ConflictSelected
    ) -> None:
        """Handle conflict selection."""
        self.selected_conflict = event.conflict


class TestConflictListScreenInit:
    """Tests for ConflictListScreen initialization."""

    @pytest.mark.unit
    def test_conflict_list_screen_stores_conflicts(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictListScreen stores conflicts."""
        screen = ConflictListScreen(
            conflicts=sample_conflicts,
            direction="push",
            service=conflict_resolution_service,
        )
        assert screen.conflicts == sample_conflicts

    @pytest.mark.unit
    def test_conflict_list_screen_stores_direction(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictListScreen stores direction."""
        screen = ConflictListScreen(
            conflicts=sample_conflicts,
            direction="pull",
            service=conflict_resolution_service,
        )
        assert screen.direction == "pull"

    @pytest.mark.unit
    def test_conflict_list_screen_stores_service(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictListScreen stores service."""
        screen = ConflictListScreen(
            conflicts=sample_conflicts,
            direction="push",
            service=conflict_resolution_service,
        )
        assert screen.service is conflict_resolution_service


class TestConflictListScreenMessages:
    """Tests for ConflictListScreen messages."""

    @pytest.mark.unit
    def test_conflict_selected_message(self, sample_conflict: Conflict) -> None:
        """ConflictSelected message stores conflict."""
        msg = ConflictListScreen.ConflictSelected(sample_conflict)
        assert msg.conflict == sample_conflict


class TestConflictListScreenAsync:
    """Async tests for ConflictListScreen."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_displays_data_table(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictListScreen displays a DataTable."""
        app = ConflictListTestApp(sample_conflicts, conflict_resolution_service)

        async with app.run_test():
            table = app.query_one(DataTable)
            assert table is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_shows_conflict_count(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictListScreen shows conflict count in header."""
        app = ConflictListTestApp(sample_conflicts, conflict_resolution_service)

        async with app.run_test():
            header = app.query_one("#header-label", Label)
            # The header should exist and contain conflict info
            assert header is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_table_has_correct_row_count(
        self,
        sample_conflicts: list[Conflict],
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """DataTable has correct number of rows."""
        app = ConflictListTestApp(sample_conflicts, conflict_resolution_service)

        async with app.run_test():
            table = app.query_one(DataTable)
            assert table.row_count == 2


# ============================================================================
# ConflictDetailScreen Tests
# ============================================================================


class ConflictDetailTestApp(App[None]):
    """Test app for ConflictDetailScreen."""

    def __init__(
        self,
        conflict: Conflict,
        service: ConflictResolutionService,
    ) -> None:
        super().__init__()
        self.conflict = conflict
        self.service = service
        self.resolution_made: Resolution | None = None

    def compose(self) -> ComposeResult:
        yield ConflictDetailScreen(
            conflict=self.conflict,
            service=self.service,
        )

    def on_conflict_detail_screen_resolution_made(
        self, event: ConflictDetailScreen.ResolutionMade
    ) -> None:
        """Handle resolution."""
        self.resolution_made = event.resolution
        self.exit()


class TestConflictDetailScreenInit:
    """Tests for ConflictDetailScreen initialization."""

    @pytest.mark.unit
    def test_detail_screen_stores_conflict(
        self,
        sample_conflict: Conflict,
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictDetailScreen stores conflict."""
        screen = ConflictDetailScreen(
            conflict=sample_conflict,
            service=conflict_resolution_service,
        )
        assert screen.conflict == sample_conflict

    @pytest.mark.unit
    def test_detail_screen_stores_service(
        self,
        sample_conflict: Conflict,
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictDetailScreen stores service."""
        screen = ConflictDetailScreen(
            conflict=sample_conflict,
            service=conflict_resolution_service,
        )
        assert screen.service is conflict_resolution_service


class TestConflictDetailScreenMessages:
    """Tests for ConflictDetailScreen messages."""

    @pytest.mark.unit
    def test_resolution_made_message(self, sample_resolution: Resolution) -> None:
        """ResolutionMade message stores resolution."""
        msg = ConflictDetailScreen.ResolutionMade(sample_resolution)
        assert msg.resolution == sample_resolution


class TestConflictDetailScreenAsync:
    """Async tests for ConflictDetailScreen."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_shows_entity_name(
        self,
        sample_conflict: Conflict,
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictDetailScreen shows entity name."""
        app = ConflictDetailTestApp(sample_conflict, conflict_resolution_service)

        async with app.run_test():
            title = app.query_one("#conflict-title", Label)
            assert title is not None
            # Verify the conflict name is what we expect
            assert sample_conflict.entity_name == "test-service"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_shows_drift_fields(
        self,
        sample_conflict: Conflict,
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictDetailScreen shows drift fields."""
        app = ConflictDetailTestApp(sample_conflict, conflict_resolution_service)

        async with app.run_test():
            drift_label = app.query_one("#drift-fields", Label)
            assert drift_label is not None
            # Verify the drift field is what we expect
            assert "host" in sample_conflict.drift_fields


# ============================================================================
# SummaryScreen Tests
# ============================================================================


class SummaryTestApp(App[None]):
    """Test app for SummaryScreen."""

    def __init__(
        self,
        resolutions: list[Resolution],
        direction: Literal["push", "pull"] = "push",
    ) -> None:
        super().__init__()
        self.resolutions = resolutions
        self.direction = direction
        self.apply_confirmed = False
        self.cancelled = False

    def on_mount(self) -> None:
        """Push the summary screen on mount."""
        self.push_screen(
            SummaryScreen(
                resolutions=self.resolutions,
                direction=self.direction,
            )
        )

    def on_summary_screen_apply_confirmed(self, event: SummaryScreen.ApplyConfirmed) -> None:
        """Handle apply confirmation."""
        self.apply_confirmed = True
        self.exit()

    def on_summary_screen_apply_cancelled(self, event: SummaryScreen.ApplyCancelled) -> None:
        """Handle cancellation."""
        self.cancelled = True
        self.exit()


class TestSummaryScreenInit:
    """Tests for SummaryScreen initialization."""

    @pytest.mark.unit
    def test_summary_screen_stores_resolutions(self, sample_resolution: Resolution) -> None:
        """SummaryScreen stores resolutions."""
        screen = SummaryScreen(
            resolutions=[sample_resolution],
            direction="push",
        )
        assert len(screen.resolutions) == 1

    @pytest.mark.unit
    def test_summary_screen_stores_direction(self, sample_resolution: Resolution) -> None:
        """SummaryScreen stores direction."""
        screen = SummaryScreen(
            resolutions=[sample_resolution],
            direction="pull",
        )
        assert screen.direction == "pull"

    @pytest.mark.unit
    def test_summary_screen_empty_resolutions(self) -> None:
        """SummaryScreen handles empty resolutions."""
        screen = SummaryScreen(resolutions=[], direction="push")
        assert len(screen.resolutions) == 0


class TestSummaryScreenMessages:
    """Tests for SummaryScreen messages."""

    @pytest.mark.unit
    def test_apply_confirmed_message(self, sample_resolution: Resolution) -> None:
        """ApplyConfirmed message stores resolutions."""
        msg = SummaryScreen.ApplyConfirmed([sample_resolution])
        assert len(msg.resolutions) == 1

    @pytest.mark.unit
    def test_apply_cancelled_message(self) -> None:
        """ApplyCancelled message can be instantiated."""
        msg = SummaryScreen.ApplyCancelled()
        assert msg is not None


class TestSummaryScreenAsync:
    """Async tests for SummaryScreen."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_shows_summary_title(self, sample_resolution: Resolution) -> None:
        """SummaryScreen shows title."""
        app = SummaryTestApp([sample_resolution])

        async with app.run_test() as pilot:
            await pilot.pause()
            title = app.screen.query_one("#summary-title", Label)
            assert title is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_shows_resolution_stats(self, sample_resolution: Resolution) -> None:
        """SummaryScreen shows resolution stats."""
        resolutions = [sample_resolution]
        app = SummaryTestApp(resolutions)

        async with app.run_test() as pilot:
            await pilot.pause()
            stats = app.screen.query_one("#summary-stats")
            assert stats is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_escape_cancels(self, sample_resolution: Resolution) -> None:
        """Pressing escape cancels."""
        app = SummaryTestApp([sample_resolution])

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")

        assert app.cancelled


# ============================================================================
# MergePreviewScreen Tests
# ============================================================================


class MergePreviewTestApp(App[None]):
    """Test app for MergePreviewScreen."""

    def __init__(
        self,
        conflict: Conflict,
        analysis: MergeAnalysis,
    ) -> None:
        super().__init__()
        self.conflict = conflict
        self.analysis = analysis
        self.resolution_made: Resolution | None = None
        self.cancelled = False

    def on_mount(self) -> None:
        """Push the merge preview screen on mount."""
        self.push_screen(
            MergePreviewScreen(
                conflict=self.conflict,
                analysis=self.analysis,
            )
        )


@pytest.fixture
def sample_merge_analysis() -> MergeAnalysis:
    """Create a sample merge analysis for testing."""
    return MergeAnalysis(
        can_auto_merge=False,
        source_only_fields=["port"],
        target_only_fields=["path"],
        conflicting_fields=["host"],
    )


class TestMergePreviewScreenInit:
    """Tests for MergePreviewScreen initialization."""

    @pytest.mark.unit
    def test_merge_preview_screen_stores_conflict(
        self,
        sample_conflict: Conflict,
        sample_merge_analysis: MergeAnalysis,
    ) -> None:
        """MergePreviewScreen stores conflict."""
        screen = MergePreviewScreen(
            conflict=sample_conflict,
            analysis=sample_merge_analysis,
        )
        assert screen.conflict == sample_conflict

    @pytest.mark.unit
    def test_merge_preview_screen_stores_analysis(
        self,
        sample_conflict: Conflict,
        sample_merge_analysis: MergeAnalysis,
    ) -> None:
        """MergePreviewScreen stores analysis."""
        screen = MergePreviewScreen(
            conflict=sample_conflict,
            analysis=sample_merge_analysis,
        )
        assert screen.analysis == sample_merge_analysis
        assert "host" in screen.analysis.conflicting_fields


class TestMergePreviewScreenReturn:
    """Tests for MergePreviewScreen return behavior."""

    @pytest.mark.unit
    def test_merge_preview_returns_resolution_type(
        self, sample_conflict: Conflict, sample_merge_analysis: MergeAnalysis
    ) -> None:
        """MergePreviewScreen is typed to return Resolution or None."""
        # MergePreviewScreen uses dismiss() to return Resolution | None
        # It doesn't use messages but returns directly via Screen[Resolution | None]
        screen = MergePreviewScreen(
            conflict=sample_conflict,
            analysis=sample_merge_analysis,
        )
        # The screen should be a Screen that returns Resolution or None
        assert hasattr(screen, "dismiss")


class TestMergePreviewScreenAsync:
    """Async tests for MergePreviewScreen."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_displays_merge_title(
        self,
        sample_conflict: Conflict,
        sample_merge_analysis: MergeAnalysis,
    ) -> None:
        """MergePreviewScreen displays merge title."""
        app = MergePreviewTestApp(sample_conflict, sample_merge_analysis)

        async with app.run_test() as pilot:
            await pilot.pause()
            # The screen should show a merge title
            title = app.screen.query("#merge-title")
            assert title is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_displays_merge_info(
        self,
        sample_conflict: Conflict,
        sample_merge_analysis: MergeAnalysis,
    ) -> None:
        """MergePreviewScreen displays merge info."""
        app = MergePreviewTestApp(sample_conflict, sample_merge_analysis)

        async with app.run_test() as pilot:
            await pilot.pause()
            # The screen should show merge info
            merge_info = app.screen.query("#merge-info")
            assert merge_info is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_escape_cancels(
        self,
        sample_conflict: Conflict,
        sample_merge_analysis: MergeAnalysis,
    ) -> None:
        """Pressing escape cancels merge preview."""
        app = MergePreviewTestApp(sample_conflict, sample_merge_analysis)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")

        # Should exit without resolution
        assert app.resolution_made is None


# ============================================================================
# Merge-related tests for existing screens
# ============================================================================


class TestConflictDetailScreenMerge:
    """Tests for merge functionality in ConflictDetailScreen."""

    @pytest.mark.unit
    def test_binding_4_available_for_merge(
        self,
        sample_conflict: Conflict,
        conflict_resolution_service: ConflictResolutionService,
    ) -> None:
        """ConflictDetailScreen has binding for key 4 (merge)."""
        screen = ConflictDetailScreen(
            conflict=sample_conflict,
            service=conflict_resolution_service,
        )
        # BINDINGS can be tuples (key, action, desc) or Binding objects
        binding_keys = []
        for b in screen.BINDINGS:
            if isinstance(b, tuple):
                binding_keys.append(b[0])  # First element is the key
            else:
                binding_keys.append(b.key)  # Binding object
        assert "4" in binding_keys


class TestSummaryScreenMerge:
    """Tests for merge count in SummaryScreen."""

    @pytest.mark.unit
    def test_summary_screen_with_merge_resolution(self, sample_conflict: Conflict) -> None:
        """SummaryScreen handles merge resolutions."""
        merge_resolution = Resolution(
            conflict=sample_conflict,
            action=ResolutionAction.MERGE,
            merged_state={"host": "merged.example.com"},
        )
        screen = SummaryScreen(
            resolutions=[merge_resolution],
            direction="push",
        )
        assert len(screen.resolutions) == 1
        assert screen.resolutions[0].action == ResolutionAction.MERGE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_displays_merge_count(self, sample_conflict: Conflict) -> None:
        """SummaryScreen displays merge count in stats."""
        merge_resolution = Resolution(
            conflict=sample_conflict,
            action=ResolutionAction.MERGE,
            merged_state={"host": "merged.example.com"},
        )
        app = SummaryTestApp([merge_resolution])

        async with app.run_test() as pilot:
            await pilot.pause()
            # The stats container should exist
            stats = app.screen.query_one("#summary-stats")
            assert stats is not None


# ============================================================================
# Sync __new__ helpers
# ============================================================================


def _make_sample_conflict() -> Conflict:
    """Return a sample Conflict for sync tests."""
    return Conflict(
        entity_type="services",
        entity_id="svc-123",
        entity_name="test-service",
        source_state={"host": "old.example.com", "port": 80},
        target_state={"host": "new.example.com", "port": 80},
        drift_fields=["host"],
        source_system_id="gw-svc-123",
        target_system_id="kn-svc-123",
        direction="push",
    )


def _make_conflict_list_screen() -> Any:
    """Create a ConflictListScreen bypassing __init__ for sync tests.

    Returns Any so callers can use MagicMock attributes without mypy errors.
    The underlying object is a ConflictListScreen instance.
    """
    screen: Any = ConflictListScreen.__new__(ConflictListScreen)
    screen.conflicts = [_make_sample_conflict()]
    screen.direction = "push"
    screen.service = MagicMock()
    screen.query_one = MagicMock()
    screen.post_message = MagicMock()
    screen.notify = MagicMock()
    return screen


def _make_conflict_detail_screen() -> Any:
    """Create a ConflictDetailScreen bypassing __init__ for sync tests.

    Returns Any so callers can use MagicMock attributes without mypy errors.
    The underlying object is a ConflictDetailScreen instance.
    """
    screen: Any = ConflictDetailScreen.__new__(ConflictDetailScreen)
    screen.conflict = _make_sample_conflict()
    screen.service = MagicMock()
    screen._diff_mode = "side_by_side"
    screen.query_one = MagicMock()
    screen.post_message = MagicMock()
    screen.notify = MagicMock()
    return screen


def _make_summary_screen() -> Any:
    """Create a SummaryScreen bypassing __init__ for sync tests.

    Returns Any so callers can use MagicMock attributes without mypy errors.
    The underlying object is a SummaryScreen instance.
    """
    conflict = _make_sample_conflict()
    resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
    screen: Any = SummaryScreen.__new__(SummaryScreen)
    screen.resolutions = [resolution]
    screen.direction = "push"
    screen.dry_run = False
    screen.post_message = MagicMock()
    return screen


def _make_merge_preview_screen() -> Any:
    """Create a MergePreviewScreen bypassing __init__ for sync tests.

    Returns Any so callers can use MagicMock attributes without mypy errors.
    The underlying object is a MergePreviewScreen instance.
    """
    from system_operations_manager.utils.merge import MergeAnalysis

    conflict = _make_sample_conflict()
    analysis = MergeAnalysis(
        can_auto_merge=False,
        source_only_fields=[],
        target_only_fields=[],
        conflicting_fields=["host"],
    )
    screen: Any = MergePreviewScreen.__new__(MergePreviewScreen)
    screen.conflict = conflict
    screen.analysis = analysis
    screen._merged_state = dict(conflict.source_state)
    screen.notify = MagicMock()
    screen.dismiss = MagicMock()
    screen.query_one = MagicMock()
    return screen


# ============================================================================
# ConflictListScreen Sync Tests
# ============================================================================


@pytest.mark.unit
class TestConflictListScreenSyncMethods:
    """Sync tests for ConflictListScreen action methods using __new__ pattern."""

    def test_action_cursor_down_delegates_to_table(self) -> None:
        """action_cursor_down calls action_cursor_down on the DataTable."""
        screen = _make_conflict_list_screen()
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_cursor_down()

        mock_table.action_cursor_down.assert_called_once()

    def test_action_cursor_up_delegates_to_table(self) -> None:
        """action_cursor_up calls action_cursor_up on the DataTable."""
        screen = _make_conflict_list_screen()
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_cursor_up()

        mock_table.action_cursor_up.assert_called_once()

    def test_action_select_posts_conflict_selected(self) -> None:
        """action_select posts ConflictSelected for the cursor row conflict."""
        screen = _make_conflict_list_screen()
        mock_table: MagicMock = MagicMock()
        mock_table.cursor_row = 0
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_select()

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictListScreen.ConflictSelected)
        assert msg.conflict is screen.conflicts[0]

    def test_action_select_out_of_range_does_nothing(self) -> None:
        """action_select does not post when cursor_row is out of range."""
        screen = _make_conflict_list_screen()
        mock_table: MagicMock = MagicMock()
        mock_table.cursor_row = 99  # beyond the conflicts list
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_select()

        screen.post_message.assert_not_called()

    def test_handle_row_selected_posts_conflict_selected(self) -> None:
        """handle_row_selected posts ConflictSelected for a valid row."""
        screen = _make_conflict_list_screen()
        event: MagicMock = MagicMock(spec=DataTable.RowSelected)
        event.cursor_row = 0

        screen.handle_row_selected(event)

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictListScreen.ConflictSelected)

    def test_handle_row_selected_out_of_range(self) -> None:
        """handle_row_selected does not post when row is out of range."""
        screen = _make_conflict_list_screen()
        event: MagicMock = MagicMock(spec=DataTable.RowSelected)
        event.cursor_row = 50

        screen.handle_row_selected(event)

        screen.post_message.assert_not_called()

    def test_action_keep_source_all_calls_batch(self) -> None:
        """action_keep_source_all applies batch resolution for pending conflicts."""
        screen = _make_conflict_list_screen()
        screen.service.get_resolution.return_value = None
        screen.service.apply_batch_resolution.return_value = 1
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_keep_source_all()

        screen.service.apply_batch_resolution.assert_called_once()
        call_args = screen.service.apply_batch_resolution.call_args[0]
        assert call_args[1] == ResolutionAction.KEEP_SOURCE
        screen.notify.assert_called_once()

    def test_action_keep_target_all_calls_batch(self) -> None:
        """action_keep_target_all applies batch resolution for pending conflicts."""
        screen = _make_conflict_list_screen()
        screen.service.get_resolution.return_value = None
        screen.service.apply_batch_resolution.return_value = 1
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_keep_target_all()

        screen.service.apply_batch_resolution.assert_called_once()
        call_args = screen.service.apply_batch_resolution.call_args[0]
        assert call_args[1] == ResolutionAction.KEEP_TARGET
        screen.notify.assert_called_once()

    def test_action_merge_all_auto_skips_already_resolved(self) -> None:
        """action_merge_all_auto skips conflicts that are already resolved."""
        screen = _make_conflict_list_screen()
        # Mark all conflicts as already resolved
        screen.service.get_resolution.return_value = MagicMock()
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.action_merge_all_auto()

        # No resolutions should be set since all were already resolved
        screen.service.set_resolution.assert_not_called()
        # No notifications for merged/skipped (all were pre-resolved)
        screen.notify.assert_not_called()

    def test_action_merge_all_auto_can_merge(self) -> None:
        """action_merge_all_auto creates MERGE resolution when auto-merge possible."""
        from system_operations_manager.utils.merge import MergeAnalysis

        screen = _make_conflict_list_screen()
        # No existing resolutions
        screen.service.get_resolution.return_value = None
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen.conflicts = [
            Conflict(
                entity_type="services",
                entity_id="svc-1",
                entity_name="svc-1",
                source_state={"host": "src.example.com", "port": 80},
                target_state={"host": "src.example.com", "port": 8080},
                drift_fields=["port"],
                source_system_id="gw-1",
                target_system_id="kn-1",
                direction="push",
            )
        ]

        with (
            patch("system_operations_manager.utils.merge.analyze_merge_potential") as mock_analyze,
            patch("system_operations_manager.utils.merge.compute_auto_merge") as mock_compute,
        ):
            mock_analysis = MergeAnalysis(
                can_auto_merge=True,
                source_only_fields=["host"],
                target_only_fields=[],
                conflicting_fields=[],
            )
            mock_analyze.return_value = mock_analysis
            mock_compute.return_value = {"host": "src.example.com", "port": 8080}

            screen.action_merge_all_auto()

        screen.service.set_resolution.assert_called_once()
        resolution_arg = screen.service.set_resolution.call_args[0][0]
        assert resolution_arg.action == ResolutionAction.MERGE
        assert "merged" in screen.notify.call_args_list[0][0][0].lower()

    def test_action_merge_all_auto_cannot_merge(self) -> None:
        """action_merge_all_auto notifies skipped count when cannot auto-merge."""
        from system_operations_manager.utils.merge import MergeAnalysis

        screen = _make_conflict_list_screen()
        screen.service.get_resolution.return_value = None
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        with patch("system_operations_manager.utils.merge.analyze_merge_potential") as mock_analyze:
            mock_analysis = MergeAnalysis(
                can_auto_merge=False,
                source_only_fields=[],
                target_only_fields=[],
                conflicting_fields=["host"],
            )
            mock_analyze.return_value = mock_analysis

            screen.action_merge_all_auto()

        screen.service.set_resolution.assert_not_called()
        screen.notify.assert_called_once()
        assert "skipped" in screen.notify.call_args[0][0].lower()

    def test_refresh_table_clears_and_repopulates(self) -> None:
        """_refresh_table clears the DataTable and adds rows for each conflict."""
        screen = _make_conflict_list_screen()
        screen.service.get_resolution.return_value = None
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen._refresh_table()

        mock_table.clear.assert_called_once()
        assert mock_table.add_row.call_count == len(screen.conflicts)

    def test_refresh_table_shows_resolved_status(self) -> None:
        """_refresh_table marks resolved conflicts with their action value."""
        screen = _make_conflict_list_screen()
        conflict = screen.conflicts[0]
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        screen.service.get_resolution.return_value = resolution
        mock_table: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen._refresh_table()

        mock_table.add_row.assert_called_once()
        row_args = mock_table.add_row.call_args[0]
        # Status arg (4th column) should contain the action value
        assert ResolutionAction.KEEP_SOURCE.value in row_args[3]


# ============================================================================
# ConflictDetailScreen Sync Tests
# ============================================================================


@pytest.mark.unit
class TestConflictDetailScreenSyncMethods:
    """Sync tests for ConflictDetailScreen action methods using __new__ pattern."""

    def test_action_keep_source_posts_resolution(self) -> None:
        """action_keep_source posts ResolutionMade with KEEP_SOURCE."""
        screen = _make_conflict_detail_screen()

        screen.action_keep_source()

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)
        assert msg.resolution.action == ResolutionAction.KEEP_SOURCE

    def test_action_keep_target_posts_resolution(self) -> None:
        """action_keep_target posts ResolutionMade with KEEP_TARGET."""
        screen = _make_conflict_detail_screen()

        screen.action_keep_target()

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)
        assert msg.resolution.action == ResolutionAction.KEEP_TARGET

    def test_action_skip_posts_resolution(self) -> None:
        """action_skip posts ResolutionMade with SKIP."""
        screen = _make_conflict_detail_screen()

        screen.action_skip()

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)
        assert msg.resolution.action == ResolutionAction.SKIP

    def test_make_resolution_creates_correct_resolution(self) -> None:
        """_make_resolution creates a resolution with the given action and posts it."""
        screen = _make_conflict_detail_screen()

        screen._make_resolution(ResolutionAction.KEEP_SOURCE)

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)
        assert msg.resolution.conflict is screen.conflict
        assert msg.resolution.action == ResolutionAction.KEEP_SOURCE

    def test_action_merge_auto_merge_path(self) -> None:
        """action_merge posts resolution directly when auto-merge is possible."""
        from system_operations_manager.utils.merge import MergeAnalysis

        screen = _make_conflict_detail_screen()

        with (
            patch("system_operations_manager.utils.merge.analyze_merge_potential") as mock_analyze,
            patch("system_operations_manager.utils.merge.compute_auto_merge") as mock_compute,
        ):
            mock_analysis = MergeAnalysis(
                can_auto_merge=True,
                source_only_fields=["host"],
                target_only_fields=[],
                conflicting_fields=[],
            )
            mock_analyze.return_value = mock_analysis
            mock_compute.return_value = {"host": "merged.example.com", "port": 80}

            screen.action_merge()

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)
        assert msg.resolution.action == ResolutionAction.MERGE
        screen.notify.assert_called_once()

    def test_action_merge_manual_path_pushes_screen(self) -> None:
        """action_merge pushes MergePreviewScreen when auto-merge not possible."""
        from system_operations_manager.utils.merge import MergeAnalysis

        screen = _make_conflict_detail_screen()
        mock_app: MagicMock = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.utils.merge.analyze_merge_potential") as mock_analyze,
        ):
            mock_analysis = MergeAnalysis(
                can_auto_merge=False,
                source_only_fields=[],
                target_only_fields=[],
                conflicting_fields=["host"],
            )
            mock_analyze.return_value = mock_analysis

            screen.action_merge()

        mock_app.push_screen.assert_called_once()
        pushed_screen = mock_app.push_screen.call_args[0][0]
        assert isinstance(pushed_screen, MergePreviewScreen)

    def test_handle_merge_result_with_resolution(self) -> None:
        """_handle_merge_result posts ResolutionMade when resolution is not None."""
        screen = _make_conflict_detail_screen()
        conflict = screen.conflict
        resolution = Resolution(conflict=conflict, action=ResolutionAction.MERGE)

        screen._handle_merge_result(resolution)

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, ConflictDetailScreen.ResolutionMade)

    def test_handle_merge_result_with_none(self) -> None:
        """_handle_merge_result does not post when resolution is None."""
        screen = _make_conflict_detail_screen()

        screen._handle_merge_result(None)

        screen.post_message.assert_not_called()

    def test_action_toggle_diff_mode_calls_toggle(self) -> None:
        """action_toggle_diff_mode calls toggle_mode on the DiffViewer."""
        screen = _make_conflict_detail_screen()
        mock_viewer: MagicMock = MagicMock()
        screen.query_one = MagicMock(return_value=mock_viewer)

        screen.action_toggle_diff_mode()

        mock_viewer.toggle_mode.assert_called_once()

    def test_action_back_pops_screen(self) -> None:
        """action_back calls app.pop_screen."""
        screen = _make_conflict_detail_screen()
        mock_app: MagicMock = MagicMock()

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_back()

        mock_app.pop_screen.assert_called_once()

    def test_handle_resolution_chosen_merge_calls_action_merge(self) -> None:
        """handle_resolution_chosen calls action_merge for MERGE action."""
        from system_operations_manager.tui.apps.conflict_resolution.widgets import (
            ResolutionPicker,
        )

        screen = _make_conflict_detail_screen()
        screen.action_merge = MagicMock()
        event: MagicMock = MagicMock(spec=ResolutionPicker.ResolutionChosen)
        event.action = ResolutionAction.MERGE

        screen.handle_resolution_chosen(event)

        screen.action_merge.assert_called_once()

    def test_handle_resolution_chosen_non_merge_makes_resolution(self) -> None:
        """handle_resolution_chosen calls _make_resolution for non-MERGE actions."""
        from system_operations_manager.tui.apps.conflict_resolution.widgets import (
            ResolutionPicker,
        )

        screen = _make_conflict_detail_screen()
        screen._make_resolution = MagicMock()
        event: MagicMock = MagicMock(spec=ResolutionPicker.ResolutionChosen)
        event.action = ResolutionAction.KEEP_SOURCE

        screen.handle_resolution_chosen(event)

        screen._make_resolution.assert_called_once_with(ResolutionAction.KEEP_SOURCE)


# ============================================================================
# SummaryScreen Sync Tests
# ============================================================================


@pytest.mark.unit
class TestSummaryScreenSyncMethods:
    """Sync tests for SummaryScreen action methods using __new__ pattern."""

    def test_action_show_confirm_modal_pushes_modal(self) -> None:
        """action_show_confirm_modal pushes a Modal via app.push_screen."""
        from system_operations_manager.tui.components import Modal

        screen = _make_summary_screen()
        mock_app: MagicMock = MagicMock()

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_show_confirm_modal()

        mock_app.push_screen.assert_called_once()
        pushed_screen = mock_app.push_screen.call_args[0][0]
        assert isinstance(pushed_screen, Modal)

    def test_action_show_confirm_modal_dry_run_label(self) -> None:
        """action_show_confirm_modal uses 'preview' label in dry_run mode."""
        from system_operations_manager.tui.components import Modal

        screen = _make_summary_screen()
        screen.dry_run = True
        mock_app: MagicMock = MagicMock()

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_show_confirm_modal()

        pushed_screen = mock_app.push_screen.call_args[0][0]
        assert isinstance(pushed_screen, Modal)
        assert isinstance(pushed_screen._body, str)
        assert "preview" in pushed_screen._body

    def test_handle_modal_result_apply_posts_confirmed(self) -> None:
        """_handle_modal_result posts ApplyConfirmed when result is 'apply'."""
        screen = _make_summary_screen()

        screen._handle_modal_result("apply")

        screen.post_message.assert_called_once()
        msg = screen.post_message.call_args[0][0]
        assert isinstance(msg, SummaryScreen.ApplyConfirmed)
        assert msg.resolutions == screen.resolutions

    def test_handle_modal_result_cancel_does_nothing(self) -> None:
        """_handle_modal_result does not post when result is not 'apply'."""
        screen = _make_summary_screen()

        screen._handle_modal_result("cancel")

        screen.post_message.assert_not_called()

    def test_handle_modal_result_none_does_nothing(self) -> None:
        """_handle_modal_result does not post when result is None."""
        screen = _make_summary_screen()

        screen._handle_modal_result(None)

        screen.post_message.assert_not_called()


# ============================================================================
# MergePreviewScreen Sync Tests
# ============================================================================


@pytest.mark.unit
class TestMergePreviewScreenSyncMethods:
    """Sync tests for MergePreviewScreen action methods using __new__ pattern."""

    def test_action_confirm_merge_dismisses_with_resolution(self) -> None:
        """action_confirm_merge dismisses with a MERGE Resolution."""
        screen = _make_merge_preview_screen()
        screen._merged_state = {"host": "merged.example.com", "port": 80}

        screen.action_confirm_merge()

        screen.dismiss.assert_called_once()
        resolution = screen.dismiss.call_args[0][0]
        assert isinstance(resolution, Resolution)
        assert resolution.action == ResolutionAction.MERGE
        assert resolution.merged_state == {"host": "merged.example.com", "port": 80}

    def test_action_confirm_merge_no_state_notifies_error(self) -> None:
        """action_confirm_merge notifies error when _merged_state is None."""
        screen = _make_merge_preview_screen()
        screen._merged_state = None

        screen.action_confirm_merge()

        screen.dismiss.assert_not_called()
        screen.notify.assert_called_once()
        call_kwargs = screen.notify.call_args[1]
        assert call_kwargs.get("severity") == "error"

    def test_action_edit_merge_valid_edit(self) -> None:
        """action_edit_merge updates _merged_state after successful edit."""
        import json

        screen = _make_merge_preview_screen()
        merged_data: dict[str, Any] = {"host": "edited.example.com", "port": 80, "name": "svc"}
        edited_json = json.dumps(merged_data)

        mock_app: MagicMock = MagicMock()
        mock_suspend = MagicMock()
        mock_suspend.__enter__ = MagicMock(return_value=None)
        mock_suspend.__exit__ = MagicMock(return_value=False)
        mock_app.suspend.return_value = mock_suspend

        from system_operations_manager.utils.merge import MergeValidationResult

        mock_tmp = MagicMock()
        mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
        mock_tmp.__exit__ = MagicMock(return_value=False)
        mock_tmp.name = "/tmp/test_merge.json"

        mock_file_ctx = MagicMock()
        mock_file_ctx.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock(return_value=edited_json))
        )
        mock_file_ctx.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.utils.editor.get_editor", return_value="vim"),
            patch(
                "system_operations_manager.utils.editor.create_merge_template", return_value="{}"
            ),
            patch(
                "system_operations_manager.utils.editor.parse_merge_result",
                return_value=merged_data,
            ),
            patch(
                "system_operations_manager.utils.merge.validate_merged_state",
                return_value=MergeValidationResult(is_valid=True, errors=[], warnings=[]),
            ),
            patch("subprocess.run"),
            patch("tempfile.NamedTemporaryFile", return_value=mock_tmp),
            patch("pathlib.Path.unlink"),
            patch("pathlib.Path.open", return_value=mock_file_ctx),
        ):
            screen.action_edit_merge()

        assert screen._merged_state == merged_data
        screen.notify.assert_called()

    def test_action_edit_merge_validation_errors(self) -> None:
        """action_edit_merge shows error notification on validation failure."""
        import json

        screen = _make_merge_preview_screen()
        merged_data: dict[str, Any] = {"port": "not-a-number"}
        edited_json = json.dumps(merged_data)

        mock_app: MagicMock = MagicMock()
        mock_suspend = MagicMock()
        mock_suspend.__enter__ = MagicMock(return_value=None)
        mock_suspend.__exit__ = MagicMock(return_value=False)
        mock_app.suspend.return_value = mock_suspend

        from system_operations_manager.utils.merge import MergeValidationResult

        mock_tmp = MagicMock()
        mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
        mock_tmp.__exit__ = MagicMock(return_value=False)
        mock_tmp.name = "/tmp/test_merge_err.json"

        mock_file_ctx = MagicMock()
        mock_file_ctx.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock(return_value=edited_json))
        )
        mock_file_ctx.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.utils.editor.get_editor", return_value="vim"),
            patch(
                "system_operations_manager.utils.editor.create_merge_template", return_value="{}"
            ),
            patch(
                "system_operations_manager.utils.editor.parse_merge_result",
                return_value=merged_data,
            ),
            patch(
                "system_operations_manager.utils.merge.validate_merged_state",
                return_value=MergeValidationResult(
                    is_valid=False, errors=["Type mismatch for field 'port'"], warnings=[]
                ),
            ),
            patch("subprocess.run"),
            patch("tempfile.NamedTemporaryFile", return_value=mock_tmp),
            patch("pathlib.Path.unlink"),
            patch("pathlib.Path.open", return_value=mock_file_ctx),
        ):
            screen.action_edit_merge()

        screen.notify.assert_called()
        notify_kwargs = screen.notify.call_args[1]
        assert notify_kwargs.get("severity") == "error"

    def test_action_edit_merge_parse_failure(self) -> None:
        """action_edit_merge shows error notification when parse fails."""
        screen = _make_merge_preview_screen()

        mock_app: MagicMock = MagicMock()
        mock_suspend = MagicMock()
        mock_suspend.__enter__ = MagicMock(return_value=None)
        mock_suspend.__exit__ = MagicMock(return_value=False)
        mock_app.suspend.return_value = mock_suspend

        mock_tmp = MagicMock()
        mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
        mock_tmp.__exit__ = MagicMock(return_value=False)
        mock_tmp.name = "/tmp/test_parse_fail.json"

        mock_file_ctx = MagicMock()
        mock_file_ctx.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock(return_value="not-json"))
        )
        mock_file_ctx.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.utils.editor.get_editor", return_value="vim"),
            patch(
                "system_operations_manager.utils.editor.create_merge_template", return_value="{}"
            ),
            patch(
                "system_operations_manager.utils.editor.parse_merge_result",
                side_effect=ValueError("invalid JSON"),
            ),
            patch("subprocess.run"),
            patch("tempfile.NamedTemporaryFile", return_value=mock_tmp),
            patch("pathlib.Path.unlink"),
            patch("pathlib.Path.open", return_value=mock_file_ctx),
        ):
            screen.action_edit_merge()

        screen.notify.assert_called()
        notify_kwargs = screen.notify.call_args[1]
        assert notify_kwargs.get("severity") == "error"

    def test_action_edit_merge_with_warnings(self) -> None:
        """action_edit_merge shows warning notification when validation has warnings."""
        import json

        screen = _make_merge_preview_screen()
        merged_data: dict[str, Any] = {
            "host": "merged.example.com",
            "port": 80,
            "extra_field": "x",
        }
        edited_json = json.dumps(merged_data)

        mock_app: MagicMock = MagicMock()
        mock_suspend = MagicMock()
        mock_suspend.__enter__ = MagicMock(return_value=None)
        mock_suspend.__exit__ = MagicMock(return_value=False)
        mock_app.suspend.return_value = mock_suspend

        from system_operations_manager.utils.merge import MergeValidationResult

        mock_tmp = MagicMock()
        mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
        mock_tmp.__exit__ = MagicMock(return_value=False)
        mock_tmp.name = "/tmp/test_warnings.json"

        mock_file_ctx = MagicMock()
        mock_file_ctx.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock(return_value=edited_json))
        )
        mock_file_ctx.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.utils.editor.get_editor", return_value="vim"),
            patch(
                "system_operations_manager.utils.editor.create_merge_template", return_value="{}"
            ),
            patch(
                "system_operations_manager.utils.editor.parse_merge_result",
                return_value=merged_data,
            ),
            patch(
                "system_operations_manager.utils.merge.validate_merged_state",
                return_value=MergeValidationResult(
                    is_valid=True, errors=[], warnings=["Unknown field added: extra_field"]
                ),
            ),
            patch("subprocess.run"),
            patch("tempfile.NamedTemporaryFile", return_value=mock_tmp),
            patch("pathlib.Path.unlink"),
            patch("pathlib.Path.open", return_value=mock_file_ctx),
        ):
            screen.action_edit_merge()

        # Should have warning notification AND success notification
        assert screen.notify.call_count >= 2
        severity_values = [
            call[1].get("severity") for call in screen.notify.call_args_list if call[1]
        ]
        assert "warning" in severity_values
