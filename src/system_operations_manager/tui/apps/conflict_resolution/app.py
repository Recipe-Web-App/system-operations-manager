"""Main Textual application for conflict resolution TUI.

This module provides the ConflictResolutionApp, the entry point for
interactive conflict resolution during Kong sync operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ConflictResolutionService,
    Resolution,
)
from system_operations_manager.tui.apps.conflict_resolution.screens import (
    ConflictDetailScreen,
    ConflictListScreen,
    SummaryScreen,
)

if TYPE_CHECKING:
    pass


class ConflictResolutionApp(App[list[Resolution]]):
    """TUI application for interactive conflict resolution.

    This app presents conflicts between source and target systems,
    allows users to choose resolution actions, and returns the
    list of resolutions when complete.

    Attributes:
        conflicts: List of conflicts to resolve.
        direction: Sync direction (push or pull).
        dry_run: Whether this is a dry-run (preview only).
    """

    TITLE = "Kong Sync - Conflict Resolution"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("a", "apply", "Apply All", show=True),
        Binding("?", "help", "Help", show=True),
    ]

    def __init__(
        self,
        conflicts: list[Conflict],
        direction: Literal["push", "pull"],
        dry_run: bool = False,
    ) -> None:
        """Initialize the conflict resolution app.

        Args:
            conflicts: List of conflicts to resolve.
            direction: Sync direction for context labels.
            dry_run: If True, resolutions are for preview only.
        """
        super().__init__()
        self.conflicts = conflicts
        self.direction = direction
        self.dry_run = dry_run
        self.service = ConflictResolutionService()
        self._result: list[Resolution] = []

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - push the initial screen."""
        self.push_screen(
            ConflictListScreen(
                conflicts=self.conflicts,
                direction=self.direction,
                service=self.service,
            )
        )

    async def action_quit(self) -> None:
        """Quit without applying resolutions."""
        self._result = []
        self.exit([])

    async def action_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_apply(self) -> None:
        """Show summary screen before applying."""
        resolutions = self.service.get_all_resolutions()
        if resolutions:
            self.push_screen(
                SummaryScreen(
                    resolutions=resolutions,
                    direction=self.direction,
                    dry_run=self.dry_run,
                )
            )

    def action_help(self) -> None:
        """Show help overlay."""
        # TODO: Implement help screen in Phase 6
        self.notify("Help: j/k to navigate, Enter to select, a to apply, q to quit")

    @on(ConflictListScreen.ConflictSelected)
    def handle_conflict_selected(self, event: ConflictListScreen.ConflictSelected) -> None:
        """Handle conflict selection from list."""
        self.push_screen(
            ConflictDetailScreen(
                conflict=event.conflict,
                service=self.service,
            )
        )

    @on(ConflictDetailScreen.ResolutionMade)
    def handle_resolution_made(self, event: ConflictDetailScreen.ResolutionMade) -> None:
        """Handle resolution from detail screen."""
        self.service.set_resolution(event.resolution)
        self.pop_screen()
        self.notify(
            f"Resolved: {event.resolution.conflict.entity_name} -> {event.resolution.action.value}"
        )

    @on(SummaryScreen.ApplyConfirmed)
    def handle_apply_confirmed(self, event: SummaryScreen.ApplyConfirmed) -> None:
        """Handle confirmation from summary screen."""
        self._result = event.resolutions
        self.exit(event.resolutions)

    @on(SummaryScreen.ApplyCancelled)
    def handle_apply_cancelled(self, event: SummaryScreen.ApplyCancelled) -> None:
        """Handle cancellation from summary screen."""
        self.pop_screen()

    def run_and_get_resolutions(self) -> list[Resolution]:
        """Run the app and return resolutions.

        This is the main entry point for launching the TUI.

        Returns:
            List of resolutions made by the user, or empty list if cancelled.
        """
        result = self.run()
        return result if result else []
