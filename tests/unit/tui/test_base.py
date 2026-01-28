"""Unit tests for TUI base module.

Tests the BaseScreen and BaseWidget classes.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from system_operations_manager.tui.base import BaseScreen, BaseWidget

# ============================================================================
# Test Apps for async testing
# ============================================================================


class WidgetTestApp(App[None]):
    """App for testing BaseWidget subclass."""

    class SampleWidget(BaseWidget):
        """Concrete widget for testing."""

        def compose(self) -> ComposeResult:
            yield Label("Test Widget")

    def compose(self) -> ComposeResult:
        yield self.SampleWidget(id="test-widget")


class ScreenTestApp(App[None]):
    """App for testing BaseScreen."""

    class SampleScreen(BaseScreen[None]):
        """Concrete screen for testing."""

        def compose(self) -> ComposeResult:
            yield Label("Test Screen")

    class SecondScreen(BaseScreen[None]):
        """Second screen for testing navigation."""

        def compose(self) -> ComposeResult:
            yield Label("Second Screen")

    def compose(self) -> ComposeResult:
        yield Label("Main")

    def on_mount(self) -> None:
        """Push initial test screen."""
        self.push_screen(self.SampleScreen())


# ============================================================================
# Sync Tests - Class structure
# ============================================================================


class TestBaseWidgetStructure:
    """Tests for BaseWidget class structure."""

    @pytest.mark.unit
    def test_base_widget_inherits_from_widget(self) -> None:
        """BaseWidget inherits from Textual Widget."""
        from textual.widget import Widget

        assert issubclass(BaseWidget, Widget)

    @pytest.mark.unit
    def test_base_widget_has_post_event_method(self) -> None:
        """BaseWidget has post_event method."""
        assert hasattr(BaseWidget, "post_event")
        assert callable(BaseWidget.post_event)

    @pytest.mark.unit
    def test_base_widget_has_notify_user_method(self) -> None:
        """BaseWidget has notify_user method."""
        assert hasattr(BaseWidget, "notify_user")
        assert callable(BaseWidget.notify_user)


class TestBaseScreenStructure:
    """Tests for BaseScreen class structure."""

    @pytest.mark.unit
    def test_base_screen_inherits_from_screen(self) -> None:
        """BaseScreen inherits from Textual Screen."""
        from textual.screen import Screen

        assert issubclass(BaseScreen, Screen)

    @pytest.mark.unit
    def test_base_screen_has_go_back_method(self) -> None:
        """BaseScreen has go_back method."""
        assert hasattr(BaseScreen, "go_back")
        assert callable(BaseScreen.go_back)

    @pytest.mark.unit
    def test_base_screen_has_notify_user_method(self) -> None:
        """BaseScreen has notify_user method."""
        assert hasattr(BaseScreen, "notify_user")
        assert callable(BaseScreen.notify_user)

    @pytest.mark.unit
    def test_base_screen_generic_type(self) -> None:
        """BaseScreen supports generic type parameter."""
        # Test that we can create type hints with different parameters
        # This validates the TypeVar usage
        assert BaseScreen[str] is not None
        assert BaseScreen[int] is not None
        assert BaseScreen[None] is not None


# ============================================================================
# Async Tests - Functional behavior
# ============================================================================


class TestBaseWidgetAsync:
    """Async tests for BaseWidget functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_widget_notify_user_information(self) -> None:
        """notify_user() shows an information notification."""
        app = WidgetTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", WidgetTestApp.SampleWidget)
            widget.notify_user("Test message")
            # Notification is shown (no exception thrown)
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_widget_notify_user_warning(self) -> None:
        """notify_user() shows a warning notification."""
        app = WidgetTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", WidgetTestApp.SampleWidget)
            widget.notify_user("Warning message", severity="warning")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_widget_notify_user_error(self) -> None:
        """notify_user() shows an error notification."""
        app = WidgetTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", WidgetTestApp.SampleWidget)
            widget.notify_user("Error message", severity="error")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_widget_post_event(self) -> None:
        """post_event() posts a message to the app."""
        from textual.message import Message

        app = WidgetTestApp()

        class TestMessage(Message):
            pass

        async with app.run_test():
            widget = app.query_one("#test-widget", WidgetTestApp.SampleWidget)
            # post_event is a convenience wrapper that calls post_message
            # If no exception is raised, the message was posted successfully
            widget.post_event(TestMessage())


class TestBaseScreenAsync:
    """Async tests for BaseScreen functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_go_back_pops_to_previous(self) -> None:
        """go_back() pops to previous screen when stack has multiple."""
        app = ScreenTestApp()

        async with app.run_test():
            screen = app.screen
            assert isinstance(screen, ScreenTestApp.SampleScreen)
            # ScreenTestApp pushes TestScreen on mount, so we have 2 screens
            initial_stack_size = len(app.screen_stack)
            assert initial_stack_size == 2  # default + TestScreen
            screen.go_back()
            # Should pop back to default screen
            assert len(app.screen_stack) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_go_back_pops_pushed_screen(self) -> None:
        """go_back() pops a pushed screen."""
        app = ScreenTestApp()

        async with app.run_test():
            # Push another screen on top of TestScreen
            app.push_screen(ScreenTestApp.SecondScreen())
            # Stack is: default + TestScreen (from on_mount) + SecondScreen
            assert len(app.screen_stack) == 3

            # Go back should pop the SecondScreen
            screen = app.screen
            assert isinstance(screen, ScreenTestApp.SecondScreen)
            screen.go_back()
            # Now back to TestScreen
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, ScreenTestApp.SampleScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_notify_user_information(self) -> None:
        """notify_user() shows notification from screen."""
        app = ScreenTestApp()

        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, ScreenTestApp.SampleScreen)
            screen.notify_user("Test notification")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_screen_notify_user_error(self) -> None:
        """notify_user() shows error notification."""
        app = ScreenTestApp()

        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, ScreenTestApp.SampleScreen)
            screen.notify_user("Error!", severity="error")
            await pilot.pause()
