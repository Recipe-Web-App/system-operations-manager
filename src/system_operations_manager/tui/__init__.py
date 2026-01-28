"""Terminal User Interface components for System Operations Manager.

This package provides TUI applications built with Textual for
interactive workflows that benefit from rich terminal interfaces.

Usage:
    from system_operations_manager.tui import BaseScreen, BaseWidget, Colors, Styles
    from system_operations_manager.tui.components import Modal, DiffViewer
    from system_operations_manager.tui.apps.conflict_resolution import ConflictResolutionApp
"""

from system_operations_manager.tui.base import BaseScreen, BaseWidget
from system_operations_manager.tui.theme import Colors, Styles

__all__ = [
    "BaseScreen",
    "BaseWidget",
    "Colors",
    "Styles",
]
