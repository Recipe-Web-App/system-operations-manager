"""Screen definitions for Kubernetes resource browser TUI.

This module provides the main resource list screen with DataTable display,
namespace/cluster selectors, and resource type filtering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import DataTable, Label

from system_operations_manager.integrations.kubernetes.models.base import K8sEntityBase
from system_operations_manager.tui.apps.kubernetes.app import (
    CLUSTER_SCOPED_TYPES,
    RESOURCE_TYPE_ORDER,
    ResourceType,
)
from system_operations_manager.tui.apps.kubernetes.widgets import (
    ClusterSelector,
    NamespaceSelector,
    ResourceTypeFilter,
)
from system_operations_manager.tui.base import BaseScreen

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient
    from system_operations_manager.integrations.kubernetes.models.cluster import (
        EventSummary,
        NamespaceSummary,
        NodeSummary,
    )
    from system_operations_manager.integrations.kubernetes.models.configuration import (
        ConfigMapSummary,
        SecretSummary,
    )
    from system_operations_manager.integrations.kubernetes.models.networking import (
        IngressSummary,
        NetworkPolicySummary,
        ServiceSummary,
    )
    from system_operations_manager.integrations.kubernetes.models.workloads import (
        DaemonSetSummary,
        DeploymentSummary,
        PodSummary,
        ReplicaSetSummary,
        StatefulSetSummary,
    )

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
        return (r.name, r.namespace or "", ready, str(r.updated_replicas), str(r.available_replicas), r.age)

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
        self._resources: list[K8sEntityBase] = []
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

    def _fetch_resources(self) -> list[K8sEntityBase]:
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
    def _workload_mgr(self) -> Any:
        """Lazy-load WorkloadManager."""
        from system_operations_manager.services.kubernetes.workload_manager import WorkloadManager

        return WorkloadManager(self._client)

    @property
    def _networking_mgr(self) -> Any:
        """Lazy-load NetworkingManager."""
        from system_operations_manager.services.kubernetes.networking_manager import (
            NetworkingManager,
        )

        return NetworkingManager(self._client)

    @property
    def _config_mgr(self) -> Any:
        """Lazy-load ConfigurationManager."""
        from system_operations_manager.services.kubernetes.configuration_manager import (
            ConfigurationManager,
        )

        return ConfigurationManager(self._client)

    @property
    def _namespace_mgr(self) -> Any:
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
        self._current_namespace = event.namespace
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
    def handle_resource_type_changed(
        self, event: ResourceTypeFilter.ResourceTypeChanged
    ) -> None:
        """Handle resource type change from filter widget."""
        self._current_type = event.resource_type
        self._load_resources()
