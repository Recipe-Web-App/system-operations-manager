"""CLI commands for Flux CD resources.

Provides commands for managing Flux GitRepositories, HelmRepositories,
Kustomizations, and HelmReleases via the FluxManager service.
"""

from __future__ import annotations

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
    from system_operations_manager.services.kubernetes.flux_manager import (
        FluxManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

GIT_REPOSITORY_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("url", "URL"),
    ("ref_branch", "Branch"),
    ("ready", "Ready"),
    ("suspended", "Suspended"),
    ("age", "Age"),
]

HELM_REPOSITORY_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("url", "URL"),
    ("repo_type", "Type"),
    ("ready", "Ready"),
    ("suspended", "Suspended"),
    ("age", "Age"),
]

KUSTOMIZATION_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("source_name", "Source"),
    ("path", "Path"),
    ("ready", "Ready"),
    ("suspended", "Suspended"),
    ("age", "Age"),
]

HELM_RELEASE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("chart_name", "Chart"),
    ("chart_source_name", "Source"),
    ("ready", "Ready"),
    ("suspended", "Suspended"),
    ("age", "Age"),
]


# =============================================================================
# Command Registration
# =============================================================================


def register_flux_commands(
    app: typer.Typer,
    get_manager: Callable[[], FluxManager],
) -> None:
    """Register Flux CD CLI commands."""

    flux_app = typer.Typer(
        name="flux",
        help="Manage Flux CD resources",
        no_args_is_help=True,
    )
    app.add_typer(flux_app, name="flux")

    # -------------------------------------------------------------------------
    # Source Commands
    # -------------------------------------------------------------------------

    source_app = typer.Typer(
        name="source",
        help="Manage Flux sources",
        no_args_is_help=True,
    )
    flux_app.add_typer(source_app, name="source")

    # ---- GitRepository Commands ----

    git_app = typer.Typer(
        name="git",
        help="Manage Flux GitRepositories",
        no_args_is_help=True,
    )
    source_app.add_typer(git_app, name="git")

    @git_app.command("list")
    def list_git_repositories(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Flux GitRepositories.

        Examples:
            ops k8s flux source git list
            ops k8s flux source git list -n flux-system
            ops k8s flux source git list -l app=podinfo -o json
        """
        try:
            manager = get_manager()
            repos = manager.list_git_repositories(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(repos, GIT_REPOSITORY_COLUMNS, title="GitRepositories")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("get")
    def get_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a Flux GitRepository.

        Examples:
            ops k8s flux source git get podinfo
            ops k8s flux source git get podinfo -n flux-system -o yaml
        """
        try:
            manager = get_manager()
            repo = manager.get_git_repository(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(repo, title=f"GitRepository: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("create")
    def create_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        url: str = typer.Option(..., "--url", help="Git repository URL"),
        namespace: NamespaceOption = None,
        branch: str | None = typer.Option(None, "--branch", help="Branch to track"),
        tag: str | None = typer.Option(None, "--tag", help="Tag to track"),
        semver: str | None = typer.Option(None, "--semver", help="Semver range to track"),
        commit: str | None = typer.Option(None, "--commit", help="Specific commit SHA"),
        interval: str = typer.Option("1m", "--interval", help="Reconciliation interval"),
        secret_ref: str | None = typer.Option(
            None, "--secret-ref", help="Secret name for authentication"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Flux GitRepository.

        Examples:
            ops k8s flux source git create podinfo \\
                --url https://github.com/stefanprodan/podinfo \\
                --branch main
            ops k8s flux source git create podinfo \\
                --url https://github.com/stefanprodan/podinfo \\
                --tag v6.0.0 --interval 5m
        """
        try:
            manager = get_manager()
            repo = manager.create_git_repository(
                name,
                namespace=namespace,
                url=url,
                ref_branch=branch,
                ref_tag=tag,
                ref_semver=semver,
                ref_commit=commit,
                interval=interval,
                secret_ref=secret_ref,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(repo, title=f"Created GitRepository: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("delete")
    def delete_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Flux GitRepository.

        Examples:
            ops k8s flux source git delete podinfo
            ops k8s flux source git delete podinfo --force
        """
        try:
            if not force and not confirm_delete("GitRepository", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_git_repository(name, namespace=namespace)
            console.print(f"[green]Deleted GitRepository '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("suspend")
    def suspend_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Suspend reconciliation of a Flux GitRepository.

        Examples:
            ops k8s flux source git suspend podinfo
            ops k8s flux source git suspend podinfo -n flux-system
        """
        try:
            manager = get_manager()
            result = manager.suspend_git_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Suspended: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("resume")
    def resume_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Resume reconciliation of a Flux GitRepository.

        Examples:
            ops k8s flux source git resume podinfo
            ops k8s flux source git resume podinfo -n flux-system
        """
        try:
            manager = get_manager()
            result = manager.resume_git_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Resumed: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("reconcile")
    def reconcile_git_repository(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Trigger reconciliation of a Flux GitRepository.

        Examples:
            ops k8s flux source git reconcile podinfo
            ops k8s flux source git reconcile podinfo -n flux-system
        """
        try:
            manager = get_manager()
            result = manager.reconcile_git_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Reconcile: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @git_app.command("status")
    def git_repository_status(
        name: str = typer.Argument(help="GitRepository name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get status of a Flux GitRepository.

        Examples:
            ops k8s flux source git status podinfo
            ops k8s flux source git status podinfo -o json
        """
        try:
            manager = get_manager()
            result = manager.get_git_repository_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # ---- HelmRepository Commands ----

    helm_repo_app = typer.Typer(
        name="helm",
        help="Manage Flux HelmRepositories",
        no_args_is_help=True,
    )
    source_app.add_typer(helm_repo_app, name="helm")

    @helm_repo_app.command("list")
    def list_helm_repositories(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Flux HelmRepositories.

        Examples:
            ops k8s flux source helm list
            ops k8s flux source helm list -n flux-system -o json
        """
        try:
            manager = get_manager()
            repos = manager.list_helm_repositories(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(repos, HELM_REPOSITORY_COLUMNS, title="HelmRepositories")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("get")
    def get_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a Flux HelmRepository.

        Examples:
            ops k8s flux source helm get bitnami
            ops k8s flux source helm get bitnami -o yaml
        """
        try:
            manager = get_manager()
            repo = manager.get_helm_repository(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(repo, title=f"HelmRepository: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("create")
    def create_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        url: str = typer.Option(..., "--url", help="Helm repository URL"),
        namespace: NamespaceOption = None,
        repo_type: str = typer.Option("default", "--type", help="Repository type (default or oci)"),
        interval: str = typer.Option("1m", "--interval", help="Reconciliation interval"),
        secret_ref: str | None = typer.Option(
            None, "--secret-ref", help="Secret name for authentication"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Flux HelmRepository.

        Examples:
            ops k8s flux source helm create bitnami \\
                --url https://charts.bitnami.com/bitnami
            ops k8s flux source helm create ghcr \\
                --url oci://ghcr.io/fluxcd/charts \\
                --type oci
        """
        try:
            manager = get_manager()
            repo = manager.create_helm_repository(
                name,
                namespace=namespace,
                url=url,
                repo_type=repo_type,
                interval=interval,
                secret_ref=secret_ref,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(repo, title=f"Created HelmRepository: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("delete")
    def delete_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Flux HelmRepository.

        Examples:
            ops k8s flux source helm delete bitnami
            ops k8s flux source helm delete bitnami --force
        """
        try:
            if not force and not confirm_delete("HelmRepository", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_helm_repository(name, namespace=namespace)
            console.print(f"[green]Deleted HelmRepository '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("suspend")
    def suspend_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Suspend reconciliation of a Flux HelmRepository.

        Examples:
            ops k8s flux source helm suspend bitnami
        """
        try:
            manager = get_manager()
            result = manager.suspend_helm_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Suspended: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("resume")
    def resume_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Resume reconciliation of a Flux HelmRepository.

        Examples:
            ops k8s flux source helm resume bitnami
        """
        try:
            manager = get_manager()
            result = manager.resume_helm_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Resumed: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("reconcile")
    def reconcile_helm_repository(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Trigger reconciliation of a Flux HelmRepository.

        Examples:
            ops k8s flux source helm reconcile bitnami
        """
        try:
            manager = get_manager()
            result = manager.reconcile_helm_repository(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Reconcile: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @helm_repo_app.command("status")
    def helm_repository_status(
        name: str = typer.Argument(help="HelmRepository name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get status of a Flux HelmRepository.

        Examples:
            ops k8s flux source helm status bitnami
            ops k8s flux source helm status bitnami -o json
        """
        try:
            manager = get_manager()
            result = manager.get_helm_repository_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Kustomization Commands
    # -------------------------------------------------------------------------

    ks_app = typer.Typer(
        name="ks",
        help="Manage Flux Kustomizations",
        no_args_is_help=True,
    )
    flux_app.add_typer(ks_app, name="ks")

    @ks_app.command("list")
    def list_kustomizations(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Flux Kustomizations.

        Examples:
            ops k8s flux ks list
            ops k8s flux ks list -n flux-system -o json
        """
        try:
            manager = get_manager()
            ks_list = manager.list_kustomizations(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(ks_list, KUSTOMIZATION_COLUMNS, title="Kustomizations")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("get")
    def get_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a Flux Kustomization.

        Examples:
            ops k8s flux ks get app-ks
            ops k8s flux ks get app-ks -n flux-system -o yaml
        """
        try:
            manager = get_manager()
            ks = manager.get_kustomization(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(ks, title=f"Kustomization: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("create")
    def create_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        source_name: str = typer.Option(..., "--source-name", help="Source reference name"),
        source_kind: str = typer.Option(
            ..., "--source-kind", help="Source reference kind (e.g. GitRepository)"
        ),
        namespace: NamespaceOption = None,
        source_namespace: str | None = typer.Option(
            None, "--source-namespace", help="Source reference namespace"
        ),
        path: str = typer.Option("./", "--path", help="Path within the source"),
        interval: str = typer.Option("5m", "--interval", help="Reconciliation interval"),
        prune: bool = typer.Option(True, "--prune/--no-prune", help="Prune deleted resources"),
        target_namespace: str | None = typer.Option(
            None, "--target-namespace", help="Target namespace for resources"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Flux Kustomization.

        Examples:
            ops k8s flux ks create app-ks \\
                --source-name podinfo \\
                --source-kind GitRepository \\
                --path ./kustomize
            ops k8s flux ks create app-ks \\
                --source-name podinfo \\
                --source-kind GitRepository \\
                --path ./deploy \\
                --target-namespace app-ns \\
                --prune
        """
        try:
            manager = get_manager()
            ks = manager.create_kustomization(
                name,
                namespace=namespace,
                source_kind=source_kind,
                source_name=source_name,
                source_namespace=source_namespace,
                path=path,
                interval=interval,
                prune=prune,
                target_namespace=target_namespace,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(ks, title=f"Created Kustomization: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("delete")
    def delete_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Flux Kustomization.

        Examples:
            ops k8s flux ks delete app-ks
            ops k8s flux ks delete app-ks --force
        """
        try:
            if not force and not confirm_delete("Kustomization", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_kustomization(name, namespace=namespace)
            console.print(f"[green]Deleted Kustomization '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("suspend")
    def suspend_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Suspend reconciliation of a Flux Kustomization.

        Examples:
            ops k8s flux ks suspend app-ks
        """
        try:
            manager = get_manager()
            result = manager.suspend_kustomization(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Suspended: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("resume")
    def resume_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Resume reconciliation of a Flux Kustomization.

        Examples:
            ops k8s flux ks resume app-ks
        """
        try:
            manager = get_manager()
            result = manager.resume_kustomization(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Resumed: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("reconcile")
    def reconcile_kustomization(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Trigger reconciliation of a Flux Kustomization.

        Examples:
            ops k8s flux ks reconcile app-ks
        """
        try:
            manager = get_manager()
            result = manager.reconcile_kustomization(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Reconcile: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ks_app.command("status")
    def kustomization_status(
        name: str = typer.Argument(help="Kustomization name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get status of a Flux Kustomization.

        Examples:
            ops k8s flux ks status app-ks
            ops k8s flux ks status app-ks -o json
        """
        try:
            manager = get_manager()
            result = manager.get_kustomization_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # HelmRelease Commands
    # -------------------------------------------------------------------------

    hr_app = typer.Typer(
        name="hr",
        help="Manage Flux HelmReleases",
        no_args_is_help=True,
    )
    flux_app.add_typer(hr_app, name="hr")

    @hr_app.command("list")
    def list_helm_releases(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Flux HelmReleases.

        Examples:
            ops k8s flux hr list
            ops k8s flux hr list -n flux-system -o json
        """
        try:
            manager = get_manager()
            releases = manager.list_helm_releases(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(releases, HELM_RELEASE_COLUMNS, title="HelmReleases")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("get")
    def get_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a Flux HelmRelease.

        Examples:
            ops k8s flux hr get nginx
            ops k8s flux hr get nginx -n flux-system -o yaml
        """
        try:
            manager = get_manager()
            release = manager.get_helm_release(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(release, title=f"HelmRelease: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("create")
    def create_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        chart: str = typer.Option(..., "--chart", help="Helm chart name"),
        source_name: str = typer.Option(..., "--source-name", help="Chart source reference name"),
        source_kind: str = typer.Option(
            ..., "--source-kind", help="Chart source reference kind (e.g. HelmRepository)"
        ),
        namespace: NamespaceOption = None,
        source_namespace: str | None = typer.Option(
            None, "--source-namespace", help="Chart source reference namespace"
        ),
        interval: str = typer.Option("5m", "--interval", help="Reconciliation interval"),
        target_namespace: str | None = typer.Option(
            None, "--target-namespace", help="Target namespace for deployed resources"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Flux HelmRelease.

        Examples:
            ops k8s flux hr create nginx \\
                --chart nginx \\
                --source-name bitnami \\
                --source-kind HelmRepository
            ops k8s flux hr create nginx \\
                --chart nginx \\
                --source-name bitnami \\
                --source-kind HelmRepository \\
                --target-namespace web
        """
        try:
            manager = get_manager()
            release = manager.create_helm_release(
                name,
                namespace=namespace,
                chart_name=chart,
                chart_source_kind=source_kind,
                chart_source_name=source_name,
                chart_source_namespace=source_namespace,
                interval=interval,
                target_namespace=target_namespace,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(release, title=f"Created HelmRelease: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("delete")
    def delete_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Flux HelmRelease.

        Examples:
            ops k8s flux hr delete nginx
            ops k8s flux hr delete nginx --force
        """
        try:
            if not force and not confirm_delete("HelmRelease", name, namespace):
                raise typer.Exit(0)
            manager = get_manager()
            manager.delete_helm_release(name, namespace=namespace)
            console.print(f"[green]Deleted HelmRelease '{name}'[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("suspend")
    def suspend_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Suspend reconciliation of a Flux HelmRelease.

        Examples:
            ops k8s flux hr suspend nginx
        """
        try:
            manager = get_manager()
            result = manager.suspend_helm_release(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Suspended: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("resume")
    def resume_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Resume reconciliation of a Flux HelmRelease.

        Examples:
            ops k8s flux hr resume nginx
        """
        try:
            manager = get_manager()
            result = manager.resume_helm_release(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Resumed: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("reconcile")
    def reconcile_helm_release(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Trigger reconciliation of a Flux HelmRelease.

        Examples:
            ops k8s flux hr reconcile nginx
        """
        try:
            manager = get_manager()
            result = manager.reconcile_helm_release(name, namespace=namespace)
            formatter = get_formatter(OutputFormat.TABLE, console)
            formatter.format_dict(result, title=f"Reconcile: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @hr_app.command("status")
    def helm_release_status(
        name: str = typer.Argument(help="HelmRelease name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get status of a Flux HelmRelease.

        Examples:
            ops k8s flux hr status nginx
            ops k8s flux hr status nginx -o json
        """
        try:
            manager = get_manager()
            result = manager.get_helm_release_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(result, title=f"Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)
