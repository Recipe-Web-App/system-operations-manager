"""CLI commands for ArgoCD resources.

Provides commands for managing ArgoCD Applications and AppProjects
via the ArgoCDManager service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    DryRunOption,
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
    from system_operations_manager.services.kubernetes.argocd_manager import (
        ArgoCDManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

APPLICATION_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("project", "Project"),
    ("sync_status", "Sync"),
    ("health_status", "Health"),
    ("repo_url", "Repository"),
    ("path", "Path"),
    ("age", "Age"),
]

PROJECT_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("description", "Description"),
    ("source_repos", "Source Repos"),
    ("age", "Age"),
]


# =============================================================================
# Command Registration
# =============================================================================


def register_argocd_commands(
    app: typer.Typer,
    get_manager: Callable[[], ArgoCDManager],
) -> None:
    """Register ArgoCD CLI commands."""

    argocd_app = typer.Typer(
        name="argocd",
        help="Manage ArgoCD resources",
        no_args_is_help=True,
    )
    app.add_typer(argocd_app, name="argocd")

    # -------------------------------------------------------------------------
    # Application Commands
    # -------------------------------------------------------------------------

    app_cmd = typer.Typer(
        name="app",
        help="Manage ArgoCD Applications",
        no_args_is_help=True,
    )
    argocd_app.add_typer(app_cmd, name="app")

    @app_cmd.command("list")
    def list_applications(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ArgoCD Applications.

        Examples:
            ops k8s argocd app list
            ops k8s argocd app list -n argocd
            ops k8s argocd app list -l environment=production -o json
        """
        try:
            manager = get_manager()
            apps = manager.list_applications(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(apps, APPLICATION_COLUMNS, title="ArgoCD Applications")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("get")
    def get_application(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get an ArgoCD Application.

        Examples:
            ops k8s argocd app get my-app
            ops k8s argocd app get my-app -n argocd -o yaml
        """
        try:
            manager = get_manager()
            application = manager.get_application(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(application, title=f"Application: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("create")
    def create_application(
        name: str = typer.Argument(help="Application name"),
        repo_url: str = typer.Option(..., "--repo-url", help="Source Git repository URL"),
        path: str = typer.Option(..., "--path", help="Path within the repository"),
        dest_server: str = typer.Option(
            "https://kubernetes.default.svc", "--dest-server", help="Destination cluster server"
        ),
        namespace: NamespaceOption = None,
        project: str = typer.Option("default", "--project", help="ArgoCD project"),
        target_revision: str = typer.Option("HEAD", "--target-revision", help="Branch/tag/commit"),
        dest_namespace: str = typer.Option(
            "default", "--dest-namespace", help="Destination namespace"
        ),
        auto_sync: bool = typer.Option(False, "--auto-sync", help="Enable automated sync"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ArgoCD Application.

        Examples:
            ops k8s argocd app create my-app \\
                --repo-url https://github.com/org/repo \\
                --path k8s/overlays/prod
            ops k8s argocd app create my-app \\
                --repo-url https://github.com/org/repo \\
                --path charts/myapp \\
                --target-revision main \\
                --auto-sync
        """
        try:
            manager = get_manager()
            application = manager.create_application(
                name,
                namespace=namespace,
                project=project,
                repo_url=repo_url,
                path=path,
                target_revision=target_revision,
                dest_server=dest_server,
                dest_namespace=dest_namespace,
                auto_sync=auto_sync,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(application, title=f"Created Application: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("delete")
    def delete_application(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete an ArgoCD Application.

        Examples:
            ops k8s argocd app delete my-app
            ops k8s argocd app delete my-app -n argocd --force
        """
        try:
            if not force and not confirm_delete("Application", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_application(name, namespace=namespace)
            console.print(f"[green]Deleted Application '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("sync")
    def sync_application(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        revision: str | None = typer.Option(None, "--revision", help="Sync to specific revision"),
        prune: bool = typer.Option(False, "--prune", help="Prune resources not in git"),
        dry_run: DryRunOption = False,
    ) -> None:
        """Sync an ArgoCD Application.

        Examples:
            ops k8s argocd app sync my-app
            ops k8s argocd app sync my-app --revision v1.2.3
            ops k8s argocd app sync my-app --prune --dry-run
        """
        try:
            manager = get_manager()
            result = manager.sync_application(
                name,
                namespace=namespace,
                revision=revision,
                prune=prune,
                dry_run=dry_run,
            )
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Sync: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("rollback")
    def rollback_application(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        revision_id: int = typer.Option(
            0, "--revision-id", help="History revision ID (0=previous)"
        ),
    ) -> None:
        """Rollback an ArgoCD Application to a previous revision.

        Examples:
            ops k8s argocd app rollback my-app
            ops k8s argocd app rollback my-app --revision-id 2
        """
        try:
            manager = get_manager()
            result = manager.rollback_application(
                name,
                namespace=namespace,
                revision_id=revision_id,
            )
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Rollback: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("health")
    def application_health(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Check ArgoCD Application health status.

        Examples:
            ops k8s argocd app health my-app
            ops k8s argocd app health my-app -n argocd -o json
        """
        try:
            manager = get_manager()
            result = manager.get_application_health(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Health: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @app_cmd.command("diff")
    def application_diff(
        name: str = typer.Argument(help="Application name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show sync diff for an ArgoCD Application.

        Examples:
            ops k8s argocd app diff my-app
            ops k8s argocd app diff my-app -n argocd -o json
        """
        try:
            manager = get_manager()
            result = manager.diff_application(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Diff: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Project Commands
    # -------------------------------------------------------------------------

    project_cmd = typer.Typer(
        name="project",
        help="Manage ArgoCD Projects",
        no_args_is_help=True,
    )
    argocd_app.add_typer(project_cmd, name="project")

    @project_cmd.command("list")
    def list_projects(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ArgoCD Projects.

        Examples:
            ops k8s argocd project list
            ops k8s argocd project list -n argocd
            ops k8s argocd project list -o json
        """
        try:
            manager = get_manager()
            projects = manager.list_projects(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(projects, PROJECT_COLUMNS, title="ArgoCD Projects")
        except KubernetesError as e:
            handle_k8s_error(e)

    @project_cmd.command("get")
    def get_project(
        name: str = typer.Argument(help="Project name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get an ArgoCD Project.

        Examples:
            ops k8s argocd project get my-project
            ops k8s argocd project get my-project -n argocd -o yaml
        """
        try:
            manager = get_manager()
            project = manager.get_project(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(project, title=f"Project: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @project_cmd.command("create")
    def create_project(
        name: str = typer.Argument(help="Project name"),
        namespace: NamespaceOption = None,
        description: str = typer.Option("", "--description", help="Project description"),
        source_repos: list[str] | None = typer.Option(
            None, "--source-repo", help="Allowed source repos"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ArgoCD Project.

        Examples:
            ops k8s argocd project create my-project \\
                --description "My project" \\
                --source-repo https://github.com/org/repo
            ops k8s argocd project create my-project \\
                --source-repo https://github.com/org/repo1 \\
                --source-repo https://github.com/org/repo2
        """
        try:
            manager = get_manager()
            project = manager.create_project(
                name,
                namespace=namespace,
                description=description,
                source_repos=source_repos,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(project, title=f"Created Project: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @project_cmd.command("delete")
    def delete_project(
        name: str = typer.Argument(help="Project name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete an ArgoCD Project.

        Examples:
            ops k8s argocd project delete my-project
            ops k8s argocd project delete my-project -n argocd --force
        """
        try:
            if not force and not confirm_delete("AppProject", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_project(name, namespace=namespace)
            console.print(f"[green]Deleted Project '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)
