"""CLI commands for Kubernetes resource optimization.

Provides commands for analyzing resource usage, generating right-sizing
recommendations, detecting orphan pods and stale jobs, and summarizing
optimization opportunities.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    AllNamespacesOption,
    LabelSelectorOption,
    NamespaceOption,
    OutputOption,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kubernetes.optimization_manager import (
    DEFAULT_STALE_JOB_HOURS,
    UNDERUTILIZED_CPU_THRESHOLD,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes.optimization_manager import (
        OptimizationManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

ANALYSIS_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("workload_type", "Kind"),
    ("replicas", "Replicas"),
    ("cpu_utilization_pct", "CPU %"),
    ("memory_utilization_pct", "Mem %"),
    ("status", "Status"),
    ("age", "Age"),
]

ORPHAN_POD_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("phase", "Phase"),
    ("cpu_usage", "CPU"),
    ("memory_usage", "Memory"),
    ("node_name", "Node"),
    ("age", "Age"),
]

STALE_JOB_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("status", "Status"),
    ("age_hours", "Stale (hrs)"),
    ("age", "Age"),
]


# =============================================================================
# Custom Option Types
# =============================================================================

ThresholdOption = Annotated[
    float,
    typer.Option(
        "--threshold",
        "-t",
        help="Utilization threshold (0.0-1.0) below which workloads are flagged",
    ),
]

StaleHoursOption = Annotated[
    float,
    typer.Option(
        "--stale-hours",
        help="Hours after completion before a job is considered stale",
    ),
]

WorkloadTypeOption = Annotated[
    str,
    typer.Option(
        "--type",
        help="Workload type: Deployment, StatefulSet, or DaemonSet",
    ),
]


# =============================================================================
# Command Registration
# =============================================================================


def register_optimization_commands(
    app: typer.Typer,
    get_manager: Callable[[], OptimizationManager],
) -> None:
    """Register optimization commands with the Kubernetes CLI app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns an OptimizationManager instance.
    """
    optimize_app = typer.Typer(
        name="optimize",
        help="Resource optimization analysis and recommendations",
        no_args_is_help=True,
    )

    # -------------------------------------------------------------------------
    # analyze
    # -------------------------------------------------------------------------

    @optimize_app.command("analyze")
    def analyze(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        label_selector: LabelSelectorOption = None,
        threshold: ThresholdOption = UNDERUTILIZED_CPU_THRESHOLD,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Analyze resource usage vs requests for workloads.

        Compares actual CPU/memory consumption (from metrics-server)
        against resource requests for Deployments, StatefulSets, and DaemonSets.

        Examples:
            ops k8s optimize analyze
            ops k8s optimize analyze -A
            ops k8s optimize analyze -n production --threshold 0.3
            ops k8s optimize analyze -l app=nginx -o json
        """
        try:
            manager = get_manager()
            analyses = manager.analyze_workloads(
                namespace=namespace,
                all_namespaces=all_namespaces,
                label_selector=label_selector,
                threshold=threshold,
            )

            if not analyses:
                console.print("[dim]No workloads found to analyze.[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(analyses, ANALYSIS_COLUMNS, title="Resource Analysis")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # recommend
    # -------------------------------------------------------------------------

    @optimize_app.command("recommend")
    def recommend(
        name: Annotated[str, typer.Argument(help="Workload name")],
        namespace: NamespaceOption = None,
        workload_type: WorkloadTypeOption = "Deployment",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get right-sizing recommendations for a workload.

        Suggests adjusted resource requests and limits based on actual
        usage from metrics-server, with a safety buffer.

        Examples:
            ops k8s optimize recommend my-deployment
            ops k8s optimize recommend my-sts -n production --type StatefulSet
            ops k8s optimize recommend my-deploy -o yaml
        """
        try:
            manager = get_manager()
            rec = manager.recommend(
                name=name,
                namespace=namespace,
                workload_type=workload_type,
            )

            formatter = get_formatter(output, console)
            formatter.format_resource(rec, title=f"Recommendation: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # unused
    # -------------------------------------------------------------------------

    @optimize_app.command("unused")
    def unused(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        stale_hours: StaleHoursOption = DEFAULT_STALE_JOB_HOURS,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Find orphan pods, stale jobs, and idle workloads.

        Detects:
        - Bare pods with no owner controller
        - Completed/failed jobs lingering past a configurable age
        - Controller-managed workloads with negligible resource usage

        Examples:
            ops k8s optimize unused
            ops k8s optimize unused -A
            ops k8s optimize unused -n staging --stale-hours 48
            ops k8s optimize unused -o json
        """
        try:
            manager = get_manager()
            result = manager.find_unused(
                namespace=namespace,
                all_namespaces=all_namespaces,
                stale_job_hours=stale_hours,
            )

            formatter = get_formatter(output, console)

            orphan_pods = result["orphan_pods"]
            stale_jobs = result["stale_jobs"]
            idle_workloads = result["idle_workloads"]

            if not orphan_pods and not stale_jobs and not idle_workloads:
                console.print("[green]No unused resources found. Cluster is clean![/green]")
                return

            if orphan_pods:
                formatter.format_list(
                    orphan_pods, ORPHAN_POD_COLUMNS, title="Orphan Pods (no owner controller)"
                )

            if stale_jobs:
                formatter.format_list(stale_jobs, STALE_JOB_COLUMNS, title="Stale Jobs")

            if idle_workloads:
                formatter.format_list(idle_workloads, ANALYSIS_COLUMNS, title="Idle Workloads")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # summary
    # -------------------------------------------------------------------------

    @optimize_app.command("summary")
    def summary(
        namespace: NamespaceOption = None,
        all_namespaces: AllNamespacesOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show a high-level summary of optimization opportunities.

        Rolls up resource analysis, orphan pods, and stale jobs
        into a single overview.

        Examples:
            ops k8s optimize summary
            ops k8s optimize summary -A
            ops k8s optimize summary -n production -o json
        """
        try:
            manager = get_manager()
            s = manager.get_summary(
                namespace=namespace,
                all_namespaces=all_namespaces,
            )

            formatter = get_formatter(output, console)
            data = {
                "workloads_analyzed": s.total_workloads_analyzed,
                "overprovisioned": s.overprovisioned_count,
                "underutilized": s.underutilized_count,
                "healthy": s.ok_count,
                "orphan_pods": s.orphan_pod_count,
                "stale_jobs": s.stale_job_count,
                "cpu_waste": s.cpu_waste_display,
                "memory_waste": s.memory_waste_display,
            }
            formatter.format_dict(data, title="Optimization Summary")
        except KubernetesError as e:
            handle_k8s_error(e)

    app.add_typer(optimize_app, name="optimize")
