"""CLI commands for Kubernetes storage resources.

Provides commands for managing persistent volumes, persistent volume claims,
and storage classes via the StorageManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    AllNamespacesOption,
    ForceOption,
    LabelSelectorOption,
    NamespaceOption,
    OutputOption,
    confirm_delete,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes import StorageManager

# =============================================================================
# Column Definitions
# =============================================================================

PV_COLUMNS = [
    ("name", "Name"),
    ("capacity", "Capacity"),
    ("access_modes", "Access Modes"),
    ("reclaim_policy", "Reclaim Policy"),
    ("status", "Status"),
    ("storage_class", "StorageClass"),
    ("age", "Age"),
]

PVC_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("status", "Status"),
    ("volume", "Volume"),
    ("capacity", "Capacity"),
    ("access_modes", "Access Modes"),
    ("storage_class", "StorageClass"),
    ("age", "Age"),
]

STORAGE_CLASS_COLUMNS = [
    ("name", "Name"),
    ("provisioner", "Provisioner"),
    ("reclaim_policy", "Reclaim Policy"),
    ("volume_binding_mode", "Binding Mode"),
    ("allow_volume_expansion", "Allow Expansion"),
    ("age", "Age"),
]


# =============================================================================
# Helpers
# =============================================================================


def _parse_labels(labels: list[str] | None) -> dict[str, str] | None:
    """Parse key=value label strings into a dict."""
    if not labels:
        return None
    result: dict[str, str] = {}
    for label in labels:
        key, sep, value = label.partition("=")
        if not sep:
            console.print(f"[red]Error:[/red] Invalid label format '{label}', expected key=value")
            raise typer.Exit(1)
        result[key] = value
    return result


# =============================================================================
# Command Registration
# =============================================================================


def register_storage_commands(
    app: typer.Typer,
    get_manager: Callable[[], StorageManager],
) -> None:
    """Register storage CLI commands."""

    # -------------------------------------------------------------------------
    # Persistent Volumes (cluster-scoped)
    # -------------------------------------------------------------------------

    pvs_app = typer.Typer(
        name="pvs",
        help="Manage Kubernetes persistent volumes",
        no_args_is_help=True,
    )
    app.add_typer(pvs_app, name="pvs")

    @pvs_app.command("list")
    def list_pvs(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List persistent volumes.

        Examples:
            ops k8s pvs list
            ops k8s pvs list -l tier=fast
        """
        try:
            manager = get_manager()
            resources = manager.list_persistent_volumes(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, PV_COLUMNS, title="Persistent Volumes")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pvs_app.command("get")
    def get_pv(
        name: str = typer.Argument(help="PersistentVolume name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a persistent volume.

        Examples:
            ops k8s pvs get pv-data-01
        """
        try:
            manager = get_manager()
            resource = manager.get_persistent_volume(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"PersistentVolume: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pvs_app.command("delete")
    def delete_pv(
        name: str = typer.Argument(help="PersistentVolume name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a persistent volume.

        Examples:
            ops k8s pvs delete pv-data-01
        """
        try:
            if not force and not confirm_delete("persistent volume", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_persistent_volume(name)
            console.print(f"[green]PersistentVolume '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Persistent Volume Claims (namespaced)
    # -------------------------------------------------------------------------

    pvcs_app = typer.Typer(
        name="pvcs",
        help="Manage Kubernetes persistent volume claims",
        no_args_is_help=True,
    )
    app.add_typer(pvcs_app, name="pvcs")

    @pvcs_app.command("list")
    def list_pvcs(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List persistent volume claims.

        Examples:
            ops k8s pvcs list
            ops k8s pvcs list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_persistent_volume_claims(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, PVC_COLUMNS, title="Persistent Volume Claims")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pvcs_app.command("get")
    def get_pvc(
        name: str = typer.Argument(help="PVC name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a persistent volume claim.

        Examples:
            ops k8s pvcs get data-pvc
        """
        try:
            manager = get_manager()
            resource = manager.get_persistent_volume_claim(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"PVC: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pvcs_app.command("create")
    def create_pvc(
        name: str = typer.Argument(help="PVC name"),
        namespace: NamespaceOption = None,
        storage_class: str | None = typer.Option(None, "--storage-class", help="StorageClass name"),
        access_mode: list[str] | None = typer.Option(
            None, "--access-mode", help="Access mode (repeatable, e.g., ReadWriteOnce)"
        ),
        storage: str = typer.Option("1Gi", "--storage", help="Storage size (e.g., 10Gi)"),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a persistent volume claim.

        Examples:
            ops k8s pvcs create data-pvc --storage 10Gi --access-mode ReadWriteOnce
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_persistent_volume_claim(
                name,
                namespace=namespace,
                storage_class=storage_class,
                access_modes=access_mode,
                storage=storage,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created PVC: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pvcs_app.command("delete")
    def delete_pvc(
        name: str = typer.Argument(help="PVC name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a persistent volume claim.

        Examples:
            ops k8s pvcs delete data-pvc
        """
        try:
            if not force and not confirm_delete("PVC", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_persistent_volume_claim(name, namespace=namespace)
            console.print(f"[green]PVC '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Storage Classes (cluster-scoped)
    # -------------------------------------------------------------------------

    sc_app = typer.Typer(
        name="storage-classes",
        help="View Kubernetes storage classes",
        no_args_is_help=True,
    )
    app.add_typer(sc_app, name="storage-classes")

    @sc_app.command("list")
    def list_storage_classes(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List storage classes.

        Examples:
            ops k8s storage-classes list
        """
        try:
            manager = get_manager()
            resources = manager.list_storage_classes()
            formatter = get_formatter(output, console)
            formatter.format_list(resources, STORAGE_CLASS_COLUMNS, title="Storage Classes")
        except KubernetesError as e:
            handle_k8s_error(e)

    @sc_app.command("get")
    def get_storage_class(
        name: str = typer.Argument(help="StorageClass name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a storage class.

        Examples:
            ops k8s storage-classes get standard
        """
        try:
            manager = get_manager()
            resource = manager.get_storage_class(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"StorageClass: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)
