"""Screen definitions for Kubernetes resource browser TUI.

This module provides the main resource list screen with DataTable display,
namespace/cluster selectors, and resource type filtering. Also includes
the cluster status dashboard screen with auto-refresh.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import structlog
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Label

from system_operations_manager.integrations.kubernetes.models.base import K8sEntityBase
from system_operations_manager.tui.apps.kubernetes.types import (
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
