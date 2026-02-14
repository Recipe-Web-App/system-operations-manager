"""CLI commands for cert-manager resources.

Provides commands for managing Certificates, Issuers, ClusterIssuers,
and troubleshooting ACME challenges via the CertManagerManager service.
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
from system_operations_manager.services.kubernetes.certmanager_manager import (
    LETSENCRYPT_PRODUCTION,
    LETSENCRYPT_STAGING,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes.certmanager_manager import (
        CertManagerManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

CERTIFICATE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("secret_name", "Secret"),
    ("issuer_name", "Issuer"),
    ("dns_names", "DNS Names"),
    ("ready", "Ready"),
    ("renewal_time", "Renewal"),
    ("age", "Age"),
]

ISSUER_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("issuer_type", "Type"),
    ("acme_server", "ACME Server"),
    ("ready", "Ready"),
    ("age", "Age"),
]

CLUSTER_ISSUER_COLUMNS = [
    ("name", "Name"),
    ("issuer_type", "Type"),
    ("acme_server", "ACME Server"),
    ("ready", "Ready"),
    ("age", "Age"),
]

CERTIFICATE_REQUEST_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("issuer_name", "Issuer"),
    ("issuer_kind", "Kind"),
    ("ready", "Ready"),
    ("approved", "Approved"),
    ("age", "Age"),
]

ORDER_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("state", "State"),
    ("dns_names", "DNS Names"),
    ("age", "Age"),
]

CHALLENGE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("challenge_type", "Type"),
    ("dns_name", "Domain"),
    ("state", "State"),
    ("presented", "Presented"),
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


def _parse_issuer_config(config_str: str) -> dict[str, object]:
    """Parse a JSON issuer config string into a dict."""
    try:
        config = json.loads(config_str)
        if not isinstance(config, dict):
            console.print("[red]Error:[/red] Issuer config must be a JSON object")
            raise typer.Exit(1)
        return config
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON issuer config: {e}")
        raise typer.Exit(1) from None


# =============================================================================
# Command Registration
# =============================================================================


def register_certs_commands(
    app: typer.Typer,
    get_manager: Callable[[], CertManagerManager],
) -> None:
    """Register cert-manager CLI commands."""

    certs_app = typer.Typer(
        name="certs",
        help="Manage cert-manager certificates and issuers",
        no_args_is_help=True,
    )
    app.add_typer(certs_app, name="certs")

    # -------------------------------------------------------------------------
    # Certificates (namespaced)
    # -------------------------------------------------------------------------

    cert_app = typer.Typer(
        name="cert",
        help="Manage Certificates",
        no_args_is_help=True,
    )
    certs_app.add_typer(cert_app, name="cert")

    @cert_app.command("list")
    def list_certificates(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Certificates in a namespace.

        Examples:
            ops k8s certs cert list
            ops k8s certs cert list -n production
            ops k8s certs cert list -l app=myapp -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_certificates(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CERTIFICATE_COLUMNS, title="Certificates")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cert_app.command("get")
    def get_certificate(
        name: str = typer.Argument(help="Certificate name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a Certificate.

        Examples:
            ops k8s certs cert get my-tls-cert
            ops k8s certs cert get my-tls-cert -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_certificate(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Certificate: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cert_app.command("create")
    def create_certificate(
        name: str = typer.Argument(help="Certificate name"),
        namespace: NamespaceOption = None,
        secret_name: str = typer.Option(..., "--secret-name", help="Target Secret name"),
        issuer_name: str = typer.Option(..., "--issuer-name", help="Issuer or ClusterIssuer name"),
        dns_name: list[str] = typer.Option(..., "--dns-name", help="DNS name / SAN (repeatable)"),
        issuer_kind: str = typer.Option(
            "Issuer", "--issuer-kind", help="Issuer kind: Issuer or ClusterIssuer"
        ),
        common_name: str | None = typer.Option(None, "--common-name", help="Certificate CN"),
        duration: str | None = typer.Option(
            None, "--duration", help="Validity duration (e.g. 2160h for 90 days)"
        ),
        renew_before: str | None = typer.Option(
            None, "--renew-before", help="Renewal window (e.g. 360h for 15 days)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Certificate.

        Examples:
            ops k8s certs cert create my-tls \\
                --secret-name my-tls-secret \\
                --issuer-name letsencrypt-prod \\
                --dns-name example.com --dns-name www.example.com

            ops k8s certs cert create my-tls \\
                --secret-name my-tls-secret \\
                --issuer-name ca-issuer \\
                --issuer-kind ClusterIssuer \\
                --dns-name internal.example.com \\
                --duration 8760h --renew-before 720h
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            resource = manager.create_certificate(
                name,
                namespace=namespace,
                secret_name=secret_name,
                issuer_name=issuer_name,
                dns_names=dns_name,
                issuer_kind=issuer_kind,
                common_name=common_name,
                duration=duration,
                renew_before=renew_before,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Certificate: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cert_app.command("delete")
    def delete_certificate(
        name: str = typer.Argument(help="Certificate name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Certificate.

        Examples:
            ops k8s certs cert delete my-tls
            ops k8s certs cert delete my-tls -n production --force
        """
        try:
            if not force and not confirm_delete("Certificate", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_certificate(name, namespace=namespace)
            console.print(f"[green]Certificate '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cert_app.command("status")
    def certificate_status(
        name: str = typer.Argument(help="Certificate name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show status of a Certificate.

        Displays conditions, expiry, and renewal information.

        Examples:
            ops k8s certs cert status my-tls
            ops k8s certs cert status my-tls -n production -o json
        """
        try:
            manager = get_manager()
            status = manager.get_certificate_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"Certificate Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cert_app.command("renew")
    def renew_certificate(
        name: str = typer.Argument(help="Certificate name"),
        namespace: NamespaceOption = None,
    ) -> None:
        """Force renewal of a Certificate.

        Triggers cert-manager to re-issue the certificate by adding
        the renewal annotation.

        Examples:
            ops k8s certs cert renew my-tls
            ops k8s certs cert renew my-tls -n production
        """
        try:
            manager = get_manager()
            result = manager.renew_certificate(name, namespace=namespace)
            if result.get("renewed"):
                console.print(f"[green]Certificate '{name}' renewal triggered[/green]")
            else:
                console.print(
                    f"[yellow]Certificate '{name}' renewal may not have been triggered[/yellow]"
                )
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Issuers (namespaced)
    # -------------------------------------------------------------------------

    issuer_app = typer.Typer(
        name="issuer",
        help="Manage Issuers",
        no_args_is_help=True,
    )
    certs_app.add_typer(issuer_app, name="issuer")

    @issuer_app.command("list")
    def list_issuers(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Issuers in a namespace.

        Examples:
            ops k8s certs issuer list
            ops k8s certs issuer list -n cert-manager
            ops k8s certs issuer list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_issuers(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, ISSUER_COLUMNS, title="Issuers")
        except KubernetesError as e:
            handle_k8s_error(e)

    @issuer_app.command("get")
    def get_issuer(
        name: str = typer.Argument(help="Issuer name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an Issuer.

        Examples:
            ops k8s certs issuer get letsencrypt-staging
            ops k8s certs issuer get letsencrypt-staging -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_issuer(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Issuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @issuer_app.command("create")
    def create_issuer(
        name: str = typer.Argument(help="Issuer name"),
        namespace: NamespaceOption = None,
        issuer_type: str = typer.Option(
            ..., "--type", help="Issuer type: acme, ca, selfSigned, vault"
        ),
        config: str = typer.Option(
            ...,
            "--config",
            help='Type-specific config as JSON (e.g. \'{"server":"...","email":"..."}\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an Issuer.

        Examples:
            ops k8s certs issuer create self-signed --type selfSigned --config '{}'

            ops k8s certs issuer create my-ca --type ca \\
                --config '{"secretName":"ca-key-pair"}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            parsed_config = _parse_issuer_config(config)
            resource = manager.create_issuer(
                name,
                namespace=namespace,
                issuer_type=issuer_type,
                config=parsed_config,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Issuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @issuer_app.command("delete")
    def delete_issuer(
        name: str = typer.Argument(help="Issuer name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete an Issuer.

        Examples:
            ops k8s certs issuer delete letsencrypt-staging
            ops k8s certs issuer delete letsencrypt-staging --force
        """
        try:
            if not force and not confirm_delete("Issuer", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_issuer(name, namespace=namespace)
            console.print(f"[green]Issuer '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @issuer_app.command("status")
    def issuer_status(
        name: str = typer.Argument(help="Issuer name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show status of an Issuer.

        Examples:
            ops k8s certs issuer status letsencrypt-prod
            ops k8s certs issuer status letsencrypt-prod -o json
        """
        try:
            manager = get_manager()
            status = manager.get_issuer_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"Issuer Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ClusterIssuers (cluster-scoped)
    # -------------------------------------------------------------------------

    ci_app = typer.Typer(
        name="clusterissuer",
        help="Manage ClusterIssuers",
        no_args_is_help=True,
    )
    certs_app.add_typer(ci_app, name="clusterissuer")

    @ci_app.command("list")
    def list_cluster_issuers(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ClusterIssuers.

        Examples:
            ops k8s certs clusterissuer list
            ops k8s certs clusterissuer list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_issuers(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(
                resources,
                CLUSTER_ISSUER_COLUMNS,
                title="Cluster Issuers",
            )
        except KubernetesError as e:
            handle_k8s_error(e)

    @ci_app.command("get")
    def get_cluster_issuer(
        name: str = typer.Argument(help="ClusterIssuer name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a ClusterIssuer.

        Examples:
            ops k8s certs clusterissuer get letsencrypt-prod
            ops k8s certs clusterissuer get letsencrypt-prod -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_issuer(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterIssuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ci_app.command("create")
    def create_cluster_issuer(
        name: str = typer.Argument(help="ClusterIssuer name"),
        issuer_type: str = typer.Option(
            ..., "--type", help="Issuer type: acme, ca, selfSigned, vault"
        ),
        config: str = typer.Option(
            ...,
            "--config",
            help='Type-specific config as JSON (e.g. \'{"server":"...","email":"..."}\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a ClusterIssuer.

        Examples:
            ops k8s certs clusterissuer create self-signed --type selfSigned --config '{}'

            ops k8s certs clusterissuer create my-ca --type ca \\
                --config '{"secretName":"ca-key-pair"}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            parsed_config = _parse_issuer_config(config)
            resource = manager.create_cluster_issuer(
                name,
                issuer_type=issuer_type,
                config=parsed_config,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ClusterIssuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ci_app.command("delete")
    def delete_cluster_issuer(
        name: str = typer.Argument(help="ClusterIssuer name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a ClusterIssuer.

        Examples:
            ops k8s certs clusterissuer delete letsencrypt-staging
            ops k8s certs clusterissuer delete letsencrypt-staging --force
        """
        try:
            if not force and not confirm_delete("ClusterIssuer", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cluster_issuer(name)
            console.print(f"[green]ClusterIssuer '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ci_app.command("status")
    def cluster_issuer_status(
        name: str = typer.Argument(help="ClusterIssuer name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show status of a ClusterIssuer.

        Examples:
            ops k8s certs clusterissuer status letsencrypt-prod
            ops k8s certs clusterissuer status letsencrypt-prod -o json
        """
        try:
            manager = get_manager()
            status = manager.get_cluster_issuer_status(name)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"ClusterIssuer Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ACME / Let's Encrypt Helpers
    # -------------------------------------------------------------------------

    acme_app = typer.Typer(
        name="acme",
        help="ACME / Let's Encrypt helpers",
        no_args_is_help=True,
    )
    certs_app.add_typer(acme_app, name="acme")

    @acme_app.command("create-issuer")
    def create_acme_issuer(
        name: str = typer.Argument(help="Issuer name"),
        namespace: NamespaceOption = None,
        email: str = typer.Option(..., "--email", help="ACME registration email"),
        server: str = typer.Option(
            LETSENCRYPT_STAGING,
            "--server",
            help="ACME server URL (default: LE staging)",
        ),
        production: bool = typer.Option(
            False, "--production", help="Use Let's Encrypt production server"
        ),
        private_key_secret: str = typer.Option(
            "", "--private-key-secret", help="Secret name for ACME account key"
        ),
        solver_type: str = typer.Option(
            "http01", "--solver-type", help="Solver type: http01 or dns01"
        ),
        ingress_class: str | None = typer.Option(
            None, "--ingress-class", help="Ingress class for HTTP-01 solver"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ACME Issuer (e.g. Let's Encrypt).

        Examples:
            ops k8s certs acme create-issuer letsencrypt-staging \\
                --email admin@example.com

            ops k8s certs acme create-issuer letsencrypt-prod \\
                --email admin@example.com --production \\
                --ingress-class nginx
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            acme_server = LETSENCRYPT_PRODUCTION if production else server
            resource = manager.create_acme_issuer(
                name,
                namespace=namespace,
                email=email,
                server=acme_server,
                private_key_secret=private_key_secret,
                solver_type=solver_type,
                ingress_class=ingress_class,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ACME Issuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @acme_app.command("create-clusterissuer")
    def create_acme_cluster_issuer(
        name: str = typer.Argument(help="ClusterIssuer name"),
        email: str = typer.Option(..., "--email", help="ACME registration email"),
        server: str = typer.Option(
            LETSENCRYPT_STAGING,
            "--server",
            help="ACME server URL (default: LE staging)",
        ),
        production: bool = typer.Option(
            False, "--production", help="Use Let's Encrypt production server"
        ),
        private_key_secret: str = typer.Option(
            "", "--private-key-secret", help="Secret name for ACME account key"
        ),
        solver_type: str = typer.Option(
            "http01", "--solver-type", help="Solver type: http01 or dns01"
        ),
        ingress_class: str | None = typer.Option(
            None, "--ingress-class", help="Ingress class for HTTP-01 solver"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ACME ClusterIssuer (e.g. Let's Encrypt).

        Examples:
            ops k8s certs acme create-clusterissuer letsencrypt-staging \\
                --email admin@example.com

            ops k8s certs acme create-clusterissuer letsencrypt-prod \\
                --email admin@example.com --production \\
                --solver-type http01 --ingress-class nginx
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            acme_server = LETSENCRYPT_PRODUCTION if production else server
            resource = manager.create_acme_cluster_issuer(
                name,
                email=email,
                server=acme_server,
                private_key_secret=private_key_secret,
                solver_type=solver_type,
                ingress_class=ingress_class,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ACME ClusterIssuer: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # CertificateRequests (namespaced, read-only)
    # -------------------------------------------------------------------------

    req_app = typer.Typer(
        name="request",
        help="View CertificateRequests",
        no_args_is_help=True,
    )
    certs_app.add_typer(req_app, name="request")

    @req_app.command("list")
    def list_certificate_requests(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List CertificateRequests in a namespace.

        Examples:
            ops k8s certs request list
            ops k8s certs request list -n production
            ops k8s certs request list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_certificate_requests(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(
                resources, CERTIFICATE_REQUEST_COLUMNS, title="Certificate Requests"
            )
        except KubernetesError as e:
            handle_k8s_error(e)

    @req_app.command("get")
    def get_certificate_request(
        name: str = typer.Argument(help="CertificateRequest name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a CertificateRequest.

        Examples:
            ops k8s certs request get my-cert-request
            ops k8s certs request get my-cert-request -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_certificate_request(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"CertificateRequest: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Challenges (namespaced, read-only + troubleshoot)
    # -------------------------------------------------------------------------

    challenge_app = typer.Typer(
        name="challenge",
        help="Troubleshoot ACME challenges",
        no_args_is_help=True,
    )
    certs_app.add_typer(challenge_app, name="challenge")

    @challenge_app.command("list")
    def list_challenges(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ACME Challenges in a namespace.

        Examples:
            ops k8s certs challenge list
            ops k8s certs challenge list -n cert-manager
            ops k8s certs challenge list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_challenges(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CHALLENGE_COLUMNS, title="ACME Challenges")
        except KubernetesError as e:
            handle_k8s_error(e)

    @challenge_app.command("get")
    def get_challenge(
        name: str = typer.Argument(help="Challenge name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an ACME Challenge.

        Examples:
            ops k8s certs challenge get my-challenge
            ops k8s certs challenge get my-challenge -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_challenge(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Challenge: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @challenge_app.command("troubleshoot")
    def troubleshoot_challenge(
        name: str = typer.Argument(help="Challenge name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Troubleshoot an ACME Challenge.

        Shows detailed information about the challenge including solver
        configuration, status, failure reasons, and related resources.

        Examples:
            ops k8s certs challenge troubleshoot my-challenge
            ops k8s certs challenge troubleshoot my-challenge -n cert-manager -o json
        """
        try:
            manager = get_manager()
            info = manager.troubleshoot_challenge(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(info, title=f"Challenge Troubleshooting: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)
