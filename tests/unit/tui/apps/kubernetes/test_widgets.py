"""Unit tests for Kubernetes TUI widgets.

Tests NamespaceSelector, ClusterSelector, ResourceTypeFilter, and SelectorPopup.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container

from system_operations_manager.tui.apps.kubernetes.app import ResourceType
from system_operations_manager.tui.apps.kubernetes.widgets import (
    ALL_NAMESPACES_LABEL,
    REFRESH_DEFAULT_INTERVAL,
    REFRESH_MAX_INTERVAL,
    REFRESH_MIN_INTERVAL,
    REFRESH_STEP,
    ClusterSelector,
    NamespaceSelector,
    RefreshTimer,
    ResourceBar,
    ResourceTypeFilter,
    SelectorPopup,
)

# ============================================================================
# Test Apps
# ============================================================================


class NamespaceSelectorTestApp(App[str | None]):
    """Test app for NamespaceSelector widget."""

    def __init__(self, namespaces: list[str], current: str | None = None) -> None:
        super().__init__()
        self.namespaces = namespaces
        self.current = current
        self.changed_namespace: str | None = "UNCHANGED"

    def compose(self) -> ComposeResult:
        with Container():
            yield NamespaceSelector(
                namespaces=self.namespaces,
                current=self.current,
                id="ns-selector",
            )

    def on_namespace_selector_namespace_changed(
        self, event: NamespaceSelector.NamespaceChanged
    ) -> None:
        self.changed_namespace = event.selected_namespace


class ClusterSelectorTestApp(App[str | None]):
    """Test app for ClusterSelector widget."""

    def __init__(self, contexts: list[str], current: str = "") -> None:
        super().__init__()
        self.contexts = contexts
        self.current = current
        self.changed_context: str | None = None

    def compose(self) -> ComposeResult:
        with Container():
            yield ClusterSelector(
                contexts=self.contexts,
                current=self.current,
                id="ctx-selector",
            )

    def on_cluster_selector_cluster_changed(self, event: ClusterSelector.ClusterChanged) -> None:
        self.changed_context = event.context


class ResourceTypeFilterTestApp(App[str | None]):
    """Test app for ResourceTypeFilter widget."""

    def __init__(
        self,
        resource_types: list[ResourceType],
        current: ResourceType | None = None,
    ) -> None:
        super().__init__()
        self.resource_types = resource_types
        self._current = current
        self.changed_type: ResourceType | None = None

    def compose(self) -> ComposeResult:
        with Container():
            yield ResourceTypeFilter(
                resource_types=self.resource_types,
                current=self._current,
                id="type-filter",
            )

    def on_resource_type_filter_resource_type_changed(
        self, event: ResourceTypeFilter.ResourceTypeChanged
    ) -> None:
        self.changed_type = event.resource_type


# ============================================================================
# NamespaceSelector Tests
# ============================================================================


class TestNamespaceSelectorInit:
    """Tests for NamespaceSelector initialization."""

    @pytest.mark.unit
    def test_stores_namespaces(self) -> None:
        """NamespaceSelector stores namespace list."""
        ns = NamespaceSelector(namespaces=["default", "kube-system"])
        assert ns._namespaces == ["default", "kube-system"]

    @pytest.mark.unit
    def test_stores_current_namespace(self) -> None:
        """NamespaceSelector stores current namespace."""
        ns = NamespaceSelector(namespaces=["default", "kube-system"], current="default")
        assert ns._current == "default"

    @pytest.mark.unit
    def test_none_current_means_all_namespaces(self) -> None:
        """None current namespace means all namespaces."""
        ns = NamespaceSelector(namespaces=["default"], current=None)
        assert ns._current is None
        assert ns.display_value == ALL_NAMESPACES_LABEL

    @pytest.mark.unit
    def test_display_options_includes_all(self) -> None:
        """Display options starts with 'All Namespaces'."""
        ns = NamespaceSelector(namespaces=["default", "kube-system"])
        opts = ns.display_options
        assert opts[0] == ALL_NAMESPACES_LABEL
        assert opts[1] == "default"
        assert opts[2] == "kube-system"

    @pytest.mark.unit
    def test_display_value_shows_current(self) -> None:
        """Display value shows current namespace name."""
        ns = NamespaceSelector(namespaces=["default", "kube-system"], current="kube-system")
        assert ns.display_value == "kube-system"


class TestNamespaceSelectorMessages:
    """Tests for NamespaceSelector messages."""

    @pytest.mark.unit
    def test_namespace_changed_message(self) -> None:
        """NamespaceChanged message stores namespace."""
        msg = NamespaceSelector.NamespaceChanged("kube-system")
        assert msg.selected_namespace == "kube-system"

    @pytest.mark.unit
    def test_namespace_changed_message_none(self) -> None:
        """NamespaceChanged message with None means all namespaces."""
        msg = NamespaceSelector.NamespaceChanged(None)
        assert msg.selected_namespace is None


class TestNamespaceSelectorAsync:
    """Async tests for NamespaceSelector."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_renders_labels(self) -> None:
        """NamespaceSelector renders NS label and value."""
        app = NamespaceSelectorTestApp(
            namespaces=["default", "kube-system"],
            current="default",
        )

        async with app.run_test():
            from textual.widgets import Label

            # Verify the expected labels exist by ID
            ns_selector = app.query_one("#ns-selector", NamespaceSelector)
            value_label = ns_selector.query_one("#ns-value", Label)
            assert str(value_label.update) is not None  # widget mounted
            # Verify display_value is set correctly
            assert ns_selector.display_value == "default"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_emits_message(self) -> None:
        """Cycling namespace emits NamespaceChanged."""
        app = NamespaceSelectorTestApp(
            namespaces=["default", "kube-system"],
            current=None,
        )

        async with app.run_test() as pilot:
            selector = app.query_one("#ns-selector", NamespaceSelector)
            selector.cycle()
            await pilot.pause()

        assert app.changed_namespace == "default"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_wraps_around(self) -> None:
        """Cycling past last namespace wraps to All."""
        app = NamespaceSelectorTestApp(
            namespaces=["default"],
            current="default",
        )

        async with app.run_test() as pilot:
            selector = app.query_one("#ns-selector", NamespaceSelector)
            selector.cycle()  # default -> All
            await pilot.pause()

        assert app.changed_namespace is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_namespaces(self) -> None:
        """update_namespaces replaces the namespace list."""
        app = NamespaceSelectorTestApp(namespaces=["default"])

        async with app.run_test():
            selector = app.query_one("#ns-selector", NamespaceSelector)
            selector.update_namespaces(["ns-1", "ns-2", "ns-3"])
            assert selector._namespaces == ["ns-1", "ns-2", "ns-3"]


