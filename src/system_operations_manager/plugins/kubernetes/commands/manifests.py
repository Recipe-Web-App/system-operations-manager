"""CLI commands for Kubernetes manifest operations.

Provides apply, diff, and validate commands for YAML manifest
files and directories.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
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
    from system_operations_manager.services.kubernetes.manifest_manager import ManifestManager

# ---------------------------------------------------------------------------
# Manifest-specific options
# ---------------------------------------------------------------------------

ServerDryRunOption = Annotated[
    bool,
    typer.Option(
        "--server-dry-run",
        help="Perform server-side dry run (validates on server without persisting)",
    ),
]

ManifestPathArgument = Annotated[
    Path,
    typer.Argument(
        help="Path to a YAML file or directory of manifests",
        exists=True,
        resolve_path=True,
    ),
]

# ---------------------------------------------------------------------------
# Column definitions for table output
# ---------------------------------------------------------------------------

VALIDATION_COLUMNS = [
    ("resource", "Resource"),
    ("file", "File"),
    ("valid", "Valid"),
    ("errors", "Errors"),
]

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


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register_manifest_commands(
    app: typer.Typer,
    get_manager: Callable[[], ManifestManager],
) -> None:
    """Register manifest management commands with the Kubernetes CLI app."""

    manifests_app = typer.Typer(
        name="manifests",
        help="Manage Kubernetes YAML manifests",
        no_args_is_help=True,
    )
    app.add_typer(manifests_app, name="manifests")

    # -----------------------------------------------------------------
    # apply
    # -----------------------------------------------------------------

    @manifests_app.command("apply")
    def apply_manifests(
        path: ManifestPathArgument,
        namespace: NamespaceOption = None,
        dry_run: DryRunOption = False,
        server_dry_run: ServerDryRunOption = False,
        force: ForceOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Apply manifests from a file or directory to the cluster.

        Validates manifests before applying. Use ``--dry-run`` for a
        client-side dry run (no API calls) or ``--server-dry-run`` for
        server-side validation without persisting.

        Examples:
            ops k8s manifests apply deployment.yaml
            ops k8s manifests apply ./manifests/ -n production
            ops k8s manifests apply app.yaml --dry-run
            ops k8s manifests apply app.yaml --server-dry-run
        """
        try:
            manager = get_manager()
            manifests = manager.load_manifests(path)

            if not manifests:
                console.print("[yellow]No manifests found[/yellow]")
                return

            # Validate first
            validation = manager.validate_manifests(manifests, str(path))
            invalid = [v for v in validation if not v.valid]
            if invalid and not force:
                console.print("[red]Validation errors:[/red]")
                for v in invalid:
                    for err in v.errors:
                        console.print(f"  {v.resource}: {err}")
                raise typer.Exit(1)

            results = manager.apply_manifests(
                manifests,
                namespace,
                dry_run=dry_run,
                server_dry_run=server_dry_run,
                force=force,
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

            # Non-zero exit if any failed
            if any(not r.success for r in results):
                raise typer.Exit(1)

        except (FileNotFoundError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # diff
    # -----------------------------------------------------------------

    @manifests_app.command("diff")
    def diff_manifests(
        path: ManifestPathArgument,
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show differences between local manifests and live cluster state.

        Fetches each resource from the cluster and produces a unified
        diff. Resources that do not exist on the cluster are shown as
        entirely new.

        Examples:
            ops k8s manifests diff deployment.yaml
            ops k8s manifests diff ./manifests/ -n production
            ops k8s manifests diff app.yaml --output yaml
        """
        try:
            manager = get_manager()
            manifests = manager.load_manifests(path)

            if not manifests:
                console.print("[yellow]No manifests found[/yellow]")
                return

            results = manager.diff_manifests(manifests, namespace)

            formatter = get_formatter(output, console)
            result_dicts = [asdict(r) for r in results]

            if output == OutputFormat.TABLE:
                _print_diff_table(results)
            else:
                formatter.format_dict(
                    {"results": result_dicts, "total": len(result_dicts)},
                    title="Diff Results",
                )

        except (FileNotFoundError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    # -----------------------------------------------------------------
    # validate
    # -----------------------------------------------------------------

    @manifests_app.command("validate")
    def validate_manifests(
        path: ManifestPathArgument,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Validate YAML manifests client-side (no cluster connection required).

        Checks that each manifest has the required fields:
        ``apiVersion``, ``kind``, ``metadata``, and ``metadata.name``.

        Examples:
            ops k8s manifests validate deployment.yaml
            ops k8s manifests validate ./manifests/
            ops k8s manifests validate app.yaml --output json
        """
        try:
            manager = get_manager()
            manifests = manager.load_manifests(path)

            if not manifests:
                console.print("[yellow]No manifests found[/yellow]")
                return

            results = manager.validate_manifests(manifests, str(path))

            formatter = get_formatter(output, console)
            result_dicts = [asdict(r) for r in results]

            if output == OutputFormat.TABLE:
                _print_validation_table(result_dicts)
            else:
                formatter.format_dict(
                    {"results": result_dicts, "total": len(result_dicts)},
                    title="Validation Results",
                )

            invalid_count = sum(1 for r in results if not r.valid)
            if invalid_count:
                console.print(f"\n[red]{invalid_count} manifest(s) invalid[/red]")
                raise typer.Exit(1)
            else:
                console.print(f"\n[green]All {len(results)} manifest(s) valid[/green]")

        except (FileNotFoundError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

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

    def _print_validation_table(results: list[dict[str, object]]) -> None:
        """Print validation results as a Rich table."""
        from system_operations_manager.cli.output import Table

        table = Table(title="Validation Results")
        table.add_column("Resource", style="cyan")
        table.add_column("File", style="white")
        table.add_column("Valid", style="white")
        table.add_column("Errors", style="red")

        for r in results:
            valid = "[green]Yes[/green]" if r["valid"] else "[red]No[/red]"
            error_list = r.get("errors", [])
            errors = "; ".join(str(e) for e in error_list) if isinstance(error_list, list) else ""
            table.add_row(
                str(r["resource"]),
                str(r["file"]),
                valid,
                errors,
            )
        console.print(table)

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

        # Print inline diffs for changed resources
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
