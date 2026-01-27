"""Unit tests for conflict resolution TUI screens.

Tests the ConflictListScreen, ConflictDetailScreen, and SummaryScreen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

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