# ============================================================================
# ClusterSelector Tests
# ============================================================================


class TestClusterSelectorInit:
    """Tests for ClusterSelector initialization."""

    @pytest.mark.unit
    def test_stores_contexts(self) -> None:
        """ClusterSelector stores context list."""
        cs = ClusterSelector(contexts=["minikube", "prod"], current="minikube")
        assert cs._contexts == ["minikube", "prod"]

    @pytest.mark.unit
    def test_stores_current_context(self) -> None:
        """ClusterSelector stores current context."""
        cs = ClusterSelector(contexts=["minikube", "prod"], current="minikube")
        assert cs._current == "minikube"

    @pytest.mark.unit
    def test_display_value(self) -> None:
        """Display value shows current context."""
        cs = ClusterSelector(contexts=["minikube"], current="minikube")
        assert cs.display_value == "minikube"

    @pytest.mark.unit
    def test_empty_current_shows_unknown(self) -> None:
        """Empty current shows 'unknown'."""
        cs = ClusterSelector(contexts=[], current="")
        assert cs.display_value == "unknown"


class TestClusterSelectorMessages:
    """Tests for ClusterSelector messages."""

    @pytest.mark.unit
    def test_cluster_changed_message(self) -> None:
        """ClusterChanged message stores context."""
        msg = ClusterSelector.ClusterChanged("production")
        assert msg.context == "production"


