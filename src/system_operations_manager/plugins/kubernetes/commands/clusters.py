"""CLI commands for Kubernetes cluster-level resources.

Provides commands for managing nodes, events, and cluster info
via the NamespaceClusterManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    AllNamespacesOption,
    FieldSelectorOption,
    LabelSelectorOption,
    NamespaceOption,
    OutputOption,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes import NamespaceClusterManager

# =============================================================================
# Column Definitions
# =============================================================================

NODE_COLUMNS = [
    ("name", "Name"),
    ("status", "Status"),
    ("roles", "Roles"),
    ("version", "Version"),
    ("internal_ip", "Internal-IP"),
    ("os_image", "OS Image"),
    ("age", "Age"),
]

EVENT_COLUMNS = [
    ("last_timestamp", "Last Seen"),
    ("type", "Type"),
    ("reason", "Reason"),
    ("source_component", "Source"),
    ("message", "Message"),
    ("count", "Count"),
]

# =============================================================================
# Custom Option Annotations
# =============================================================================

InvolvedObjectOption = Annotated[
    str | None,
    typer.Option(
        "--involved-object",
        help="Filter events by involved object name",
    ),
]


# =============================================================================
# Command Registration
# =============================================================================


def register_cluster_commands(
    app: typer.Typer,
    get_manager: Callable[[], NamespaceClusterManager],
) -> None:
    """Register cluster-level CLI commands."""

    # -------------------------------------------------------------------------
    # Nodes
    # -------------------------------------------------------------------------

    nodes_app = typer.Typer(
        name="nodes",
        help="Manage Kubernetes nodes",
        no_args_is_help=True,
    )
    app.add_typer(nodes_app, name="nodes")

    @nodes_app.command("list")
    def list_nodes(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List cluster nodes.

        Examples:
            ops k8s nodes list
            ops k8s nodes list -l node-role.kubernetes.io/control-plane=
        """
        try:
            manager = get_manager()
            resources = manager.list_nodes(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, NODE_COLUMNS, title="Nodes")
        except KubernetesError as e:
            handle_k8s_error(e)

    @nodes_app.command("get")
    def get_node(
        name: str = typer.Argument(help="Node name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a node.

        Examples:
            ops k8s nodes get worker-1
        """
        try:
            manager = get_manager()
            resource = manager.get_node(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Node: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    events_app = typer.Typer(
        name="events",
        help="View Kubernetes events",
        no_args_is_help=True,
    )
    app.add_typer(events_app, name="events")

    @events_app.command("list")
    def list_events(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        field_selector: FieldSelectorOption = None,
        involved_object: InvolvedObjectOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List events.

        Examples:
            ops k8s events list
            ops k8s events list -A
            ops k8s events list --involved-object my-pod
            ops k8s events list --field-selector type=Warning
        """
        try:
            manager = get_manager()
            resources = manager.list_events(
                namespace=namespace,
                all_namespaces=all_namespaces,
                field_selector=field_selector,
                involved_object=involved_object,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, EVENT_COLUMNS, title="Events")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Cluster Info
    # -------------------------------------------------------------------------

    @app.command("cluster-info")
    def cluster_info(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show cluster information.

        Examples:
            ops k8s cluster-info
            ops k8s cluster-info -o json
        """
        try:
            manager = get_manager()
            info = manager.get_cluster_info()
            formatter = get_formatter(output, console)
            formatter.format_dict(info, title="Cluster Info")
        except KubernetesError as e:
            handle_k8s_error(e)
