"""CLI commands for Argo Workflows resources.

Provides commands for managing Workflows, WorkflowTemplates,
CronWorkflows, and workflow artifacts via the WorkflowsManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
import yaml

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
    from system_operations_manager.services.kubernetes.workflows_manager import (
        WorkflowsManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

WORKFLOW_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("phase", "Phase"),
    ("progress", "Progress"),
    ("duration", "Duration"),
    ("entrypoint", "Entrypoint"),
    ("age", "Age"),
]

WORKFLOW_TEMPLATE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("entrypoint", "Entrypoint"),
    ("templates_count", "Templates"),
    ("description", "Description"),
    ("age", "Age"),
]

CRON_WORKFLOW_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("schedule", "Schedule"),
    ("suspend", "Suspended"),
    ("active_count", "Active"),
    ("last_scheduled", "Last Run"),
    ("age", "Age"),
]

ARTIFACT_COLUMNS = [
    ("name", "Name"),
    ("node_id", "Node"),
    ("path", "Path"),
    ("artifact_type", "Type"),
    ("bucket", "Bucket"),
    ("key", "Key"),
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


def _parse_arguments(arguments: list[str] | None) -> dict[str, str] | None:
    """Parse key=value argument strings into a dict."""
    if not arguments:
        return None
    result: dict[str, str] = {}
    for arg in arguments:
        key, sep, value = arg.partition("=")
        if not sep:
            console.print(f"[red]Error:[/red] Invalid argument format '{arg}', expected key=value")
            raise typer.Exit(1)
        result[key] = value
    return result


def _load_spec_from_file(spec_file: Path) -> dict[str, Any]:
    """Load a spec dict from a YAML file."""
    try:
        with spec_file.open("r") as f:
            spec = yaml.safe_load(f)
            if not isinstance(spec, dict):
                console.print("[red]Error:[/red] Spec file must contain a YAML object")
                raise typer.Exit(1)
            return spec
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Spec file not found: {spec_file}")
        raise typer.Exit(1) from None
    except yaml.YAMLError as e:
        console.print(f"[red]Error:[/red] Invalid YAML in spec file: {e}")
        raise typer.Exit(1) from None


# =============================================================================
# Command Registration
# =============================================================================


def register_workflow_commands(
    app: typer.Typer,
    get_manager: Callable[[], WorkflowsManager],
) -> None:
    """Register Argo Workflows CLI commands."""

    # -------------------------------------------------------------------------
    # Workflows (main app)
    # -------------------------------------------------------------------------

    workflows_app = typer.Typer(
        name="workflows",
        help="Manage Argo Workflows",
        no_args_is_help=True,
    )
    app.add_typer(workflows_app, name="workflows")

    @workflows_app.command("list")
    def list_workflows(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        phase: str | None = typer.Option(
            None,
            "--phase",
            help="Filter by workflow phase (Pending, Running, Succeeded, Failed, Error)",
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Argo Workflows in a namespace.

        Examples:
            ops k8s workflows list
            ops k8s workflows list -n production
            ops k8s workflows list --phase Running -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_workflows(
                namespace=namespace,
                label_selector=label_selector,
                phase=phase,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, WORKFLOW_COLUMNS, title="Workflows")
        except KubernetesError as e:
            handle_k8s_error(e)

    @workflows_app.command("get")
    def get_workflow(
        name: str = typer.Argument(help="Workflow name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a Workflow.

        Examples:
            ops k8s workflows get my-workflow
            ops k8s workflows get my-workflow -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_workflow(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Workflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @workflows_app.command("create")
    def create_workflow(
        name: str = typer.Argument(help="Workflow name"),
        namespace: NamespaceOption = None,
        template_ref: str = typer.Option(
            ..., "--template-ref", help="WorkflowTemplate name to reference"
        ),
        argument: list[str] | None = typer.Option(
            None, "--argument", "-a", help="Workflow arguments (key=value, repeatable)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Workflow from a WorkflowTemplate.

        Examples:
            ops k8s workflows create my-workflow --template-ref my-template
            ops k8s workflows create my-workflow --template-ref my-template \\
                --argument message=hello --argument count=5
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            arguments = _parse_arguments(argument)

            resource = manager.create_workflow(
                name,
                namespace=namespace,
                template_ref=template_ref,
                arguments=arguments,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Workflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @workflows_app.command("delete")
    def delete_workflow(
        name: str = typer.Argument(help="Workflow name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Workflow.

        Examples:
            ops k8s workflows delete my-workflow
            ops k8s workflows delete my-workflow -n production --force
        """
        try:
            if not force and not confirm_delete("Workflow", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_workflow(name, namespace=namespace)
            console.print(f"[green]Workflow '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @workflows_app.command("logs")
    def workflow_logs(
        name: str = typer.Argument(help="Workflow name"),
        namespace: NamespaceOption = None,
        container: str = typer.Option("main", "--container", "-c", help="Container name"),
        follow: bool = typer.Option(False, "--follow", "-f", help="Stream logs in real-time"),
    ) -> None:
        """Get logs for a Workflow's pods.

        Examples:
            ops k8s workflows logs my-workflow
            ops k8s workflows logs my-workflow --follow
            ops k8s workflows logs my-workflow --container wait
        """
        try:
            manager = get_manager()
            result = manager.get_workflow_logs(
                name, namespace=namespace, container=container, follow=follow
            )
            if isinstance(result, str):
                console.print(result)
            else:
                for line in result:
                    console.print(line, end="")
        except KubernetesError as e:
            handle_k8s_error(e)

    @workflows_app.command("artifacts")
    def workflow_artifacts(
        name: str = typer.Argument(help="Workflow name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List artifacts from a Workflow.

        Examples:
            ops k8s workflows artifacts my-workflow
            ops k8s workflows artifacts my-workflow -n production -o json
        """
        try:
            manager = get_manager()
            artifacts = manager.list_workflow_artifacts(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_list(artifacts, ARTIFACT_COLUMNS, title=f"Artifacts: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # WorkflowTemplates (sub-app)
    # -------------------------------------------------------------------------

    templates_app = typer.Typer(
        name="templates",
        help="Manage Argo WorkflowTemplates",
        no_args_is_help=True,
    )
    workflows_app.add_typer(templates_app, name="templates")

    @templates_app.command("list")
    def list_templates(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List WorkflowTemplates in a namespace.

        Examples:
            ops k8s workflows templates list
            ops k8s workflows templates list -n production
            ops k8s workflows templates list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_workflow_templates(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, WORKFLOW_TEMPLATE_COLUMNS, title="Workflow Templates")
        except KubernetesError as e:
            handle_k8s_error(e)

    @templates_app.command("get")
    def get_template(
        name: str = typer.Argument(help="WorkflowTemplate name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a WorkflowTemplate.

        Examples:
            ops k8s workflows templates get my-template
            ops k8s workflows templates get my-template -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_workflow_template(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"WorkflowTemplate: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @templates_app.command("create")
    def create_template(
        name: str = typer.Argument(help="WorkflowTemplate name"),
        namespace: NamespaceOption = None,
        spec_file: Path = typer.Option(
            ..., "--spec-file", help="Path to YAML file with template spec"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a WorkflowTemplate from a spec file.

        The spec file should contain the 'spec' section of a WorkflowTemplate YAML.

        Examples:
            ops k8s workflows templates create my-template --spec-file template-spec.yaml
            ops k8s workflows templates create my-template --spec-file template-spec.yaml -l env=prod
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            spec = _load_spec_from_file(spec_file)

            resource = manager.create_workflow_template(
                name,
                namespace=namespace,
                spec=spec,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created WorkflowTemplate: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @templates_app.command("delete")
    def delete_template(
        name: str = typer.Argument(help="WorkflowTemplate name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a WorkflowTemplate.

        Examples:
            ops k8s workflows templates delete my-template
            ops k8s workflows templates delete my-template -n production --force
        """
        try:
            if not force and not confirm_delete("WorkflowTemplate", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_workflow_template(name, namespace=namespace)
            console.print(f"[green]WorkflowTemplate '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # CronWorkflows (sub-app)
    # -------------------------------------------------------------------------

    cron_app = typer.Typer(
        name="cron",
        help="Manage Argo CronWorkflows",
        no_args_is_help=True,
    )
    workflows_app.add_typer(cron_app, name="cron")

    @cron_app.command("list")
    def list_cron_workflows(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List CronWorkflows in a namespace.

        Examples:
            ops k8s workflows cron list
            ops k8s workflows cron list -n production
            ops k8s workflows cron list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_cron_workflows(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CRON_WORKFLOW_COLUMNS, title="Cron Workflows")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cron_app.command("get")
    def get_cron_workflow(
        name: str = typer.Argument(help="CronWorkflow name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a CronWorkflow.

        Examples:
            ops k8s workflows cron get my-cron-workflow
            ops k8s workflows cron get my-cron-workflow -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_cron_workflow(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"CronWorkflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cron_app.command("create")
    def create_cron_workflow(
        name: str = typer.Argument(help="CronWorkflow name"),
        namespace: NamespaceOption = None,
        schedule: str = typer.Option(
            ..., "--schedule", help="Cron schedule expression (e.g., '0 0 * * *')"
        ),
        template_ref: str = typer.Option(
            ..., "--template-ref", help="WorkflowTemplate name to reference"
        ),
        timezone: str = typer.Option(
            "", "--timezone", help="Timezone for schedule (e.g., 'America/Los_Angeles')"
        ),
        concurrency_policy: str = typer.Option(
            "Allow", "--concurrency-policy", help="Concurrency policy: Allow, Forbid, or Replace"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a CronWorkflow.

        Examples:
            ops k8s workflows cron create my-cron --schedule "0 0 * * *" --template-ref my-template
            ops k8s workflows cron create my-cron --schedule "*/5 * * * *" \\
                --template-ref my-template --timezone "America/Los_Angeles" --concurrency-policy Forbid
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)

            resource = manager.create_cron_workflow(
                name,
                namespace=namespace,
                schedule=schedule,
                template_ref=template_ref,
                timezone=timezone,
                concurrency_policy=concurrency_policy,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created CronWorkflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cron_app.command("delete")
    def delete_cron_workflow(
        name: str = typer.Argument(help="CronWorkflow name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a CronWorkflow.

        Examples:
            ops k8s workflows cron delete my-cron
            ops k8s workflows cron delete my-cron -n production --force
        """
        try:
            if not force and not confirm_delete("CronWorkflow", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cron_workflow(name, namespace=namespace)
            console.print(f"[green]CronWorkflow '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cron_app.command("suspend")
    def suspend_cron_workflow(
        name: str = typer.Argument(help="CronWorkflow name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Suspend a CronWorkflow.

        Examples:
            ops k8s workflows cron suspend my-cron
            ops k8s workflows cron suspend my-cron -n production
        """
        try:
            manager = get_manager()
            resource = manager.suspend_cron_workflow(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Suspended CronWorkflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cron_app.command("resume")
    def resume_cron_workflow(
        name: str = typer.Argument(help="CronWorkflow name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Resume a suspended CronWorkflow.

        Examples:
            ops k8s workflows cron resume my-cron
            ops k8s workflows cron resume my-cron -n production
        """
        try:
            manager = get_manager()
            resource = manager.resume_cron_workflow(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Resumed CronWorkflow: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)
