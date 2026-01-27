"""Reusable TUI components.

This package provides widgets that can be used across multiple TUI
applications for consistent functionality.

Usage:
    from system_operations_manager.tui.components import Modal, DiffViewer

    # Create a confirmation modal
    modal = Modal(
        title="Confirm Action",
        body="Are you sure you want to proceed?",
        buttons=[("Confirm", "confirm", "success"), ("Cancel", "cancel", "default")],
    )

    # Create a diff viewer
    diff = DiffViewer(
        source_state={"key": "new"},
        target_state={"key": "old"},
    )
"""

from system_operations_manager.tui.components.diff_viewer import DiffViewer
from system_operations_manager.tui.components.modal import Modal

__all__ = [
    "DiffViewer",
    "Modal",
]