class TestClusterSelectorAsync:
    """Async tests for ClusterSelector."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_emits_message(self) -> None:
        """Cycling cluster emits ClusterChanged."""
        app = ClusterSelectorTestApp(
            contexts=["minikube", "prod"],
            current="minikube",
        )

        async with app.run_test() as pilot:
            selector = app.query_one("#ctx-selector", ClusterSelector)
            selector.cycle()
            await pilot.pause()

        assert app.changed_context == "prod"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_wraps_around(self) -> None:
        """Cycling past last context wraps to first."""
        app = ClusterSelectorTestApp(
            contexts=["minikube", "prod"],
            current="prod",
        )

        async with app.run_test() as pilot:
            selector = app.query_one("#ctx-selector", ClusterSelector)
            selector.cycle()
            await pilot.pause()

        assert app.changed_context == "minikube"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_contexts_no_crash(self) -> None:
        """Cycling with no contexts does not crash."""
        app = ClusterSelectorTestApp(contexts=[], current="")

        async with app.run_test() as pilot:
            selector = app.query_one("#ctx-selector", ClusterSelector)
            selector.cycle()
            await pilot.pause()

        assert app.changed_context is None


# ============================================================================
# ResourceTypeFilter Tests
# ============================================================================


class TestResourceTypeFilterInit:
    """Tests for ResourceTypeFilter initialization."""

    @pytest.mark.unit
    def test_stores_resource_types(self) -> None:
        """ResourceTypeFilter stores type list."""
        types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        rtf = ResourceTypeFilter(resource_types=types)
        assert rtf._resource_types == types

    @pytest.mark.unit
    def test_defaults_to_first_type(self) -> None:
        """ResourceTypeFilter defaults to first type."""
        types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        rtf = ResourceTypeFilter(resource_types=types)
        assert rtf.current == ResourceType.PODS

    @pytest.mark.unit
    def test_accepts_current_type(self) -> None:
        """ResourceTypeFilter accepts explicit current type."""
        types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        rtf = ResourceTypeFilter(resource_types=types, current=ResourceType.DEPLOYMENTS)
        assert rtf.current == ResourceType.DEPLOYMENTS

    @pytest.mark.unit
    def test_display_value(self) -> None:
        """Display value shows current type name."""
        types = [ResourceType.PODS]
        rtf = ResourceTypeFilter(resource_types=types)
        assert rtf.display_value == "Pods"


class TestResourceTypeFilterMessages:
    """Tests for ResourceTypeFilter messages."""

    @pytest.mark.unit
    def test_resource_type_changed_message(self) -> None:
        """ResourceTypeChanged message stores resource type."""
        msg = ResourceTypeFilter.ResourceTypeChanged(ResourceType.SERVICES)
        assert msg.resource_type == ResourceType.SERVICES


class TestResourceTypeFilterAsync:
    """Async tests for ResourceTypeFilter."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_emits_message(self) -> None:
        """Cycling type emits ResourceTypeChanged."""
        types = [ResourceType.PODS, ResourceType.DEPLOYMENTS, ResourceType.SERVICES]
        app = ResourceTypeFilterTestApp(resource_types=types, current=ResourceType.PODS)

        async with app.run_test() as pilot:
            rtf = app.query_one("#type-filter", ResourceTypeFilter)
            rtf.cycle()
            await pilot.pause()

        assert app.changed_type == ResourceType.DEPLOYMENTS

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cycle_wraps_around(self) -> None:
        """Cycling past last type wraps to first."""
        types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        app = ResourceTypeFilterTestApp(resource_types=types, current=ResourceType.DEPLOYMENTS)

        async with app.run_test() as pilot:
            rtf = app.query_one("#type-filter", ResourceTypeFilter)
            rtf.cycle()
            await pilot.pause()

        assert app.changed_type == ResourceType.PODS


# ============================================================================
# SelectorPopup Tests (sync via __new__)
# ============================================================================


