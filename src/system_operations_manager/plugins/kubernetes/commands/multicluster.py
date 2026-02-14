"""Multi-cluster Kubernetes CLI commands.

Provides commands for cross-cluster operations: status overview,
multi-cluster deploy, and resource synchronization.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    DryRunOption,
    NamespaceOption,
    OutputOption,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from collections.abc import Callable

    from system_operations_manager.services.kubernetes.multicluster_manager import (
        MultiClusterManager,
    )

console = Console()

# ---------------------------------------------------------------------------
# Column Definitions
# ---------------------------------------------------------------------------

STATUS_COLUMNS = [
    ("cluster", "Cluster"),
    ("context", "Context"),
    ("connected", "Connected"),
    ("version", "Version"),
    ("node_count", "Nodes"),
    ("namespace", "Namespace"),
]

DEPLOY_COLUMNS = [
    ("cluster", "Cluster"),
    ("success", "Success"),
    ("resources_applied", "Applied"),
    ("resources_failed", "Failed"),
    ("error", "Error"),
]

SYNC_COLUMNS = [
    ("cluster", "Cluster"),
    ("success", "Success"),
    ("action", "Action"),
    ("error", "Error"),
]

# ---------------------------------------------------------------------------
# Shared Option Types
# ---------------------------------------------------------------------------

ClustersOption = str | None


def _parse_clusters(clusters_str: str | None) -> list[str] | None:
    """Parse a comma-separated cluster list into a list of names."""
    if not clusters_str:
        return None
    return [c.strip() for c in clusters_str.split(",") if c.strip()]


# ---------------------------------------------------------------------------
# Command Registration
# ---------------------------------------------------------------------------


def register_multicluster_commands(
    app: typer.Typer,
    get_manager: Callable[[], MultiClusterManager],
) -> None:
    """Register multi-cluster CLI commands."""
    mc_app = typer.Typer(
        name="multicluster",
        help="Multi-cluster operations (status, deploy, sync)",
        no_args_is_help=True,
    )
    app.add_typer(mc_app, name="multicluster")

    # -------------------------------------------------------------------
    # status
    # -------------------------------------------------------------------

    @mc_app.command("status")
    def status(
        clusters: str | None = typer.Option(
            None,
            "--clusters",
            "-c",
            help="Comma-separated cluster names (default: all configured)",
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show connectivity and version status for multiple clusters.

        Examples:
            ops k8s multicluster status
            ops k8s multicluster status --clusters staging,production
            ops k8s multicluster status --output json
        """
        try:
            manager = get_manager()
            cluster_list = _parse_clusters(clusters)
            result = manager.multi_cluster_status(cluster_list)

            formatter = get_formatter(output, console)
            formatter.format_list(
                result.clusters,
                STATUS_COLUMNS,
                title=f"Multi-Cluster Status ({result.connected}/{result.total} connected)",
            )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------
    # deploy
    # -------------------------------------------------------------------

    @mc_app.command("deploy")
    def deploy(
        file: str = typer.Option(
            ...,
            "--file",
            "-f",
            help="Path to manifest file or directory, or '-' for stdin",
        ),
        clusters: str | None = typer.Option(
            None,
            "--clusters",
            "-c",
            help="Comma-separated cluster names (default: all configured)",
        ),
        namespace: NamespaceOption = None,
        dry_run: DryRunOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Deploy manifests to multiple clusters.

        Reads a YAML manifest from a file, directory, or stdin and applies
        it to the specified (or all configured) clusters.

        Examples:
            ops k8s multicluster deploy --file app.yaml
            ops k8s multicluster deploy --file app.yaml --clusters staging,production
            ops k8s multicluster deploy --file manifests/ --namespace app --dry-run
            cat app.yaml | ops k8s multicluster deploy --file -
        """
        try:
            manager = get_manager()

            # Load manifests from file or stdin
            if file == "-":
                content = sys.stdin.read()
                if not content.strip():
                    console.print("[red]Error:[/red] No input received from stdin")
                    raise typer.Exit(1)
                manifests = manager.load_manifests_from_string(content)
            else:
                manifest_path = Path(file)
                if not manifest_path.exists():
                    console.print(f"[red]Error:[/red] Path not found: {file}")
                    raise typer.Exit(1)
                manifests = manager.load_manifests_from_path(manifest_path)

            if not manifests:
                console.print("[yellow]Warning:[/yellow] No manifests found in input")
                raise typer.Exit(0)

            cluster_list = _parse_clusters(clusters)
            result = manager.deploy_manifests_to_clusters(
                manifests,
                clusters=cluster_list,
                namespace=namespace,
                dry_run=dry_run,
            )

            if dry_run:
                console.print("[yellow]Dry run mode - no changes applied[/yellow]\n")

            formatter = get_formatter(output, console)
            formatter.format_list(
                result.cluster_results,
                DEPLOY_COLUMNS,
                title=f"Multi-Cluster Deploy ({result.successful}/{result.total_clusters} succeeded)",
            )

            if result.failed > 0:
                raise typer.Exit(1)

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------
    # sync
    # -------------------------------------------------------------------

    @mc_app.command("sync")
    def sync(
        source: str = typer.Option(
            ...,
            "--source",
            "-s",
            help="Source cluster name to read the resource from",
        ),
        target: str = typer.Option(
            ...,
            "--target",
            "-t",
            help="Comma-separated target cluster names",
        ),
        kind: str = typer.Option(
            ...,
            "--kind",
            "-k",
            help="Kubernetes resource kind (e.g., Deployment, ConfigMap, Secret)",
        ),
        name: str = typer.Option(
            ...,
            "--name",
            help="Resource name",
        ),
        namespace: NamespaceOption = None,
        dry_run: DryRunOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Sync a resource from one cluster to others.

        Reads a resource from the source cluster, strips server-managed
        metadata, and applies it to each target cluster.

        Examples:
            ops k8s multicluster sync --source staging --target production --kind ConfigMap --name app-config -n default
            ops k8s multicluster sync -s dev -t staging,production -k Deployment --name api-server -n app --dry-run
            ops k8s multicluster sync --source prod --target dr --kind Secret --name tls-cert -n istio-system
        """
        try:
            manager = get_manager()
            target_clusters = [t.strip() for t in target.split(",") if t.strip()]

            if not target_clusters:
                console.print("[red]Error:[/red] No target clusters specified")
                raise typer.Exit(1)

            if source in target_clusters:
                console.print(
                    "[yellow]Warning:[/yellow] Source cluster is also a target, it will be skipped"
                )
                target_clusters = [t for t in target_clusters if t != source]
                if not target_clusters:
                    console.print("[red]Error:[/red] No target clusters remaining after filtering")
                    raise typer.Exit(1)

            result = manager.sync_resource(
                source,
                target_clusters,
                resource_type=kind,
                resource_name=name,
                namespace=namespace,
                dry_run=dry_run,
            )

            if dry_run:
                console.print("[yellow]Dry run mode - no changes applied[/yellow]\n")

            formatter = get_formatter(output, console)
            formatter.format_list(
                result.cluster_results,
                SYNC_COLUMNS,
                title=(
                    f"Sync {kind}/{name} from {source} "
                    f"({result.successful}/{result.total_targets} succeeded)"
                ),
            )

            if result.failed > 0:
                raise typer.Exit(1)

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)
