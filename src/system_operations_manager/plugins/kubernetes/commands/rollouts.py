"""CLI commands for Argo Rollouts resources.

Provides commands for managing Rollouts, AnalysisTemplates,
and AnalysisRuns via the RolloutsManager service.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
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
    from system_operations_manager.services.kubernetes.rollouts_manager import (
        RolloutsManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

ROLLOUT_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("strategy", "Strategy"),
    ("phase", "Phase"),
    ("replicas", "Replicas"),
    ("ready_replicas", "Ready"),
    ("canary_weight", "Weight"),
    ("image", "Image"),
    ("age", "Age"),
]

ANALYSIS_TEMPLATE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("metrics_count", "Metrics"),
    ("args", "Args"),
    ("age", "Age"),
]

ANALYSIS_RUN_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("phase", "Phase"),
    ("metrics_count", "Metrics"),
    ("rollout_ref", "Rollout"),
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


def _parse_canary_steps(steps_str: str | None) -> list[dict[str, object]] | None:
    """Parse a JSON canary steps string into a list of dicts."""
    if not steps_str:
        return None
    try:
        steps = json.loads(steps_str)
        if not isinstance(steps, list):
            console.print("[red]Error:[/red] Canary steps must be a JSON array")
            raise typer.Exit(1)
        return steps
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON canary steps: {e}")
        raise typer.Exit(1) from None


# =============================================================================
# Command Registration
# =============================================================================


def register_rollout_commands(
    app: typer.Typer,
    get_manager: Callable[[], RolloutsManager],
) -> None:
    """Register Argo Rollouts CLI commands."""

    # -------------------------------------------------------------------------
    # Rollouts
    # -------------------------------------------------------------------------

    rollouts_app = typer.Typer(
        name="rollouts",
        help="Manage Argo Rollouts",
        no_args_is_help=True,
    )
    app.add_typer(rollouts_app, name="rollouts")

    @rollouts_app.command("list")
    def list_rollouts(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Rollouts in a namespace.

        Examples:
            ops k8s rollouts list
            ops k8s rollouts list -n production
            ops k8s rollouts list -l app=myapp -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_rollouts(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ROLLOUT_COLUMNS, title="Rollouts")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("get")
    def get_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a Rollout.

        Examples:
            ops k8s rollouts get my-rollout
            ops k8s rollouts get my-rollout -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_rollout(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Rollout: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("create")
    def create_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        image: str = typer.Option(..., "--image", help="Container image"),
        strategy: str = typer.Option(
            "canary", "--strategy", help="Deployment strategy: canary or blueGreen"
        ),
        replicas: int = typer.Option(1, "--replicas", help="Number of replicas"),
        canary_steps: str | None = typer.Option(
            None,
            "--canary-steps",
            help='Canary steps as JSON array (e.g. \'[{"setWeight":20},{"pause":{}}]\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Rollout.

        Examples:
            ops k8s rollouts create my-rollout --image nginx:1.21
            ops k8s rollouts create my-rollout --image nginx:1.21 --strategy blueGreen
            ops k8s rollouts create my-rollout --image nginx:1.21 \\
                --canary-steps '[{"setWeight":20},{"pause":{"duration":"1m"}},{"setWeight":40}]'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            steps = _parse_canary_steps(canary_steps)

            resource = manager.create_rollout(
                name,
                namespace=namespace,
                image=image,
                replicas=replicas,
                strategy=strategy,
                canary_steps=steps,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Rollout: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("delete")
    def delete_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Rollout.

        Examples:
            ops k8s rollouts delete my-rollout
            ops k8s rollouts delete my-rollout -n production --force
        """
        try:
            if not force and not confirm_delete("Rollout", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_rollout(name, namespace=namespace)
            console.print(f"[green]Rollout '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("status")
    def rollout_status(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show detailed status for a Rollout.

        Examples:
            ops k8s rollouts status my-rollout
            ops k8s rollouts status my-rollout -n production -o json
        """
        try:
            manager = get_manager()
            status = manager.get_rollout_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"Rollout Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("promote")
    def promote_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        full: bool = typer.Option(
            False,
            "--full",
            help="Fully promote (skip remaining steps)",
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Promote a Rollout to the next step or fully.

        Examples:
            ops k8s rollouts promote my-rollout
            ops k8s rollouts promote my-rollout --full
            ops k8s rollouts promote my-rollout -n production
        """
        try:
            manager = get_manager()
            resource = manager.promote_rollout(name, namespace=namespace, full=full)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Promoted Rollout: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("abort")
    def abort_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Abort a Rollout in progress.

        Examples:
            ops k8s rollouts abort my-rollout
            ops k8s rollouts abort my-rollout -n production
        """
        try:
            manager = get_manager()
            resource = manager.abort_rollout(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Aborted Rollout: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @rollouts_app.command("retry")
    def retry_rollout(
        name: str = typer.Argument(help="Rollout name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Retry a failed or aborted Rollout.

        Examples:
            ops k8s rollouts retry my-rollout
            ops k8s rollouts retry my-rollout -n production
        """
        try:
            manager = get_manager()
            resource = manager.retry_rollout(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Retried Rollout: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # AnalysisTemplates
    # -------------------------------------------------------------------------

    at_app = typer.Typer(
        name="analysis-templates",
        help="Manage Argo Rollouts AnalysisTemplates",
        no_args_is_help=True,
    )
    app.add_typer(at_app, name="analysis-templates")

    @at_app.command("list")
    def list_analysis_templates(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List AnalysisTemplates in a namespace.

        Examples:
            ops k8s analysis-templates list
            ops k8s analysis-templates list -n production
            ops k8s analysis-templates list -l app=myapp -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_analysis_templates(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ANALYSIS_TEMPLATE_COLUMNS, title="Analysis Templates")
        except KubernetesError as e:
            handle_k8s_error(e)

    @at_app.command("get")
    def get_analysis_template(
        name: str = typer.Argument(help="AnalysisTemplate name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an AnalysisTemplate.

        Examples:
            ops k8s analysis-templates get success-rate
            ops k8s analysis-templates get success-rate -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_analysis_template(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"AnalysisTemplate: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # AnalysisRuns
    # -------------------------------------------------------------------------

    ar_app = typer.Typer(
        name="analysis-runs",
        help="Manage Argo Rollouts AnalysisRuns",
        no_args_is_help=True,
    )
    app.add_typer(ar_app, name="analysis-runs")

    @ar_app.command("list")
    def list_analysis_runs(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List AnalysisRuns in a namespace.

        Examples:
            ops k8s analysis-runs list
            ops k8s analysis-runs list -n production
            ops k8s analysis-runs list -l rollout=my-rollout -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_analysis_runs(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ANALYSIS_RUN_COLUMNS, title="Analysis Runs")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ar_app.command("get")
    def get_analysis_run(
        name: str = typer.Argument(help="AnalysisRun name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an AnalysisRun.

        Examples:
            ops k8s analysis-runs get my-rollout-abc123
            ops k8s analysis-runs get my-rollout-abc123 -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_analysis_run(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"AnalysisRun: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)
