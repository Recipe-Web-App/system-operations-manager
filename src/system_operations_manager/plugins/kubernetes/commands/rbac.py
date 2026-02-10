"""CLI commands for Kubernetes RBAC resources.

Provides commands for managing service accounts, roles, cluster roles,
role bindings, and cluster role bindings via the RBACManager service.
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
    from system_operations_manager.services.kubernetes import RBACManager

# =============================================================================
# Column Definitions
# =============================================================================

SERVICE_ACCOUNT_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("secrets_count", "Secrets"),
    ("age", "Age"),
]

ROLE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("rules_count", "Rules"),
    ("age", "Age"),
]

CLUSTER_ROLE_COLUMNS = [
    ("name", "Name"),
    ("rules_count", "Rules"),
    ("age", "Age"),
]

ROLE_BINDING_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("role_ref_kind", "Role Kind"),
    ("role_ref_name", "Role Name"),
    ("subjects", "Subjects"),
    ("age", "Age"),
]

CLUSTER_ROLE_BINDING_COLUMNS = [
    ("name", "Name"),
    ("role_ref_kind", "Role Kind"),
    ("role_ref_name", "Role Name"),
    ("subjects", "Subjects"),
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


def _parse_json_option(value: str, label: str) -> dict[str, str]:
    """Parse a JSON string option."""
    try:
        result: dict[str, str] = json.loads(value)
        return result
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON for {label}: {e}")
        raise typer.Exit(1) from None


def _parse_json_list_option(values: list[str] | None, label: str) -> list[dict[str, str]] | None:
    """Parse a list of JSON string options."""
    if not values:
        return None
    return [_parse_json_option(v, label) for v in values]


# =============================================================================
# Command Registration
# =============================================================================


def register_rbac_commands(
    app: typer.Typer,
    get_manager: Callable[[], RBACManager],
) -> None:
    """Register RBAC CLI commands."""

    # -------------------------------------------------------------------------
    # Service Accounts
    # -------------------------------------------------------------------------

    sa_app = typer.Typer(
        name="service-accounts",
        help="Manage Kubernetes service accounts",
        no_args_is_help=True,
    )
    app.add_typer(sa_app, name="service-accounts")

    @sa_app.command("list")
    def list_service_accounts(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List service accounts.

        Examples:
            ops k8s service-accounts list
            ops k8s service-accounts list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_service_accounts(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, SERVICE_ACCOUNT_COLUMNS, title="Service Accounts")
        except KubernetesError as e:
            handle_k8s_error(e)

    @sa_app.command("get")
    def get_service_account(
        name: str = typer.Argument(help="ServiceAccount name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a service account.

        Examples:
            ops k8s service-accounts get default
        """
        try:
            manager = get_manager()
            resource = manager.get_service_account(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ServiceAccount: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @sa_app.command("create")
    def create_service_account(
        name: str = typer.Argument(help="ServiceAccount name"),
        namespace: NamespaceOption = None,
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a service account.

        Examples:
            ops k8s service-accounts create my-sa
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_service_account(name, namespace=namespace, labels=labels)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ServiceAccount: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @sa_app.command("delete")
    def delete_service_account(
        name: str = typer.Argument(help="ServiceAccount name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a service account.

        Examples:
            ops k8s service-accounts delete my-sa
        """
        try:
            if not force and not confirm_delete("service account", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_service_account(name, namespace=namespace)
            console.print(f"[green]ServiceAccount '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Roles (namespaced)
    # -------------------------------------------------------------------------

    roles_app = typer.Typer(
        name="roles",
        help="Manage Kubernetes roles",
        no_args_is_help=True,
    )
    app.add_typer(roles_app, name="roles")

    @roles_app.command("list")
    def list_roles(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List roles.

        Examples:
            ops k8s roles list
            ops k8s roles list -n kube-system
        """
        try:
            manager = get_manager()
            resources = manager.list_roles(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ROLE_COLUMNS, title="Roles")
        except KubernetesError as e:
            handle_k8s_error(e)

    @roles_app.command("get")
    def get_role(
        name: str = typer.Argument(help="Role name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a role.

        Examples:
            ops k8s roles get pod-reader
        """
        try:
            manager = get_manager()
            resource = manager.get_role(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Role: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @roles_app.command("create")
    def create_role(
        name: str = typer.Argument(help="Role name"),
        namespace: NamespaceOption = None,
        rule: list[str] | None = typer.Option(
            None, "--rule", help="Policy rule as JSON (repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a role.

        Examples:
            ops k8s roles create pod-reader \\
                --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["pods"]}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            rules = _parse_json_list_option(rule, "rule")

            resource = manager.create_role(name, namespace=namespace, rules=rules, labels=labels)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Role: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @roles_app.command("delete")
    def delete_role(
        name: str = typer.Argument(help="Role name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a role.

        Examples:
            ops k8s roles delete pod-reader
        """
        try:
            if not force and not confirm_delete("role", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_role(name, namespace=namespace)
            console.print(f"[green]Role '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Cluster Roles (cluster-scoped)
    # -------------------------------------------------------------------------

    cluster_roles_app = typer.Typer(
        name="cluster-roles",
        help="Manage Kubernetes cluster roles",
        no_args_is_help=True,
    )
    app.add_typer(cluster_roles_app, name="cluster-roles")

    @cluster_roles_app.command("list")
    def list_cluster_roles(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List cluster roles.

        Examples:
            ops k8s cluster-roles list
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_roles(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CLUSTER_ROLE_COLUMNS, title="Cluster Roles")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cluster_roles_app.command("get")
    def get_cluster_role(
        name: str = typer.Argument(help="ClusterRole name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a cluster role.

        Examples:
            ops k8s cluster-roles get cluster-admin
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_role(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterRole: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cluster_roles_app.command("create")
    def create_cluster_role(
        name: str = typer.Argument(help="ClusterRole name"),
        rule: list[str] | None = typer.Option(
            None, "--rule", help="Policy rule as JSON (repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a cluster role.

        Examples:
            ops k8s cluster-roles create node-reader \\
                --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["nodes"]}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            rules = _parse_json_list_option(rule, "rule")

            resource = manager.create_cluster_role(name, rules=rules, labels=labels)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ClusterRole: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cluster_roles_app.command("delete")
    def delete_cluster_role(
        name: str = typer.Argument(help="ClusterRole name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a cluster role.

        Examples:
            ops k8s cluster-roles delete node-reader
        """
        try:
            if not force and not confirm_delete("cluster role", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cluster_role(name)
            console.print(f"[green]ClusterRole '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Role Bindings (namespaced)
    # -------------------------------------------------------------------------

    rb_app = typer.Typer(
        name="role-bindings",
        help="Manage Kubernetes role bindings",
        no_args_is_help=True,
    )
    app.add_typer(rb_app, name="role-bindings")

    @rb_app.command("list")
    def list_role_bindings(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List role bindings.

        Examples:
            ops k8s role-bindings list
            ops k8s role-bindings list -n default
        """
        try:
            manager = get_manager()
            resources = manager.list_role_bindings(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ROLE_BINDING_COLUMNS, title="Role Bindings")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rb_app.command("get")
    def get_role_binding(
        name: str = typer.Argument(help="RoleBinding name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a role binding.

        Examples:
            ops k8s role-bindings get read-pods
        """
        try:
            manager = get_manager()
            resource = manager.get_role_binding(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"RoleBinding: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rb_app.command("create")
    def create_role_binding(
        name: str = typer.Argument(help="RoleBinding name"),
        namespace: NamespaceOption = None,
        role_ref: str = typer.Option(
            ...,
            "--role-ref",
            help='Role reference as JSON (e.g., \'{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}\')',
        ),
        subject: list[str] | None = typer.Option(
            None,
            "--subject",
            help='Subject as JSON (repeatable, e.g., \'{"kind":"User","name":"jane"}\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a role binding.

        Examples:
            ops k8s role-bindings create read-pods \\
                --role-ref '{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}' \\
                --subject '{"kind":"User","name":"jane"}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            role_ref_dict = _parse_json_option(role_ref, "role-ref")
            subjects_list = _parse_json_list_option(subject, "subject") or []

            resource = manager.create_role_binding(
                name,
                namespace=namespace,
                role_ref=role_ref_dict,
                subjects=subjects_list,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created RoleBinding: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rb_app.command("delete")
    def delete_role_binding(
        name: str = typer.Argument(help="RoleBinding name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a role binding.

        Examples:
            ops k8s role-bindings delete read-pods
        """
        try:
            if not force and not confirm_delete("role binding", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_role_binding(name, namespace=namespace)
            console.print(f"[green]RoleBinding '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Cluster Role Bindings (cluster-scoped)
    # -------------------------------------------------------------------------

    crb_app = typer.Typer(
        name="cluster-role-bindings",
        help="Manage Kubernetes cluster role bindings",
        no_args_is_help=True,
    )
    app.add_typer(crb_app, name="cluster-role-bindings")

    @crb_app.command("list")
    def list_cluster_role_bindings(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List cluster role bindings.

        Examples:
            ops k8s cluster-role-bindings list
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_role_bindings(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(
                resources, CLUSTER_ROLE_BINDING_COLUMNS, title="Cluster Role Bindings"
            )
        except KubernetesError as e:
            handle_k8s_error(e)

    @crb_app.command("get")
    def get_cluster_role_binding(
        name: str = typer.Argument(help="ClusterRoleBinding name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a cluster role binding.

        Examples:
            ops k8s cluster-role-bindings get cluster-admin-binding
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_role_binding(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterRoleBinding: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @crb_app.command("create")
    def create_cluster_role_binding(
        name: str = typer.Argument(help="ClusterRoleBinding name"),
        role_ref: str = typer.Option(
            ...,
            "--role-ref",
            help="Role reference as JSON",
        ),
        subject: list[str] | None = typer.Option(
            None,
            "--subject",
            help="Subject as JSON (repeatable)",
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a cluster role binding.

        Examples:
            ops k8s cluster-role-bindings create admin-binding \\
                --role-ref '{"kind":"ClusterRole","name":"cluster-admin","api_group":"rbac.authorization.k8s.io"}' \\
                --subject '{"kind":"User","name":"admin"}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            role_ref_dict = _parse_json_option(role_ref, "role-ref")
            subjects_list = _parse_json_list_option(subject, "subject") or []

            resource = manager.create_cluster_role_binding(
                name,
                role_ref=role_ref_dict,
                subjects=subjects_list,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ClusterRoleBinding: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @crb_app.command("delete")
    def delete_cluster_role_binding(
        name: str = typer.Argument(help="ClusterRoleBinding name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a cluster role binding.

        Examples:
            ops k8s cluster-role-bindings delete admin-binding
        """
        try:
            if not force and not confirm_delete("cluster role binding", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cluster_role_binding(name)
            console.print(f"[green]ClusterRoleBinding '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
