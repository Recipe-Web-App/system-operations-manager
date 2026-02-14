"""Custom widgets for Kubernetes resource browser TUI.

Provides selector widgets for namespace, cluster context, and resource
type filtering. Each widget supports both quick-cycle (lowercase key)
and popup selection (uppercase key) modes. Also includes dashboard
widgets for resource utilization bars and auto-refresh timers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from system_operations_manager.tui.base import BaseWidget

if TYPE_CHECKING:
    from system_operations_manager.tui.apps.kubernetes.types import ResourceType

ALL_NAMESPACES_LABEL = "All Namespaces"


class SelectorPopup(ModalScreen[str | None]):
    """Modal popup for selecting from a list of options.

    Presents an OptionList overlay and returns the selected value
    or None if dismissed.
    """

    DEFAULT_CSS = """
    SelectorPopup {
        align: center middle;
    }

    SelectorPopup #popup-container {
        width: 50;
        max-height: 70%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    SelectorPopup #popup-title {
        text-style: bold;
        margin-bottom: 1;
    }

    SelectorPopup OptionList {
        height: auto;
        max-height: 20;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_popup", "Close"),
    ]

    def __init__(
        self,
        title: str,
        options: list[str],
        current: str | None = None,
    ) -> None:
        """Initialize the selector popup.

        Args:
            title: Title displayed above the option list.
            options: List of option strings to display.
            current: Currently selected option (highlighted).
        """
        super().__init__()
        self._title = title
        self._options = options
        self._current = current

    def compose(self) -> ComposeResult:
        """Compose the popup layout."""
        with Vertical(id="popup-container"):
            yield Label(self._title, id="popup-title")
            option_list = OptionList(
                *[Option(opt, id=opt) for opt in self._options],
                id="popup-options",
            )
            yield option_list

    def on_mount(self) -> None:
        """Highlight the current selection on mount."""
        if self._current and self._current in self._options:
            option_list = self.query_one("#popup-options", OptionList)
            idx = self._options.index(self._current)
            option_list.highlighted = idx

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        self.dismiss(str(event.option.prompt))

    def action_dismiss_popup(self) -> None:
        """Dismiss without selection."""
        self.dismiss(None)


