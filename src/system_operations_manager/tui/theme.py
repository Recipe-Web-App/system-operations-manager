"""Theme constants and style utilities for TUI components.

This module provides consistent theming across all TUI applications,
including color definitions and style helper functions.

Usage:
    from system_operations_manager.tui.theme import Colors, Styles

    # Use colors in DEFAULT_CSS
    DEFAULT_CSS = f'''
    .success {{ color: {Colors.SUCCESS}; }}
    '''

    # Use style helpers
    styled_text = Styles.success("Operation complete")
"""

from __future__ import annotations


class Colors:
    """Color constants for TUI theming.

    These map to Textual CSS variables where possible, but provide
    fallback hex values for use in markup.
    """

    # Semantic colors (Textual CSS variables)
    SUCCESS = "$success"
    WARNING = "$warning"
    ERROR = "$error"
    PRIMARY = "$primary"
    ACCENT = "$accent"

    # Text colors
    TEXT = "$text"
    TEXT_MUTED = "$text-muted"
    TEXT_DISABLED = "$text-disabled"

    # Surface colors
    SURFACE = "$surface"
    SURFACE_DARKEN = "$surface-darken-1"
    SURFACE_LIGHTEN = "$surface-lighten-1"

    # Diff colors (hex for Rich markup compatibility)
    DIFF_ADD = "#22c55e"  # Green for additions
    DIFF_REMOVE = "#ef4444"  # Red for removals
    DIFF_CHANGE = "#eab308"  # Yellow for changes
    DIFF_CONTEXT = "#6b7280"  # Gray for context lines

    # Modal colors
    MODAL_BACKGROUND = "rgba(0, 0, 0, 0.6)"
    MODAL_SURFACE = "$surface"


class Styles:
    """Style helper functions for Rich markup.

    These functions wrap text in Rich markup tags for consistent styling.
    """

    @staticmethod
    def success(text: str) -> str:
        """Style text as success (green)."""
        return f"[green]{text}[/green]"

    @staticmethod
    def warning(text: str) -> str:
        """Style text as warning (yellow)."""
        return f"[yellow]{text}[/yellow]"

    @staticmethod
    def error(text: str) -> str:
        """Style text as error (red)."""
        return f"[red]{text}[/red]"

    @staticmethod
    def muted(text: str) -> str:
        """Style text as muted (dim)."""
        return f"[dim]{text}[/dim]"

    @staticmethod
    def bold(text: str) -> str:
        """Style text as bold."""
        return f"[bold]{text}[/bold]"

    @staticmethod
    def primary(text: str) -> str:
        """Style text in primary color (cyan)."""
        return f"[cyan]{text}[/cyan]"

    @staticmethod
    def highlight(text: str) -> str:
        """Style text with highlight (reverse)."""
        return f"[reverse]{text}[/reverse]"
