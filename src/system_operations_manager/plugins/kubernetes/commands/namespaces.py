"""CLI commands for Kubernetes namespace resources.

Provides commands for managing namespaces
via the NamespaceClusterManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    ForceOption,
    LabelSelectorOption,
    OutputOption,
    confirm_delete,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes import NamespaceClusterManager

# =============================================================================
# Column Definitions
# =============================================================================

NAMESPACE_COLUMNS = [
    ("name", "Name"),
    ("status", "Status"),
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


def register_namespace_commands(
    app: typer.Typer,
    get_manager: Callable[[], NamespaceClusterManager],
) -> None:
    """Register namespace CLI commands."""

    namespaces_app = typer.Typer(
        name="namespaces",
        help="Manage Kubernetes namespaces",
        no_args_is_help=True,
    )
    app.add_typer(namespaces_app, name="namespaces")

    @namespaces_app.command("list")
    def list_namespaces(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List namespaces.

        Examples:
            ops k8s namespaces list
            ops k8s namespaces list -l env=production
        """
        try:
            manager = get_manager()
            resources = manager.list_namespaces(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, NAMESPACE_COLUMNS, title="Namespaces")
        except KubernetesError as e:
            handle_k8s_error(e)

    @namespaces_app.command("get")
    def get_namespace(
        name: str = typer.Argument(help="Namespace name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a namespace.

        Examples:
            ops k8s namespaces get kube-system
        """
        try:
            manager = get_manager()
            resource = manager.get_namespace(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Namespace: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @namespaces_app.command("create")
    def create_namespace(
        name: str = typer.Argument(help="Namespace name"),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a namespace.

        Examples:
            ops k8s namespaces create my-namespace
            ops k8s namespaces create my-namespace --label env=dev
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_namespace(name, labels=labels)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Namespace: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @namespaces_app.command("delete")
    def delete_namespace(
        name: str = typer.Argument(help="Namespace name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a namespace.

        Examples:
            ops k8s namespaces delete my-namespace
            ops k8s namespaces delete my-namespace --force
        """
        try:
            if not force and not confirm_delete("namespace", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_namespace(name)
            console.print(f"[green]Namespace '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
