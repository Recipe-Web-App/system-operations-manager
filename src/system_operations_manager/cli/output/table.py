"""Centralized table output for CLI commands.

This module provides a custom Table class that wraps Rich's Table
with sensible defaults for CLI output across the entire application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from rich.table import Table as RichTable

if TYPE_CHECKING:
    from rich.console import ConsoleRenderable, RichCast
    from rich.style import Style

OverflowMethod = Literal["fold", "crop", "ellipsis", "ignore"]
JustifyMethod = Literal["default", "left", "center", "right", "full"]
VerticalAlignMethod = Literal["top", "middle", "bottom"]


class Table(RichTable):
    """Rich Table with sensible defaults for CLI output.

    Extends Rich's Table to provide consistent styling across all CLI commands.
    Key difference: columns use overflow="fold" by default to wrap text
    instead of truncating.

    Usage:
        from system_operations_manager.cli.output import Table

        table = Table(title="My Table")
        table.add_column("Name")  # Will wrap long text by default
        table.add_column("ID", no_wrap=True)  # Override to disable wrapping
        table.add_row("example-name", "abc123")
    """

    def add_column(
        self,
        header: ConsoleRenderable | RichCast | str = "",
        footer: ConsoleRenderable | RichCast | str = "",
        *,
        header_style: Style | str | None = None,
        highlight: bool | None = None,
        footer_style: Style | str | None = None,
        style: Style | str | None = None,
        justify: JustifyMethod = "default",
        vertical: VerticalAlignMethod = "top",
        overflow: OverflowMethod = "fold",
        width: int | None = None,
        min_width: int | None = None,
        max_width: int | None = None,
        ratio: int | None = None,
        no_wrap: bool = False,
    ) -> None:
        """Add a column with overflow="fold" by default.

        Args:
            header: Column header text or renderable.
            footer: Column footer text or renderable.
            header_style: Style for the header.
            highlight: Enable syntax highlighting.
            footer_style: Style for the footer.
            style: Style for the column cells.
            justify: How to justify cell contents.
            vertical: Vertical alignment of cell contents.
            overflow: How to handle text overflow. Defaults to "fold" (wrap text).
            width: Fixed column width.
            min_width: Minimum column width.
            max_width: Maximum column width.
            ratio: Ratio for flexible column sizing.
            no_wrap: Disable text wrapping.
        """
        super().add_column(
            header,
            footer,
            header_style=header_style,
            highlight=highlight,
            footer_style=footer_style,
            style=style,
            justify=justify,
            vertical=vertical,
            overflow=overflow,
            width=width,
            min_width=min_width,
            max_width=max_width,
            ratio=ratio,
            no_wrap=no_wrap,
        )
