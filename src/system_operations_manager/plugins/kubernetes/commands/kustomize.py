"""CLI commands for Kustomize operations.

Provides build, apply, diff, overlays, and validate commands
for working with Kustomize-managed Kubernetes manifests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.integrations.kubernetes.kustomize_client import (
    KustomizeBinaryNotFoundError,
    KustomizeError,
)
from system_operations_manager.plugins.kubernetes.commands.base import (
    DryRunOption,
    ForceOption,
    NamespaceOption,
    OutputOption,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kubernetes.manifest_manager import DiffResult

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes.kustomize_manager import KustomizeManager

# ---------------------------------------------------------------------------
# Kustomize-specific options
# ---------------------------------------------------------------------------

KustomizationPathArgument = Annotated[
    Path,
    typer.Argument(
        help="Path to directory containing kustomization.yaml",
        exists=True,
        resolve_path=True,
        file_okay=False,
        dir_okay=True,
    ),
]

ServerDryRunOption = Annotated[
    bool,
    typer.Option(
        "--server-dry-run",
        help="Perform server-side dry run (validates on server without persisting)",
    ),
]

EnableHelmOption = Annotated[
    bool,
    typer.Option(
        "--enable-helm",
        help="Enable Helm chart inflation generator",
    ),
]

EnableAlphaPluginsOption = Annotated[
    bool,
    typer.Option(
        "--enable-alpha-plugins",
        help="Enable alpha Kustomize plugins",
    ),
]

OutputFileOption = Annotated[
    Path | None,
    typer.Option(
        "--output-file",
        "-f",
        help="Write rendered YAML to file instead of stdout",
    ),
]

# ---------------------------------------------------------------------------
# Column definitions for table output
# ---------------------------------------------------------------------------

APPLY_COLUMNS = [
    ("resource", "Resource"),
    ("namespace", "Namespace"),
    ("action", "Action"),
    ("success", "Success"),
    ("message", "Message"),
]

DIFF_COLUMNS = [
    ("resource", "Resource"),
    ("namespace", "Namespace"),
    ("exists_on_cluster", "On Cluster"),
    ("identical", "Identical"),
]

OVERLAY_COLUMNS = [
    ("name", "Name"),
    ("path", "Path"),
    ("valid", "Valid"),
    ("resources", "Resources"),
]


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register_kustomize_commands(
    app: typer.Typer,
    get_manager: Callable[[], KustomizeManager],
) -> None:
    """Register Kustomize commands with the Kubernetes CLI app."""

    kustomize_app = typer.Typer(
        name="kustomize",
        help="Kustomize manifest management",
        no_args_is_help=True,
    )
    app.add_typer(kustomize_app, name="kustomize")

    # -----------------------------------------------------------------
    # build
    # -----------------------------------------------------------------

    @kustomize_app.command("build")
    def build(
        path: KustomizationPathArgument,
        enable_helm: EnableHelmOption = False,
        enable_alpha_plugins: EnableAlphaPluginsOption = False,
        output_file: OutputFileOption = None,
    ) -> None:
        """Build kustomization and render final manifests.

        Runs ``kustomize build`` and outputs the rendered YAML.
        By default prints to stdout; use ``--output-file`` to write
        to a file.

        Examples:
            ops k8s kustomize build ./overlays/dev
            ops k8s kustomize build ./base --output-file rendered.yaml
            ops k8s kustomize build ./overlays/prod --enable-helm
        """
        try:
            manager = get_manager()
            result = manager.build(
                path,
                enable_helm=enable_helm,
                enable_alpha_plugins=enable_alpha_plugins,
                output_file=output_file,
            )

            if not result.success:
                console.print(f"[red]Build failed:[/red] {result.error}")
                raise typer.Exit(1)

            if output_file:
                console.print(f"[green]Rendered YAML written to:[/green] {result.output_file}")
            else:
                console.print(result.rendered_yaml)

        except KustomizeBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except KustomizeError as e:
            _handle_kustomize_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # apply
    # -----------------------------------------------------------------

    @kustomize_app.command("apply")
    def apply(
        path: KustomizationPathArgument,
        namespace: NamespaceOption = None,
        dry_run: DryRunOption = False,
        server_dry_run: ServerDryRunOption = False,
        force: ForceOption = False,
        enable_helm: EnableHelmOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Build kustomization and apply to the cluster.

        Runs ``kustomize build`` then applies the rendered manifests.
        Use ``--dry-run`` for client-side preview or ``--server-dry-run``
        for server-side validation.

        Examples:
            ops k8s kustomize apply ./overlays/dev
            ops k8s kustomize apply ./overlays/prod -n production
            ops k8s kustomize apply ./base --dry-run
            ops k8s kustomize apply ./overlays/staging --server-dry-run
        """
        try:
            manager = get_manager()
            results = manager.apply(
                path,
                namespace=namespace,
                dry_run=dry_run,
                server_dry_run=server_dry_run,
                force=force,
                enable_helm=enable_helm,
            )

            formatter = get_formatter(output, console)
            result_dicts = [asdict(r) for r in results]

            if output == OutputFormat.TABLE:
                _print_apply_table(result_dicts)
            else:
                formatter.format_dict(
                    {"results": result_dicts, "total": len(result_dicts)},
                    title="Apply Results",
                )

            if any(not r.success for r in results):
                raise typer.Exit(1)

        except KustomizeBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except KustomizeError as e:
            _handle_kustomize_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # diff
    # -----------------------------------------------------------------

    @kustomize_app.command("diff")
    def diff(
        path: KustomizationPathArgument,
        namespace: NamespaceOption = None,
        enable_helm: EnableHelmOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Build kustomization and diff against live cluster state.

        Runs ``kustomize build`` then compares each resource against
        what exists on the cluster.

        Examples:
            ops k8s kustomize diff ./overlays/dev
            ops k8s kustomize diff ./overlays/prod -n production
            ops k8s kustomize diff ./base --output yaml
        """
        try:
            manager = get_manager()
            results = manager.diff(path, namespace=namespace, enable_helm=enable_helm)

            formatter = get_formatter(output, console)
            result_dicts = [asdict(r) for r in results]

            if output == OutputFormat.TABLE:
                _print_diff_table(results)
            else:
                formatter.format_dict(
                    {"results": result_dicts, "total": len(result_dicts)},
                    title="Diff Results",
                )

        except KustomizeBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except KustomizeError as e:
            _handle_kustomize_error(e)
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # overlays
    # -----------------------------------------------------------------

    @kustomize_app.command("overlays")
    def overlays(
        path: KustomizationPathArgument,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List available Kustomize overlays in a directory.

        Scans for directories containing kustomization.yaml files,
        typically in patterns like ``base/``, ``overlays/{dev,staging,prod}/``.

        Examples:
            ops k8s kustomize overlays .
            ops k8s kustomize overlays ./k8s --output json
        """
        try:
            manager = get_manager()
            overlay_list = manager.list_overlays(path)

            if not overlay_list:
                console.print("[yellow]No overlays found[/yellow]")
                return

            formatter = get_formatter(output, console)
            overlay_dicts = [asdict(o) for o in overlay_list]

            if output == OutputFormat.TABLE:
                _print_overlays_table(overlay_dicts)
            else:
                formatter.format_dict(
                    {"overlays": overlay_dicts, "total": len(overlay_dicts)},
                    title="Kustomize Overlays",
                )

        except KustomizeBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except KustomizeError as e:
            _handle_kustomize_error(e)

    # -----------------------------------------------------------------
    # validate
    # -----------------------------------------------------------------

    @kustomize_app.command("validate")
    def validate(
        path: KustomizationPathArgument,
    ) -> None:
        """Validate a kustomization directory.

        Checks for kustomization.yaml and attempts a build to
        validate the structure (no cluster connection required).

        Examples:
            ops k8s kustomize validate ./overlays/dev
            ops k8s kustomize validate ./base
        """
        try:
            manager = get_manager()
            valid, error = manager.validate(path)

            if valid:
                console.print(f"[green]Kustomization valid:[/green] {path}")
            else:
                console.print(f"[red]Kustomization invalid:[/red] {path}")
                console.print(f"  Error: {error}")
                raise typer.Exit(1)

        except KustomizeBinaryNotFoundError as e:
            _handle_binary_not_found(e)
        except KustomizeError as e:
            _handle_kustomize_error(e)

    # -----------------------------------------------------------------
    # Error helpers
    # -----------------------------------------------------------------

    def _handle_binary_not_found(e: KustomizeBinaryNotFoundError) -> None:
        """Handle missing kustomize binary with install guidance."""
        console.print(f"[red]Error:[/red] {e.message}")
        console.print(
            "\n[dim]Install kustomize: "
            "https://kubectl.docs.kubernetes.io/installation/kustomize/[/dim]"
        )
        raise typer.Exit(1) from None

    def _handle_kustomize_error(e: KustomizeError) -> None:
        """Handle general kustomize errors."""
        console.print(f"[red]Kustomize error:[/red] {e.message}")
        if e.stderr:
            console.print(f"\n[dim]{e.stderr}[/dim]")
        raise typer.Exit(1) from None

    # -----------------------------------------------------------------
    # Table helpers
    # -----------------------------------------------------------------

    def _print_apply_table(results: list[dict[str, object]]) -> None:
        """Print apply results as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Apply Results")
        table.add_column("Resource", style="cyan")
        table.add_column("Namespace", style="white")
        table.add_column("Action", style="green")
        table.add_column("Status", style="white")
        table.add_column("Message", style="dim")

        for r in results:
            status = "[green]OK[/green]" if r["success"] else "[red]FAILED[/red]"
            table.add_row(
                str(r["resource"]),
                str(r["namespace"]),
                str(r["action"]),
                status,
                str(r.get("message", "")),
            )
        console.print(table)
        console.print(f"\n[dim]Total: {len(results)} resource(s)[/dim]")

    def _print_diff_table(results: list[DiffResult]) -> None:
        """Print diff results with summary table and inline diffs."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Diff Summary")
        table.add_column("Resource", style="cyan")
        table.add_column("Namespace", style="white")
        table.add_column("On Cluster", style="white")
        table.add_column("Status", style="white")

        for r in results:
            on_cluster = "[green]Yes[/green]" if r.exists_on_cluster else "[yellow]No[/yellow]"
            if r.identical:
                status = "[green]Identical[/green]"
            elif r.exists_on_cluster:
                status = "[yellow]Changed[/yellow]"
            else:
                status = "[blue]New[/blue]"
            table.add_row(r.resource, r.namespace, on_cluster, status)

        console.print(table)

        for r in results:
            if r.diff and not r.identical:
                console.print(f"\n[bold]{r.resource}:[/bold]")
                for line in r.diff.splitlines():
                    if line.startswith("+"):
                        console.print(f"[green]{line}[/green]")
                    elif line.startswith("-"):
                        console.print(f"[red]{line}[/red]")
                    elif line.startswith("@@"):
                        console.print(f"[cyan]{line}[/cyan]")
                    else:
                        console.print(line)

    def _print_overlays_table(overlays: list[dict[str, object]]) -> None:
        """Print overlays as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Kustomize Overlays")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Valid", style="white")
        table.add_column("Resources", style="dim")

        for o in overlays:
            valid = "[green]Yes[/green]" if o["valid"] else "[red]No[/red]"
            resources = o.get("resources", [])
            resource_str = f"{len(resources)} resource(s)" if isinstance(resources, list) else ""
            table.add_row(
                str(o["name"]),
                str(o["path"]),
                valid,
                resource_str,
            )
        console.print(table)
        console.print(f"\n[dim]Total: {len(overlays)} overlay(s)[/dim]")
