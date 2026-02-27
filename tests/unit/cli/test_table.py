"""Tests for cli/output/table.py — covers missing TYPE_CHECKING imports (lines 14-15)."""

from __future__ import annotations

import pytest
from rich.console import Console
from rich.table import Column

from system_operations_manager.cli.output.table import Table


@pytest.mark.unit
class TestTableDefaults:
    """Tests that Table applies sensible defaults and delegates correctly to RichTable."""

    def test_table_is_instantiable(self) -> None:
        table = Table(title="Test Table")
        assert table is not None

    def test_add_column_uses_fold_overflow_by_default(self) -> None:
        """The custom add_column must default overflow to 'fold'."""
        table = Table()
        table.add_column("Name")
        col: Column = table.columns[0]
        assert col.overflow == "fold"

    def test_add_column_respects_explicit_overflow(self) -> None:
        """Caller can override the default overflow value."""
        table = Table()
        table.add_column("ID", overflow="ellipsis")
        assert table.columns[0].overflow == "ellipsis"

    def test_add_column_with_no_wrap_true(self) -> None:
        table = Table()
        table.add_column("Fixed", no_wrap=True)
        assert table.columns[0].no_wrap is True

    def test_add_column_with_style(self) -> None:
        table = Table()
        table.add_column("Styled", style="cyan")
        assert table.columns[0].style == "cyan"

    def test_add_column_with_justify(self) -> None:
        table = Table()
        table.add_column("Right", justify="right")
        assert table.columns[0].justify == "right"

    def test_add_column_with_width(self) -> None:
        table = Table()
        table.add_column("Wide", width=20)
        assert table.columns[0].width == 20

    def test_add_column_with_min_max_width(self) -> None:
        table = Table()
        table.add_column("Bounded", min_width=5, max_width=30)
        col = table.columns[0]
        assert col.min_width == 5
        assert col.max_width == 30

    def test_multiple_columns_added(self) -> None:
        table = Table(title="Multi")
        table.add_column("A")
        table.add_column("B")
        table.add_column("C")
        assert len(table.columns) == 3

    def test_table_renders_without_error(self) -> None:
        """Table can be rendered by a Rich Console without raising."""
        table = Table(title="Render Test")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("CLI", "OK")
        table.add_row("DB", "Degraded")

        console = Console(force_terminal=True, width=80)
        # Should not raise.
        with console.capture() as cap:
            console.print(table)
        output = cap.get()
        assert "CLI" in output
        assert "Render Test" in output

    def test_add_column_header_text(self) -> None:
        table = Table()
        table.add_column("My Header")
        assert table.columns[0].header == "My Header"

    def test_add_column_with_ratio(self) -> None:
        table = Table()
        table.add_column("Flexible", ratio=2)
        assert table.columns[0].ratio == 2

    def test_add_column_vertical_default(self) -> None:
        """Vertical alignment defaults to 'top'."""
        table = Table()
        table.add_column("Cell")
        assert table.columns[0].vertical == "top"

    def test_add_column_vertical_override(self) -> None:
        table = Table()
        table.add_column("Cell", vertical="middle")
        assert table.columns[0].vertical == "middle"


@pytest.mark.unit
class TestTableTypeCheckingImports:
    """Ensure the TYPE_CHECKING-gated imports (lines 14-15) are accessible at runtime.

    At runtime TYPE_CHECKING is False, so the imports on lines 14-15 are NOT
    executed.  We verify the type aliases defined after that block are still
    accessible, confirming the module loads cleanly.
    """

    def test_overflow_method_literal_accessible(self) -> None:
        # OverflowMethod is a Literal — its __args__ reflects valid values.
        import typing

        from system_operations_manager.cli.output.table import OverflowMethod

        args = typing.get_args(OverflowMethod)
        assert "fold" in args
        assert "crop" in args
        assert "ellipsis" in args
        assert "ignore" in args

    def test_justify_method_literal_accessible(self) -> None:
        import typing

        from system_operations_manager.cli.output.table import JustifyMethod

        args = typing.get_args(JustifyMethod)
        assert "left" in args
        assert "right" in args
        assert "center" in args

    def test_vertical_align_method_literal_accessible(self) -> None:
        import typing

        from system_operations_manager.cli.output.table import VerticalAlignMethod

        args = typing.get_args(VerticalAlignMethod)
        assert "top" in args
        assert "middle" in args
        assert "bottom" in args
