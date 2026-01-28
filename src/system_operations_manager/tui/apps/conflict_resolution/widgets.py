"""App-specific widgets for conflict resolution TUI.

This module provides widgets specific to the conflict resolution app:
- ResolutionPicker: Allows user to choose a resolution action

For reusable widgets, see system_operations_manager.tui.components.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, RadioButton, RadioSet

from system_operations_manager.services.kong.conflict_resolver import (
    ResolutionAction,
)


class ResolutionPicker(Widget):
    """Widget for choosing a resolution action.

    Displays radio buttons for each resolution option with
    descriptions. Emits ResolutionChosen message when selected.
    """

    DEFAULT_CSS = """
    ResolutionPicker {
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-top: 1;
    }

    ResolutionPicker .picker-title {
        text-style: bold;
        margin-bottom: 1;
    }

    ResolutionPicker RadioSet {
        width: 100%;
    }
    """

    class ResolutionChosen(Message):
        """Message emitted when a resolution is chosen."""

        def __init__(self, action: ResolutionAction) -> None:
            self.action = action
            super().__init__()

    def __init__(
        self,
        source_label: str = "Source",
        target_label: str = "Target",
        **kwargs: Any,
    ) -> None:
        """Initialize the resolution picker.

        Args:
            source_label: Label for source option (e.g., "Gateway").
            target_label: Label for target option (e.g., "Konnect").
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self.source_label = source_label
        self.target_label = target_label

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label("Choose resolution:", classes="picker-title")
        yield RadioSet(
            RadioButton(
                f"[1] Keep {self.source_label} (sync to {self.target_label})",
                id="keep-source",
            ),
            RadioButton(
                f"[2] Keep {self.target_label} (no changes)",
                id="keep-target",
            ),
            RadioButton(
                "[3] Skip (leave unchanged)",
                id="skip",
            ),
            RadioButton(
                "[4] Merge (combine changes)",
                id="merge",
            ),
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio selection."""
        if event.pressed is None:
            return

        button_id = event.pressed.id
        action_map = {
            "keep-source": ResolutionAction.KEEP_SOURCE,
            "keep-target": ResolutionAction.KEEP_TARGET,
            "skip": ResolutionAction.SKIP,
            "merge": ResolutionAction.MERGE,
        }

        action = action_map.get(button_id or "")
        if action:
            self.post_message(self.ResolutionChosen(action))
