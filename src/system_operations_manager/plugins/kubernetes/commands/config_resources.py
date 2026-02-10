"""CLI commands for Kubernetes configuration resources.

Provides commands for managing configmaps and secrets
via the ConfigurationManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
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
    from system_operations_manager.services.kubernetes import ConfigurationManager

# =============================================================================
# Column Definitions
# =============================================================================

CONFIGMAP_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("data_keys", "Keys"),
    ("age", "Age"),
]

SECRET_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("type", "Type"),
    ("data_keys", "Keys"),
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


def _parse_data(data_items: list[str] | None) -> dict[str, str] | None:
    """Parse key=value data strings into a dict."""
    if not data_items:
        return None
    result: dict[str, str] = {}
    for item in data_items:
        key, sep, value = item.partition("=")
        if not sep:
            console.print(f"[red]Error:[/red] Invalid data format '{item}', expected key=value")
            raise typer.Exit(1)
        result[key] = value
    return result


# =============================================================================
# Command Registration
# =============================================================================


def register_config_commands(
    app: typer.Typer,
    get_manager: Callable[[], ConfigurationManager],
) -> None:
    """Register configuration CLI commands."""

    # -------------------------------------------------------------------------
    # ConfigMaps
    # -------------------------------------------------------------------------

    configmaps_app = typer.Typer(
        name="configmaps",
        help="Manage Kubernetes configmaps",
        no_args_is_help=True,
    )
    app.add_typer(configmaps_app, name="configmaps")

    @configmaps_app.command("list")
    def list_configmaps(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List configmaps.

        Examples:
            ops k8s configmaps list
            ops k8s configmaps list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_config_maps(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CONFIGMAP_COLUMNS, title="ConfigMaps")
        except KubernetesError as e:
            handle_k8s_error(e)

    @configmaps_app.command("get")
    def get_configmap(
        name: str = typer.Argument(help="ConfigMap name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a configmap.

        Examples:
            ops k8s configmaps get my-config
        """
        try:
            manager = get_manager()
            resource = manager.get_config_map(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ConfigMap: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @configmaps_app.command("get-data")
    def get_configmap_data(
        name: str = typer.Argument(help="ConfigMap name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get configmap data key-value pairs.

        Examples:
            ops k8s configmaps get-data my-config
            ops k8s configmaps get-data my-config -o json
        """
        try:
            manager = get_manager()
            data = manager.get_config_map_data(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(data, title=f"ConfigMap Data: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @configmaps_app.command("create")
    def create_configmap(
        name: str = typer.Argument(help="ConfigMap name"),
        namespace: NamespaceOption = None,
        data: list[str] | None = typer.Option(
            None, "--data", "-d", help="Data entries (key=value, repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a configmap.

        Examples:
            ops k8s configmaps create my-config --data key1=value1 --data key2=value2
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            data_dict = _parse_data(data)

            resource = manager.create_config_map(
                name,
                namespace=namespace,
                data=data_dict,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ConfigMap: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @configmaps_app.command("update")
    def update_configmap(
        name: str = typer.Argument(help="ConfigMap name"),
        namespace: NamespaceOption = None,
        data: list[str] | None = typer.Option(
            None, "--data", "-d", help="New data entries (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a configmap's data.

        Examples:
            ops k8s configmaps update my-config --data key1=newvalue
        """
        try:
            manager = get_manager()
            data_dict = _parse_data(data)

            resource = manager.update_config_map(
                name,
                namespace=namespace,
                data=data_dict,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Updated ConfigMap: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @configmaps_app.command("delete")
    def delete_configmap(
        name: str = typer.Argument(help="ConfigMap name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a configmap.

        Examples:
            ops k8s configmaps delete my-config
        """
        try:
            if not force and not confirm_delete("configmap", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_config_map(name, namespace=namespace)
            console.print(f"[green]ConfigMap '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Secrets
    # -------------------------------------------------------------------------

    secrets_app = typer.Typer(
        name="secrets",
        help="Manage Kubernetes secrets",
        no_args_is_help=True,
    )
    app.add_typer(secrets_app, name="secrets")

    @secrets_app.command("list")
    def list_secrets(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List secrets.

        Examples:
            ops k8s secrets list
            ops k8s secrets list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_secrets(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, SECRET_COLUMNS, title="Secrets")
        except KubernetesError as e:
            handle_k8s_error(e)

    @secrets_app.command("get")
    def get_secret(
        name: str = typer.Argument(help="Secret name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a secret (values are hidden).

        Examples:
            ops k8s secrets get my-secret
        """
        try:
            manager = get_manager()
            resource = manager.get_secret(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Secret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @secrets_app.command("create")
    def create_secret(
        name: str = typer.Argument(help="Secret name"),
        namespace: NamespaceOption = None,
        data: list[str] | None = typer.Option(
            None, "--data", "-d", help="Data entries (key=value, repeatable)"
        ),
        secret_type: str = typer.Option("Opaque", "--type", "-t", help="Secret type"),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a secret.

        Examples:
            ops k8s secrets create my-secret --data username=admin --data password=s3cret
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            data_dict = _parse_data(data)

            resource = manager.create_secret(
                name,
                namespace=namespace,
                data=data_dict,
                secret_type=secret_type,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Secret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @secrets_app.command("create-tls")
    def create_tls_secret(
        name: str = typer.Argument(help="Secret name"),
        namespace: NamespaceOption = None,
        cert: Path = typer.Option(..., "--cert", help="Path to PEM-encoded certificate file"),
        key: Path = typer.Option(..., "--key", help="Path to PEM-encoded private key file"),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a TLS secret from certificate and key files.

        Examples:
            ops k8s secrets create-tls my-tls --cert ./tls.crt --key ./tls.key
        """
        try:
            if not cert.exists():
                console.print(f"[red]Error:[/red] Certificate file not found: {cert}")
                raise typer.Exit(1)
            if not key.exists():
                console.print(f"[red]Error:[/red] Key file not found: {key}")
                raise typer.Exit(1)

            manager = get_manager()
            labels = _parse_labels(label)
            cert_content = cert.read_text()
            key_content = key.read_text()

            resource = manager.create_tls_secret(
                name,
                namespace=namespace,
                cert=cert_content,
                key=key_content,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created TLS Secret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @secrets_app.command("create-docker-registry")
    def create_docker_registry_secret(
        name: str = typer.Argument(help="Secret name"),
        namespace: NamespaceOption = None,
        server: str = typer.Option(..., "--server", help="Docker registry server URL"),
        username: str = typer.Option(..., "--username", help="Registry username"),
        password: str = typer.Option(..., "--password", help="Registry password"),
        email: str = typer.Option("", "--email", help="Registry email"),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a docker-registry secret.

        Examples:
            ops k8s secrets create-docker-registry my-reg \\
                --server https://index.docker.io/v1/ \\
                --username user --password pass
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)

            resource = manager.create_docker_registry_secret(
                name,
                namespace=namespace,
                server=server,
                username=username,
                password=password,
                email=email,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Docker Registry Secret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @secrets_app.command("delete")
    def delete_secret(
        name: str = typer.Argument(help="Secret name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a secret.

        Examples:
            ops k8s secrets delete my-secret
        """
        try:
            if not force and not confirm_delete("secret", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_secret(name, namespace=namespace)
            console.print(f"[green]Secret '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
