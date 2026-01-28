"""Unit tests for ConflictResolutionApp.

Tests the main TUI application for conflict resolution.
"""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    Resolution,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.app import (
    ConflictResolutionApp,
)

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
def sample_conflicts() -> list[Conflict]:
    """Create multiple sample conflicts."""
    conflicts = []
    for i in range(3):
        conflicts.append(
            Conflict(
                entity_type="services",
                entity_id=f"svc-{i}",
                entity_name=f"service-{i}",
                source_state={"host": f"old-{i}.example.com"},
                target_state={"host": f"new-{i}.example.com"},
                drift_fields=["host"],
                source_system_id=f"gw-svc-{i}",
                target_system_id=f"kn-svc-{i}",
                direction="push",
            )
        )
    return conflicts


# ============================================================================
# Initialization Tests
# ============================================================================


class TestConflictResolutionAppInit:
    """Tests for ConflictResolutionApp initialization."""

    @pytest.mark.unit
    def test_app_stores_conflicts(self, sample_conflicts: list[Conflict]) -> None:
        """App stores conflicts."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )
        assert app.conflicts == sample_conflicts

    @pytest.mark.unit
    def test_app_stores_direction(self, sample_conflict: Conflict) -> None:
        """App stores direction."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="pull",
            dry_run=False,
        )
        assert app.direction == "pull"

    @pytest.mark.unit
    def test_app_stores_dry_run(self, sample_conflict: Conflict) -> None:
        """App stores dry_run flag."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=True,
        )
        assert app.dry_run is True

    @pytest.mark.unit
    def test_app_initializes_empty_result(self, sample_conflict: Conflict) -> None:
        """App starts with empty result list."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        assert app._result == []

    @pytest.mark.unit
    def test_app_initializes_service(self, sample_conflict: Conflict) -> None:
        """App initializes a ConflictResolutionService."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        from system_operations_manager.services.kong.conflict_resolver import (
            ConflictResolutionService,
        )

        assert isinstance(app.service, ConflictResolutionService)

    @pytest.mark.unit
    def test_app_service_starts_empty(self, sample_conflict: Conflict) -> None:
        """App service starts with no resolutions."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        assert app.service.get_all_resolutions() == []


# ============================================================================
# Resolution Management Tests
# ============================================================================


class TestConflictResolutionAppResolutions:
    """Tests for resolution management via service."""

    @pytest.mark.unit
    def test_service_can_store_resolution(self, sample_conflict: Conflict) -> None:
        """App service can store a resolution."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        resolution = Resolution(
            conflict=sample_conflict,
            action=ResolutionAction.KEEP_SOURCE,
        )
        app.service.set_resolution(resolution)

        resolutions = app.service.get_all_resolutions()
        assert len(resolutions) == 1
        assert resolutions[0].action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.unit
    def test_service_can_store_multiple_resolutions(self, sample_conflicts: list[Conflict]) -> None:
        """App service can hold multiple resolutions."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )

        for conflict in sample_conflicts:
            app.service.set_resolution(
                Resolution(
                    conflict=conflict,
                    action=ResolutionAction.KEEP_SOURCE,
                )
            )

        resolutions = app.service.get_all_resolutions()
        assert len(resolutions) == len(sample_conflicts)


# ============================================================================
# Async Tests
# ============================================================================


class TestConflictResolutionAppAsync:
    """Async tests for ConflictResolutionApp."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_starts_with_list_screen(self, sample_conflicts: list[Conflict]) -> None:
        """App starts on ConflictListScreen."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )

        async with app.run_test():
            # Should be on ConflictListScreen
            from system_operations_manager.tui.apps.conflict_resolution.screens import (
                ConflictListScreen,
            )

            # The active screen should be ConflictListScreen
            assert isinstance(app.screen, ConflictListScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_quit_action_works(self, sample_conflicts: list[Conflict]) -> None:
        """Quit action exits the app."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )

        async with app.run_test() as pilot:
            await pilot.press("q")

        # App should have exited (no resolutions returned means cancelled)
        assert app._result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_escape_goes_back(self, sample_conflicts: list[Conflict]) -> None:
        """Escape key triggers back action."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )

        async with app.run_test() as pilot:
            # On initial screen, escape does nothing (can't go back)
            initial_stack_size = len(app.screen_stack)
            await pilot.press("escape")
            # Stack should be same size (already at root)
            assert len(app.screen_stack) <= initial_stack_size

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_shows_conflicts_in_table(self, sample_conflicts: list[Conflict]) -> None:
        """App displays conflicts in a table."""
        app = ConflictResolutionApp(
            conflicts=sample_conflicts,
            direction="push",
            dry_run=False,
        )

        async with app.run_test() as pilot:
            from textual.widgets import DataTable

            await pilot.pause()
            table = app.screen.query_one(DataTable)
            assert table.row_count == len(sample_conflicts)


class TestRunAndGetResolutions:
    """Tests for run_and_get_resolutions method."""

    @pytest.mark.unit
    def test_run_and_get_resolutions_method_exists(self, sample_conflict: Conflict) -> None:
        """run_and_get_resolutions method exists."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        assert hasattr(app, "run_and_get_resolutions")
        assert callable(app.run_and_get_resolutions)

    @pytest.mark.unit
    def test_result_can_be_set(self, sample_conflict: Conflict) -> None:
        """_result can be set with resolutions."""
        app = ConflictResolutionApp(
            conflicts=[sample_conflict],
            direction="push",
            dry_run=False,
        )
        resolution = Resolution(
            conflict=sample_conflict,
            action=ResolutionAction.KEEP_SOURCE,
        )
        app._result = [resolution]

        assert isinstance(app._result, list)
        assert len(app._result) == 1
        assert app._result[0].action == ResolutionAction.KEEP_SOURCE
