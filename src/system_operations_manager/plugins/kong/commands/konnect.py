"""Kong Konnect CLI commands.

Commands for configuring and managing Kong Konnect integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from system_operations_manager.cli.output import Table

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect import KonnectClient
    from system_operations_manager.integrations.konnect.models import ControlPlane

console = Console()


def register_konnect_commands(
    app: typer.Typer,
) -> None:
    """Register Konnect commands with the CLI.

    Args:
        app: Parent Typer app to register commands under.
    """
    konnect_app = typer.Typer(
        name="konnect",
        help="Kong Konnect integration commands",
        no_args_is_help=True,
    )

    @konnect_app.command("login")
    def login(
        token: Annotated[
            str | None,
            typer.Option(
                "--token",
                "-t",
                help="Konnect Personal Access Token (will prompt if not provided)",
            ),
        ] = None,
        region: Annotated[
            str,
            typer.Option(
                "--region",
                "-r",
                help="Konnect region (us, eu, au)",
            ),
        ] = "us",
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                "-f",
                help="Overwrite existing configuration",
            ),
        ] = False,
    ) -> None:
        """Configure Konnect credentials.

        Stores your Konnect Personal Access Token for use with other commands.
        The token is stored in ~/.config/ops/konnect.yaml with restricted permissions.

        Get your token from: https://cloud.konghq.com/global/account/tokens
        """
        from pydantic import SecretStr

        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
            KonnectRegion,
        )
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectAuthError,
        )

        # Check if already configured
        if (
            KonnectConfig.exists()
            and not force
            and not Confirm.ask(
                "[yellow]Konnect is already configured. Overwrite?[/yellow]",
                default=False,
            )
        ):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

        # Get token interactively if not provided
        if not token:
            console.print(
                "\n[bold]Kong Konnect Login[/bold]\n"
                "Get your Personal Access Token from:\n"
                "[link=https://cloud.konghq.com/global/account/tokens]"
                "https://cloud.konghq.com/global/account/tokens[/link]\n"
            )
            token = Prompt.ask("Enter your Konnect API token", password=True)

        if not token:
            console.print("[red]Error: Token is required[/red]")
            raise typer.Exit(1) from None

        # Validate region
        try:
            konnect_region = KonnectRegion(region.lower())
        except ValueError:
            console.print(f"[red]Error: Invalid region '{region}'. Must be: us, eu, au[/red]")
            raise typer.Exit(1) from None

        # Validate token by making a test request
        console.print(f"[dim]Validating token with {konnect_region.value} region...[/dim]")
        config = KonnectConfig(
            token=SecretStr(token),
            region=konnect_region,
        )

        try:
            with KonnectClient(config) as client:
                client.validate_token()
                control_planes = client.list_control_planes()
        except KonnectAuthError as e:
            console.print(f"[red]Authentication failed: {e.message}[/red]")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            raise typer.Exit(1) from None

        # Save configuration
        config.save()
        console.print(
            f"[green]✓ Konnect credentials saved to {KonnectConfig.get_config_path()}[/green]"
        )

        # Show available control planes
        if control_planes:
            console.print(f"\n[bold]Available Control Planes ({len(control_planes)}):[/bold]")
            table = Table(show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("ID", style="dim")
            table.add_column("Type")

            for cp in control_planes:
                table.add_row(
                    cp.name,
                    cp.id,
                    cp.cluster_type or "-",
                )
            console.print(table)
            console.print(
                "\n[dim]Run 'ops kong konnect setup --control-plane <name>' "
                "to configure data plane connection[/dim]"
            )
        else:
            console.print(
                "\n[yellow]No control planes found. Create one in Konnect first.[/yellow]"
            )

    @konnect_app.command("setup")
    def setup(
        control_plane: Annotated[
            str | None,
            typer.Option(
                "--control-plane",
                "-c",
                help="Control plane name or ID",
            ),
        ] = None,
        namespace: Annotated[
            str,
            typer.Option(
                "--namespace",
                "-n",
                help="Kubernetes namespace for the secret",
            ),
        ] = "kong",
        secret_name: Annotated[
            str,
            typer.Option(
                "--secret-name",
                help="Name for the TLS secret",
            ),
        ] = "konnect-client-tls",
        update_values: Annotated[
            bool,
            typer.Option(
                "--update-values",
                help="Update kong-values.yaml with Konnect endpoints",
            ),
        ] = False,
        values_file: Annotated[
            str | None,
            typer.Option(
                "--values-file",
                help="Path to kong-values.yaml (for --update-values)",
            ),
        ] = None,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                "-f",
                help="Overwrite existing secret",
            ),
        ] = False,
    ) -> None:
        """Set up Konnect data plane connection.

        Creates the TLS secret needed for Kong data plane to connect to Konnect.
        Optionally updates your kong-values.yaml with the correct endpoints.

        Prerequisites:
        - Run 'ops kong konnect login' first
        - Have a control plane created in Konnect
        """
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectConfigError,
        )

        # Load config
        try:
            config = KonnectConfig.load()
        except KonnectConfigError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")
            raise typer.Exit(1) from None

        with KonnectClient(config) as client:
            # Determine control plane name to use
            cp_name_to_find: str | None = control_plane
            if not cp_name_to_find and config.default_control_plane:
                cp_name_to_find = config.default_control_plane
                console.print(f"[dim]Using default control plane: {cp_name_to_find}[/dim]")

            # Get control plane - either by lookup or interactive selection
            cp = _get_or_select_control_plane(client, cp_name_to_find)

            console.print(f"\n[bold]Control Plane:[/bold] {cp.name}")
            console.print(f"[dim]ID: {cp.id}[/dim]")

            # Check for existing certificates
            existing_certs = client.list_dp_certificates(cp.id)

            if existing_certs:
                console.print(
                    f"\n[yellow]Found {len(existing_certs)} existing certificate(s)[/yellow]"
                )
                if not force:
                    create_new = Confirm.ask(
                        "Create a new certificate?",
                        default=False,
                    )
                    if not create_new:
                        console.print(
                            "[yellow]Note: Using existing certificate. "
                            "Private key is not available for existing certs.[/yellow]"
                        )
                        console.print("[yellow]Use --force to create a new certificate.[/yellow]")
                        raise typer.Exit(1) from None

            # Create new certificate
            console.print("[dim]Generating data plane certificate...[/dim]")
            cert = client.create_dp_certificate(cp.id)

            if not cert.key:
                console.print("[red]Error: Certificate created but no private key returned[/red]")
                raise typer.Exit(1) from None

            console.print(f"[green]✓ Certificate created: {cert.id}[/green]")

        # Create Kubernetes secret
        console.print(
            f"\n[dim]Creating Kubernetes secret '{secret_name}' in namespace '{namespace}'...[/dim]"
        )

        try:
            _create_tls_secret(
                namespace=namespace,
                secret_name=secret_name,
                cert_pem=cert.cert,
                key_pem=cert.key,
                force=force,
            )
            console.print(
                f"[green]✓ Secret '{secret_name}' created in namespace '{namespace}'[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to create secret: {e}[/red]")
            raise typer.Exit(1) from None

        # Show endpoints info
        console.print("\n[bold]Konnect Endpoints:[/bold]")
        if cp.control_plane_endpoint:
            console.print(f"  Control Plane: {cp.control_plane_endpoint}")
        if cp.telemetry_endpoint:
            console.print(f"  Telemetry: {cp.telemetry_endpoint}")

        # Update values file if requested
        if update_values:
            if not values_file:
                values_file = "k8s/gateway/kong-values.yaml"
            console.print(f"\n[dim]Updating {values_file}...[/dim]")

            if not cp.telemetry_endpoint or not cp.control_plane_endpoint:
                console.print(
                    "[yellow]Warning: Control plane missing endpoint information. "
                    "Cannot update values file.[/yellow]"
                )
            else:
                try:
                    _update_values_file(
                        values_path=values_file,
                        telemetry_endpoint=cp.telemetry_endpoint,
                        control_plane_endpoint=cp.control_plane_endpoint,
                    )
                    console.print(f"[green]✓ Updated {values_file}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to update values file: {e}[/red]")
                    raise typer.Exit(1) from None

        console.print("\n[green]✓ Konnect setup complete![/green]")
        console.print(
            "\n[dim]Next steps:\n"
            "  1. Ensure your kong-values.yaml has the correct Konnect endpoints\n"
            "  2. Run 'ops kong deploy install' or 'helm upgrade' to apply[/dim]"
        )

    @konnect_app.command("status")
    def status() -> None:
        """Show Konnect configuration status."""
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectConfigError,
        )

        # Check if configured
        if not KonnectConfig.exists():
            console.print("[yellow]Konnect is not configured[/yellow]")
            console.print("[dim]Run 'ops kong konnect login' to configure[/dim]")
            raise typer.Exit(0)

        # Load and display config
        try:
            config = KonnectConfig.load()
        except KonnectConfigError as e:
            console.print(f"[red]Error loading config: {e.message}[/red]")
            raise typer.Exit(1) from None

        console.print("[bold]Konnect Configuration[/bold]")
        console.print(f"  Region: {config.region.value}")
        console.print(f"  API URL: {config.api_url}")
        console.print(f"  Config file: {KonnectConfig.get_config_path()}")
        if config.default_control_plane:
            console.print(f"  Default CP: {config.default_control_plane}")

        # Validate connection
        console.print("\n[dim]Validating connection...[/dim]")
        try:
            with KonnectClient(config) as client:
                client.validate_token()
                cps = client.list_control_planes()
            console.print("[green]✓ Connection OK[/green]")
            console.print(f"[dim]Found {len(cps)} control plane(s)[/dim]")
        except Exception as e:
            console.print(f"[red]✗ Connection failed: {e}[/red]")
            raise typer.Exit(1) from None

    @konnect_app.command("list-control-planes")
    def list_control_planes() -> None:
        """List available control planes."""
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectConfigError,
        )

        try:
            config = KonnectConfig.load()
        except KonnectConfigError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1) from None

        with KonnectClient(config) as client:
            cps = client.list_control_planes()

        if not cps:
            console.print("[yellow]No control planes found[/yellow]")
            return

        table = Table(title=f"Control Planes ({len(cps)})")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Type")
        table.add_column("Endpoint", style="dim")

        for cp in cps:
            table.add_row(
                cp.name,
                cp.id,
                cp.cluster_type or "-",
                cp.control_plane_endpoint or "-",
            )

        console.print(table)

    app.add_typer(konnect_app)


def _get_or_select_control_plane(
    client: KonnectClient,
    name_or_id: str | None,
) -> ControlPlane:
    """Get a control plane by name/ID or prompt for interactive selection.

    Args:
        client: Konnect API client.
        name_or_id: Control plane name or ID, or None for interactive selection.

    Returns:
        Selected control plane.

    Raises:
        typer.Exit: If control plane not found or no control planes available.
    """
    from rich.prompt import IntPrompt

    from system_operations_manager.integrations.konnect.exceptions import (
        KonnectNotFoundError,
    )

    if name_or_id:
        # Find by name/ID
        try:
            return client.find_control_plane(name_or_id)
        except KonnectNotFoundError:
            console.print(f"[red]Control plane '{name_or_id}' not found[/red]")
            raise typer.Exit(1) from None

    # Interactive selection
    cps = client.list_control_planes()
    if not cps:
        console.print("[red]No control planes found. Create one in Konnect first.[/red]")
        raise typer.Exit(1) from None

    console.print("\n[bold]Select a Control Plane:[/bold]")
    for i, listed_cp in enumerate(cps, 1):
        console.print(f"  {i}. {listed_cp.name} [dim]({listed_cp.id})[/dim]")

    selection = IntPrompt.ask(
        "\nEnter number",
        default=1,
        choices=[str(i) for i in range(1, len(cps) + 1)],
    )
    return cps[selection - 1]


def _create_tls_secret(
    namespace: str,
    secret_name: str,
    cert_pem: str,
    key_pem: str,
    force: bool = False,
) -> None:
    """Create a Kubernetes TLS secret.

    Args:
        namespace: Kubernetes namespace.
        secret_name: Name for the secret.
        cert_pem: Certificate PEM content.
        key_pem: Private key PEM content.
        force: Overwrite existing secret.
    """
    try:
        from system_operations_manager.services.kubernetes import KubernetesService
    except ImportError as e:
        raise RuntimeError(
            "kubernetes package not installed. Install with: pip install kubernetes"
        ) from e

    k8s = KubernetesService()

    # Ensure namespace exists
    k8s.ensure_namespace(namespace)

    # Create TLS secret
    k8s.create_tls_secret(
        namespace=namespace,
        name=secret_name,
        cert_pem=cert_pem,
        key_pem=key_pem,
        force=force,
    )


def _update_values_file(
    values_path: str, telemetry_endpoint: str, control_plane_endpoint: str
) -> None:
    """Update Helm values file with Konnect endpoints.

    Args:
        values_path: Path to the Helm values file.
        telemetry_endpoint: Konnect telemetry endpoint (e.g., "host.konghq.com:443").
        control_plane_endpoint: Konnect control plane endpoint.
    """
    from pathlib import Path

    import yaml

    path = Path(values_path)

    # Load existing values
    if path.exists():
        with path.open("r") as f:
            values = yaml.safe_load(f) or {}
    else:
        values = {}

    # Ensure nested structure exists
    if "gateway" not in values:
        values["gateway"] = {}
    if "env" not in values["gateway"]:
        values["gateway"]["env"] = {}

    # Extract hostname from endpoint (e.g., "host.konghq.com:443" -> "host.konghq.com")
    telemetry_host = (
        telemetry_endpoint.split(":")[0] if ":" in telemetry_endpoint else telemetry_endpoint
    )
    control_plane_host = (
        control_plane_endpoint.split(":")[0]
        if ":" in control_plane_endpoint
        else control_plane_endpoint
    )

    # Update values with Konnect endpoints
    values["gateway"]["env"]["cluster_telemetry_endpoint"] = telemetry_endpoint
    values["gateway"]["env"]["cluster_telemetry_server_name"] = telemetry_host
    values["gateway"]["env"]["cluster_control_plane"] = control_plane_endpoint
    values["gateway"]["env"]["cluster_server_name"] = control_plane_host

    # Write back
    with path.open("w") as f:
        yaml.dump(values, f, default_flow_style=False, sort_keys=False)
