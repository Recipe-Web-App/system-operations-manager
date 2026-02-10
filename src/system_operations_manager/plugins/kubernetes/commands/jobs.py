"""CLI commands for Kubernetes job resources.

Provides commands for managing jobs and cronjobs
via the JobManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

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
    from system_operations_manager.services.kubernetes import JobManager

# =============================================================================
# Column Definitions
# =============================================================================

JOB_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("completions", "Completions"),
    ("succeeded", "Succeeded"),
    ("failed", "Failed"),
    ("active", "Active"),
    ("age", "Age"),
]

CRONJOB_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("schedule", "Schedule"),
    ("suspend", "Suspend"),
    ("active_count", "Active"),
    ("last_schedule_time", "Last Schedule"),
    ("age", "Age"),
]

# =============================================================================
# Custom Option Annotations
# =============================================================================

PropagationPolicyOption = Annotated[
    str,
    typer.Option(
        "--propagation-policy",
        help="Deletion propagation (Background, Foreground, Orphan)",
    ),
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


def register_job_commands(
    app: typer.Typer,
    get_manager: Callable[[], JobManager],
) -> None:
    """Register job CLI commands."""

    # -------------------------------------------------------------------------
    # Jobs
    # -------------------------------------------------------------------------

    jobs_app = typer.Typer(
        name="jobs",
        help="Manage Kubernetes jobs",
        no_args_is_help=True,
    )
    app.add_typer(jobs_app, name="jobs")

    @jobs_app.command("list")
    def list_jobs(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List jobs.

        Examples:
            ops k8s jobs list
            ops k8s jobs list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_jobs(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, JOB_COLUMNS, title="Jobs")
        except KubernetesError as e:
            handle_k8s_error(e)

    @jobs_app.command("get")
    def get_job(
        name: str = typer.Argument(help="Job name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a job.

        Examples:
            ops k8s jobs get my-job
        """
        try:
            manager = get_manager()
            resource = manager.get_job(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Job: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @jobs_app.command("create")
    def create_job(
        name: str = typer.Argument(help="Job name"),
        image: str = typer.Option(..., "--image", "-i", help="Container image"),
        namespace: NamespaceOption = None,
        command: list[str] | None = typer.Option(
            None, "--command", "-c", help="Container command (repeatable)"
        ),
        completions: int = typer.Option(
            1, "--completions", help="Number of successful completions needed"
        ),
        parallelism: int = typer.Option(
            1, "--parallelism", help="Number of pods to run in parallel"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a job.

        Examples:
            ops k8s jobs create my-job --image busybox --command echo --command hello
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_job(
                name,
                namespace=namespace,
                image=image,
                command=command,
                completions=completions,
                parallelism=parallelism,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Job: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @jobs_app.command("delete")
    def delete_job(
        name: str = typer.Argument(help="Job name"),
        namespace: NamespaceOption = None,
        propagation_policy: PropagationPolicyOption = "Background",
        force: ForceOption = False,
    ) -> None:
        """Delete a job.

        Examples:
            ops k8s jobs delete my-job
            ops k8s jobs delete my-job --propagation-policy Foreground
        """
        try:
            if not force and not confirm_delete("job", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_job(
                name,
                namespace=namespace,
                propagation_policy=propagation_policy,
            )
            console.print(f"[green]Job '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # CronJobs
    # -------------------------------------------------------------------------

    cronjobs_app = typer.Typer(
        name="cronjobs",
        help="Manage Kubernetes cronjobs",
        no_args_is_help=True,
    )
    app.add_typer(cronjobs_app, name="cronjobs")

    @cronjobs_app.command("list")
    def list_cronjobs(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List cronjobs.

        Examples:
            ops k8s cronjobs list
            ops k8s cronjobs list -A
        """
        try:
            manager = get_manager()
            resources = manager.list_cron_jobs(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CRONJOB_COLUMNS, title="CronJobs")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("get")
    def get_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a cronjob.

        Examples:
            ops k8s cronjobs get my-cronjob
        """
        try:
            manager = get_manager()
            resource = manager.get_cron_job(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"CronJob: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("create")
    def create_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        image: str = typer.Option(..., "--image", "-i", help="Container image"),
        schedule: str = typer.Option(
            ..., "--schedule", "-s", help="Cron schedule expression (e.g., '*/5 * * * *')"
        ),
        namespace: NamespaceOption = None,
        command: list[str] | None = typer.Option(
            None, "--command", "-c", help="Container command (repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a cronjob.

        Examples:
            ops k8s cronjobs create my-cron --image busybox --schedule '*/5 * * * *'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_cron_job(
                name,
                namespace=namespace,
                image=image,
                command=command,
                schedule=schedule,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created CronJob: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("update")
    def update_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        namespace: NamespaceOption = None,
        schedule: str | None = typer.Option(None, "--schedule", "-s", help="New cron schedule"),
        suspend: bool | None = typer.Option(
            None, "--suspend/--no-suspend", help="Suspend or unsuspend the cronjob"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a cronjob.

        Examples:
            ops k8s cronjobs update my-cron --schedule '0 * * * *'
            ops k8s cronjobs update my-cron --suspend
        """
        try:
            manager = get_manager()
            resource = manager.update_cron_job(
                name,
                namespace=namespace,
                schedule=schedule,
                suspend=suspend,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Updated CronJob: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("delete")
    def delete_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a cronjob.

        Examples:
            ops k8s cronjobs delete my-cronjob
        """
        try:
            if not force and not confirm_delete("cronjob", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cron_job(name, namespace=namespace)
            console.print(f"[green]CronJob '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("suspend")
    def suspend_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Suspend a cronjob.

        Examples:
            ops k8s cronjobs suspend my-cronjob
        """
        try:
            manager = get_manager()
            manager.suspend_cron_job(name, namespace=namespace)
            console.print(f"[green]CronJob '{name}' suspended[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cronjobs_app.command("resume")
    def resume_cronjob(
        name: str = typer.Argument(help="CronJob name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Resume a suspended cronjob.

        Examples:
            ops k8s cronjobs resume my-cronjob
        """
        try:
            manager = get_manager()
            manager.resume_cron_job(name, namespace=namespace)
            console.print(f"[green]CronJob '{name}' resumed[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
