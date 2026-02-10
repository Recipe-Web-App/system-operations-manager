"""Base utilities for Kubernetes CLI commands.

Provides common Typer options, error handling utilities,
and shared functionality for all Kubernetes CLI commands.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConflictError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
    KubernetesValidationError,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat

# Shared console instance
console = Console()


# =============================================================================
# Common Typer Option Annotations
# =============================================================================

OutputOption = Annotated[
    OutputFormat,
    typer.Option(
        "--output",
        "-o",
        help="Output format: table, json, or yaml",
        case_sensitive=False,
    ),
]

NamespaceOption = Annotated[
    str | None,
    typer.Option(
        "--namespace",
        "-n",
        help="Kubernetes namespace (defaults to config or 'default')",
    ),
]

AllNamespacesOption = Annotated[
    bool,
    typer.Option(
        "--all-namespaces",
        "-A",
        help="List resources across all namespaces",
    ),
]

LabelSelectorOption = Annotated[
    str | None,
    typer.Option(
        "--selector",
        "-l",
        help="Label selector (e.g., 'app=nginx,tier=frontend')",
    ),
]

FieldSelectorOption = Annotated[
    str | None,
    typer.Option(
        "--field-selector",
        help="Field selector (e.g., 'status.phase=Running')",
    ),
]

ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Skip confirmation prompts",
    ),
]

DryRunOption = Annotated[
    bool,
    typer.Option(
        "--dry-run",
        help="Only print what would be done, don't execute",
    ),
]


# =============================================================================
# Error Handling
# =============================================================================


def handle_k8s_error(error: KubernetesError) -> None:
    """Handle Kubernetes errors with user-friendly output.

    Args:
        error: The Kubernetes error to handle.

    Raises:
        typer.Exit: Always exits with code 1.
    """
    if isinstance(error, KubernetesConnectionError):
        console.print("[red]Error:[/red] Cannot connect to Kubernetes cluster")
        console.print(f"  {error.message}")
        if error.original_error:
            console.print(f"  Cause: {error.original_error}")
        console.print(
            "\n[dim]Hint: Check that your kubeconfig is valid and the cluster is reachable.[/dim]"
        )

    elif isinstance(error, KubernetesAuthError):
        console.print("[red]Error:[/red] Authentication/authorization failed")
        console.print(f"  {error.message}")
        console.print("\n[dim]Hint: Check your credentials, token, or RBAC permissions.[/dim]")

    elif isinstance(error, KubernetesNotFoundError):
        console.print("[red]Error:[/red] Resource not found")
        console.print(f"  {error.message}")

    elif isinstance(error, KubernetesValidationError):
        console.print("[red]Error:[/red] Validation failed")
        console.print(f"  {error.message}")
        if error.validation_errors:
            console.print("\n  Field errors:")
            for field, err in error.validation_errors.items():
                console.print(f"    - {field}: {err}")

    elif isinstance(error, KubernetesConflictError):
        console.print("[red]Error:[/red] Resource conflict")
        console.print(f"  {error.message}")

    elif isinstance(error, KubernetesTimeoutError):
        console.print("[red]Error:[/red] Operation timed out")
        console.print(f"  {error.message}")
        console.print(
            "\n[dim]Hint: Try increasing the timeout with --timeout or OPS_K8S_TIMEOUT.[/dim]"
        )

    else:
        console.print(f"[red]Error:[/red] {error.message}")
        if error.status_code:
            console.print(f"  HTTP Status: {error.status_code}")

    raise typer.Exit(1)


# =============================================================================
# Confirmation Utilities
# =============================================================================


def confirm_delete(resource_type: str, name: str, namespace: str | None = None) -> bool:
    """Prompt user to confirm deletion."""
    msg = f"Are you sure you want to delete {resource_type} '{name}'"
    if namespace:
        msg += f" in namespace '{namespace}'"
    msg += "?"
    return typer.confirm(msg, default=False)


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user to confirm an action."""
    return typer.confirm(message, default=default)
