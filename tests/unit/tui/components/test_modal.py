"""Unit tests for Modal component.

Tests the reusable Modal dialog widget.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, Static

from system_operations_manager.tui.components.modal import ButtonVariant, Modal


class ModalTestApp(App[str | None]):
    """Test app for Modal component."""

    def __init__(self, modal: Modal) -> None:
        super().__init__()
        self.modal = modal
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Test App")

    def on_mount(self) -> None:
        """Push the modal on mount."""
        self.push_screen(self.modal, self._handle_result)

    def _handle_result(self, result: str | None) -> None:
        """Store the result and exit."""
        self.result = result
        self.exit(result)


# ============================================================================
# Initialization Tests
# ============================================================================


class TestModalInit:
    """Tests for Modal initialization."""

    @pytest.mark.unit
    def test_modal_with_minimal_params(self) -> None:
        """Modal can be created with just title and body."""
        modal = Modal(title="Test", body="Test body")
        assert modal._title == "Test"
        assert modal._body == "Test body"

    @pytest.mark.unit
    def test_modal_default_buttons(self) -> None:
        """Modal defaults to OK button if none provided."""
        modal = Modal(title="Test", body="Body")
        # Default is OK + Cancel (if show_cancel=True)
        assert len(modal._buttons) == 2
        assert modal._buttons[0][0] == "OK"
        assert modal._buttons[0][1] == "ok"

    @pytest.mark.unit
    def test_modal_custom_buttons(self) -> None:
        """Modal accepts custom buttons."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("Save", "save", "success"),
            ("Delete", "delete", "error"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons)
        # Includes custom buttons + auto-added cancel
        assert len(modal._buttons) == 3
        assert modal._buttons[0] == ("Save", "save", "success")
        assert modal._buttons[1] == ("Delete", "delete", "error")

    @pytest.mark.unit
    def test_modal_no_cancel_button(self) -> None:
        """Modal respects show_cancel=False."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("OK", "ok", "primary"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons, show_cancel=False)
        assert len(modal._buttons) == 1
        assert modal._buttons[0][1] == "ok"

    @pytest.mark.unit
    def test_modal_custom_cancel_label(self) -> None:
        """Modal uses custom cancel label."""
        modal = Modal(title="Test", body="Body", cancel_label="Dismiss")
        # Last button should be the cancel with custom label
        assert modal._buttons[-1][0] == "Dismiss"
        assert modal._buttons[-1][1] == "cancel"

    @pytest.mark.unit
    def test_modal_with_cancel_already_in_buttons(self) -> None:
        """Modal doesn't duplicate cancel if already present."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("Yes", "yes", "success"),
            ("Cancel", "cancel", "default"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons)
        # Should not add another cancel
        cancel_count = sum(1 for b in modal._buttons if b[1] == "cancel")
        assert cancel_count == 1

    @pytest.mark.unit
    def test_modal_with_widget_body(self) -> None:
        """Modal accepts a Widget as body."""
        body_widget = Static("Widget body")
        modal = Modal(title="Test", body=body_widget)
        assert modal._body is body_widget

    @pytest.mark.unit
    def test_modal_button_metadata_created(self) -> None:
        """Modal creates button metadata for retrieval."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("Save", "save", "success"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons, show_cancel=False)
        assert "modal-btn-save" in modal._button_metadata
        assert modal._button_metadata["modal-btn-save"] == ("save", "Save")


# ============================================================================
# Message Tests
# ============================================================================


class TestModalMessages:
    """Tests for Modal message classes."""

    @pytest.mark.unit
    def test_button_pressed_message(self) -> None:
        """ButtonPressed message stores button info."""
        msg = Modal.ButtonPressed("save", "Save")
        assert msg.button_id == "save"
        assert msg.button_label == "Save"

    @pytest.mark.unit
    def test_cancelled_message(self) -> None:
        """Cancelled message can be instantiated."""
        msg = Modal.Cancelled()
        assert msg is not None


# ============================================================================
# Async Tests
# ============================================================================


class TestModalAsync:
    """Async tests for Modal interaction."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_button_click_returns_id(self) -> None:
        """Clicking a button returns its ID."""
        modal = Modal(
            title="Confirm",
            body="Are you sure?",
            buttons=[("Yes", "yes", "success"), ("No", "no", "default")],
            show_cancel=False,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            # Wait for modal to be mounted
            await pilot.pause()
            # Find and click the Yes button on the active screen
            yes_button = app.screen.query_one("#modal-btn-yes", Button)
            await pilot.click(yes_button)

        assert app.result == "yes"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_escape_returns_none(self) -> None:
        """Pressing Escape cancels and returns None."""
        modal = Modal(title="Test", body="Test body")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.press("escape")

        assert app.result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_cancel_button_returns_none(self) -> None:
        """Clicking Cancel button returns None."""
        modal = Modal(title="Test", body="Test body")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            cancel_button = app.screen.query_one("#modal-btn-cancel", Button)
            await pilot.click(cancel_button)

        assert app.result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_displays_title(self) -> None:
        """Modal displays the title."""
        modal = Modal(title="My Title", body="Body text")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            title_label = app.screen.query_one(".modal-title", Label)
            # The title should be stored on the modal
            assert modal._title == "My Title"
            assert title_label is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_displays_string_body(self) -> None:
        """Modal displays string body as Static."""
        modal = Modal(title="Title", body="This is the body")
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            body_static = app.screen.query_one(".modal-body Static", Static)
            # Body is stored on the modal
            assert modal._body == "This is the body"
            assert body_static is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_keyboard_navigation_works(self) -> None:
        """Tab key can be pressed without error."""
        modal = Modal(
            title="Test",
            body="Body",
            buttons=[("A", "a", "default"), ("B", "b", "default")],
            show_cancel=False,
        )
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            # Verify both buttons exist
            first_btn = app.screen.query_one("#modal-btn-a", Button)
            second_btn = app.screen.query_one("#modal-btn-b", Button)
            assert first_btn is not None
            assert second_btn is not None

            # Tab navigation should work without error
            await pilot.press("tab")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_button_variants(self) -> None:
        """Modal buttons have correct variants."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("Primary", "primary", "primary"),
            ("Success", "success", "success"),
            ("Error", "error", "error"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons, show_cancel=False)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            primary_btn = app.screen.query_one("#modal-btn-primary", Button)
            success_btn = app.screen.query_one("#modal-btn-success", Button)
            error_btn = app.screen.query_one("#modal-btn-error", Button)

            assert primary_btn.variant == "primary"
            assert success_btn.variant == "success"
            assert error_btn.variant == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_renders_buttons(self) -> None:
        """Modal renders all buttons."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("OK", "ok", "primary"),
            ("Cancel", "cancel", "default"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons, show_cancel=False)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            all_buttons = app.screen.query("Button")
            assert len(all_buttons) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_modal_first_button_focused_on_mount(self) -> None:
        """First button is focused when modal opens."""
        buttons: list[tuple[str, str, ButtonVariant]] = [
            ("First", "first", "primary"),
            ("Second", "second", "default"),
        ]
        modal = Modal(title="Test", body="Body", buttons=buttons, show_cancel=False)
        app = ModalTestApp(modal)

        async with app.run_test() as pilot:
            await pilot.pause()
            first_btn = app.screen.query_one("#modal-btn-first", Button)
            assert first_btn.has_focus