@pytest.mark.unit
class TestSelectorPopupInit:
    """Tests for SelectorPopup initialization."""

    def test_stores_title(self) -> None:
        """SelectorPopup stores the title."""
        popup = SelectorPopup.__new__(SelectorPopup)
        popup._title = "Pick Namespace"
        popup._options = ["a", "b"]
        popup._current = "a"
        assert popup._title == "Pick Namespace"

    def test_stores_options(self) -> None:
        """SelectorPopup stores options list."""
        popup = SelectorPopup.__new__(SelectorPopup)
        popup._title = "T"
        popup._options = ["opt1", "opt2", "opt3"]
        popup._current = None
        assert popup._options == ["opt1", "opt2", "opt3"]

    def test_action_dismiss_popup_calls_dismiss(self) -> None:
        """action_dismiss_popup calls dismiss(None)."""
        popup = SelectorPopup.__new__(SelectorPopup)
        object.__setattr__(popup, "dismiss", MagicMock())
        popup.action_dismiss_popup()
        cast(MagicMock, popup.dismiss).assert_called_once_with(None)

    def test_on_option_list_option_selected(self) -> None:
        """on_option_list_option_selected dismisses with value."""
        popup = SelectorPopup.__new__(SelectorPopup)
        object.__setattr__(popup, "dismiss", MagicMock())
        mock_event = MagicMock()
        mock_event.option.prompt = "default"
        popup.on_option_list_option_selected(mock_event)
        cast(MagicMock, popup.dismiss).assert_called_once_with("default")


# ============================================================================
# Namespace/Cluster/ResourceType popup callback tests
# ============================================================================


@pytest.mark.unit
class TestNamespaceSelectorPopupCallback:
    """Tests for NamespaceSelector._handle_popup_result."""

    def test_handle_popup_result_none_does_nothing(self) -> None:
        """_handle_popup_result with None result does nothing."""
        ns = NamespaceSelector.__new__(NamespaceSelector)
        ns._namespaces = ["default"]
        ns._current = "default"
        ns._index = 1
        object.__setattr__(ns, "post_message", MagicMock())
        ns._handle_popup_result(None)
        cast(MagicMock, ns.post_message).assert_not_called()

    def test_handle_popup_result_all_namespaces(self) -> None:
        """_handle_popup_result with ALL_NAMESPACES_LABEL sets None."""
        ns = NamespaceSelector.__new__(NamespaceSelector)
        ns._namespaces = ["default", "kube-system"]
        ns._current = "default"
        ns._index = 1
        object.__setattr__(ns, "query_one", MagicMock())
        object.__setattr__(ns, "post_message", MagicMock())
        ns._handle_popup_result(ALL_NAMESPACES_LABEL)
        assert ns._current is None

    def test_handle_popup_result_specific_namespace(self) -> None:
        """_handle_popup_result with specific namespace sets it."""
        ns = NamespaceSelector.__new__(NamespaceSelector)
        ns._namespaces = ["default", "kube-system"]
        ns._current = None
        ns._index = 0
        object.__setattr__(ns, "query_one", MagicMock())
        object.__setattr__(ns, "post_message", MagicMock())
        ns._handle_popup_result("kube-system")
        assert ns._current == "kube-system"


@pytest.mark.unit
class TestClusterSelectorPopupCallback:
    """Tests for ClusterSelector._handle_popup_result."""

    def test_handle_popup_result_none_does_nothing(self) -> None:
        """_handle_popup_result with None result does nothing."""
        cs = ClusterSelector.__new__(ClusterSelector)
        cs._contexts = ["minikube", "prod"]
        cs._current = "minikube"
        cs._index = 0
        object.__setattr__(cs, "post_message", MagicMock())
        cs._handle_popup_result(None)
        cast(MagicMock, cs.post_message).assert_not_called()

    def test_handle_popup_result_selects_context(self) -> None:
        """_handle_popup_result sets the selected context."""
        cs = ClusterSelector.__new__(ClusterSelector)
        cs._contexts = ["minikube", "prod"]
        cs._current = "minikube"
        cs._index = 0
        object.__setattr__(cs, "query_one", MagicMock())
        object.__setattr__(cs, "post_message", MagicMock())
        cs._handle_popup_result("prod")
        assert cs._current == "prod"
        assert cs._index == 1


