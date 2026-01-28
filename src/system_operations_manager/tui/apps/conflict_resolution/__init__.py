"""Conflict Resolution TUI for Kong Sync operations.

This module provides an interactive terminal interface for resolving
conflicts between Kong Gateway and Konnect control plane during sync
operations.

Usage:
    from system_operations_manager.tui.apps.conflict_resolution import ConflictResolutionApp

    app = ConflictResolutionApp(conflicts=conflicts, direction="push")
    resolutions = app.run_and_get_resolutions()
"""

from system_operations_manager.tui.apps.conflict_resolution.app import ConflictResolutionApp

__all__ = ["ConflictResolutionApp"]
