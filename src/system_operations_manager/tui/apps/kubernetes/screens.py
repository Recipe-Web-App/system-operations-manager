"""Screen definitions for Kubernetes resource browser TUI.

This module provides the main resource list screen with DataTable display,
namespace/cluster selectors, and resource type filtering. Also includes
the cluster status dashboard screen with auto-refresh, and the resource
detail screen for inspecting individual resources.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import structlog
import yaml
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import DataTable, Label, Static

from system_operations_manager.integrations.kubernetes.models.base import K8sEntityBase
from system_operations_manager.tui.apps.kubernetes.types import (
    CREATABLE_TYPES,
    DELETABLE_TYPES,
    EDITABLE_TYPES,
    RESOURCE_TYPE_ORDER,
    ResourceType,
)
from system_operations_manager.tui.apps.kubernetes.widgets import (
    ClusterSelector,
    NamespaceSelector,
    RefreshTimer,
    ResourceBar,
    ResourceTypeFilter,
)
from system_operations_manager.tui.base import BaseScreen

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient
    from system_operations_manager.integrations.kubernetes.models.cluster import NodeSummary
    from system_operations_manager.integrations.kubernetes.models.workloads import PodSummary
    from system_operations_manager.services.kubernetes.configuration_manager import (
        ConfigurationManager,
    )
    from system_operations_manager.services.kubernetes.namespace_manager import (
        NamespaceClusterManager,
    )
    from system_operations_manager.services.kubernetes.networking_manager import (
        NetworkingManager,
    )
    from system_operations_manager.services.kubernetes.workload_manager import WorkloadManager

logger = structlog.get_logger()

# Column definitions per resource type: list of (label, width) tuples
COLUMN_DEFS: dict[ResourceType, list[tuple[str, int]]] = {
    ResourceType.PODS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Status", 12),
        ("Ready", 8),
        ("Restarts", 10),
        ("Node", 20),
        ("Age", 8),
    ],
    ResourceType.DEPLOYMENTS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Ready", 10),
        ("Up-to-date", 12),
        ("Available", 10),
        ("Age", 8),
    ],
    ResourceType.STATEFULSETS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Ready", 10),
        ("Age", 8),
    ],
    ResourceType.DAEMONSETS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Desired", 10),
        ("Current", 10),
        ("Ready", 8),
        ("Age", 8),
    ],
    ResourceType.REPLICASETS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Desired", 10),
        ("Ready", 8),
        ("Age", 8),
    ],
    ResourceType.SERVICES: [
        ("Name", 30),
        ("Namespace", 15),
        ("Type", 12),
        ("Cluster-IP", 16),
        ("Ports", 20),
        ("Age", 8),
    ],
    ResourceType.INGRESSES: [
        ("Name", 30),
        ("Namespace", 15),
        ("Class", 15),
        ("Hosts", 30),
        ("Addresses", 20),
        ("Age", 8),
    ],
    ResourceType.NETWORK_POLICIES: [
        ("Name", 30),
        ("Namespace", 15),
        ("Policy Types", 15),
        ("Ingress Rules", 13),
        ("Egress Rules", 13),
        ("Age", 8),
    ],
    ResourceType.CONFIGMAPS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Data Keys", 30),
        ("Age", 8),
    ],
    ResourceType.SECRETS: [
        ("Name", 30),
        ("Namespace", 15),
        ("Type", 20),
        ("Data Keys", 20),
        ("Age", 8),
    ],
    ResourceType.NAMESPACES: [
        ("Name", 30),
        ("Status", 12),
        ("Age", 8),
    ],
    ResourceType.NODES: [
        ("Name", 30),
        ("Status", 10),
        ("Roles", 15),
        ("Version", 15),
        ("Age", 8),
    ],
    ResourceType.EVENTS: [
        ("Type", 10),
        ("Reason", 15),
        ("Object", 25),
        ("Message", 40),
        ("Count", 6),
        ("Age", 8),
    ],
}


def _resource_to_row(resource: K8sEntityBase, resource_type: ResourceType) -> tuple[str, ...]:
    """Convert a K8s resource model to a DataTable row tuple.

    Args:
        resource: The resource model instance.
        resource_type: The type of resource for column mapping.

    Returns:
        Tuple of string values matching the column definitions.
    """
    r: Any = resource

    if resource_type == ResourceType.PODS:
        ready = f"{r.ready_count}/{r.total_count}"
        phase_colors = {
            "Running": "green",
            "Succeeded": "green",
            "Pending": "yellow",
            "Failed": "red",
            "Unknown": "dim",
        }
        color = phase_colors.get(r.phase, "dim")
        status = f"[{color}]{r.phase}[/{color}]"
        return (r.name, r.namespace or "", status, ready, str(r.restarts), r.node_name or "", r.age)

    if resource_type == ResourceType.DEPLOYMENTS:
        ready = f"{r.ready_replicas}/{r.replicas}"
        return (
            r.name,
            r.namespace or "",
            ready,
            str(r.updated_replicas),
            str(r.available_replicas),
            r.age,
        )

    if resource_type == ResourceType.STATEFULSETS:
        ready = f"{r.ready_replicas}/{r.replicas}"
        return (r.name, r.namespace or "", ready, r.age)

    if resource_type == ResourceType.DAEMONSETS:
        return (
            r.name,
            r.namespace or "",
            str(r.desired_number_scheduled),
            str(r.current_number_scheduled),
            str(r.number_ready),
            r.age,
        )

    if resource_type == ResourceType.REPLICASETS:
        return (r.name, r.namespace or "", str(r.replicas), str(r.ready_replicas), r.age)

    if resource_type == ResourceType.SERVICES:
        ports = ", ".join(f"{p.port}/{p.protocol}" for p in r.ports[:3])
        if len(r.ports) > 3:
            ports += f" (+{len(r.ports) - 3})"
        return (r.name, r.namespace or "", r.type, r.cluster_ip or "", ports, r.age)

    if resource_type == ResourceType.INGRESSES:
        hosts = ", ".join(r.hosts[:3])
        if len(r.hosts) > 3:
            hosts += f" (+{len(r.hosts) - 3})"
        addresses = ", ".join(r.addresses[:2])
        if len(r.addresses) > 2:
            addresses += f" (+{len(r.addresses) - 2})"
        return (r.name, r.namespace or "", r.class_name or "", hosts, addresses, r.age)

    if resource_type == ResourceType.NETWORK_POLICIES:
        policy_types = ", ".join(r.policy_types)
        return (
            r.name,
            r.namespace or "",
            policy_types,
            str(r.ingress_rules_count),
            str(r.egress_rules_count),
            r.age,
        )

    if resource_type == ResourceType.CONFIGMAPS:
        keys = ", ".join(r.data_keys[:5])
        if len(r.data_keys) > 5:
            keys += f" (+{len(r.data_keys) - 5})"
        return (r.name, r.namespace or "", keys, r.age)

    if resource_type == ResourceType.SECRETS:
        keys = ", ".join(r.data_keys[:5])
        if len(r.data_keys) > 5:
            keys += f" (+{len(r.data_keys) - 5})"
        return (r.name, r.namespace or "", r.type, keys, r.age)

    if resource_type == ResourceType.NAMESPACES:
        status_colors = {"Active": "green", "Terminating": "yellow"}
        color = status_colors.get(r.status, "dim")
        status = f"[{color}]{r.status}[/{color}]"
        return (r.name, status, r.age)

    if resource_type == ResourceType.NODES:
        status_colors = {"Ready": "green", "NotReady": "red"}
        color = status_colors.get(r.status, "dim")
        status = f"[{color}]{r.status}[/{color}]"
        roles = ", ".join(r.roles)
        return (r.name, status, roles, r.version or "", r.age)

    if resource_type == ResourceType.EVENTS:
        type_colors = {"Normal": "green", "Warning": "yellow"}
        color = type_colors.get(r.type, "dim")
        event_type = f"[{color}]{r.type}[/{color}]"
        obj = f"{r.involved_object_kind or ''}/{r.involved_object_name or ''}"
        msg = (r.message or "")[:60]
        return (event_type, r.reason or "", obj, msg, str(r.count), r.age)

    return (r.name, r.age)


class ResourceListScreen(BaseScreen[None]):
    """Screen showing a browsable list of Kubernetes resources.

    Displays a DataTable of resources with toolbar selectors for
    namespace, cluster context, and resource type. Supports keyboard
    navigation and both cycle and popup selection modes.
    """

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("enter", "select", "Select"),
        ("escape", "back", "Back"),
        ("n", "cycle_namespace", "Next NS"),
        ("N", "select_namespace", "Pick NS"),
        ("c", "cycle_cluster", "Next Ctx"),
        ("C", "select_cluster", "Pick Ctx"),
        ("f", "cycle_filter", "Next Type"),
        ("F", "select_filter", "Pick Type"),
        ("r", "refresh", "Refresh"),
        ("a", "create", "Create"),
        ("d", "delete", "Delete"),
        ("l", "logs", "Logs"),
    ]

    class ResourceSelected(Message):
        """Emitted when a user selects a resource row."""

        def __init__(self, resource: K8sEntityBase, resource_type: ResourceType) -> None:
            """Initialize with the selected resource.

            Args:
                resource: The selected resource model.
                resource_type: The type of resource.
            """
            self.resource = resource
            self.resource_type = resource_type
            super().__init__()

    def __init__(self, client: KubernetesClient) -> None:
        """Initialize the resource list screen.

        Args:
            client: Kubernetes API client.
        """
        super().__init__()
        self._client = client
        self._resources: Sequence[K8sEntityBase] = []
        self._current_type = ResourceType.PODS
        self._current_namespace: str | None = client.default_namespace
        self._namespaces: list[str] = []
        self._contexts: list[str] = []
        self._pending_delete: K8sEntityBase | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Container(
            Horizontal(
                NamespaceSelector(
                    namespaces=self._namespaces,
                    current=self._current_namespace,
                    id="ns-selector",
                ),
                ClusterSelector(
                    contexts=self._contexts,
                    current=self._client.get_current_context(),
                    id="ctx-selector",
                ),
                ResourceTypeFilter(
                    resource_types=RESOURCE_TYPE_ORDER,
                    current=self._current_type,
                    id="type-filter",
                ),
                id="toolbar",
            ),
            DataTable(id="resource-table"),
            Label("", id="status-bar"),
            id="resource-list-container",
        )

    def on_mount(self) -> None:
        """Configure the table and load initial data."""
        table = self.query_one("#resource-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        self._load_contexts()
        self._load_namespaces()
        self._load_resources()

    def _load_contexts(self) -> None:
        """Load available cluster contexts."""
        try:
            context_dicts = self._client.list_contexts()
            self._contexts = [ctx["name"] for ctx in context_dicts]
            ctx_selector = self.query_one("#ctx-selector", ClusterSelector)
            ctx_selector._contexts = self._contexts
        except Exception:
            logger.warning("failed_to_load_contexts")
            self._contexts = [self._client.get_current_context()]

    def _load_namespaces(self) -> None:
        """Load available namespaces from the cluster."""
        try:
            from system_operations_manager.services.kubernetes.namespace_manager import (
                NamespaceClusterManager,
            )

            mgr = NamespaceClusterManager(self._client)
            ns_list = mgr.list_namespaces()
            self._namespaces = [ns.name for ns in ns_list]
            ns_selector = self.query_one("#ns-selector", NamespaceSelector)
            ns_selector.update_namespaces(self._namespaces)
        except Exception:
            logger.warning("failed_to_load_namespaces")
            self._namespaces = ["default"]

    def _load_resources(self) -> None:
        """Load resources based on current type and namespace selection."""
        try:
            self._resources = self._fetch_resources()
            self._populate_table()
            count = len(self._resources)
            ns_display = self._current_namespace or "all namespaces"
            self.query_one("#status-bar", Label).update(
                f"[dim]{count} {self._current_type.value} in {ns_display}[/dim]"
            )
        except Exception as e:
            logger.error("failed_to_load_resources", error=str(e))
            self.notify_user(f"Failed to load resources: {e}", severity="error")
            self._resources = []
            self._populate_table()
            self.query_one("#status-bar", Label).update(
                f"[red]Error loading {self._current_type.value}[/red]"
            )

    def _fetch_resources(self) -> Sequence[K8sEntityBase]:
        """Fetch resources from the appropriate manager.

        Returns:
            List of resource model instances.
        """
        ns = self._current_namespace
        all_ns = ns is None

        if self._current_type == ResourceType.PODS:
            return self._workload_mgr.list_pods(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.DEPLOYMENTS:
            return self._workload_mgr.list_deployments(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.STATEFULSETS:
            return self._workload_mgr.list_stateful_sets(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.DAEMONSETS:
            return self._workload_mgr.list_daemon_sets(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.REPLICASETS:
            return self._workload_mgr.list_replica_sets(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.SERVICES:
            return self._networking_mgr.list_services(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.INGRESSES:
            return self._networking_mgr.list_ingresses(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.NETWORK_POLICIES:
            return self._networking_mgr.list_network_policies(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.CONFIGMAPS:
            return self._config_mgr.list_config_maps(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.SECRETS:
            return self._config_mgr.list_secrets(namespace=ns, all_namespaces=all_ns)

        if self._current_type == ResourceType.NAMESPACES:
            return self._namespace_mgr.list_namespaces()

        if self._current_type == ResourceType.NODES:
            return self._namespace_mgr.list_nodes()

        if self._current_type == ResourceType.EVENTS:
            return self._namespace_mgr.list_events(namespace=ns, all_namespaces=all_ns)

        return []

    @property
    def _workload_mgr(self) -> WorkloadManager:
        """Lazy-load WorkloadManager."""
        from system_operations_manager.services.kubernetes.workload_manager import WorkloadManager

        return WorkloadManager(self._client)

    @property
    def _networking_mgr(self) -> NetworkingManager:
        """Lazy-load NetworkingManager."""
        from system_operations_manager.services.kubernetes.networking_manager import (
            NetworkingManager,
        )

        return NetworkingManager(self._client)

    @property
    def _config_mgr(self) -> ConfigurationManager:
        """Lazy-load ConfigurationManager."""
        from system_operations_manager.services.kubernetes.configuration_manager import (
            ConfigurationManager,
        )

        return ConfigurationManager(self._client)

    @property
    def _namespace_mgr(self) -> NamespaceClusterManager:
        """Lazy-load NamespaceClusterManager."""
        from system_operations_manager.services.kubernetes.namespace_manager import (
            NamespaceClusterManager,
        )

        return NamespaceClusterManager(self._client)

    def _populate_table(self) -> None:
        """Populate the DataTable with current resources."""
        table = self.query_one("#resource-table", DataTable)
        table.clear(columns=True)

        columns = COLUMN_DEFS.get(self._current_type, [("Name", 30), ("Age", 8)])
        for label, width in columns:
            table.add_column(label, width=width)

        for resource in self._resources:
            row = _resource_to_row(resource, self._current_type)
            table.add_row(*row)

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def action_cursor_down(self) -> None:
        """Move table cursor down."""
        self.query_one("#resource-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move table cursor up."""
        self.query_one("#resource-table", DataTable).action_cursor_up()

    def action_select(self) -> None:
        """Select the current resource row."""
        table = self.query_one("#resource-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self._resources):
            resource = self._resources[table.cursor_row]
            self.post_message(self.ResourceSelected(resource, self._current_type))

    @on(DataTable.RowSelected)
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection via DataTable event."""
        if event.cursor_row is not None and event.cursor_row < len(self._resources):
            resource = self._resources[event.cursor_row]
            self.post_message(self.ResourceSelected(resource, self._current_type))

    def action_back(self) -> None:
        """Go back / quit."""
        self.go_back()

    def action_refresh(self) -> None:
        """Reload the current resource list."""
        self._load_resources()
        self.notify_user("Refreshed")

    def action_create(self) -> None:
        """Open the create screen for the current resource type."""
        if self._current_type not in CREATABLE_TYPES:
            self.notify_user(f"Cannot create {self._current_type.value}", severity="warning")
            return
        from system_operations_manager.tui.apps.kubernetes.create_screen import (
            ResourceCreateScreen,
        )

        self.app.push_screen(
            ResourceCreateScreen(
                resource_type=self._current_type,
                client=self._client,
                namespace=self._current_namespace,
            ),
            callback=self._handle_create_dismissed,
        )

    def _handle_create_dismissed(self, _result: None) -> None:
        """Refresh list after create screen is dismissed."""
        self._load_resources()

    def action_delete(self) -> None:
        """Delete the selected resource after confirmation."""
        if self._current_type not in DELETABLE_TYPES:
            self.notify_user(f"Cannot delete {self._current_type.value}", severity="warning")
            return
        table = self.query_one("#resource-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._resources):
            return
        resource = self._resources[table.cursor_row]
        self._pending_delete = resource

        from system_operations_manager.tui.components.modal import Modal

        type_label = self._current_type.value
        if type_label.endswith("s"):
            type_label = type_label[:-1]
        ns_text = f" in {resource.namespace}" if resource.namespace else ""
        self.app.push_screen(
            Modal(
                title="Confirm Delete",
                body=f"Delete {type_label} '{resource.name}'{ns_text}?",
                buttons=[
                    ("Delete", "delete", "error"),
                    ("Cancel", "cancel", "default"),
                ],
                show_cancel=False,
            ),
            callback=self._handle_delete_result,
        )

    def _handle_delete_result(self, result: str | None) -> None:
        """Process delete confirmation result."""
        if result == "delete" and self._pending_delete is not None:
            try:
                from system_operations_manager.tui.apps.kubernetes.delete_helpers import (
                    delete_resource,
                )

                delete_resource(
                    self._client,
                    self._current_type,
                    self._pending_delete.name,
                    self._pending_delete.namespace,
                )
                self.notify_user(f"Deleted {self._pending_delete.name}")
                self._load_resources()
            except Exception as e:
                self.notify_user(f"Delete failed: {e}", severity="error")
        self._pending_delete = None

    def action_logs(self) -> None:
        """Open log viewer for the selected pod."""
        if self._current_type != ResourceType.PODS:
            self.notify_user("Logs only available for Pods", severity="warning")
            return
        table = self.query_one("#resource-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._resources):
            return
        resource = self._resources[table.cursor_row]

        from system_operations_manager.tui.apps.kubernetes.log_viewer import (
            LogViewerScreen,
        )

        self.app.push_screen(
            LogViewerScreen(resource=cast("PodSummary", resource), client=self._client)
        )

    # Namespace actions
    def action_cycle_namespace(self) -> None:
        """Cycle to next namespace."""
        self.query_one("#ns-selector", NamespaceSelector).cycle()

    def action_select_namespace(self) -> None:
        """Open namespace popup selector."""
        self.query_one("#ns-selector", NamespaceSelector).select_from_popup()

    # Cluster actions
    def action_cycle_cluster(self) -> None:
        """Cycle to next cluster context."""
        self.query_one("#ctx-selector", ClusterSelector).cycle()

    def action_select_cluster(self) -> None:
        """Open cluster popup selector."""
        self.query_one("#ctx-selector", ClusterSelector).select_from_popup()

    # Resource type actions
    def action_cycle_filter(self) -> None:
        """Cycle to next resource type."""
        self.query_one("#type-filter", ResourceTypeFilter).cycle()

    def action_select_filter(self) -> None:
        """Open resource type popup selector."""
        self.query_one("#type-filter", ResourceTypeFilter).select_from_popup()

    # =========================================================================
    # Widget Event Handlers
    # =========================================================================

    @on(NamespaceSelector.NamespaceChanged)
    def handle_namespace_changed(self, event: NamespaceSelector.NamespaceChanged) -> None:
        """Handle namespace change from selector widget."""
        self._current_namespace = event.selected_namespace
        self._load_resources()

    @on(ClusterSelector.ClusterChanged)
    def handle_cluster_changed(self, event: ClusterSelector.ClusterChanged) -> None:
        """Handle cluster context change from selector widget."""
        try:
            self._client.switch_context(event.context)
            self._load_namespaces()
            self._load_resources()
            self.notify_user(f"Switched to context: {event.context}")
        except Exception as e:
            self.notify_user(f"Failed to switch context: {e}", severity="error")

    @on(ResourceTypeFilter.ResourceTypeChanged)
    def handle_resource_type_changed(self, event: ResourceTypeFilter.ResourceTypeChanged) -> None:
        """Handle resource type change from filter widget."""
        self._current_type = event.resource_type
        self._load_resources()


# Column definitions for dashboard tables
DASHBOARD_NODE_COLUMNS: list[tuple[str, int]] = [
    ("Name", 20),
    ("Status", 10),
    ("Roles", 15),
    ("Version", 12),
    ("CPU", 6),
    ("Memory", 10),
    ("Pods", 6),
]

DASHBOARD_EVENT_COLUMNS: list[tuple[str, int]] = [
    ("Type", 8),
    ("Reason", 15),
    ("Object", 25),
    ("Message", 40),
    ("Count", 6),
]

DASHBOARD_MAX_EVENTS = 20
DASHBOARD_MAX_NAMESPACES = 10

POD_PHASE_COLORS: dict[str, str] = {
    "Running": "green",
    "Succeeded": "green",
    "Pending": "yellow",
    "Failed": "red",
    "Unknown": "dim",
}

POD_PHASE_ORDER: list[str] = ["Running", "Pending", "Failed", "Succeeded", "Unknown"]


class DashboardScreen(BaseScreen[None]):
    """Cluster status dashboard with auto-refresh.

    Shows node health, pod status summary, resource capacity bars,
    and recent warning events in a single overview screen with
    configurable auto-refresh.
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
        ("plus", "increase_interval", "+Interval"),
        ("minus", "decrease_interval", "-Interval"),
    ]

    def __init__(self, client: KubernetesClient) -> None:
        """Initialize the dashboard screen.

        Args:
            client: Kubernetes API client.
        """
        super().__init__()
        self._client = client

    # =========================================================================
    # Lazy-loaded managers
    # =========================================================================

    @property
    def _namespace_mgr(self) -> NamespaceClusterManager:
        """Lazy-load NamespaceClusterManager."""
        from system_operations_manager.services.kubernetes.namespace_manager import (
            NamespaceClusterManager,
        )

        return NamespaceClusterManager(self._client)

    @property
    def _workload_mgr(self) -> WorkloadManager:
        """Lazy-load WorkloadManager."""
        from system_operations_manager.services.kubernetes.workload_manager import WorkloadManager

        return WorkloadManager(self._client)

    # =========================================================================
    # Layout
    # =========================================================================

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Container(
            Horizontal(
                Label("", id="cluster-info"),
                RefreshTimer(id="refresh-timer"),
                id="dashboard-header",
            ),
            Horizontal(
                Container(
                    Label("[bold]Node Health[/bold]", classes="panel-title"),
                    DataTable(id="node-table"),
                    id="node-panel",
                ),
                Vertical(
                    Container(
                        Label("[bold]Pod Status[/bold]", classes="panel-title"),
                        Label("", id="pod-phase-summary"),
                        id="pod-phase-panel",
                    ),
                    Container(
                        Label("[bold]Pods by Namespace[/bold]", classes="panel-title"),
                        Label("", id="pod-ns-summary"),
                        id="pod-ns-panel",
                    ),
                    id="pod-summary-panel",
                ),
                id="dashboard-top",
            ),
            Container(
                Label("[bold]Resource Capacity[/bold]", classes="panel-title"),
                Vertical(id="resource-bars"),
                id="resource-bars-panel",
            ),
            Container(
                Label("[bold]Recent Warnings[/bold]", classes="panel-title"),
                DataTable(id="events-table"),
                id="events-panel",
            ),
            id="dashboard-container",
        )

    # =========================================================================
    # Data loading
    # =========================================================================

    def on_mount(self) -> None:
        """Configure tables and load initial data."""
        self._setup_tables()
        self._refresh_all()

    def _setup_tables(self) -> None:
        """Configure DataTable columns for node and event tables."""
        node_table = self.query_one("#node-table", DataTable)
        node_table.cursor_type = "row"
        node_table.zebra_stripes = True
        for col_label, width in DASHBOARD_NODE_COLUMNS:
            node_table.add_column(col_label, width=width)

        events_table = self.query_one("#events-table", DataTable)
        events_table.cursor_type = "row"
        events_table.zebra_stripes = True
        for col_label, width in DASHBOARD_EVENT_COLUMNS:
            events_table.add_column(col_label, width=width)

    def _refresh_all(self) -> None:
        """Refresh all dashboard panels."""
        self._load_cluster_info()
        self._load_nodes()
        self._load_pod_summary()
        self._load_events()

    def _load_cluster_info(self) -> None:
        """Load and display cluster information header."""
        try:
            info = self._namespace_mgr.get_cluster_info()
            version = info.get("version", "unknown")
            context = info.get("context", "unknown")
            node_count = info.get("node_count", "?")
            ns_count = info.get("namespace_count", "?")
            self.query_one("#cluster-info", Label).update(
                f"[bold]Cluster:[/bold] {context}  "
                f"[bold]K8s:[/bold] {version}  "
                f"[bold]Nodes:[/bold] {node_count}  "
                f"[bold]Namespaces:[/bold] {ns_count}"
            )
        except Exception as e:
            logger.warning("dashboard_cluster_info_failed", error=str(e))
            self.query_one("#cluster-info", Label).update("[red]Failed to load cluster info[/red]")

    def _load_nodes(self) -> None:
        """Load node health data into the node table and resource bars."""
        try:
            nodes = self._namespace_mgr.list_nodes()
            table = self.query_one("#node-table", DataTable)
            table.clear()

            for node in nodes:
                status_color = {"Ready": "green", "NotReady": "red"}.get(node.status, "dim")
                status = f"[{status_color}]{node.status}[/{status_color}]"
                roles = ", ".join(node.roles)
                table.add_row(
                    node.name,
                    status,
                    roles,
                    node.version or "",
                    node.cpu_capacity or "?",
                    node.memory_capacity or "?",
                    node.pods_capacity or "?",
                )

            self._update_resource_bars(nodes)
        except Exception as e:
            logger.warning("dashboard_nodes_failed", error=str(e))
            self.notify_user(f"Failed to load nodes: {e}", severity="error")

    def _load_pod_summary(self) -> None:
        """Load pod counts by phase and namespace."""
        try:
            pods = self._workload_mgr.list_pods(all_namespaces=True)

            phase_counts: dict[str, int] = {}
            ns_counts: dict[str, int] = {}
            for pod in pods:
                phase = getattr(pod, "phase", "Unknown") or "Unknown"
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
                ns = pod.namespace or "unknown"
                ns_counts[ns] = ns_counts.get(ns, 0) + 1

            # Phase summary
            parts: list[str] = []
            for phase in POD_PHASE_ORDER:
                count = phase_counts.get(phase, 0)
                if count > 0:
                    color = POD_PHASE_COLORS.get(phase, "dim")
                    parts.append(f"[{color}]{phase}: {count}[/{color}]")
            total = len(pods)
            summary = f"Total: {total}  " + "  ".join(parts)
            self.query_one("#pod-phase-summary", Label).update(summary)

            # Namespace summary (top N)
            sorted_ns = sorted(ns_counts.items(), key=lambda x: x[1], reverse=True)
            sorted_ns = sorted_ns[:DASHBOARD_MAX_NAMESPACES]
            ns_lines = [f"  {ns_name}: [bold]{count}[/bold]" for ns_name, count in sorted_ns]
            self.query_one("#pod-ns-summary", Label).update("\n".join(ns_lines))
        except Exception as e:
            logger.warning("dashboard_pods_failed", error=str(e))
            self.query_one("#pod-phase-summary", Label).update("[red]Failed to load pods[/red]")

    def _update_resource_bars(self, nodes: list[NodeSummary]) -> None:
        """Update resource capacity bars from node data.

        Shows capacity bars per node. Actual usage is marked N/A
        since it requires metrics-server which may not be available.

        Args:
            nodes: List of node summaries with capacity data.
        """
        bars_container = self.query_one("#resource-bars", Vertical)
        bars_container.remove_children()

        for node in nodes:
            cpu_cap = self._parse_cpu(node.cpu_capacity) if node.cpu_capacity else None
            mem_cap = self._parse_memory(node.memory_capacity) if node.memory_capacity else None
            pod_cap = int(node.pods_capacity) if node.pods_capacity else None

            bars_container.mount(Label(f"  [bold]{node.name}[/bold]"))

            if cpu_cap is not None:
                bars_container.mount(
                    ResourceBar(label="CPU", capacity=cpu_cap, used=None, unit=" cores")
                )
            if mem_cap is not None:
                bars_container.mount(
                    ResourceBar(label="Mem", capacity=mem_cap, used=None, unit=" Gi")
                )
            if pod_cap is not None:
                bars_container.mount(
                    ResourceBar(label="Pods", capacity=pod_cap, used=None, unit="")
                )

    @staticmethod
    def _parse_cpu(cpu_str: str) -> int | None:
        """Parse CPU capacity string to whole cores.

        Args:
            cpu_str: CPU string like ``"8"`` or ``"4000m"``.

        Returns:
            Number of cores, or None if unparseable.
        """
        try:
            if cpu_str.endswith("m"):
                return int(cpu_str[:-1]) // 1000
            return int(cpu_str)
        except ValueError, TypeError:
            return None

    @staticmethod
    def _parse_memory(mem_str: str) -> int | None:
        """Parse memory capacity string to GiB.

        Args:
            mem_str: Memory string like ``"16Gi"`` or ``"16384Mi"``.

        Returns:
            Memory in GiB, or None if unparseable.
        """
        try:
            if mem_str.endswith("Ki"):
                return int(mem_str[:-2]) // (1024 * 1024)
            if mem_str.endswith("Mi"):
                return int(mem_str[:-2]) // 1024
            if mem_str.endswith("Gi"):
                return int(mem_str[:-2])
            return int(mem_str) // (1024**3)
        except ValueError, TypeError:
            return None

    def _load_events(self) -> None:
        """Load recent warning events into the events table."""
        try:
            events = self._namespace_mgr.list_events(all_namespaces=True)
            warnings = [e for e in events if e.type == "Warning"]
            warnings.sort(
                key=lambda e: e.last_timestamp or e.creation_timestamp or "",
                reverse=True,
            )
            warnings = warnings[:DASHBOARD_MAX_EVENTS]

            table = self.query_one("#events-table", DataTable)
            table.clear()

            for evt in warnings:
                type_markup = f"[yellow]{evt.type}[/yellow]"
                obj = f"{evt.involved_object_kind or ''}/{evt.involved_object_name or ''}"
                msg = (evt.message or "")[:60]
                table.add_row(type_markup, evt.reason or "", obj, msg, str(evt.count))
        except Exception as e:
            logger.warning("dashboard_events_failed", error=str(e))

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def action_back(self) -> None:
        """Navigate back to previous screen."""
        self.go_back()

    def action_refresh(self) -> None:
        """Manually refresh all dashboard panels."""
        self._refresh_all()
        self.query_one("#refresh-timer", RefreshTimer).reset()
        self.notify_user("Dashboard refreshed")

    def action_increase_interval(self) -> None:
        """Increase the auto-refresh interval."""
        self.query_one("#refresh-timer", RefreshTimer).increase_interval()

    def action_decrease_interval(self) -> None:
        """Decrease the auto-refresh interval."""
        self.query_one("#refresh-timer", RefreshTimer).decrease_interval()

    # =========================================================================
    # Widget Event Handlers
    # =========================================================================

    @on(RefreshTimer.RefreshTriggered)
    def handle_auto_refresh(self, event: RefreshTimer.RefreshTriggered) -> None:
        """Handle auto-refresh timer firing."""
        self._refresh_all()

    @on(RefreshTimer.IntervalChanged)
    def handle_interval_changed(self, event: RefreshTimer.IntervalChanged) -> None:
        """Handle refresh interval change."""
        self.notify_user(f"Refresh interval: {event.interval}s")