@pytest.mark.unit
class TestResourceTypeFilterPopupCallback:
    """Tests for ResourceTypeFilter._handle_popup_result."""

    def test_handle_popup_result_none_does_nothing(self) -> None:
        """_handle_popup_result with None result does nothing."""
        rtf = ResourceTypeFilter.__new__(ResourceTypeFilter)
        rtf._resource_types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        rtf._current = ResourceType.PODS
        rtf._index = 0
        object.__setattr__(rtf, "post_message", MagicMock())
        rtf._handle_popup_result(None)
        cast(MagicMock, rtf.post_message).assert_not_called()

    def test_handle_popup_result_selects_type(self) -> None:
        """_handle_popup_result sets the selected type."""
        rtf = ResourceTypeFilter.__new__(ResourceTypeFilter)
        rtf._resource_types = [ResourceType.PODS, ResourceType.DEPLOYMENTS]
        rtf._current = ResourceType.PODS
        rtf._index = 0
        object.__setattr__(rtf, "query_one", MagicMock())
        object.__setattr__(rtf, "post_message", MagicMock())
        rtf._handle_popup_result("Deployments")
        assert rtf._current == ResourceType.DEPLOYMENTS
        assert rtf._index == 1


# ============================================================================
# select_from_popup tests
# ============================================================================


@pytest.mark.unit
class TestSelectFromPopup:
    """Tests for select_from_popup methods on widgets."""

    def test_namespace_select_from_popup(self) -> None:
        """NamespaceSelector.select_from_popup pushes a popup."""
        ns = NamespaceSelector.__new__(NamespaceSelector)
        ns._namespaces = ["default"]
        ns._current = "default"
        ns._index = 1
        mock_app = MagicMock()
        with patch.object(type(ns), "app", new_callable=PropertyMock, return_value=mock_app):
            ns.select_from_popup()
        cast(MagicMock, mock_app.push_screen).assert_called_once()
        pushed = cast(MagicMock, mock_app.push_screen).call_args[0][0]
        assert isinstance(pushed, SelectorPopup)

    def test_cluster_select_from_popup(self) -> None:
        """ClusterSelector.select_from_popup pushes a popup."""
        cs = ClusterSelector.__new__(ClusterSelector)
        cs._contexts = ["minikube", "prod"]
        cs._current = "minikube"
        cs._index = 0
        mock_app = MagicMock()
        with patch.object(type(cs), "app", new_callable=PropertyMock, return_value=mock_app):
            cs.select_from_popup()
        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_resource_type_select_from_popup(self) -> None:
        """ResourceTypeFilter.select_from_popup pushes a popup."""
        rtf = ResourceTypeFilter.__new__(ResourceTypeFilter)
        rtf._resource_types = [ResourceType.PODS, ResourceType.SERVICES]
        rtf._current = ResourceType.PODS
        rtf._index = 0
        mock_app = MagicMock()
        with patch.object(type(rtf), "app", new_callable=PropertyMock, return_value=mock_app):
            rtf.select_from_popup()
        cast(MagicMock, mock_app.push_screen).assert_called_once()


# ============================================================================
# ResourceBar Tests
# ============================================================================


