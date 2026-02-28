"""Kong Gateway deployment CLI commands.

Provides commands for installing, upgrading, and managing Kong Gateway
deployments in Kubernetes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.deployment_manager import KongDeploymentManager

console = Console()


def register_deployment_commands(
    app: typer.Typer,
    get_deployment_manager: Callable[[], KongDeploymentManager],
) -> None:
    """Register deployment commands with the CLI.

    Args:
        app: Typer app to register commands with.
        get_deployment_manager: Factory function for deployment manager.
    """
    deploy_app = typer.Typer(
        name="deploy",
        help="Kong Gateway deployment management",
        no_args_is_help=True,
    )

    @deploy_app.command("status")
    def deploy_status(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong Gateway deployment status.

        Examples:
            ops kong deploy status
            ops kong deploy status --output json
        """
        try:
            manager = get_deployment_manager()
            info = manager.get_status()

            if output == OutputFormat.TABLE:
                # Status table
                table = Table(title="Kong Deployment Status")
                table.add_column("Property", style="cyan")
                table.add_column("Value")

                status_style = {
                    "running": "[green]Running[/green]",
                    "degraded": "[yellow]Degraded[/yellow]",
                    "failed": "[red]Failed[/red]",
                    "not_installed": "[dim]Not Installed[/dim]",
                    "unknown": "[dim]Unknown[/dim]",
                }.get(info.status.value, info.status.value)

                table.add_row("Status", status_style)
                table.add_row("Namespace", info.namespace)

                if info.chart:
                    table.add_row("Chart", info.chart)
                if info.chart_version:
                    table.add_row("Chart Version", info.chart_version)
                if info.app_version:
                    table.add_row("App Version", info.app_version)

                table.add_row(
                    "PostgreSQL",
                    "[green]Ready[/green]" if info.postgres_ready else "[red]Not Ready[/red]",
                )
                table.add_row(
                    "Gateway",
                    "[green]Ready[/green]" if info.gateway_ready else "[red]Not Ready[/red]",
                )
                table.add_row(
                    "Controller",
                    "[green]Ready[/green]" if info.controller_ready else "[red]Not Ready[/red]",
                )

                console.print(table)

                # Pod table
                if info.pods:
                    pod_table = Table(title="Pods")
                    pod_table.add_column("Name", style="cyan")
                    pod_table.add_column("Phase")
                    pod_table.add_column("Ready")
                    pod_table.add_column("Restarts")

                    for pod in info.pods:
                        ready_str = "[green]Yes[/green]" if pod.ready else "[red]No[/red]"
                        pod_table.add_row(
                            pod.name,
                            pod.phase,
                            ready_str,
                            str(pod.restarts),
                        )

                    console.print(pod_table)
            else:
                formatter = get_formatter(output, console)
                data = {
                    "status": info.status.value,
                    "namespace": info.namespace,
                    "chart": info.chart,
                    "chart_version": info.chart_version,
                    "app_version": info.app_version,
                    "postgres_ready": info.postgres_ready,
                    "gateway_ready": info.gateway_ready,
                    "controller_ready": info.controller_ready,
                    "pods": [
                        {
                            "name": p.name,
                            "phase": p.phase,
                            "ready": p.ready,
                            "restarts": p.restarts,
                        }
                        for p in info.pods
                    ],
                }
                formatter.format_dict(data, title="Kong Deployment Status")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from e

    @deploy_app.command("install")
    def deploy_install(
        force: ForceOption = False,
    ) -> None:
        """Install Kong Gateway with PostgreSQL.

        This command:
        1. Sets up the Kong Helm repository
        2. Creates the kong namespace
        3. Creates the PostgreSQL secret from config/.env.kong.secrets
        4. Deploys PostgreSQL
        5. Installs Kong Gateway using the kong/ingress chart

        Prerequisites:
            - Kubernetes cluster access (kubectl configured)
            - Helm 3 installed
            - config/.env.kong.secrets file exists

        Examples:
            ops kong deploy install
            ops kong deploy install --force
        """
        try:
            manager = get_deployment_manager()

            # Check current status
            info = manager.get_status()
            if info.status != info.status.NOT_INSTALLED:
                if not force and not typer.confirm(
                    f"Kong is already {info.status.value}. Reinstall?",
                    default=False,
                ):
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

                # Uninstall first
                console.print("[yellow]Uninstalling existing deployment...[/yellow]")
                manager.uninstall(keep_postgres=False, keep_secrets=False, keep_pvc=False)

            def progress(msg: str) -> None:
                console.print(f"[blue]→[/blue] {msg}")

            manager._progress = progress
            manager.install()

            console.print("\n[green]✓ Kong Gateway installed successfully![/green]")
            console.print("\n[dim]Next steps:[/dim]")
            console.print(
                "  • Port-forward Admin API: kubectl port-forward svc/kong-gateway-admin -n kong 8001:8001"
            )
            console.print("  • Check status: ops kong status")
            console.print("  • List services: ops kong services list")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            if hasattr(e, "details") and e.details:
                console.print(f"[dim]{e.details}[/dim]")
            raise typer.Exit(1) from e

    @deploy_app.command("upgrade")
    def deploy_upgrade() -> None:
        """Upgrade Kong Gateway to latest configuration.

        Updates the Kong deployment with changes from kong-values.yaml.
        PostgreSQL is not affected.

        Examples:
            ops kong deploy upgrade
        """
        try:
            manager = get_deployment_manager()

            # Check current status
            info = manager.get_status()
            if info.status == info.status.NOT_INSTALLED:
                console.print("[red]Error:[/red] Kong is not installed")
                console.print("[dim]Run 'ops kong deploy install' first[/dim]")
                raise typer.Exit(1)

            def progress(msg: str) -> None:
                console.print(f"[blue]→[/blue] {msg}")

            manager._progress = progress
            manager.upgrade()

            console.print("\n[green]✓ Kong Gateway upgraded successfully![/green]")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            if hasattr(e, "details") and e.details:
                console.print(f"[dim]{e.details}[/dim]")
            raise typer.Exit(1) from e

    @deploy_app.command("uninstall")
    def deploy_uninstall(
        keep_postgres: bool = typer.Option(
            False,
            "--keep-postgres",
            help="Keep PostgreSQL database",
        ),
        keep_secrets: bool = typer.Option(
            True,
            "--keep-secrets/--delete-secrets",
            help="Keep secrets (default: keep)",
        ),
        keep_pvc: bool = typer.Option(
            True,
            "--keep-pvc/--delete-pvc",
            help="Keep persistent volume claims (default: keep)",
        ),
        force: ForceOption = False,
    ) -> None:
        """Uninstall Kong Gateway.

        By default, keeps secrets and PVC for easier reinstallation.
        Use --delete-secrets and --delete-pvc to fully clean up.

        Examples:
            ops kong deploy uninstall
            ops kong deploy uninstall --delete-secrets --delete-pvc
            ops kong deploy uninstall --force
        """
        try:
            manager = get_deployment_manager()

            # Confirm
            if not force:
                msg = "Uninstall Kong Gateway?"
                if not keep_postgres:
                    msg += " (including PostgreSQL)"
                if not typer.confirm(msg, default=False):
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            def progress(msg: str) -> None:
                console.print(f"[blue]→[/blue] {msg}")

            manager._progress = progress
            manager.uninstall(
                keep_postgres=keep_postgres,
                keep_secrets=keep_secrets,
                keep_pvc=keep_pvc,
            )

            console.print("\n[green]✓ Kong Gateway uninstalled[/green]")

            if keep_secrets or keep_pvc:
                console.print("\n[dim]Preserved resources:[/dim]")
                if keep_secrets:
                    console.print("  • Secret: kong-postgres-secret")
                if keep_pvc:
                    console.print("  • PVC: kong-postgres-pvc")
                console.print("\n[dim]To fully clean up:[/dim]")
                console.print("  ops kong deploy uninstall --delete-secrets --delete-pvc")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from e

    @deploy_app.command("init")
    def deploy_init(
        force: ForceOption = False,
    ) -> None:
        """Initialize deployment configuration files.

        Creates the secrets file from the example template if it doesn't exist.

        Examples:
            ops kong deploy init
            ops kong deploy init --force
        """
        try:
            manager = get_deployment_manager()
            paths = manager._get_paths()

            secrets_file = paths["secrets"]
            example_file = paths["secrets_example"]

            if secrets_file.exists() and not force:
                console.print(f"[yellow]Secrets file already exists:[/yellow] {secrets_file}")
                if not typer.confirm("Overwrite?", default=False):
                    raise typer.Exit(0)

            if not example_file.exists():
                console.print(f"[red]Error:[/red] Example file not found: {example_file}")
                raise typer.Exit(1)

            # Copy example to secrets
            import shutil

            shutil.copy(example_file, secrets_file)
            console.print(f"[green]✓ Created:[/green] {secrets_file}")
            console.print("\n[yellow]Important:[/yellow] Edit the file to set your password:")
            console.print(f"  nano {secrets_file}")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from e

    # Add deploy sub-app to main kong app
    app.add_typer(deploy_app, name="deploy")
