"""Base classes for TUI screens and widgets.

This module provides abstract base classes that establish common patterns
for all TUI components in System Operations Manager.

Usage:
    from system_operations_manager.tui import BaseScreen, BaseWidget

    class MyScreen(BaseScreen[None]):
        def compose(self) -> ComposeResult:
            yield Label("My Screen")

    class MyWidget(BaseWidget):
        DEFAULT_CSS = '''
        MyWidget { height: auto; }
        '''
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widget import Widget

if TYPE_CHECKING:
    from textual.notifications import SeverityLevel

T = TypeVar("T")


class BaseWidget(Widget):
    """Base class for custom TUI widgets.

    Provides common functionality:
    - Standard message posting pattern
    - Notification helpers
    - Logging integration

    Subclasses should define:
    - DEFAULT_CSS: Widget-specific styling
    - compose(): Widget layout
    - Custom Message subclasses for events
    """

    def post_event(self, message: Message) -> None:
        """Post a message event to the app.

        Convenience method that wraps post_message with logging.

        Args:
            message: The message to post.
        """
        self.post_message(message)

    def notify_user(
        self,
        message: str,
        severity: SeverityLevel = "information",
    ) -> None:
        """Show a notification to the user.

        Args:
            message: Notification text.
            severity: One of "information", "warning", "error".
        """
        self.app.notify(message, severity=severity)


class BaseScreen(Screen[T]):
    """Base class for TUI screens.

    Provides common functionality:
    - Standard navigation helpers
    - Consistent error handling
    - Message posting patterns

    Subclasses should define:
    - BINDINGS: Keyboard bindings
    - compose(): Screen layout
    - Custom Message subclasses for screen events

    Type Parameters:
        T: The type returned when the screen is dismissed.
    """

    def go_back(self) -> None:
        """Navigate back to the previous screen.

        Safely pops the current screen if there's a screen to return to.
        """
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()

    def notify_user(
        self,
        message: str,
        severity: SeverityLevel = "information",
    ) -> None:
        """Show a notification to the user.

        Args:
            message: Notification text.
            severity: One of "information", "warning", "error".
        """
        self.app.notify(message, severity=severity)

    def compose(self) -> ComposeResult:
        """Compose the screen layout. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement compose()")