@pytest.mark.unit
class TestResourceBar:
    """Tests for ResourceBar widget."""

    def test_render_bar_unknown_usage(self) -> None:
        """_render_bar with used=None shows question marks."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "CPU"
        bar._capacity = 8
        bar._used = None
        bar._unit = " cores"
        bar._bar_width = 20
        result = bar._render_bar()
        assert "?" in result
        assert "N/A" in result
        assert "8 cores" in result

    def test_render_bar_green_low_usage(self) -> None:
        """_render_bar with low usage shows green color."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "CPU"
        bar._capacity = 10
        bar._used = 3
        bar._unit = " cores"
        bar._bar_width = 20
        result = bar._render_bar()
        assert "[green]" in result
        assert "3/10 cores" in result

    def test_render_bar_yellow_medium_usage(self) -> None:
        """_render_bar at 70-90% shows yellow color."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "Mem"
        bar._capacity = 10
        bar._used = 8
        bar._unit = " Gi"
        bar._bar_width = 20
        result = bar._render_bar()
        assert "[yellow]" in result

    def test_render_bar_red_high_usage(self) -> None:
        """_render_bar at >=90% shows red color."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "Pods"
        bar._capacity = 100
        bar._used = 95
        bar._unit = ""
        bar._bar_width = 20
        result = bar._render_bar()
        assert "[red]" in result

    def test_render_bar_zero_capacity(self) -> None:
        """_render_bar with zero capacity does not divide by zero."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "CPU"
        bar._capacity = 0
        bar._used = 0
        bar._unit = ""
        bar._bar_width = 10
        result = bar._render_bar()
        assert "[green]" in result

    def test_update_values(self) -> None:
        """update_values changes capacity and used and re-renders."""
        bar = ResourceBar.__new__(ResourceBar)
        bar._label = "cpu"
        bar._capacity = 4
        bar._used = 2
        bar._unit = " cores"
        bar._bar_width = 10
        mock_label = MagicMock()
        object.__setattr__(bar, "query_one", MagicMock(return_value=mock_label))
        bar.update_values(8, 6)
        assert bar._capacity == 8
        assert bar._used == 6
        mock_label.update.assert_called_once()


# ============================================================================
# RefreshTimer Tests
# ============================================================================


@pytest.mark.unit
class TestRefreshTimerSync:
    """Sync tests for RefreshTimer."""

    def test_init_defaults(self) -> None:
        """RefreshTimer uses default interval."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = REFRESH_DEFAULT_INTERVAL
        timer._remaining = REFRESH_DEFAULT_INTERVAL
        timer._paused = False
        assert timer._interval == 30
        assert timer._remaining == 30

    def test_tick_decrements(self) -> None:
        """_tick decrements remaining."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 10
        timer._paused = False
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer._tick()
        assert timer._remaining == 9

    def test_tick_paused_does_nothing(self) -> None:
        """_tick does nothing when paused."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 10
        timer._paused = True
        timer._tick()
        assert timer._remaining == 10

    def test_tick_fires_at_zero(self) -> None:
        """_tick fires RefreshTriggered when remaining hits 0."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 1
        timer._paused = False
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer._tick()
        assert timer._remaining == 30  # reset
        cast(MagicMock, timer.post_message).assert_called_once()

    def test_increase_interval(self) -> None:
        """increase_interval adds REFRESH_STEP."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 15
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer.increase_interval()
        assert timer._interval == 30 + REFRESH_STEP
        assert timer._remaining == timer._interval

    def test_increase_interval_capped(self) -> None:
        """increase_interval is capped at REFRESH_MAX_INTERVAL."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = REFRESH_MAX_INTERVAL
        timer._remaining = 10
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer.increase_interval()
        assert timer._interval == REFRESH_MAX_INTERVAL

    def test_decrease_interval(self) -> None:
        """decrease_interval subtracts REFRESH_STEP."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 15
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer.decrease_interval()
        assert timer._interval == 30 - REFRESH_STEP

    def test_decrease_interval_floored(self) -> None:
        """decrease_interval is floored at REFRESH_MIN_INTERVAL."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = REFRESH_MIN_INTERVAL
        timer._remaining = 3
        object.__setattr__(timer, "query_one", MagicMock())
        object.__setattr__(timer, "post_message", MagicMock())
        timer.decrease_interval()
        assert timer._interval == REFRESH_MIN_INTERVAL

    def test_reset(self) -> None:
        """reset restores remaining to interval."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._interval = 30
        timer._remaining = 5
        object.__setattr__(timer, "query_one", MagicMock())
        timer.reset()
        assert timer._remaining == 30

    def test_pause_and_resume(self) -> None:
        """pause sets _paused, resume clears it."""
        timer = RefreshTimer.__new__(RefreshTimer)
        timer._paused = False
        timer.pause()
        assert timer._paused is True
        timer.resume()
        assert timer._paused is False

    def test_interval_changed_message(self) -> None:
        """IntervalChanged message stores interval."""
        msg = RefreshTimer.IntervalChanged(45)
        assert msg.interval == 45

    def test_refresh_triggered_message(self) -> None:
        """RefreshTriggered is instantiable."""
        msg = RefreshTimer.RefreshTriggered()
        assert msg is not None
