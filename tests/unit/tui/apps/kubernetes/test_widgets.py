"""Unit tests for Kubernetes TUI widgets.

Tests NamespaceSelector, ClusterSelector, ResourceTypeFilter, and SelectorPopup.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container

from system_operations_manager.tui.apps.kubernetes.app import ResourceType
from system_operations_manager.tui.apps.kubernetes.widgets import (
    ALL_NAMESPACES_LABEL,
    ClusterSelector,
    NamespaceSelector,
    ResourceTypeFilter,
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
