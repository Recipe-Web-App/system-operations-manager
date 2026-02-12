"""CLI commands for Kyverno policy resources.

Provides commands for managing Kyverno ClusterPolicies, Policies,
PolicyReports, ClusterPolicyReports, and admission controller status
via the KyvernoManager service.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import typer
import yaml

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
    from system_operations_manager.services.kubernetes import KyvernoManager

# =============================================================================
# Column Definitions
# =============================================================================

CLUSTER_POLICY_COLUMNS = [
    ("name", "Name"),
    ("validation_failure_action", "Action"),
    ("background", "Background"),
    ("rules_count", "Rules"),
    ("ready", "Ready"),
    ("age", "Age"),
]

POLICY_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("validation_failure_action", "Action"),
    ("background", "Background"),
    ("rules_count", "Rules"),
    ("ready", "Ready"),
    ("age", "Age"),
]

CLUSTER_POLICY_REPORT_COLUMNS = [
    ("name", "Name"),
    ("pass_count", "Pass"),
    ("fail_count", "Fail"),
    ("warn_count", "Warn"),
    ("error_count", "Error"),
    ("skip_count", "Skip"),
]

POLICY_REPORT_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("pass_count", "Pass"),
    ("fail_count", "Fail"),
    ("warn_count", "Warn"),
    ("error_count", "Error"),
    ("skip_count", "Skip"),
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


def _parse_rules(rule_strings: list[str] | None) -> list[dict[str, object]] | None:
    """Parse JSON rule strings into a list of dicts."""
    if not rule_strings:
        return None
    rules: list[dict[str, object]] = []
    for rule_str in rule_strings:
        try:
            rules.append(json.loads(rule_str))
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON rule: {e}")
            raise typer.Exit(1) from None
    return rules


# =============================================================================
# Command Registration
# =============================================================================


def register_policy_commands(
    app: typer.Typer,
    get_manager: Callable[[], KyvernoManager],
) -> None:
    """Register Kyverno policy CLI commands."""

    # -------------------------------------------------------------------------
    # ClusterPolicies
    # -------------------------------------------------------------------------

    cpol_app = typer.Typer(
        name="cluster-policies",
        help="Manage Kyverno cluster policies",
        no_args_is_help=True,
    )
    app.add_typer(cpol_app, name="cluster-policies")

    @cpol_app.command("list")
    def list_cluster_policies(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Kyverno ClusterPolicies.

        Examples:
            ops k8s cluster-policies list
            ops k8s cluster-policies list -l app=security
            ops k8s cluster-policies list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_policies(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, CLUSTER_POLICY_COLUMNS, title="Cluster Policies")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cpol_app.command("get")
    def get_cluster_policy(
        name: str = typer.Argument(help="ClusterPolicy name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a Kyverno ClusterPolicy.

        Examples:
            ops k8s cluster-policies get require-labels
            ops k8s cluster-policies get require-labels -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_policy(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterPolicy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cpol_app.command("create")
    def create_cluster_policy(
        name: str = typer.Argument(help="ClusterPolicy name"),
        rule: list[str] | None = typer.Option(
            None, "--rule", help="Policy rule as JSON string (repeatable)"
        ),
        background: bool = typer.Option(
            True, "--background/--no-background", help="Enable background scanning"
        ),
        validation_failure_action: str = typer.Option(
            "Audit",
            "--action",
            help="Validation failure action: Audit or Enforce",
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Kyverno ClusterPolicy.

        Examples:
            ops k8s cluster-policies create require-labels \\
                --rule '{"name":"check-labels","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Labels required","pattern":{"metadata":{"labels":{"app":"?*"}}}}}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            rules = _parse_rules(rule)

            resource = manager.create_cluster_policy(
                name,
                rules=rules,
                background=background,
                validation_failure_action=validation_failure_action,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ClusterPolicy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @cpol_app.command("delete")
    def delete_cluster_policy(
        name: str = typer.Argument(help="ClusterPolicy name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a Kyverno ClusterPolicy.

        Examples:
            ops k8s cluster-policies delete require-labels
            ops k8s cluster-policies delete require-labels --force
        """
        try:
            if not force and not confirm_delete("ClusterPolicy", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cluster_policy(name)
            console.print(f"[green]ClusterPolicy '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Namespaced Policies
    # -------------------------------------------------------------------------

    pol_app = typer.Typer(
        name="policies",
        help="Manage Kyverno namespace-scoped policies",
        no_args_is_help=True,
    )
    app.add_typer(pol_app, name="policies")

    @pol_app.command("list")
    def list_policies(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List Kyverno Policies in a namespace.

        Examples:
            ops k8s policies list
            ops k8s policies list -n production
            ops k8s policies list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_policies(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, POLICY_COLUMNS, title="Policies")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pol_app.command("get")
    def get_policy(
        name: str = typer.Argument(help="Policy name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a Kyverno Policy.

        Examples:
            ops k8s policies get restrict-images
            ops k8s policies get restrict-images -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_policy(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Policy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pol_app.command("create")
    def create_policy(
        name: str = typer.Argument(help="Policy name"),
        namespace: NamespaceOption = None,
        rule: list[str] | None = typer.Option(
            None, "--rule", help="Policy rule as JSON string (repeatable)"
        ),
        background: bool = typer.Option(
            True, "--background/--no-background", help="Enable background scanning"
        ),
        validation_failure_action: str = typer.Option(
            "Audit",
            "--action",
            help="Validation failure action: Audit or Enforce",
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a Kyverno Policy in a namespace.

        Examples:
            ops k8s policies create restrict-images -n production \\
                --rule '{"name":"check-image","match":{"any":[{"resources":{"kinds":["Pod"]}}]},"validate":{"message":"Only allowed images","pattern":{"spec":{"containers":[{"image":"myregistry.io/*"}]}}}}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            rules = _parse_rules(rule)

            resource = manager.create_policy(
                name,
                namespace=namespace,
                rules=rules,
                background=background,
                validation_failure_action=validation_failure_action,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created Policy: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pol_app.command("delete")
    def delete_policy(
        name: str = typer.Argument(help="Policy name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a Kyverno Policy.

        Examples:
            ops k8s policies delete restrict-images
            ops k8s policies delete restrict-images -n production --force
        """
        try:
            if not force and not confirm_delete("Policy", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_policy(name, namespace=namespace)
            console.print(f"[green]Policy '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @pol_app.command("validate")
    def validate_policy(
        file: Path = typer.Option(
            ...,
            "--file",
            "-f",
            help="Path to YAML file containing the policy",
            exists=True,
            readable=True,
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Validate a Kyverno policy via dry-run.

        Reads a YAML file and attempts a dry-run create against the cluster
        to verify the policy is valid.

        Examples:
            ops k8s policies validate --file policy.yaml
            ops k8s policies validate -f ./my-cluster-policy.yaml -o json
        """
        try:
            policy_text = file.read_text()
            policy_dict = yaml.safe_load(policy_text)
            if not isinstance(policy_dict, dict):
                console.print("[red]Error:[/red] YAML file must contain a single policy document")
                raise typer.Exit(1)

            manager = get_manager()
            result = manager.validate_policy(policy_dict)

            if result.get("valid"):
                console.print("[green]Policy is valid[/green]")
                policy = result.get("policy")
                if policy and output != OutputFormat.TABLE:
                    formatter = get_formatter(output, console)
                    formatter.format_resource(policy, title="Validated Policy")
            else:
                console.print("[red]Policy is invalid[/red]")
                console.print(f"  {result.get('error', 'Unknown error')}")
                raise typer.Exit(1)
        except yaml.YAMLError as e:
            console.print(f"[red]Error:[/red] Invalid YAML: {e}")
            raise typer.Exit(1) from None
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ClusterPolicyReports (read-only)
    # -------------------------------------------------------------------------

    cpolr_app = typer.Typer(
        name="cluster-policy-reports",
        help="View Kyverno cluster policy reports",
        no_args_is_help=True,
    )
    app.add_typer(cpolr_app, name="cluster-policy-reports")

    @cpolr_app.command("list")
    def list_cluster_policy_reports(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ClusterPolicyReports.

        Examples:
            ops k8s cluster-policy-reports list
            ops k8s cluster-policy-reports list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_policy_reports()
            formatter = get_formatter(output, console)
            formatter.format_list(
                resources,
                CLUSTER_POLICY_REPORT_COLUMNS,
                title="Cluster Policy Reports",
            )
        except KubernetesError as e:
            handle_k8s_error(e)

    @cpolr_app.command("get")
    def get_cluster_policy_report(
        name: str = typer.Argument(help="ClusterPolicyReport name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a ClusterPolicyReport.

        Examples:
            ops k8s cluster-policy-reports get cpolr-require-labels
            ops k8s cluster-policy-reports get cpolr-require-labels -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_policy_report(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterPolicyReport: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Namespaced PolicyReports (read-only)
    # -------------------------------------------------------------------------

    polr_app = typer.Typer(
        name="policy-reports",
        help="View Kyverno policy reports",
        no_args_is_help=True,
    )
    app.add_typer(polr_app, name="policy-reports")

    @polr_app.command("list")
    def list_policy_reports(
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List PolicyReports in a namespace.

        Examples:
            ops k8s policy-reports list
            ops k8s policy-reports list -n production
            ops k8s policy-reports list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_policy_reports(namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_list(resources, POLICY_REPORT_COLUMNS, title="Policy Reports")
        except KubernetesError as e:
            handle_k8s_error(e)

    @polr_app.command("get")
    def get_policy_report(
        name: str = typer.Argument(help="PolicyReport name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a PolicyReport.

        Examples:
            ops k8s policy-reports get polr-restrict-images
            ops k8s policy-reports get polr-restrict-images -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_policy_report(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"PolicyReport: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # Admission Controller Status
    # -------------------------------------------------------------------------

    admission_app = typer.Typer(
        name="admission",
        help="Kyverno admission controller status",
        no_args_is_help=True,
    )
    app.add_typer(admission_app, name="admission")

    @admission_app.command("status")
    def admission_status(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kyverno admission controller status.

        Checks if the Kyverno admission controller pods are running
        in the kyverno namespace.

        Examples:
            ops k8s admission status
            ops k8s admission status -o json
        """
        try:
            manager = get_manager()
            status = manager.get_admission_status()
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title="Kyverno Admission Controller")
        except KubernetesError as e:
            handle_k8s_error(e)
