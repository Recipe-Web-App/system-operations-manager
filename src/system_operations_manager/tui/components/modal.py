"""Reusable modal component for TUI applications.

This module provides a Modal widget that can be used for confirmations,
action selection, and other overlay dialogs.

Usage:
    from system_operations_manager.tui.components import Modal

    # Simple confirmation
    modal = Modal(
        title="Confirm Delete",
        body="Are you sure you want to delete this item?",
        buttons=[
            ("Delete", "delete", "error"),
            ("Cancel", "cancel", "default"),
        ],
    )

    # Handle modal results via callback
    def handle_result(result: str | None) -> None:
        if result == "delete":
            do_delete()

    app.push_screen(modal, handle_result)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from textual.widget import Widget

ButtonVariant = Literal["default", "primary", "success", "warning", "error"]


class Modal(ModalScreen[str | None]):
    """A centered modal dialog with customizable content and buttons.

    The modal dims the background and presents a dialog box with:
    - A title
    - Body content (string or widget)
    - Action buttons with keyboard navigation

    Keyboard Navigation:
    - Tab: Move between buttons
    - Enter: Activate focused button
    - Escape: Cancel (closes modal with None result)

    Attributes:
        title: Modal title displayed at the top.
        body: Content to display (string or Widget).
        buttons: List of (label, id, variant) tuples for buttons.
    """

    DEFAULT_CSS = """
    Modal {
        align: center middle;
    }

    Modal > Container {
        width: auto;
        max-width: 80%;
        min-width: 40;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    Modal .modal-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        color: $text;
    }

    Modal .modal-body {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 1;
    }

    Modal .modal-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Modal .modal-buttons Button {
        margin: 0 1;
        min-width: 10;
    }

    Modal .modal-buttons Button:focus {
        text-style: bold reverse;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Previous", show=False),
    ]

    class ButtonPressed(Message):
        """Message emitted when a modal button is pressed.

        Attributes:
            button_id: The ID of the pressed button.
            button_label: The label text of the pressed button.
        """

        def __init__(self, button_id: str, button_label: str) -> None:
            self.button_id = button_id
            self.button_label = button_label
            super().__init__()

    class Cancelled(Message):
        """Message emitted when the modal is cancelled via Escape."""

        pass

    def __init__(
        self,
        title: str,
        body: str | Widget,
        buttons: list[tuple[str, str, ButtonVariant]] | None = None,
        *,
        show_cancel: bool = True,
        cancel_label: str = "Cancel",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the modal dialog.

        Args:
            title: Title displayed at the top of the modal.
            body: Content to display. Can be a string (rendered as Static)
                or a custom Widget.
            buttons: List of button definitions as (label, id, variant) tuples.
                Variant is one of: "default", "primary", "success", "warning", "error".
                If None, defaults to [("OK", "ok", "primary")].
            show_cancel: If True and no cancel button in buttons, adds one.
            cancel_label: Label for the auto-added cancel button.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._title = title
        self._body = body
        self._show_cancel = show_cancel
        self._cancel_label = cancel_label

        # Default buttons if none provided
        if buttons is None:
            buttons = [("OK", "ok", "primary")]

        # Add cancel button if requested and not already present
        button_ids = {b[1] for b in buttons}
        if show_cancel and "cancel" not in button_ids:
            buttons = [*buttons, (cancel_label, "cancel", "default")]

        self._buttons = buttons
        # Store button metadata for retrieval in on_button_pressed
        self._button_metadata: dict[str, tuple[str, str]] = {
            f"modal-btn-{bid}": (bid, lbl) for lbl, bid, _ in buttons
        }

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Container():
            yield Label(self._title, classes="modal-title")

            with Vertical(classes="modal-body"):
                if isinstance(self._body, str):
                    yield Static(self._body)
                else:
                    yield self._body

            with Horizontal(classes="modal-buttons"):
                for i, (label, button_id, variant) in enumerate(self._buttons):
                    yield Button(
                        label,
                        id=f"modal-btn-{button_id}",
                        variant=variant,
                        classes=f"modal-button modal-button-{i}",
                    )

    def on_mount(self) -> None:
        """Focus the first button when mounted."""
        buttons = self.query("Button")
        if buttons:
            buttons.first().focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button = event.button
        widget_id = button.id or "unknown"
        button_id, button_label = self._button_metadata.get(
            widget_id, (widget_id, str(button.label))
        )

        # Post the ButtonPressed message
        self.post_message(self.ButtonPressed(button_id, button_label))

        # If it's the cancel button, also post Cancelled
        if button_id == "cancel":
            self.post_message(self.Cancelled())
            self.dismiss(None)
        else:
            self.dismiss(button_id)

    def action_cancel(self) -> None:
        """Handle escape key - cancel the modal."""
        self.post_message(self.Cancelled())
        self.dismiss(None)
