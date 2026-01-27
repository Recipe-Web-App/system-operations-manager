"""Diff viewer widget for comparing entity states.

This module provides a reusable diff viewer widget that can display
differences between two states in either side-by-side or unified format.

Usage:
    from system_operations_manager.tui.components import DiffViewer

    diff = DiffViewer(
        source_state={"name": "new-service", "host": "new.example.com"},
        target_state={"name": "new-service", "host": "old.example.com"},
        source_label="Gateway",
        target_label="Konnect",
        drift_fields=["host"],
    )
"""

from __future__ import annotations

from typing import Any, Literal

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

from system_operations_manager.services.kong.conflict_resolver import (
    generate_entity_diff,
    generate_side_by_side_diff,
)


class DiffViewer(Widget):
    """Widget for displaying diffs between source and target state.

    Supports both side-by-side and unified diff display modes,
    with toggle capability via keyboard or method call.
    """

    DEFAULT_CSS = """
    DiffViewer {
        height: auto;
        min-height: 10;
        max-height: 30;
        border: solid $accent;
        padding: 1;
    }

    DiffViewer .diff-header {
        text-style: bold;
        margin-bottom: 1;
    }

    DiffViewer .diff-line-add {
        color: $success;
    }

    DiffViewer .diff-line-remove {
        color: $error;
    }

    DiffViewer .diff-line-context {
        color: $text-muted;
    }

    DiffViewer .diff-column {
        width: 1fr;
        padding: 0 1;
    }

    DiffViewer .diff-marker {
        width: 3;
        text-align: center;
    }
    """

    mode: reactive[Literal["side_by_side", "unified"]] = reactive("side_by_side")

    def __init__(
        self,
        source_state: dict[str, Any],
        target_state: dict[str, Any],
        source_label: str = "Source",
        target_label: str = "Target",
        drift_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the diff viewer.

        Args:
            source_state: Entity state from source system.
            target_state: Entity state from target system.
            source_label: Label for source column (e.g., "Gateway").
            target_label: Label for target column (e.g., "Konnect").
            drift_fields: Fields that differ (for highlighting).
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self.source_state = source_state
        self.target_state = target_state
        self.source_label = source_label
        self.target_label = target_label
        self.drift_fields = drift_fields or []

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield ScrollableContainer(
            Label(
                "[dim]Press 'd' to toggle diff mode[/dim]",
                classes="diff-header",
            ),
            Vertical(id="diff-content"),
        )

    def on_mount(self) -> None:
        """Render the diff on mount."""
        self._render_diff()

    def watch_mode(self) -> None:
        """React to mode changes."""
        self._render_diff()

    def toggle_mode(self) -> None:
        """Toggle between side-by-side and unified diff."""
        self.mode = "unified" if self.mode == "side_by_side" else "side_by_side"

    def _render_diff(self) -> None:
        """Render the diff content based on current mode."""
        content = self.query_one("#diff-content", Vertical)
        content.remove_children()

        if self.mode == "side_by_side":
            self._render_side_by_side(content)
        else:
            self._render_unified(content)

    def _render_side_by_side(self, container: Vertical) -> None:
        """Render side-by-side diff."""
        # Add headers
        container.mount(
            Horizontal(
                Label(f"[bold]{self.target_label}[/bold] (current)", classes="diff-column"),
                Label("", classes="diff-marker"),
                Label(f"[bold]{self.source_label}[/bold] (new)", classes="diff-column"),
            )
        )

        # Generate and render diff lines
        diff_lines = generate_side_by_side_diff(
            self.source_state,
            self.target_state,
            self.drift_fields,
        )

        for left, marker, right in diff_lines:
            # Determine styling based on marker
            if marker == "|":
                left_class = "diff-line-remove"
                right_class = "diff-line-add"
            elif marker == "<":
                left_class = "diff-line-remove"
                right_class = ""
            elif marker == ">":
                left_class = ""
                right_class = "diff-line-add"
            else:
                left_class = "diff-line-context"
                right_class = "diff-line-context"

            container.mount(
                Horizontal(
                    Static(left, classes=f"diff-column {left_class}"),
                    Static(marker, classes="diff-marker"),
                    Static(right, classes=f"diff-column {right_class}"),
                )
            )

    def _render_unified(self, container: Vertical) -> None:
        """Render unified diff."""
        diff_lines = generate_entity_diff(
            self.source_state,
            self.target_state,
            self.drift_fields,
        )

        for line in diff_lines:
            line = line.rstrip("\n")
            if line.startswith("+") and not line.startswith("+++"):
                style_class = "diff-line-add"
            elif line.startswith("-") and not line.startswith("---"):
                style_class = "diff-line-remove"
            elif line.startswith("@@"):
                style_class = ""  # Section header
            else:
                style_class = "diff-line-context"

            container.mount(Static(line, classes=style_class))