# ============================================================================
# Resource Detail Screen Constants
# ============================================================================

STATUS_COLOR_MAP: dict[str, str] = {
    "Running": "green",
    "Succeeded": "green",
    "Active": "green",
    "Ready": "green",
    "Pending": "yellow",
    "Terminating": "yellow",
    "Failed": "red",
    "NotReady": "red",
    "Unknown": "dim",
}

DETAIL_EVENTS_LIMIT = 15


class ResourceDetailScreen(BaseScreen[None]):
    """Screen showing detailed information about a single Kubernetes resource.

    Displays metadata, status indicators, labels/annotations,
    YAML representation, and related events.
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("y", "toggle_yaml", "YAML"),
        ("r", "refresh_events", "Refresh"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("l", "logs", "Logs"),
        ("x", "exec", "Exec"),
    ]

    def __init__(
        self,
        resource: K8sEntityBase,
        resource_type: ResourceType,
        client: KubernetesClient,
    ) -> None:
        """Initialize the resource detail screen.

        Args:
            resource: The K8s resource model to display.
            resource_type: The type of resource.
            client: Kubernetes API client for fetching events.
        """
        super().__init__()
        self._resource = resource
        self._resource_type = resource_type
        self._client = client
        self._yaml_visible = True

    # =========================================================================
    # Layout
    # =========================================================================

    def compose(self) -> ComposeResult:
        """Compose the detail screen layout."""
        yield Container(
            Label(self._build_header_text(), id="detail-header"),
            Horizontal(
                Container(
                    Label("[bold]Metadata[/bold]", classes="panel-title"),
                    Static(self._build_metadata_text(), id="detail-metadata"),
                    id="metadata-panel",
                    classes="detail-panel",
                ),
                Container(
                    Label("[bold]Status[/bold]", classes="panel-title"),
                    Static(self._build_status_text(), id="detail-status"),
                    id="status-panel",
                    classes="detail-panel",
                ),
                id="detail-top-row",
            ),
            Horizontal(
                Container(
                    Label("[bold]Labels[/bold]", classes="panel-title"),
                    Static(self._build_labels_text(), id="detail-labels"),
                    id="labels-panel",
                    classes="detail-panel",
                ),
                Container(
                    Label("[bold]Annotations[/bold]", classes="panel-title"),
                    Static(self._build_annotations_text(), id="detail-annotations"),
                    id="annotations-panel",
                    classes="detail-panel",
                ),
                id="detail-mid-row",
            ),
            Container(
                Label("[bold]YAML[/bold]  [dim](y to toggle)[/dim]", classes="panel-title"),
                ScrollableContainer(
                    Static(self._build_yaml_text(), id="detail-yaml-content"),
                    id="detail-yaml-scroll",
                ),
                id="yaml-panel",
                classes="detail-panel",
            ),
            Container(
                Label("[bold]Events[/bold]  [dim](r to refresh)[/dim]", classes="panel-title"),
                DataTable(id="detail-events-table"),
                id="detail-events-panel",
                classes="detail-panel",
            ),
            id="detail-container",
        )

    def on_mount(self) -> None:
        """Configure the events table and load events."""
        table = self.query_one("#detail-events-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        for col_label, width in COLUMN_DEFS[ResourceType.EVENTS]:
            table.add_column(col_label, width=width)
        self._load_events()

    # =========================================================================
    # Text Builders
    # =========================================================================

    def _build_header_text(self) -> str:
        """Build the header line with resource kind, name, and status color.

        Returns:
            Rich-markup formatted header string.
        """
        kind = self._resource_type.value
        name = self._resource.name
        ns = self._resource.namespace

        status_str = self._get_primary_status()
        color = STATUS_COLOR_MAP.get(status_str, "dim")
        status_badge = f"[{color}]{status_str}[/{color}]"

        parts = [f"[bold]{kind}[/bold] / [bold cyan]{name}[/bold cyan]"]
        if ns:
            parts.append(f"  [dim]ns:[/dim] {ns}")
        parts.append(f"  {status_badge}")
        return "".join(parts)

    def _get_primary_status(self) -> str:
        """Extract the primary status string from the resource.

        Returns:
            Status string for color mapping.
        """
        r: Any = self._resource
        if hasattr(r, "phase"):
            return str(r.phase)
        if hasattr(r, "status"):
            return str(r.status)
        return "Unknown"

    def _build_metadata_text(self) -> str:
        """Build metadata display text.

        Returns:
            Formatted metadata string with UID, creation time, and age.
        """
        r = self._resource
        lines = [
            f"[bold]UID:[/bold]      {r.uid or 'N/A'}",
            f"[bold]Created:[/bold]  {r.creation_timestamp or 'N/A'}",
            f"[bold]Age:[/bold]      {r.age}",
        ]
        if r.namespace:
            lines.insert(0, f"[bold]Namespace:[/bold] {r.namespace}")
        return "\n".join(lines)

    def _build_status_text(self) -> str:
        """Build resource-type-specific status display.

        Returns:
            Formatted status string with type-specific fields.
        """
        r: Any = self._resource
        rt = self._resource_type
        lines: list[str] = []

        if rt == ResourceType.PODS:
            color = STATUS_COLOR_MAP.get(r.phase, "dim")
            lines.append(f"[bold]Phase:[/bold]      [{color}]{r.phase}[/{color}]")
            lines.append(f"[bold]Ready:[/bold]      {r.ready_count}/{r.total_count}")
            lines.append(f"[bold]Restarts:[/bold]   {r.restarts}")
            lines.append(f"[bold]Node:[/bold]       {r.node_name or 'N/A'}")
            lines.append(f"[bold]Pod IP:[/bold]     {r.pod_ip or 'N/A'}")
        elif rt == ResourceType.DEPLOYMENTS:
            lines.append(f"[bold]Ready:[/bold]       {r.ready_replicas}/{r.replicas}")
            lines.append(f"[bold]Up-to-date:[/bold]  {r.updated_replicas}")
            lines.append(f"[bold]Available:[/bold]   {r.available_replicas}")
            lines.append(f"[bold]Strategy:[/bold]    {r.strategy or 'N/A'}")
        elif rt == ResourceType.STATEFULSETS:
            lines.append(f"[bold]Ready:[/bold]    {r.ready_replicas}/{r.replicas}")
            lines.append(f"[bold]Service:[/bold]  {r.service_name or 'N/A'}")
        elif rt == ResourceType.DAEMONSETS:
            lines.append(f"[bold]Desired:[/bold]  {r.desired_number_scheduled}")
            lines.append(f"[bold]Current:[/bold]  {r.current_number_scheduled}")
            lines.append(f"[bold]Ready:[/bold]    {r.number_ready}")
        elif rt == ResourceType.REPLICASETS:
            lines.append(f"[bold]Desired:[/bold]  {r.replicas}")
            lines.append(f"[bold]Ready:[/bold]    {r.ready_replicas}")
        elif rt == ResourceType.SERVICES:
            lines.append(f"[bold]Type:[/bold]        {r.type}")
            lines.append(f"[bold]Cluster IP:[/bold]  {r.cluster_ip or 'N/A'}")
            ports = ", ".join(f"{p.port}/{p.protocol}" for p in r.ports)
            lines.append(f"[bold]Ports:[/bold]       {ports or 'N/A'}")
        elif rt == ResourceType.INGRESSES:
            lines.append(f"[bold]Class:[/bold]      {r.class_name or 'N/A'}")
            lines.append(f"[bold]Hosts:[/bold]      {', '.join(r.hosts) or 'N/A'}")
            lines.append(f"[bold]Addresses:[/bold]  {', '.join(r.addresses) or 'N/A'}")
        elif rt == ResourceType.NETWORK_POLICIES:
            lines.append(f"[bold]Policy Types:[/bold]  {', '.join(r.policy_types)}")
            lines.append(f"[bold]Ingress Rules:[/bold] {r.ingress_rules_count}")
            lines.append(f"[bold]Egress Rules:[/bold]  {r.egress_rules_count}")
        elif rt == ResourceType.CONFIGMAPS:
            keys = ", ".join(r.data_keys[:10])
            if len(r.data_keys) > 10:
                keys += f" (+{len(r.data_keys) - 10})"
            lines.append(f"[bold]Data Keys:[/bold] {keys or 'N/A'}")
        elif rt == ResourceType.SECRETS:
            lines.append(f"[bold]Type:[/bold]      {r.type}")
            keys = ", ".join(r.data_keys[:10])
            if len(r.data_keys) > 10:
                keys += f" (+{len(r.data_keys) - 10})"
            lines.append(f"[bold]Data Keys:[/bold] {keys or 'N/A'}")
        elif rt == ResourceType.NAMESPACES:
            color = STATUS_COLOR_MAP.get(r.status, "dim")
            lines.append(f"[bold]Status:[/bold] [{color}]{r.status}[/{color}]")
        elif rt == ResourceType.NODES:
            color = STATUS_COLOR_MAP.get(r.status, "dim")
            lines.append(f"[bold]Status:[/bold]    [{color}]{r.status}[/{color}]")
            lines.append(f"[bold]Roles:[/bold]     {', '.join(r.roles)}")
            lines.append(f"[bold]Version:[/bold]   {r.version or 'N/A'}")
            lines.append(f"[bold]IP:[/bold]        {r.internal_ip or 'N/A'}")
            lines.append(f"[bold]OS:[/bold]        {r.os_image or 'N/A'}")
            lines.append(f"[bold]Runtime:[/bold]   {r.container_runtime or 'N/A'}")
        elif rt == ResourceType.EVENTS:
            type_color = {"Normal": "green", "Warning": "yellow"}.get(r.type, "dim")
            lines.append(f"[bold]Type:[/bold]    [{type_color}]{r.type}[/{type_color}]")
            lines.append(f"[bold]Reason:[/bold]  {r.reason or 'N/A'}")
            lines.append(f"[bold]Count:[/bold]   {r.count}")
            lines.append(f"[bold]Message:[/bold] {r.message or 'N/A'}")

        if not lines:
            lines.append("[dim]No status information available[/dim]")
        return "\n".join(lines)

    def _build_labels_text(self) -> str:
        """Build labels display text.

        Returns:
            Formatted labels as key=value lines, or placeholder.
        """
        labels = self._resource.labels
        if not labels:
            return "[dim]No labels[/dim]"
        lines = [f"  {key}={value}" for key, value in sorted(labels.items())]
        return "\n".join(lines)

    def _build_annotations_text(self) -> str:
        """Build annotations display text.

        Returns:
            Formatted annotations as key=value lines, or placeholder.
        """
        annotations = self._resource.annotations
        if not annotations:
            return "[dim]No annotations[/dim]"
        lines = []
        for key, value in sorted(annotations.items()):
            display_value = value if len(value) <= 60 else value[:57] + "..."
            lines.append(f"  {key}={display_value}")
        return "\n".join(lines)

    def _build_yaml_text(self) -> str:
        """Serialize the resource model to YAML string.

        Returns:
            YAML-formatted string of the resource data.
        """
        data = self._resource.model_dump(exclude_none=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    # =========================================================================
    # Events
    # =========================================================================

    def _load_events(self) -> None:
        """Load events related to this specific resource."""
        try:
            from system_operations_manager.services.kubernetes.namespace_manager import (
                NamespaceClusterManager,
            )

            mgr = NamespaceClusterManager(self._client)
            resource_name = self._resource.name
            ns = self._resource.namespace

            field_selector = f"involvedObject.name={resource_name}"

            if ns:
                events = mgr.list_events(namespace=ns, field_selector=field_selector)
            else:
                events = mgr.list_events(all_namespaces=True, field_selector=field_selector)

            events.sort(
                key=lambda e: e.last_timestamp or e.creation_timestamp or "",
                reverse=True,
            )
            events = events[:DETAIL_EVENTS_LIMIT]

            table = self.query_one("#detail-events-table", DataTable)
            table.clear()

            for evt in events:
                type_colors = {"Normal": "green", "Warning": "yellow"}
                color = type_colors.get(evt.type, "dim")
                type_markup = f"[{color}]{evt.type}[/{color}]"
                obj = f"{evt.involved_object_kind or ''}/{evt.involved_object_name or ''}"
                msg = (evt.message or "")[:60]
                table.add_row(
                    type_markup,
                    evt.reason or "",
                    obj,
                    msg,
                    str(evt.count),
                    evt.age,
                )

            count = len(events)
            logger.debug("detail_events_loaded", count=count, resource=resource_name)
        except Exception as e:
            logger.warning("detail_events_failed", error=str(e))
            self.notify_user(f"Failed to load events: {e}", severity="error")

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def action_back(self) -> None:
        """Navigate back to the resource list."""
        self.go_back()

    def action_toggle_yaml(self) -> None:
        """Toggle YAML panel visibility."""
        yaml_panel = self.query_one("#yaml-panel")
        self._yaml_visible = not self._yaml_visible
        yaml_panel.display = self._yaml_visible

    def action_refresh_events(self) -> None:
        """Refresh the events panel."""
        self._load_events()
        self.notify_user("Events refreshed")

    def action_edit(self) -> None:
        """Open YAML editor for this resource."""
        if self._resource_type not in EDITABLE_TYPES:
            self.notify_user(f"Cannot edit {self._resource_type.value}", severity="warning")
            return
        self._open_yaml_editor()

    def _open_yaml_editor(self) -> None:
        """Suspend TUI, open $EDITOR with resource YAML, apply patch."""
        import shlex
        import subprocess
        import tempfile
        from pathlib import Path

        from system_operations_manager.tui.apps.kubernetes.edit_helpers import (
            apply_patch,
            fetch_raw_resource,
        )
        from system_operations_manager.utils.editor import get_editor

        try:
            obj_dict = fetch_raw_resource(
                self._client,
                self._resource_type,
                self._resource.name,
                self._resource.namespace,
            )
        except Exception as e:
            self.notify_user(f"Failed to fetch resource: {e}", severity="error")
            return

        yaml_content = yaml.dump(obj_dict, default_flow_style=False, sort_keys=False)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            prefix=f"k8s-{self._resource.name}-",
            delete=False,
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            editor = get_editor()
            with self.app.suspend():
                subprocess.run([*shlex.split(editor), temp_path], check=False)

            with Path(temp_path).open() as f:
                edited_content = f.read()

            edited_dict = yaml.safe_load(edited_content)
            if not isinstance(edited_dict, dict):
                self.notify_user("Invalid YAML: expected a mapping", severity="error")
                return

            if edited_dict == obj_dict:
                self.notify_user("No changes detected")
                return

            apply_patch(
                self._client,
                self._resource_type,
                self._resource.name,
                self._resource.namespace,
                edited_dict,
            )
            self.notify_user(f"Updated {self._resource.name}")
            self._refresh_detail()

        except yaml.YAMLError as e:
            self.notify_user(f"YAML parse error: {e}", severity="error")
        except Exception as e:
            self.notify_user(f"Update failed: {e}", severity="error")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _refresh_detail(self) -> None:
        """Re-fetch the resource and update display panels."""
        from system_operations_manager.tui.apps.kubernetes.edit_helpers import (
            fetch_raw_resource,
        )

        try:
            obj_dict = fetch_raw_resource(
                self._client,
                self._resource_type,
                self._resource.name,
                self._resource.namespace,
            )
            # Update YAML panel
            yaml_panel = self.query_one("#yaml-content", Static)
            yaml_content = yaml.dump(obj_dict, default_flow_style=False, sort_keys=False)
            yaml_panel.update(yaml_content)
            # Refresh events
            self._load_events()
        except Exception as e:
            self.notify_user(f"Refresh failed: {e}", severity="error")

    def action_delete(self) -> None:
        """Delete this resource after confirmation."""
        if self._resource_type not in DELETABLE_TYPES:
            self.notify_user(f"Cannot delete {self._resource_type.value}", severity="warning")
            return

        from system_operations_manager.tui.components.modal import Modal

        type_label = self._resource_type.value
        if type_label.endswith("s"):
            type_label = type_label[:-1]
        ns_text = f" in {self._resource.namespace}" if self._resource.namespace else ""
        self.app.push_screen(
            Modal(
                title="Confirm Delete",
                body=(
                    f"Delete {type_label} '{self._resource.name}'{ns_text}?\n\n"
                    "This action cannot be undone."
                ),
                buttons=[
                    ("Delete", "delete", "error"),
                    ("Cancel", "cancel", "default"),
                ],
                show_cancel=False,
            ),
            callback=self._handle_delete_result,
        )

    def _handle_delete_result(self, result: str | None) -> None:
        """Process delete confirmation result."""
        if result == "delete":
            try:
                from system_operations_manager.tui.apps.kubernetes.delete_helpers import (
                    delete_resource,
                )

                delete_resource(
                    self._client,
                    self._resource_type,
                    self._resource.name,
                    self._resource.namespace,
                )
                self.notify_user(f"Deleted {self._resource.name}")
                self.go_back()
            except Exception as e:
                self.notify_user(f"Delete failed: {e}", severity="error")

    # =========================================================================
    # Logs & Exec
    # =========================================================================

    def action_logs(self) -> None:
        """Open log viewer for this pod."""
        if self._resource_type != ResourceType.PODS:
            self.notify_user(
                f"Logs not available for {self._resource_type.value}",
                severity="warning",
            )
            return

        from system_operations_manager.tui.apps.kubernetes.log_viewer import (
            LogViewerScreen,
        )

        self.app.push_screen(
            LogViewerScreen(resource=cast("PodSummary", self._resource), client=self._client)
        )

    def action_exec(self) -> None:
        """Open an interactive exec session in this pod."""
        if self._resource_type != ResourceType.PODS:
            self.notify_user(
                f"Exec not available for {self._resource_type.value}",
                severity="warning",
            )
            return

        containers = getattr(self._resource, "containers", [])
        container_names = [c.name for c in containers if c.name]

        if len(container_names) > 1:
            from system_operations_manager.tui.apps.kubernetes.widgets import (
                SelectorPopup,
            )

            self.app.push_screen(
                SelectorPopup(
                    "Select Container for Exec",
                    container_names,
                    container_names[0],
                ),
                callback=self._handle_exec_container_selected,
            )
        else:
            container = container_names[0] if container_names else None
            self._run_exec(container)

    def _handle_exec_container_selected(self, result: str | None) -> None:
        """Handle container selection for exec.

        Args:
            result: Selected container name or None if dismissed.
        """
        if result:
            self._run_exec(result)

    def _run_exec(self, container: str | None) -> None:
        """Suspend TUI and run an interactive exec session.

        Args:
            container: Container name to exec into (None for default).
        """
        from system_operations_manager.services.kubernetes.streaming_manager import (
            StreamingManager,
        )

        try:
            mgr = StreamingManager(self._client)
            ws_client = mgr.exec_command(
                self._resource.name,
                self._resource.namespace,
                container=container,
                stdin=True,
                tty=True,
            )
        except Exception as e:
            self.notify_user(f"Exec failed: {e}", severity="error")
            return

        try:
            import select
            import termios
            import tty as tty_module
        except ImportError:
            self.notify_user(
                "Interactive exec requires a Unix terminal",
                severity="error",
            )
            ws_client.close()
            return

        import sys

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            with self.app.suspend():
                tty_module.setraw(sys.stdin.fileno())
                while ws_client.is_open():
                    ws_client.update(timeout=0.1)
                    if ws_client.peek_stdout():
                        sys.stdout.write(ws_client.read_stdout())
                        sys.stdout.flush()
                    if ws_client.peek_stderr():
                        sys.stderr.write(ws_client.read_stderr())
                        sys.stderr.flush()

                    readable, _, _ = select.select([sys.stdin], [], [], 0)
                    if readable:
                        data = sys.stdin.read(1)
                        if data:
                            ws_client.write_stdin(data)
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            ws_client.close()
