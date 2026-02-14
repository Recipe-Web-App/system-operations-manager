"""CLI commands for Kubernetes networking resources.

Provides commands for managing services, ingresses, and network policies
via the NetworkingManager service.
"""

from __future__ import annotations

import json
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
    from system_operations_manager.services.kubernetes import NetworkingManager

# =============================================================================
# Column Definitions
# =============================================================================

SERVICE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("type", "Type"),
    ("cluster_ip", "Cluster-IP"),
    ("external_ip", "External-IP"),
    ("ports", "Ports"),
    ("age", "Age"),
]

INGRESS_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("class_name", "Class"),
    ("hosts", "Hosts"),
    ("addresses", "Addresses"),
    ("age", "Age"),
]

NETWORK_POLICY_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("policy_types", "Policy Types"),
    ("ingress_rules_count", "Ingress Rules"),
    ("egress_rules_count", "Egress Rules"),
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


def _parse_port(port_str: str) -> dict[str, int | str]:
    """Parse port string in format 'port:targetPort/protocol'."""
    protocol = "TCP"
    if "/" in port_str:
        port_str, protocol = port_str.rsplit("/", 1)

    if ":" in port_str:
        port_part, target_part = port_str.split(":", 1)
        return {
            "port": int(port_part),
            "target_port": int(target_part),
            "protocol": protocol,
        }
    return {
        "port": int(port_str),
        "target_port": int(port_str),
        "protocol": protocol,
    }


# =============================================================================
# Command Registration
# =============================================================================