class NamespaceSelector(BaseWidget):
    """Widget for selecting the active Kubernetes namespace.

    Supports two interaction modes:
    - Quick-cycle: press 'n' to cycle through namespaces
    - Popup selection: press 'N' to open a picker overlay

    Emits NamespaceChanged when the namespace changes.
    """

    DEFAULT_CSS = """
    NamespaceSelector {
        width: auto;
        height: 3;
        padding: 0 1;
        content-align: center middle;
    }

    NamespaceSelector .selector-label {
        color: $text-muted;
    }

    NamespaceSelector .selector-value {
        text-style: bold;
        color: $primary;
    }
    """

    class NamespaceChanged(Message):
        """Emitted when the selected namespace changes."""

        def __init__(self, selected_namespace: str | None) -> None:
            """Initialize with the new namespace.

            Args:
                selected_namespace: New namespace name, or None for all namespaces.
            """
            self.selected_namespace = selected_namespace
            super().__init__()

    def __init__(
        self,
        namespaces: list[str],
        current: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the namespace selector.

        Args:
            namespaces: Available namespace names.
            current: Currently active namespace (None = all).
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self._namespaces = namespaces
        self._current = current
        self._index = self._resolve_index()

    def _resolve_index(self) -> int:
        """Find the index of the current namespace in the list.

        Returns 0 (All Namespaces) if current is not found.
        """
        if self._current is None:
            return 0
        for i, ns in enumerate(self._namespaces):
            if ns == self._current:
                return i + 1  # offset by 1 for "All Namespaces" at index 0
        return 0

    @property
    def display_options(self) -> list[str]:
        """Full option list including 'All Namespaces'."""
        return [ALL_NAMESPACES_LABEL, *self._namespaces]

    @property
    def display_value(self) -> str:
        """Current display string."""
        if self._current is None:
            return ALL_NAMESPACES_LABEL
        return self._current

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label("NS:", classes="selector-label")
        yield Label(self.display_value, id="ns-value", classes="selector-value")

    def cycle(self) -> None:
        """Cycle to the next namespace."""
        options = self.display_options
        self._index = (self._index + 1) % len(options)
        selected = options[self._index]
        self._current = None if selected == ALL_NAMESPACES_LABEL else selected
        self.query_one("#ns-value", Label).update(self.display_value)
        self.post_message(self.NamespaceChanged(self._current))

    def select_from_popup(self) -> None:
        """Open popup for namespace selection."""
        popup = SelectorPopup(
            title="Select Namespace",
            options=self.display_options,
            current=self.display_value,
        )
        self.app.push_screen(popup, self._handle_popup_result)

    def _handle_popup_result(self, result: str | None) -> None:
        """Handle popup selection result."""
        if result is None:
            return
        if result == ALL_NAMESPACES_LABEL:
            self._current = None
        else:
            self._current = result
        self._index = self._resolve_index()
        self.query_one("#ns-value", Label).update(self.display_value)
        self.post_message(self.NamespaceChanged(self._current))

    def update_namespaces(self, namespaces: list[str]) -> None:
        """Update the available namespace list.

        Args:
            namespaces: New list of namespace names.
        """
        self._namespaces = namespaces
        self._index = self._resolve_index()


class ClusterSelector(BaseWidget):
    """Widget for selecting the active Kubernetes cluster context.

    Supports quick-cycle ('c') and popup selection ('C') modes.
    Emits ClusterChanged when the context changes.
    """

    DEFAULT_CSS = """
    ClusterSelector {
        width: auto;
        height: 3;
        padding: 0 1;
        content-align: center middle;
    }

    ClusterSelector .selector-label {
        color: $text-muted;
    }

    ClusterSelector .selector-value {
        text-style: bold;
        color: $accent;
    }
    """

    class ClusterChanged(Message):
        """Emitted when the selected cluster context changes."""

        def __init__(self, context: str) -> None:
            """Initialize with the new context name.

            Args:
                context: Kubernetes context name.
            """
            self.context = context
            super().__init__()

    def __init__(
        self,
        contexts: list[str],
        current: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize the cluster selector.

        Args:
            contexts: Available context names.
            current: Currently active context.
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self._contexts = contexts
        self._current = current
        self._index = 0
        for i, ctx in enumerate(self._contexts):
            if ctx == self._current:
                self._index = i
                break

    @property
    def display_value(self) -> str:
        """Current display string."""
        return self._current or "unknown"

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label("Ctx:", classes="selector-label")
        yield Label(self.display_value, id="ctx-value", classes="selector-value")

    def cycle(self) -> None:
        """Cycle to the next cluster context."""
        if not self._contexts:
            return
        self._index = (self._index + 1) % len(self._contexts)
        self._current = self._contexts[self._index]
        self.query_one("#ctx-value", Label).update(self.display_value)
        self.post_message(self.ClusterChanged(self._current))

    def select_from_popup(self) -> None:
        """Open popup for cluster selection."""
        popup = SelectorPopup(
            title="Select Cluster Context",
            options=self._contexts,
            current=self._current,
        )
        self.app.push_screen(popup, self._handle_popup_result)

    def _handle_popup_result(self, result: str | None) -> None:
        """Handle popup selection result."""
        if result is None:
            return
        self._current = result
        for i, ctx in enumerate(self._contexts):
            if ctx == self._current:
                self._index = i
                break
        self.query_one("#ctx-value", Label).update(self.display_value)
        self.post_message(self.ClusterChanged(self._current))


class ResourceTypeFilter(BaseWidget):
    """Widget for filtering by Kubernetes resource type.

    Supports quick-cycle ('f') and popup selection ('F') modes.
    Emits ResourceTypeChanged when the type changes.
    """

    DEFAULT_CSS = """
    ResourceTypeFilter {
        width: auto;
        height: 3;
        padding: 0 1;
        content-align: center middle;
    }

    ResourceTypeFilter .selector-label {
        color: $text-muted;
    }

    ResourceTypeFilter .selector-value {
        text-style: bold;
        color: $success;
    }
    """

    class ResourceTypeChanged(Message):
        """Emitted when the selected resource type changes."""

        def __init__(self, resource_type: ResourceType) -> None:
            """Initialize with the new resource type.

            Args:
                resource_type: Selected ResourceType enum member.
            """
            self.resource_type = resource_type
            super().__init__()

    def __init__(
        self,
        resource_types: list[ResourceType],
        current: ResourceType | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the resource type filter.

        Args:
            resource_types: Available resource types.
            current: Currently selected type (defaults to first).
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self._resource_types = resource_types
        self._current = current or resource_types[0]
        self._index = 0
        for i, rt in enumerate(self._resource_types):
            if rt == self._current:
                self._index = i
                break

    @property
    def display_value(self) -> str:
        """Current display string."""
        return self._current.value

    @property
    def current(self) -> ResourceType:
        """Currently selected resource type."""
        return self._current

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label("Type:", classes="selector-label")
        yield Label(self.display_value, id="type-value", classes="selector-value")

    def cycle(self) -> None:
        """Cycle to the next resource type."""
        self._index = (self._index + 1) % len(self._resource_types)
        self._current = self._resource_types[self._index]
        self.query_one("#type-value", Label).update(self.display_value)
        self.post_message(self.ResourceTypeChanged(self._current))

    def select_from_popup(self) -> None:
        """Open popup for resource type selection."""
        options = [rt.value for rt in self._resource_types]
        popup = SelectorPopup(
            title="Select Resource Type",
            options=options,
            current=self._current.value,
        )
        self.app.push_screen(popup, self._handle_popup_result)

    def _handle_popup_result(self, result: str | None) -> None:
        """Handle popup selection result."""
        if result is None:
            return
        for rt in self._resource_types:
            if rt.value == result:
                self._current = rt
                break
        for i, rt in enumerate(self._resource_types):
            if rt == self._current:
                self._index = i
                break
        self.query_one("#type-value", Label).update(self.display_value)
        self.post_message(self.ResourceTypeChanged(self._current))


class ResourceBar(BaseWidget):
    """Horizontal bar showing resource capacity and optional utilization.

    Renders a visual bar like: ``CPU [||||||||....] 4/8 cores``
    When actual usage is unknown: ``CPU [????????????] N/A / 8 cores``

    Color coding by utilization ratio:
    - Green: < 70%
    - Yellow: 70-90%
    - Red: >= 90%
    """

    DEFAULT_CSS = """
    ResourceBar {
        height: 1;
        width: 100%;
        padding: 0 2;
    }
    """

    def __init__(
        self,
        label: str,
        capacity: int | float,
        used: int | float | None = None,
        unit: str = "",
        bar_width: int = 20,
        **kwargs: Any,
    ) -> None:
        """Initialize the resource bar.

        Args:
            label: Resource label (e.g. "CPU", "Mem", "Pods").
            capacity: Total capacity value.
            used: Current usage, or None if unknown.
            unit: Unit suffix for display (e.g. " cores", " Gi").
            bar_width: Character width of the bar.
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self._label = label
        self._capacity = capacity
        self._used = used
        self._unit = unit
        self._bar_width = bar_width

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Horizontal(
            Label(f"{self._label:>6}  ", classes="bar-label"),
            Label(self._render_bar(), id=f"bar-{self._label.lower()}", classes="bar-value"),
        )

    def _render_bar(self) -> str:
        """Render the bar string with Rich markup colors.

        Returns:
            Formatted bar string with utilization display.
        """
        if self._used is None:
            bar = "?" * self._bar_width
            return f"[dim][{bar}][/dim]  N/A / {self._capacity}{self._unit}"

        ratio = self._used / self._capacity if self._capacity > 0 else 0
        filled = int(ratio * self._bar_width)
        empty = self._bar_width - filled

        if ratio >= 0.9:
            color = "red"
        elif ratio >= 0.7:
            color = "yellow"
        else:
            color = "green"

        filled_str = "\u2588" * filled
        empty_str = "\u2591" * empty
        bar = f"[{color}]{filled_str}[/{color}][dim]{empty_str}[/dim]"
        return f"{bar}  {self._used}/{self._capacity}{self._unit}"

    def update_values(self, capacity: int | float, used: int | float | None = None) -> None:
        """Update bar values and re-render.

        Args:
            capacity: New capacity value.
            used: New usage value, or None if unknown.
        """
        self._capacity = capacity
        self._used = used
        self.query_one(f"#bar-{self._label.lower()}", Label).update(self._render_bar())


REFRESH_DEFAULT_INTERVAL = 30
REFRESH_MIN_INTERVAL = 5
REFRESH_MAX_INTERVAL = 300
REFRESH_STEP = 5


class RefreshTimer(BaseWidget):
    """Auto-refresh countdown timer.

    Displays a countdown and emits ``RefreshTriggered`` when it reaches
    zero. The interval can be adjusted with ``increase_interval()``
    and ``decrease_interval()``.
    """

    DEFAULT_CSS = """
    RefreshTimer {
        width: auto;
        height: 1;
        padding: 0 1;
    }
    """

    class RefreshTriggered(Message):
        """Emitted when the auto-refresh timer fires."""

    class IntervalChanged(Message):
        """Emitted when the refresh interval is adjusted."""

        def __init__(self, interval: int) -> None:
            """Initialize with the new interval.

            Args:
                interval: New interval in seconds.
            """
            self.interval = interval
            super().__init__()

    def __init__(
        self,
        interval: int = REFRESH_DEFAULT_INTERVAL,
        **kwargs: Any,
    ) -> None:
        """Initialize the refresh timer.

        Args:
            interval: Refresh interval in seconds.
            **kwargs: Additional widget arguments.
        """
        super().__init__(**kwargs)
        self._interval = interval
        self._remaining = interval
        self._timer_handle: Timer | None = None
        self._paused = False

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label("Refresh: ", classes="timer-label")
        yield Label(f"{self._remaining}s", id="timer-value", classes="timer-value")

    def on_mount(self) -> None:
        """Start the countdown timer."""
        self._timer_handle = self.set_interval(1, self._tick)

    def _tick(self) -> None:
        """Handle each tick of the countdown."""
        if self._paused:
            return
        self._remaining -= 1
        self.query_one("#timer-value", Label).update(f"{self._remaining}s")
        if self._remaining <= 0:
            self._remaining = self._interval
            self.post_message(self.RefreshTriggered())

    def increase_interval(self) -> None:
        """Increase refresh interval by the step size."""
        self._interval = min(self._interval + REFRESH_STEP, REFRESH_MAX_INTERVAL)
        self._remaining = self._interval
        self._update_display()
        self.post_message(self.IntervalChanged(self._interval))

    def decrease_interval(self) -> None:
        """Decrease refresh interval by the step size."""
        self._interval = max(self._interval - REFRESH_STEP, REFRESH_MIN_INTERVAL)
        self._remaining = self._interval
        self._update_display()
        self.post_message(self.IntervalChanged(self._interval))

    def reset(self) -> None:
        """Reset countdown to full interval."""
        self._remaining = self._interval
        self._update_display()

    def pause(self) -> None:
        """Pause the countdown."""
        self._paused = True

    def resume(self) -> None:
        """Resume the countdown."""
        self._paused = False

    def _update_display(self) -> None:
        """Update the displayed countdown value."""
        self.query_one("#timer-value", Label).update(f"{self._remaining}s")
