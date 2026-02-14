"""Kubernetes plugin implementation.

This plugin provides integration with Kubernetes clusters for:
- Cluster Management: Context switching, status, node info
- Workloads: Pods, Deployments, StatefulSets, DaemonSets, ReplicaSets
- Networking: Services, Ingresses, NetworkPolicies
- Configuration: ConfigMaps, Secrets
- Storage: PVs, PVCs, StorageClasses
- RBAC: ServiceAccounts, Roles, RoleBindings
- Jobs: Jobs, CronJobs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
import typer
from rich.console import Console

from system_operations_manager.cli.output import Table
from system_operations_manager.core.plugins.base import Plugin, hookimpl
from system_operations_manager.integrations.kubernetes.client import KubernetesClient
from system_operations_manager.integrations.kubernetes.config import KubernetesPluginConfig
from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
    KubernetesError,
)
from system_operations_manager.plugins.kubernetes.commands.base import (
    OutputOption,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()
console = Console()


class KubernetesPlugin(Plugin):
    """Kubernetes cluster management plugin.

    Provides CLI commands and API access to Kubernetes clusters via
    the official kubernetes Python client.
    """

    name = "kubernetes"
    version = "0.1.0"
    description = "Kubernetes cluster management and resource operations"

    def __init__(self) -> None:
        """Initialize Kubernetes plugin."""
        super().__init__()
        self._client: KubernetesClient | None = None
        self._plugin_config: KubernetesPluginConfig | None = None

    def on_initialize(self) -> None:
        """Initialize Kubernetes plugin with configuration.

        Parses the plugin configuration and creates the Kubernetes client.
        Environment variables can override configuration file values.
        """
        try:
            config_dict = self._config or {}
            self._plugin_config = KubernetesPluginConfig.from_env(config_dict)
            self._client = KubernetesClient(self._plugin_config)

            logger.info(
                "Kubernetes plugin initialized",
                context=self._client.get_current_context(),
                namespace=self._plugin_config.get_active_namespace(),
            )
        except KubernetesConnectionError:
            # Don't fail plugin init on connection errors - commands will fail gracefully
            logger.warning(
                "Kubernetes plugin initialized without cluster connection",
            )
        except Exception as e:
            logger.error("Failed to initialize Kubernetes plugin", error=str(e))
            raise

    @hookimpl
    def register_commands(self, app: typer.Typer) -> None:
        """Register Kubernetes commands with the CLI."""
        k8s_app = typer.Typer(
            name="k8s",
            help="Kubernetes cluster management commands",
            no_args_is_help=True,
        )

        self._register_status_commands(k8s_app)
        self._register_entity_commands(k8s_app)

        app.add_typer(k8s_app, name="k8s")
        logger.debug("Kubernetes commands registered")

    def _register_status_commands(self, app: typer.Typer) -> None:
        """Register status and cluster info commands."""
        client = self._client
        plugin_config = self._plugin_config

        @app.command()
        def status(
            output: OutputOption = OutputFormat.TABLE,
        ) -> None:
            """Show Kubernetes cluster status and connectivity.

            Examples:
                ops k8s status
                ops k8s status --output json
            """
            if not client:
                console.print("[red]Error:[/red] Kubernetes plugin not configured")
                raise typer.Exit(1)

            try:
                connected = client.check_connection()
                context = client.get_current_context()
                namespace = plugin_config.get_active_namespace() if plugin_config else "default"

                data: dict[str, str | int] = {
                    "context": context,
                    "namespace": namespace,
                    "connected": "yes" if connected else "no",
                }

                if connected:
                    try:
                        version = client.get_cluster_version()
                        data["cluster_version"] = version
                    except KubernetesError:
                        data["cluster_version"] = "unknown"

                    try:
                        nodes = client.core_v1.list_node()
                        data["nodes"] = len(nodes.items) if nodes.items else 0
                    except Exception:
                        data["nodes"] = "unknown"

                if output == OutputFormat.TABLE:
                    table = Table(title="Kubernetes Cluster Status")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")

                    table.add_row("Context", str(data["context"]))
                    table.add_row("Namespace", str(data["namespace"]))
                    table.add_row(
                        "Connected",
                        "[green]Yes[/green]" if connected else "[red]No[/red]",
                    )
                    if connected:
                        table.add_row("Cluster Version", str(data.get("cluster_version", "-")))
                        table.add_row("Nodes", str(data.get("nodes", "-")))

                    console.print(table)
                else:
                    formatter = get_formatter(output, console)
                    formatter.format_dict(data, title="Kubernetes Cluster Status")

            except KubernetesError as e:
                handle_k8s_error(e)

        @app.command()
        def contexts(
            output: OutputOption = OutputFormat.TABLE,
        ) -> None:
            """List available Kubernetes contexts.

            Examples:
                ops k8s contexts
                ops k8s contexts --output json
            """
            if not client:
                console.print("[red]Error:[/red] Kubernetes plugin not configured")
                raise typer.Exit(1)

            try:
                ctx_list = client.list_contexts()

                if output == OutputFormat.TABLE:
                    table = Table(title="Kubernetes Contexts")
                    table.add_column("", style="green", width=2)
                    table.add_column("Name", style="cyan")
                    table.add_column("Cluster", style="white")
                    table.add_column("Namespace", style="white")

                    for ctx in ctx_list:
                        marker = "*" if ctx.get("active") else ""
                        table.add_row(
                            marker,
                            ctx.get("name", ""),
                            ctx.get("cluster", ""),
                            ctx.get("namespace", "default"),
                        )
                    console.print(table)
                else:
                    formatter = get_formatter(output, console)
                    formatter.format_dict(
                        {"contexts": ctx_list},
                        title="Kubernetes Contexts",
                    )

            except KubernetesError as e:
                handle_k8s_error(e)

        @app.command(name="use-context")
        def use_context(
            context_name: str = typer.Argument(help="Context name to switch to"),
        ) -> None:
            """Switch to a different Kubernetes context.

            Examples:
                ops k8s use-context production
                ops k8s use-context minikube
            """
            if not client:
                console.print("[red]Error:[/red] Kubernetes plugin not configured")
                raise typer.Exit(1)

            try:
                client.switch_context(context_name)
                console.print(f"[green]Switched to context '{context_name}'[/green]")
            except KubernetesError as e:
                handle_k8s_error(e)

    def _register_entity_commands(self, k8s_app: typer.Typer) -> None:
        """Register all entity CRUD commands via command modules."""
        from system_operations_manager.plugins.kubernetes.commands import (
            register_argocd_commands,
            register_certs_commands,
            register_cluster_commands,
            register_config_commands,
            register_external_secrets_commands,
            register_flux_commands,
            register_helm_commands,
            register_job_commands,
            register_kustomize_commands,
            register_manifest_commands,
            register_namespace_commands,
            register_networking_commands,
            register_optimization_commands,
            register_policy_commands,
            register_rbac_commands,
            register_rollout_commands,
            register_storage_commands,
            register_workflow_commands,
            register_workload_commands,
        )
        from system_operations_manager.services.kubernetes import (
            ArgoCDManager,
            CertManagerManager,
            ConfigurationManager,
            ExternalSecretsManager,
            FluxManager,
            HelmManager,
            JobManager,
            KustomizeManager,
            KyvernoManager,
            ManifestManager,
            NamespaceClusterManager,
            NetworkingManager,
            OptimizationManager,
            RBACManager,
            RolloutsManager,
            StorageManager,
            WorkflowsManager,
            WorkloadManager,
        )

        def get_workload_manager() -> WorkloadManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return WorkloadManager(self._client)

        def get_networking_manager() -> NetworkingManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return NetworkingManager(self._client)

        def get_config_manager() -> ConfigurationManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return ConfigurationManager(self._client)

        def get_namespace_cluster_manager() -> NamespaceClusterManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return NamespaceClusterManager(self._client)

        def get_job_manager() -> JobManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return JobManager(self._client)

        def get_storage_manager() -> StorageManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return StorageManager(self._client)

        def get_rbac_manager() -> RBACManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return RBACManager(self._client)

        def get_manifest_manager() -> ManifestManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return ManifestManager(self._client)

        def get_helm_manager() -> HelmManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return HelmManager(self._client)

        def get_kustomize_manager() -> KustomizeManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return KustomizeManager(self._client)

        def get_kyverno_manager() -> KyvernoManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return KyvernoManager(self._client)

        def get_external_secrets_manager() -> ExternalSecretsManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return ExternalSecretsManager(self._client)

        def get_flux_manager() -> FluxManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return FluxManager(self._client)

        def get_optimization_manager() -> OptimizationManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return OptimizationManager(self._client)

        def get_argocd_manager() -> ArgoCDManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return ArgoCDManager(self._client)

        def get_rollouts_manager() -> RolloutsManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return RolloutsManager(self._client)

        def get_workflows_manager() -> WorkflowsManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return WorkflowsManager(self._client)

        def get_certmanager_manager() -> CertManagerManager:
            if not self._client:
                raise RuntimeError("Kubernetes client not initialized")
            return CertManagerManager(self._client)

        register_workload_commands(k8s_app, get_workload_manager)
        register_networking_commands(k8s_app, get_networking_manager)
        register_config_commands(k8s_app, get_config_manager)
        register_cluster_commands(k8s_app, get_namespace_cluster_manager)
        register_namespace_commands(k8s_app, get_namespace_cluster_manager)
        register_job_commands(k8s_app, get_job_manager)
        register_storage_commands(k8s_app, get_storage_manager)
        register_rbac_commands(k8s_app, get_rbac_manager)
        register_helm_commands(k8s_app, get_helm_manager)
        register_kustomize_commands(k8s_app, get_kustomize_manager)
        register_manifest_commands(k8s_app, get_manifest_manager)
        register_policy_commands(k8s_app, get_kyverno_manager)
        register_external_secrets_commands(k8s_app, get_external_secrets_manager)
        register_flux_commands(k8s_app, get_flux_manager)
        register_optimization_commands(k8s_app, get_optimization_manager)
        register_argocd_commands(k8s_app, get_argocd_manager)
        register_rollout_commands(k8s_app, get_rollouts_manager)
        register_workflow_commands(k8s_app, get_workflows_manager)
        register_certs_commands(k8s_app, get_certmanager_manager)

    @hookimpl
    def cleanup(self) -> None:
        """Cleanup Kubernetes plugin resources."""
        if self._client:
            self._client.close()
            self._client = None
        super().cleanup()
        logger.debug("Kubernetes plugin cleaned up")

    @property
    def client(self) -> KubernetesClient | None:
        """Get the Kubernetes client."""
        return self._client

    @property
    def plugin_config(self) -> KubernetesPluginConfig | None:
        """Get the Kubernetes plugin configuration."""
        return self._plugin_config