def register_networking_commands(
    app: typer.Typer,
    get_manager: Callable[[], NetworkingManager],
) -> None:
    """Register networking CLI commands."""

    # -------------------------------------------------------------------------
    # Services
    # -------------------------------------------------------------------------

    services_app = typer.Typer(
        name="services",
        help="Manage Kubernetes services",
        no_args_is_help=True,
    )
    app.add_typer(services_app, name="services")

    @services_app.command("list")
    def list_services(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List services.

        Examples:
            ops k8s services list
            ops k8s services list -A
            ops k8s services list -l app=nginx
        """
        try:
            manager = get_manager()
            resources = manager.list_services(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, SERVICE_COLUMNS, title="Services")
        except KubernetesError as e:
            handle_k8s_error(e)

    @services_app.command("get")
    def get_service(
        name: str = typer.Argument(help="Service name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a service.

        Examples:
            ops k8s services get my-service
            ops k8s services get my-service -o json
        """
        try:
            manager = get_manager()
            resource = manager.get_service(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Service: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @services_app.command("create")
    def create_service(
        name: str = typer.Argument(help="Service name"),
        namespace: NamespaceOption = None,
        service_type: str = typer.Option(
            "ClusterIP",
            "--type",
            "-t",
            help="Service type (ClusterIP, NodePort, LoadBalancer)",
        ),
        selector: list[str] | None = typer.Option(
            None,
            "--selector",
            "-s",
            help="Pod selector (key=value, repeatable)",
        ),
        port: list[str] | None = typer.Option(
            None,
            "--port",
            "-p",
            help="Port mapping (port:targetPort/protocol, repeatable)",
        ),
        label: list[str] | None = typer.Option(
            None,
            "--label",
            "-l",
            help="Labels (key=value, repeatable)",
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a service.

        Examples:
            ops k8s services create my-svc --type ClusterIP --port 80:8080/TCP --selector app=web
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            selector_dict = _parse_labels(selector)
            ports = [_parse_port(p) for p in port] if port else None

            resource = manager.create_service(
                name,
                namespace=namespace,
                type=service_type,
                selector=selector_dict,
                ports=ports,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Service: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @services_app.command("update")
    def update_service(
        name: str = typer.Argument(help="Service name"),
        namespace: NamespaceOption = None,
        service_type: str | None = typer.Option(
            None,
            "--type",
            "-t",
            help="New service type",
        ),
        selector: list[str] | None = typer.Option(
            None,
            "--selector",
            "-s",
            help="New pod selector (key=value, repeatable)",
        ),
        port: list[str] | None = typer.Option(
            None,
            "--port",
            "-p",
            help="New port mapping (port:targetPort/protocol, repeatable)",
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a service.

        Examples:
            ops k8s services update my-svc --type LoadBalancer
        """
        try:
            manager = get_manager()
            selector_dict = _parse_labels(selector)
            ports = [_parse_port(p) for p in port] if port else None

            resource = manager.update_service(
                name,
                namespace=namespace,
                type=service_type,
                selector=selector_dict,
                ports=ports,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Updated Service: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @services_app.command("delete")
    def delete_service(
        name: str = typer.Argument(help="Service name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a service.

        Examples:
            ops k8s services delete my-service
            ops k8s services delete my-service --force
        """
        try:
            if not force and not confirm_delete("service", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_service(name, namespace=namespace)
            console.print(f"[green]Service '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Ingresses
    # -------------------------------------------------------------------------

    ingresses_app = typer.Typer(
        name="ingresses",
        help="Manage Kubernetes ingresses",
        no_args_is_help=True,
    )
    app.add_typer(ingresses_app, name="ingresses")

    @ingresses_app.command("list")
    def list_ingresses(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ingresses.

        Examples:
            ops k8s ingresses list
            ops k8s ingresses list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_ingresses(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, INGRESS_COLUMNS, title="Ingresses")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ingresses_app.command("get")
    def get_ingress(
        name: str = typer.Argument(help="Ingress name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an ingress.

        Examples:
            ops k8s ingresses get my-ingress
        """
        try:
            manager = get_manager()
            resource = manager.get_ingress(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Ingress: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ingresses_app.command("create")
    def create_ingress(
        name: str = typer.Argument(help="Ingress name"),
        namespace: NamespaceOption = None,
        class_name: str | None = typer.Option(
            None, "--class-name", help="Ingress class (e.g., nginx)"
        ),
        rule: list[str] | None = typer.Option(
            None, "--rule", help="Ingress rule as JSON string (repeatable)"
        ),
        tls: list[str] | None = typer.Option(
            None, "--tls", help="TLS config as JSON string (repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ingress.

        Examples:
            ops k8s ingresses create my-ingress --class-name nginx \\
                --rule '{"host":"example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"web","service_port":80}]}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            rules = [json.loads(r) for r in rule] if rule else None
            tls_configs = [json.loads(t) for t in tls] if tls else None

            resource = manager.create_ingress(
                name,
                namespace=namespace,
                class_name=class_name,
                rules=rules,
                tls=tls_configs,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Ingress: {name}")
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON: {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    @ingresses_app.command("update")
    def update_ingress(
        name: str = typer.Argument(help="Ingress name"),
        namespace: NamespaceOption = None,
        class_name: str | None = typer.Option(None, "--class-name", help="New ingress class"),
        rule: list[str] | None = typer.Option(
            None, "--rule", help="New ingress rule as JSON string (repeatable)"
        ),
        tls: list[str] | None = typer.Option(
            None, "--tls", help="New TLS config as JSON string (repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an ingress.

        Examples:
            ops k8s ingresses update my-ingress --class-name nginx
        """
        try:
            manager = get_manager()
            rules = [json.loads(r) for r in rule] if rule else None
            tls_configs = [json.loads(t) for t in tls] if tls else None

            resource = manager.update_ingress(
                name,
                namespace=namespace,
                class_name=class_name,
                rules=rules,
                tls=tls_configs,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Updated Ingress: {name}")
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON: {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    @ingresses_app.command("delete")
    def delete_ingress(
        name: str = typer.Argument(help="Ingress name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete an ingress.

        Examples:
            ops k8s ingresses delete my-ingress
        """
        try:
            if not force and not confirm_delete("ingress", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_ingress(name, namespace=namespace)
            console.print(f"[green]Ingress '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Network Policies
    # -------------------------------------------------------------------------

    netpol_app = typer.Typer(
        name="network-policies",
        help="Manage Kubernetes network policies",
        no_args_is_help=True,
    )
    app.add_typer(netpol_app, name="network-policies")

    @netpol_app.command("list")
    def list_network_policies(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List network policies.

        Examples:
            ops k8s network-policies list
            ops k8s network-policies list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_network_policies(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, NETWORK_POLICY_COLUMNS, title="Network Policies")
        except KubernetesError as e:
            handle_k8s_error(e)

    @netpol_app.command("get")
    def get_network_policy(
        name: str = typer.Argument(help="NetworkPolicy name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a network policy.

        Examples:
            ops k8s network-policies get deny-all
        """
        try:
            manager = get_manager()
            resource = manager.get_network_policy(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"NetworkPolicy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @netpol_app.command("create")
    def create_network_policy(
        name: str = typer.Argument(help="NetworkPolicy name"),
        namespace: NamespaceOption = None,
        pod_selector: list[str] | None = typer.Option(
            None, "--pod-selector", help="Pod selector (key=value, repeatable)"
        ),
        policy_type: list[str] | None = typer.Option(
            None, "--policy-type", help="Policy type: Ingress or Egress (repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a network policy.

        Examples:
            ops k8s network-policies create deny-all --pod-selector app=web --policy-type Ingress
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            selector_dict = _parse_labels(pod_selector)

            resource = manager.create_network_policy(
                name,
                namespace=namespace,
                pod_selector=selector_dict,
                policy_types=policy_type,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created NetworkPolicy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @netpol_app.command("delete")
    def delete_network_policy(
        name: str = typer.Argument(help="NetworkPolicy name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a network policy.

        Examples:
            ops k8s network-policies delete deny-all
        """
        try:
            if not force and not confirm_delete("network policy", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_network_policy(name, namespace=namespace)
            console.print(f"[green]NetworkPolicy '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
