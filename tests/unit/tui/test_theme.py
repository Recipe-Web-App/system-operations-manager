"""Unit tests for TUI theme module.

Tests the Colors constants and Styles helper methods.
"""

from __future__ import annotations

import pytest

from system_operations_manager.tui.theme import Colors, Styles


class TestColors:
    """Tests for Colors class constants."""

    @pytest.mark.unit
    def test_success_color(self) -> None:
        """SUCCESS color is defined."""
        assert Colors.SUCCESS == "$success"

    @pytest.mark.unit
    def test_warning_color(self) -> None:
        """WARNING color is defined."""
        assert Colors.WARNING == "$warning"

    @pytest.mark.unit
    def test_error_color(self) -> None:
        """ERROR color is defined."""
        assert Colors.ERROR == "$error"

    @pytest.mark.unit
    def test_primary_color(self) -> None:
        """PRIMARY color is defined."""
        assert Colors.PRIMARY == "$primary"

    @pytest.mark.unit
    def test_accent_color(self) -> None:
        """ACCENT color is defined."""
        assert Colors.ACCENT == "$accent"

    @pytest.mark.unit
    def test_text_muted_color(self) -> None:
        """TEXT_MUTED color is defined."""
        assert Colors.TEXT_MUTED == "$text-muted"

    @pytest.mark.unit
    def test_text_colors_defined(self) -> None:
        """TEXT color constants are defined."""
        assert Colors.TEXT == "$text"
        assert Colors.TEXT_DISABLED == "$text-disabled"

    @pytest.mark.unit
    def test_surface_colors_defined(self) -> None:
        """SURFACE color constants are defined."""
        assert Colors.SURFACE == "$surface"
        assert Colors.SURFACE_DARKEN == "$surface-darken-1"
        assert Colors.SURFACE_LIGHTEN == "$surface-lighten-1"

    @pytest.mark.unit
    def test_diff_add_color(self) -> None:
        """DIFF_ADD color is a hex value."""
        assert Colors.DIFF_ADD.startswith("#")
        assert Colors.DIFF_ADD == "#22c55e"

    @pytest.mark.unit
    def test_diff_remove_color(self) -> None:
        """DIFF_REMOVE color is a hex value."""
        assert Colors.DIFF_REMOVE.startswith("#")
        assert Colors.DIFF_REMOVE == "#ef4444"

    @pytest.mark.unit
    def test_diff_change_color(self) -> None:
        """DIFF_CHANGE color is a hex value."""
        assert Colors.DIFF_CHANGE.startswith("#")
        assert Colors.DIFF_CHANGE == "#eab308"

    @pytest.mark.unit
    def test_diff_context_color(self) -> None:
        """DIFF_CONTEXT color is a hex value."""
        assert Colors.DIFF_CONTEXT.startswith("#")

    @pytest.mark.unit
    def test_modal_colors_defined(self) -> None:
        """MODAL colors are defined."""
        assert Colors.MODAL_BACKGROUND == "rgba(0, 0, 0, 0.6)"
        assert Colors.MODAL_SURFACE == "$surface"


class TestStyles:
    """Tests for Styles class methods."""

    @pytest.mark.unit
    def test_success_wraps_text(self) -> None:
        """success() wraps text in green markup."""
        result = Styles.success("test")
        assert result == "[green]test[/green]"

    @pytest.mark.unit
    def test_success_with_empty_string(self) -> None:
        """success() handles empty string."""
        result = Styles.success("")
        assert result == "[green][/green]"

    @pytest.mark.unit
    def test_error_wraps_text(self) -> None:
        """error() wraps text in red markup."""
        result = Styles.error("test")
        assert result == "[red]test[/red]"

    @pytest.mark.unit
    def test_warning_wraps_text(self) -> None:
        """warning() wraps text in yellow markup."""
        result = Styles.warning("test")
        assert result == "[yellow]test[/yellow]"

    @pytest.mark.unit
    def test_muted_wraps_text(self) -> None:
        """muted() wraps text in dim markup."""
        result = Styles.muted("test")
        assert result == "[dim]test[/dim]"

    @pytest.mark.unit
    def test_bold_wraps_text(self) -> None:
        """bold() wraps text in bold markup."""
        result = Styles.bold("test")
        assert result == "[bold]test[/bold]"

    @pytest.mark.unit
    def test_primary_wraps_text(self) -> None:
        """primary() wraps text in cyan markup."""
        result = Styles.primary("test")
        assert result == "[cyan]test[/cyan]"

    @pytest.mark.unit
    def test_highlight_wraps_text(self) -> None:
        """highlight() wraps text in reverse markup."""
        result = Styles.highlight("test")
        assert result == "[reverse]test[/reverse]"

    @pytest.mark.unit
    def test_style_can_nest(self) -> None:
        """Styles can be nested."""
        result = Styles.bold(Styles.error("important"))
        assert result == "[bold][red]important[/red][/bold]"

    @pytest.mark.unit
    def test_style_with_special_characters(self) -> None:
        """Styles handle special characters."""
        result = Styles.success("test [with] brackets")
        assert result == "[green]test [with] brackets[/green]"

    @pytest.mark.unit
    def test_styles_are_static_methods(self) -> None:
        """All style methods are static methods."""
        # Can call without instantiation
        assert Styles.success("x") == "[green]x[/green]"
        assert Styles.warning("x") == "[yellow]x[/yellow]"
        assert Styles.error("x") == "[red]x[/red]"
        assert Styles.muted("x") == "[dim]x[/dim]"
        assert Styles.bold("x") == "[bold]x[/bold]"
        assert Styles.primary("x") == "[cyan]x[/cyan]"
        assert Styles.highlight("x") == "[reverse]x[/reverse]"
