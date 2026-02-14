"""CLI commands for Kubernetes workload resources.

Provides commands for managing pods, deployments, statefulsets,
daemonsets, and replicasets via the WorkloadManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    AllNamespacesOption,
    FieldSelectorOption,
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
    from system_operations_manager.services.kubernetes import WorkloadManager

# =============================================================================
# Column Definitions
# =============================================================================

POD_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("phase", "Status"),
    ("ready_count", "Ready"),
    ("restarts", "Restarts"),
    ("node_name", "Node"),
    ("pod_ip", "IP"),
    ("age", "Age"),
]

DEPLOYMENT_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("ready_replicas", "Ready"),
    ("replicas", "Desired"),
    ("updated_replicas", "Up-to-date"),
    ("available_replicas", "Available"),
    ("age", "Age"),
]

STATEFULSET_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("ready_replicas", "Ready"),
    ("replicas", "Desired"),
    ("service_name", "Service"),
    ("age", "Age"),
]

DAEMONSET_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("desired_number_scheduled", "Desired"),
    ("current_number_scheduled", "Current"),
    ("number_ready", "Ready"),
    ("age", "Age"),
]

REPLICASET_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("ready_replicas", "Ready"),
    ("replicas", "Desired"),
    ("age", "Age"),
]


# =============================================================================
# Helpers
# =============================================================================


def _parse_labels(labels: list[str] | None) -> dict[str, str] | None:
    """Parse label key=value pairs."""
    if not labels:
        return None
    result: dict[str, str] = {}
    for label in labels:
        key, sep, value = label.partition("=")
        if not sep:
            console.print(f"[red]Error:[/red] Invalid label format '{label}'. Use key=value")
            raise typer.Exit(1)
        result[key] = value
    return result


# =============================================================================
# Registration
# =============================================================================


def register_workload_commands(
    app: typer.Typer,
    get_manager: Callable[[], WorkloadManager],
) -> None:
    """Register workload commands with the Kubernetes CLI app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a WorkloadManager instance.
    """
    # -------------------------------------------------------------------------
    # Pod Commands
    # -------------------------------------------------------------------------
    pods_app = typer.Typer(
        name="pods",
        help="Manage Kubernetes pods",
        no_args_is_help=True,
    )

    @pods_app.command("list")
    def list_pods(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        field_selector: FieldSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List pods.

        Examples:
            ops k8s pods list
            ops k8s pods list --all-namespaces
            ops k8s pods list -n kube-system
            ops k8s pods list -l app=nginx
            ops k8s pods list --field-selector status.phase=Running
        """
        try:
            manager = get_manager()
            pods = manager.list_pods(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
                field_selector=field_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(pods, POD_COLUMNS, title="Pods")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pods_app.command("get")
    def get_pod(
        name: Annotated[str, typer.Argument(help="Pod name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a pod by name.

        Examples:
            ops k8s pods get my-pod
            ops k8s pods get my-pod -n production
            ops k8s pods get my-pod --output yaml
        """
        try:
            manager = get_manager()
            pod = manager.get_pod(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(pod, title=f"Pod: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pods_app.command("delete")
    def delete_pod(
        name: Annotated[str, typer.Argument(help="Pod name")],
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a pod.

        Examples:
            ops k8s pods delete my-pod
            ops k8s pods delete my-pod --force
            ops k8s pods delete my-pod -n production
        """
        try:
            if not force and not confirm_delete("pod", name, namespace):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_pod(name, namespace)
            console.print(f"[green]Pod '{name}' deleted successfully[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pods_app.command("logs")
    def pod_logs(
        name: Annotated[str, typer.Argument(help="Pod name")],
        namespace: NamespaceOption = None,
        container: Annotated[
            str | None,
            typer.Option("--container", "-c", help="Container name"),
        ] = None,
        tail: Annotated[
            int | None,
            typer.Option("--tail", help="Number of lines from the end of the logs"),
        ] = None,
        previous: Annotated[
            bool,
            typer.Option("--previous", "-p", help="Show logs from previous container instance"),
        ] = False,
    ) -> None:
        """Get pod logs.

        Examples:
            ops k8s pods logs my-pod
            ops k8s pods logs my-pod --tail 100
            ops k8s pods logs my-pod -c sidecar
            ops k8s pods logs my-pod --previous
        """
        try:
            manager = get_manager()
            logs = manager.get_pod_logs(
                name, namespace, container=container, tail_lines=tail, previous=previous
            )
            console.print(logs)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Deployment Commands
    # -------------------------------------------------------------------------
    deployments_app = typer.Typer(
        name="deployments",
        help="Manage Kubernetes deployments",
        no_args_is_help=True,
    )

    @deployments_app.command("list")
    def list_deployments(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List deployments.

        Examples:
            ops k8s deployments list
            ops k8s deployments list --all-namespaces
            ops k8s deployments list -n production
            ops k8s deployments list -l app=nginx
        """
        try:
            manager = get_manager()
            deployments = manager.list_deployments(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(deployments, DEPLOYMENT_COLUMNS, title="Deployments")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("get")
    def get_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a deployment by name.

        Examples:
            ops k8s deployments get my-app
            ops k8s deployments get my-app -n production
            ops k8s deployments get my-app --output yaml
        """
        try:
            manager = get_manager()
            deployment = manager.get_deployment(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(deployment, title=f"Deployment: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("create")
    def create_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        image: Annotated[str, typer.Option("--image", "-i", help="Container image")],
        namespace: NamespaceOption = None,
        replicas: Annotated[int, typer.Option("--replicas", "-r", help="Number of replicas")] = 1,
        port: Annotated[
            int | None,
            typer.Option("--port", "-p", help="Container port to expose"),
        ] = None,
        labels: Annotated[
            list[str] | None,
            typer.Option("--label", "-l", help="Labels (key=value, can be repeated)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new deployment.

        Examples:
            ops k8s deployments create my-app --image nginx:1.21
            ops k8s deployments create my-app --image nginx:1.21 --replicas 3
            ops k8s deployments create my-app --image nginx:1.21 --port 80 -l app=nginx
        """
        try:
            manager = get_manager()
            label_dict = _parse_labels(labels)
            deployment = manager.create_deployment(
                name, namespace, image=image, replicas=replicas, labels=label_dict, port=port
            )
            console.print(f"[green]Deployment '{name}' created successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(deployment, title=f"Deployment: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("update")
    def update_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        image: Annotated[
            str | None, typer.Option("--image", "-i", help="New container image")
        ] = None,
        replicas: Annotated[
            int | None, typer.Option("--replicas", "-r", help="New number of replicas")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing deployment.

        Examples:
            ops k8s deployments update my-app --image nginx:1.22
            ops k8s deployments update my-app --replicas 5
            ops k8s deployments update my-app --image nginx:1.22 --replicas 3
        """
        try:
            manager = get_manager()
            deployment = manager.update_deployment(name, namespace, image=image, replicas=replicas)
            console.print(f"[green]Deployment '{name}' updated successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(deployment, title=f"Deployment: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("delete")
    def delete_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a deployment.

        Examples:
            ops k8s deployments delete my-app
            ops k8s deployments delete my-app --force
            ops k8s deployments delete my-app -n production
        """
        try:
            if not force and not confirm_delete("deployment", name, namespace):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_deployment(name, namespace)
            console.print(f"[green]Deployment '{name}' deleted successfully[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("scale")
    def scale_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        replicas: Annotated[int, typer.Option("--replicas", "-r", help="Number of replicas")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Scale a deployment.

        Examples:
            ops k8s deployments scale my-app --replicas 5
            ops k8s deployments scale my-app --replicas 0
            ops k8s deployments scale my-app -r 10 -n production
        """
        try:
            manager = get_manager()
            deployment = manager.scale_deployment(name, namespace, replicas=replicas)
            console.print(f"[green]Deployment '{name}' scaled to {replicas} replicas[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(deployment, title=f"Deployment: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("restart")
    def restart_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Restart a deployment via rolling restart.

        Examples:
            ops k8s deployments restart my-app
            ops k8s deployments restart my-app -n production
        """
        try:
            manager = get_manager()
            deployment = manager.restart_deployment(name, namespace)
            console.print(f"[green]Deployment '{name}' restarted[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(deployment, title=f"Deployment: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("rollout-status")
    def rollout_status(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get rollout status for a deployment.

        Examples:
            ops k8s deployments rollout-status my-app
            ops k8s deployments rollout-status my-app --output json
        """
        try:
            manager = get_manager()
            status = manager.get_rollout_status(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"Rollout Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @deployments_app.command("rollback")
    def rollback_deployment(
        name: Annotated[str, typer.Argument(help="Deployment name")],
        namespace: NamespaceOption = None,
        revision: Annotated[
            int | None,
            typer.Option("--revision", help="Revision to roll back to"),
        ] = None,
    ) -> None:
        """Roll back a deployment to a previous revision.

        Examples:
            ops k8s deployments rollback my-app
            ops k8s deployments rollback my-app --revision 3
            ops k8s deployments rollback my-app -n production
        """
        try:
            manager = get_manager()
            manager.rollback_deployment(name, namespace, revision=revision)
            rev_text = f"revision {revision}" if revision else "previous revision"
            console.print(f"[green]Deployment '{name}' rolled back to {rev_text}[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # StatefulSet Commands
    # -------------------------------------------------------------------------
    statefulsets_app = typer.Typer(
        name="statefulsets",
        help="Manage Kubernetes StatefulSets",
        no_args_is_help=True,
    )

    @statefulsets_app.command("list")
    def list_statefulsets(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List StatefulSets.

        Examples:
            ops k8s statefulsets list
            ops k8s statefulsets list --all-namespaces
            ops k8s statefulsets list -l app=database
        """
        try:
            manager = get_manager()
            sts = manager.list_stateful_sets(
                namespace=namespace, all_namespaces=all_namespaces, label_selector=label_selector
            )
            formatter = get_formatter(output, console)
            formatter.format_list(sts, STATEFULSET_COLUMNS, title="StatefulSets")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("get")
    def get_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a StatefulSet by name.

        Examples:
            ops k8s statefulsets get my-db
            ops k8s statefulsets get my-db --output yaml
        """
        try:
            manager = get_manager()
            sts = manager.get_stateful_set(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(sts, title=f"StatefulSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("create")
    def create_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        image: Annotated[str, typer.Option("--image", "-i", help="Container image")],
        service_name: Annotated[str, typer.Option("--service-name", help="Headless service name")],
        namespace: NamespaceOption = None,
        replicas: Annotated[int, typer.Option("--replicas", "-r", help="Number of replicas")] = 1,
        port: Annotated[int | None, typer.Option("--port", "-p", help="Container port")] = None,
        labels: Annotated[
            list[str] | None,
            typer.Option("--label", "-l", help="Labels (key=value, can be repeated)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new StatefulSet.

        Examples:
            ops k8s statefulsets create my-db --image postgres:15 --service-name my-db-svc
            ops k8s statefulsets create my-db --image postgres:15 --service-name my-db-svc --replicas 3
        """
        try:
            manager = get_manager()
            label_dict = _parse_labels(labels)
            sts = manager.create_stateful_set(
                name,
                namespace,
                image=image,
                replicas=replicas,
                service_name=service_name,
                labels=label_dict,
                port=port,
            )
            console.print(f"[green]StatefulSet '{name}' created successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(sts, title=f"StatefulSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("update")
    def update_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        namespace: NamespaceOption = None,
        image: Annotated[
            str | None, typer.Option("--image", "-i", help="New container image")
        ] = None,
        replicas: Annotated[
            int | None, typer.Option("--replicas", "-r", help="New replica count")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a StatefulSet.

        Examples:
            ops k8s statefulsets update my-db --image postgres:16
            ops k8s statefulsets update my-db --replicas 5
        """
        try:
            manager = get_manager()
            sts = manager.update_stateful_set(name, namespace, image=image, replicas=replicas)
            console.print(f"[green]StatefulSet '{name}' updated successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(sts, title=f"StatefulSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("delete")
    def delete_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a StatefulSet.

        Examples:
            ops k8s statefulsets delete my-db
            ops k8s statefulsets delete my-db --force
        """
        try:
            if not force and not confirm_delete("statefulset", name, namespace):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_stateful_set(name, namespace)
            console.print(f"[green]StatefulSet '{name}' deleted successfully[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("scale")
    def scale_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        replicas: Annotated[int, typer.Option("--replicas", "-r", help="Number of replicas")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Scale a StatefulSet.

        Examples:
            ops k8s statefulsets scale my-db --replicas 5
        """
        try:
            manager = get_manager()
            sts = manager.scale_stateful_set(name, namespace, replicas=replicas)
            console.print(f"[green]StatefulSet '{name}' scaled to {replicas} replicas[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(sts, title=f"StatefulSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @statefulsets_app.command("restart")
    def restart_statefulset(
        name: Annotated[str, typer.Argument(help="StatefulSet name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Restart a StatefulSet via rolling restart.

        Examples:
            ops k8s statefulsets restart my-db
        """
        try:
            manager = get_manager()
            sts = manager.restart_stateful_set(name, namespace)
            console.print(f"[green]StatefulSet '{name}' restarted[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(sts, title=f"StatefulSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # DaemonSet Commands
    # -------------------------------------------------------------------------
    daemonsets_app = typer.Typer(
        name="daemonsets",
        help="Manage Kubernetes DaemonSets",
        no_args_is_help=True,
    )

    @daemonsets_app.command("list")
    def list_daemonsets(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List DaemonSets.

        Examples:
            ops k8s daemonsets list
            ops k8s daemonsets list --all-namespaces
            ops k8s daemonsets list -n kube-system
        """
        try:
            manager = get_manager()
            ds = manager.list_daemon_sets(
                namespace=namespace, all_namespaces=all_namespaces, label_selector=label_selector
            )
            formatter = get_formatter(output, console)
            formatter.format_list(ds, DAEMONSET_COLUMNS, title="DaemonSets")
        except KubernetesError as e:
            handle_k8s_error(e)

    @daemonsets_app.command("get")
    def get_daemonset(
        name: Annotated[str, typer.Argument(help="DaemonSet name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a DaemonSet by name.

        Examples:
            ops k8s daemonsets get my-logger
            ops k8s daemonsets get my-logger --output yaml
        """
        try:
            manager = get_manager()
            ds = manager.get_daemon_set(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(ds, title=f"DaemonSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @daemonsets_app.command("create")
    def create_daemonset(
        name: Annotated[str, typer.Argument(help="DaemonSet name")],
        image: Annotated[str, typer.Option("--image", "-i", help="Container image")],
        namespace: NamespaceOption = None,
        port: Annotated[int | None, typer.Option("--port", "-p", help="Container port")] = None,
        labels: Annotated[
            list[str] | None,
            typer.Option("--label", "-l", help="Labels (key=value, can be repeated)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new DaemonSet.

        Examples:
            ops k8s daemonsets create my-logger --image fluentd:latest
            ops k8s daemonsets create my-logger --image fluentd:latest --port 24224
        """
        try:
            manager = get_manager()
            label_dict = _parse_labels(labels)
            ds = manager.create_daemon_set(
                name, namespace, image=image, labels=label_dict, port=port
            )
            console.print(f"[green]DaemonSet '{name}' created successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(ds, title=f"DaemonSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @daemonsets_app.command("update")
    def update_daemonset(
        name: Annotated[str, typer.Argument(help="DaemonSet name")],
        namespace: NamespaceOption = None,
        image: Annotated[
            str | None, typer.Option("--image", "-i", help="New container image")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a DaemonSet.

        Examples:
            ops k8s daemonsets update my-logger --image fluentd:v2
        """
        try:
            manager = get_manager()
            ds = manager.update_daemon_set(name, namespace, image=image)
            console.print(f"[green]DaemonSet '{name}' updated successfully[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(ds, title=f"DaemonSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @daemonsets_app.command("delete")
    def delete_daemonset(
        name: Annotated[str, typer.Argument(help="DaemonSet name")],
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a DaemonSet.

        Examples:
            ops k8s daemonsets delete my-logger
            ops k8s daemonsets delete my-logger --force
        """
        try:
            if not force and not confirm_delete("daemonset", name, namespace):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_daemon_set(name, namespace)
            console.print(f"[green]DaemonSet '{name}' deleted successfully[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @daemonsets_app.command("restart")
    def restart_daemonset(
        name: Annotated[str, typer.Argument(help="DaemonSet name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Restart a DaemonSet via rolling restart.

        Examples:
            ops k8s daemonsets restart my-logger
        """
        try:
            manager = get_manager()
            ds = manager.restart_daemon_set(name, namespace)
            console.print(f"[green]DaemonSet '{name}' restarted[/green]\n")
            formatter = get_formatter(output, console)
            formatter.format_resource(ds, title=f"DaemonSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ReplicaSet Commands
    # -------------------------------------------------------------------------
    replicasets_app = typer.Typer(
        name="replicasets",
        help="Manage Kubernetes ReplicaSets",
        no_args_is_help=True,
    )

    @replicasets_app.command("list")
    def list_replicasets(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ReplicaSets.

        Examples:
            ops k8s replicasets list
            ops k8s replicasets list --all-namespaces
        """
        try:
            manager = get_manager()
            rs = manager.list_replica_sets(
                namespace=namespace, all_namespaces=all_namespaces, label_selector=label_selector
            )
            formatter = get_formatter(output, console)
            formatter.format_list(rs, REPLICASET_COLUMNS, title="ReplicaSets")
        except KubernetesError as e:
            handle_k8s_error(e)

    @replicasets_app.command("get")
    def get_replicaset(
        name: Annotated[str, typer.Argument(help="ReplicaSet name")],
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a ReplicaSet by name.

        Examples:
            ops k8s replicasets get my-rs
            ops k8s replicasets get my-rs --output yaml
        """
        try:
            manager = get_manager()
            rs = manager.get_replica_set(name, namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(rs, title=f"ReplicaSet: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @replicasets_app.command("delete")
    def delete_replicaset(
        name: Annotated[str, typer.Argument(help="ReplicaSet name")],
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a ReplicaSet.

        Examples:
            ops k8s replicasets delete my-rs
            ops k8s replicasets delete my-rs --force
        """
        try:
            if not force and not confirm_delete("replicaset", name, namespace):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_replica_set(name, namespace)
            console.print(f"[green]ReplicaSet '{name}' deleted successfully[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Register all sub-Typers
    # -------------------------------------------------------------------------
    app.add_typer(pods_app, name="pods")
    app.add_typer(deployments_app, name="deployments")
    app.add_typer(statefulsets_app, name="statefulsets")
    app.add_typer(daemonsets_app, name="daemonsets")
    app.add_typer(replicasets_app, name="replicasets")
