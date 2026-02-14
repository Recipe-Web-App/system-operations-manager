"""CLI commands for Helm chart and release management.

Provides install, upgrade, rollback, list, uninstall, status,
history, get-values, template, search, and repo management commands.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.integrations.kubernetes.helm_client import (
    HelmBinaryNotFoundError,
    HelmError,
)
from system_operations_manager.plugins.kubernetes.commands.base import (
    DryRunOption,
    NamespaceOption,
    OutputOption,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.models.helm import HelmReleaseStatus
    from system_operations_manager.services.kubernetes.helm_manager import HelmManager

# ---------------------------------------------------------------------------
# Helm-specific options
# ---------------------------------------------------------------------------

ChartArgument = Annotated[
    str,
    typer.Argument(help="Chart reference (repo/chart, local path, or URL)"),
]

ReleaseArgument = Annotated[
    str,
    typer.Argument(help="Release name"),
]

ValuesFilesOption = Annotated[
    list[str] | None,
    typer.Option(
        "--values",
        "-f",
        help="Values YAML file (can specify multiple)",
    ),
]

SetValuesOption = Annotated[
    list[str] | None,
    typer.Option(
        "--set",
        help="Set individual values (key=value, can specify multiple)",
    ),
]

VersionOption = Annotated[
    str | None,
    typer.Option(
        "--version",
        help="Chart version constraint",
    ),
]

WaitOption = Annotated[
    bool,
    typer.Option(
        "--wait",
        help="Wait for resources to be ready",
    ),
]

TimeoutOption = Annotated[
    str | None,
    typer.Option(
        "--timeout",
        help="Timeout for --wait (e.g., 5m0s)",
    ),
]

CreateNamespaceOption = Annotated[
    bool,
    typer.Option(
        "--create-namespace",
        help="Create namespace if it doesn't exist",
    ),
]

AllNamespacesOption = Annotated[
    bool,
    typer.Option(
        "--all-namespaces",
        "-A",
        help="List releases across all namespaces",
    ),
]

KeepHistoryOption = Annotated[
    bool,
    typer.Option(
        "--keep-history",
        help="Keep release history after uninstall",
    ),
]

RevisionOption = Annotated[
    int | None,
    typer.Option(
        "--revision",
        help="Specific revision number",
    ),
]

AllValuesOption = Annotated[
    bool,
    typer.Option(
        "--all",
        "-a",
        help="Show all values (including chart defaults)",
    ),
]

# ---------------------------------------------------------------------------
# Column definitions for table output
# ---------------------------------------------------------------------------

RELEASE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("revision", "Revision"),
    ("status", "Status"),
    ("chart", "Chart"),
    ("app_version", "App Version"),
]

HISTORY_COLUMNS = [
    ("revision", "Revision"),
    ("status", "Status"),
    ("chart", "Chart"),
    ("app_version", "App Version"),
    ("description", "Description"),
]

REPO_COLUMNS = [
    ("name", "Name"),
    ("url", "URL"),
]

CHART_COLUMNS = [
    ("name", "Name"),
    ("chart_version", "Version"),
    ("app_version", "App Version"),
    ("description", "Description"),
]


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register_helm_commands(
    app: typer.Typer,
    get_manager: Callable[[], HelmManager],
) -> None:
    """Register Helm commands with the Kubernetes CLI app."""

    helm_app = typer.Typer(
        name="helm",
        help="Helm chart and release management",
        no_args_is_help=True,
    )
    app.add_typer(helm_app, name="helm")

    # -----------------------------------------------------------------
    # install
    # -----------------------------------------------------------------

    @helm_app.command("install")
    def install(
        release: ReleaseArgument,
        chart: ChartArgument,
        namespace: NamespaceOption = None,
        values_files: ValuesFilesOption = None,
        set_values: SetValuesOption = None,
        version: VersionOption = None,
        create_namespace: CreateNamespaceOption = False,
        wait: WaitOption = False,
        timeout: TimeoutOption = None,
        dry_run: DryRunOption = False,
    ) -> None:
        """Install a Helm chart.

        Examples:
            ops k8s helm install my-release bitnami/nginx
            ops k8s helm install my-app ./charts/app -n production
            ops k8s helm install redis bitnami/redis -f values.yaml --set auth.enabled=true
            ops k8s helm install pg bitnami/postgresql --version 12.0.0 --create-namespace
        """
        try:
            manager = get_manager()
            result = manager.install(
                release,
                chart,
                namespace=namespace,
                values_files=values_files,
                set_values=set_values,
                version=version,
                create_namespace=create_namespace,
                wait=wait,
                timeout=timeout,
                dry_run=dry_run,
            )

            if dry_run:
                console.print("[yellow]Dry run:[/yellow]")
            console.print(result.stdout)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # upgrade
    # -----------------------------------------------------------------

    @helm_app.command("upgrade")
    def upgrade(
        release: ReleaseArgument,
        chart: ChartArgument,
        namespace: NamespaceOption = None,
        values_files: ValuesFilesOption = None,
        set_values: SetValuesOption = None,
        version: VersionOption = None,
        install: Annotated[
            bool,
            typer.Option("--install", "-i", help="Install if release doesn't exist"),
        ] = False,
        create_namespace: CreateNamespaceOption = False,
        wait: WaitOption = False,
        timeout: TimeoutOption = None,
        dry_run: DryRunOption = False,
        reuse_values: Annotated[
            bool,
            typer.Option("--reuse-values", help="Reuse last release's values"),
        ] = False,
        reset_values: Annotated[
            bool,
            typer.Option("--reset-values", help="Reset values to chart defaults"),
        ] = False,
    ) -> None:
        """Upgrade a Helm release.

        Examples:
            ops k8s helm upgrade my-release bitnami/nginx
            ops k8s helm upgrade my-app ./charts/app -f values-prod.yaml
            ops k8s helm upgrade my-release bitnami/redis --install --create-namespace
            ops k8s helm upgrade my-release bitnami/nginx --reuse-values --set image.tag=1.25
        """
        try:
            manager = get_manager()
            result = manager.upgrade(
                release,
                chart,
                namespace=namespace,
                values_files=values_files,
                set_values=set_values,
                version=version,
                install=install,
                create_namespace=create_namespace,
                wait=wait,
                timeout=timeout,
                dry_run=dry_run,
                reuse_values=reuse_values,
                reset_values=reset_values,
            )

            if dry_run:
                console.print("[yellow]Dry run:[/yellow]")
            console.print(result.stdout)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # rollback
    # -----------------------------------------------------------------

    @helm_app.command("rollback")
    def rollback(
        release: ReleaseArgument,
        revision: Annotated[
            int | None,
            typer.Argument(help="Revision to roll back to (default: previous)"),
        ] = None,
        namespace: NamespaceOption = None,
        wait: WaitOption = False,
        timeout: TimeoutOption = None,
        dry_run: DryRunOption = False,
    ) -> None:
        """Rollback a release to a previous revision.

        Examples:
            ops k8s helm rollback my-release
            ops k8s helm rollback my-release 3
            ops k8s helm rollback my-release 2 --wait
        """
        try:
            manager = get_manager()
            result = manager.rollback(
                release,
                revision,
                namespace=namespace,
                wait=wait,
                timeout=timeout,
                dry_run=dry_run,
            )

            if dry_run:
                console.print("[yellow]Dry run:[/yellow]")
            console.print(result.stdout)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # uninstall
    # -----------------------------------------------------------------

    @helm_app.command("uninstall")
    def uninstall(
        release: ReleaseArgument,
        namespace: NamespaceOption = None,
        keep_history: KeepHistoryOption = False,
        dry_run: DryRunOption = False,
    ) -> None:
        """Uninstall a Helm release.

        Examples:
            ops k8s helm uninstall my-release
            ops k8s helm uninstall my-release -n production
            ops k8s helm uninstall my-release --keep-history
        """
        try:
            manager = get_manager()
            result = manager.uninstall(
                release,
                namespace=namespace,
                keep_history=keep_history,
                dry_run=dry_run,
            )

            if dry_run:
                console.print("[yellow]Dry run:[/yellow]")
            console.print(result.stdout)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # list
    # -----------------------------------------------------------------

    @helm_app.command("list")
    def list_releases(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        all_releases: Annotated[
            bool,
            typer.Option("--all", "-a", help="Include releases in all states"),
        ] = False,
        filter_pattern: Annotated[
            str | None,
            typer.Option("--filter", "-q", help="Filter releases by name pattern"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Helm releases.

        Examples:
            ops k8s helm list
            ops k8s helm list -n production
            ops k8s helm list -A
            ops k8s helm list --filter 'my-*' --output json
        """
        try:
            manager = get_manager()
            releases = manager.list_releases(
                namespace=namespace,
                all_namespaces=all_namespaces,
                all_releases=all_releases,
                filter_pattern=filter_pattern,
            )

            if not releases:
                console.print("[yellow]No releases found[/yellow]")
                return

            formatter = get_formatter(output, console)
            release_dicts = [asdict(r) for r in releases]

            if output == OutputFormat.TABLE:
                _print_releases_table(release_dicts)
            else:
                formatter.format_dict(
                    {"releases": release_dicts, "total": len(release_dicts)},
                    title="Helm Releases",
                )

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # history
    # -----------------------------------------------------------------

    @helm_app.command("history")
    def history(
        release: ReleaseArgument,
        namespace: NamespaceOption = None,
        max_revisions: Annotated[
            int | None,
            typer.Option("--max", help="Maximum number of revisions to show"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show release history.

        Examples:
            ops k8s helm history my-release
            ops k8s helm history my-release -n production --max 5
        """
        try:
            manager = get_manager()
            entries = manager.history(
                release,
                namespace=namespace,
                max_revisions=max_revisions,
            )

            if not entries:
                console.print("[yellow]No history found[/yellow]")
                return

            formatter = get_formatter(output, console)
            entry_dicts = [asdict(e) for e in entries]

            if output == OutputFormat.TABLE:
                _print_history_table(entry_dicts)
            else:
                formatter.format_dict(
                    {"history": entry_dicts, "total": len(entry_dicts)},
                    title=f"Release History: {release}",
                )

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # status
    # -----------------------------------------------------------------

    @helm_app.command("status")
    def status(
        release: ReleaseArgument,
        namespace: NamespaceOption = None,
        revision: RevisionOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show release status.

        Examples:
            ops k8s helm status my-release
            ops k8s helm status my-release -n production
            ops k8s helm status my-release --revision 3 --output json
        """
        try:
            manager = get_manager()
            release_status = manager.status(
                release,
                namespace=namespace,
                revision=revision,
            )

            formatter = get_formatter(output, console)

            if output == OutputFormat.TABLE:
                _print_status_table(release_status)
            else:
                formatter.format_dict(
                    asdict(release_status),
                    title=f"Release Status: {release}",
                )

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # get-values
    # -----------------------------------------------------------------

    @helm_app.command("get-values")
    def get_values(
        release: ReleaseArgument,
        namespace: NamespaceOption = None,
        all_values: AllValuesOption = False,
        revision: RevisionOption = None,
    ) -> None:
        """Get values for a release.

        Examples:
            ops k8s helm get-values my-release
            ops k8s helm get-values my-release --all
            ops k8s helm get-values my-release --revision 2
        """
        try:
            manager = get_manager()
            values = manager.get_values(
                release,
                namespace=namespace,
                all_values=all_values,
                revision=revision,
            )

            console.print(values)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # template
    # -----------------------------------------------------------------

    @helm_app.command("template")
    def template(
        release: ReleaseArgument,
        chart: ChartArgument,
        namespace: NamespaceOption = None,
        values_files: ValuesFilesOption = None,
        set_values: SetValuesOption = None,
        version: VersionOption = None,
    ) -> None:
        """Render chart templates locally.

        Examples:
            ops k8s helm template my-release bitnami/nginx
            ops k8s helm template my-app ./charts/app -f values.yaml
            ops k8s helm template my-release bitnami/redis --set auth.enabled=false
        """
        try:
            manager = get_manager()
            result = manager.template(
                release,
                chart,
                namespace=namespace,
                values_files=values_files,
                set_values=set_values,
                version=version,
            )

            if not result.success:
                console.print(f"[red]Template failed:[/red] {result.error}")
                raise typer.Exit(1)

            console.print(result.rendered_yaml)

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # search
    # -----------------------------------------------------------------

    @helm_app.command("search")
    def search(
        keyword: Annotated[str, typer.Argument(help="Search keyword")],
        version: VersionOption = None,
        all_versions: Annotated[
            bool,
            typer.Option("--versions", help="Show all versions, not just latest"),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Search chart repositories for charts.

        Examples:
            ops k8s helm search nginx
            ops k8s helm search postgresql --versions
            ops k8s helm search bitnami/redis --output json
        """
        try:
            manager = get_manager()
            charts = manager.search_repo(
                keyword,
                version=version,
                all_versions=all_versions,
            )

            if not charts:
                console.print(f"[yellow]No charts found for '{keyword}'[/yellow]")
                return

            formatter = get_formatter(output, console)
            chart_dicts = [asdict(c) for c in charts]

            if output == OutputFormat.TABLE:
                _print_charts_table(chart_dicts)
            else:
                formatter.format_dict(
                    {"charts": chart_dicts, "total": len(chart_dicts)},
                    title="Search Results",
                )

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # repo subcommands
    # -----------------------------------------------------------------

    repo_app = typer.Typer(
        name="repo",
        help="Helm chart repository management",
        no_args_is_help=True,
    )
    helm_app.add_typer(repo_app, name="repo")

    @repo_app.command("add")
    def repo_add(
        name: Annotated[str, typer.Argument(help="Repository name")],
        url: Annotated[str, typer.Argument(help="Repository URL")],
        force_update: Annotated[
            bool,
            typer.Option("--force-update", help="Replace existing repo with same name"),
        ] = False,
    ) -> None:
        """Add a chart repository.

        Examples:
            ops k8s helm repo add bitnami https://charts.bitnami.com/bitnami
            ops k8s helm repo add stable https://charts.helm.sh/stable --force-update
        """
        try:
            manager = get_manager()
            manager.repo_add(name, url, force_update=force_update)

            console.print(f"[green]Repository '{name}' added successfully[/green]")

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)

    @repo_app.command("list")
    def repo_list(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List configured chart repositories.

        Examples:
            ops k8s helm repo list
            ops k8s helm repo list --output json
        """
        try:
            manager = get_manager()
            repos = manager.repo_list()

            if not repos:
                console.print("[yellow]No repositories configured[/yellow]")
                return

            formatter = get_formatter(output, console)
            repo_dicts = [asdict(r) for r in repos]

            if output == OutputFormat.TABLE:
                _print_repos_table(repo_dicts)
            else:
                formatter.format_dict(
                    {"repositories": repo_dicts, "total": len(repo_dicts)},
                    title="Helm Repositories",
                )

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)

    @repo_app.command("update")
    def repo_update(
        names: Annotated[
            list[str] | None,
            typer.Argument(help="Specific repos to update (all if omitted)"),
        ] = None,
    ) -> None:
        """Update chart repository indexes.

        Examples:
            ops k8s helm repo update
            ops k8s helm repo update bitnami stable
        """
        try:
            manager = get_manager()
            manager.repo_update(names)

            console.print("[green]Repositories updated successfully[/green]")

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)

    @repo_app.command("remove")
    def repo_remove(
        name: Annotated[str, typer.Argument(help="Repository name to remove")],
    ) -> None:
        """Remove a chart repository.

        Examples:
            ops k8s helm repo remove bitnami
        """
        try:
            manager = get_manager()
            manager.repo_remove(name)

            console.print(f"[green]Repository '{name}' removed[/green]")

        except HelmBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except HelmError as e:
            _handle_helm_error(e)

    # -----------------------------------------------------------------
    # Error helpers
    # -----------------------------------------------------------------

    def _handle_binary_not_found(e: HelmBinaryNotFoundError) -> None:
        """Handle missing helm binary with install guidance."""
        console.print(f"[red]Error:[/red] {e.message}")
        console.print("\n[dim]Install helm: https://helm.sh/docs/intro/install/[/dim]")
        raise typer.Exit(1) from None

    def _handle_helm_error(e: HelmError) -> None:
        """Handle general helm errors."""
        console.print(f"[red]Helm error:[/red] {e.message}")
        if e.stderr:
            console.print(f"\n[dim]{e.stderr}[/dim]")
        raise typer.Exit(1) from None

    # -----------------------------------------------------------------
    # Table helpers
    # -----------------------------------------------------------------

    def _print_releases_table(releases: list[dict[str, object]]) -> None:
        """Print releases as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Helm Releases")
        table.add_column("Name", style="cyan")
        table.add_column("Namespace", style="white")
        table.add_column("Revision", style="white", justify="right")
        table.add_column("Status", style="white")
        table.add_column("Chart", style="dim")
        table.add_column("App Version", style="dim")

        for r in releases:
            status_str = str(r.get("status", ""))
            status_display = _colorize_status(status_str)
            table.add_row(
                str(r["name"]),
                str(r["namespace"]),
                str(r["revision"]),
                status_display,
                str(r["chart"]),
                str(r["app_version"]),
            )
        console.print(table)
        console.print(f"\n[dim]Total: {len(releases)} release(s)[/dim]")

    def _print_history_table(entries: list[dict[str, object]]) -> None:
        """Print release history as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Release History")
        table.add_column("Revision", style="cyan", justify="right")
        table.add_column("Status", style="white")
        table.add_column("Chart", style="dim")
        table.add_column("App Version", style="dim")
        table.add_column("Description", style="white")

        for e in entries:
            status_str = str(e.get("status", ""))
            table.add_row(
                str(e["revision"]),
                _colorize_status(status_str),
                str(e["chart"]),
                str(e["app_version"]),
                str(e["description"]),
            )
        console.print(table)

    def _print_status_table(status: HelmReleaseStatus) -> None:
        """Print release status as a Rich table."""
        from system_operations_manager.cli.output import Table

        s = asdict(status)
        table = Table(title=f"Release Status: {s['name']}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", str(s["name"]))
        table.add_row("Namespace", str(s["namespace"]))
        table.add_row("Revision", str(s["revision"]))
        table.add_row("Status", _colorize_status(str(s["status"])))
        table.add_row("Description", str(s["description"]))

        console.print(table)

        if s.get("notes"):
            console.print(f"\n[bold]Notes:[/bold]\n{s['notes']}")

    def _print_repos_table(repos: list[dict[str, object]]) -> None:
        """Print repos as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Helm Repositories")
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="white")

        for r in repos:
            table.add_row(str(r["name"]), str(r["url"]))
        console.print(table)
        console.print(f"\n[dim]Total: {len(repos)} repository(ies)[/dim]")

    def _print_charts_table(charts: list[dict[str, object]]) -> None:
        """Print search results as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Search Results")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="white")
        table.add_column("App Version", style="white")
        table.add_column("Description", style="dim")

        for c in charts:
            table.add_row(
                str(c["name"]),
                str(c["chart_version"]),
                str(c["app_version"]),
                str(c["description"]),
            )
        console.print(table)
        console.print(f"\n[dim]Total: {len(charts)} chart(s)[/dim]")

    def _colorize_status(status: str) -> str:
        """Return a Rich-formatted status string."""
        lower = status.lower()
        if lower == "deployed":
            return f"[green]{status}[/green]"
        if lower in ("failed", "uninstalled"):
            return f"[red]{status}[/red]"
        if lower in ("pending-install", "pending-upgrade", "pending-rollback"):
            return f"[yellow]{status}[/yellow]"
        if lower == "superseded":
            return f"[dim]{status}[/dim]"
        return status
