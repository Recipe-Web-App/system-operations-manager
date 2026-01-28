"""Base utilities for Kong Enterprise CLI commands.

This module provides enterprise-specific utilities, decorators, and error handling
for Kong Enterprise commands.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import typer
from rich.console import Console

from system_operations_manager.integrations.kong.exceptions import (
    KongEnterpriseRequiredError,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.enterprise import (
        EnterpriseFeatureChecker,
    )

# Shared console instance
console = Console()

# Type variables for decorator
P = ParamSpec("P")
R = TypeVar("R")


def handle_enterprise_error(error: KongEnterpriseRequiredError) -> None:
    """Handle Kong Enterprise required errors with user-friendly output.

    Args:
        error: The enterprise required error to handle.

    Raises:
        typer.Exit: Always exits with code 1.
    """
    console.print("[red]Error:[/red] Kong Enterprise Required")
    console.print(f"  {error.message}")
    console.print()
    console.print("[dim]This feature requires Kong Enterprise edition.[/dim]")
    console.print(
        "[dim]Visit https://konghq.com/products/kong-enterprise for more information.[/dim]"
    )
    raise typer.Exit(1)


def require_enterprise(
    feature: str,
    get_checker: Callable[[], EnterpriseFeatureChecker],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to require Enterprise edition for a command.

    Args:
        feature: The Enterprise feature name to require.
        get_checker: Factory function that returns an EnterpriseFeatureChecker.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                checker = get_checker()
                checker.require_enterprise(feature)
            except KongEnterpriseRequiredError as e:
                handle_enterprise_error(e)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def enterprise_status_message(is_enterprise: bool) -> str:
    """Get a status message for Enterprise availability.

    Args:
        is_enterprise: Whether Enterprise is available.

    Returns:
        Status message string.
    """
    if is_enterprise:
        return "[green]Enterprise[/green]"
    return "[yellow]Community (OSS)[/yellow]"


def format_enterprise_feature(available: bool) -> str:
    """Format an Enterprise feature availability status.

    Args:
        available: Whether the feature is available.

    Returns:
        Formatted status string.
    """
    if available:
        return "[green]Available[/green]"
    return "[dim]Not available[/dim]"
