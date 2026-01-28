"""Centralized CLI output utilities.

This package provides consistent output formatting across all CLI commands.
All table rendering should use these classes to ensure uniform behavior.

Usage:
    from system_operations_manager.cli.output import Table

    table = Table(title="Results")
    table.add_column("Name", style="cyan")
    table.add_column("Value")
    table.add_row("foo", "bar")
    console.print(table)
"""

from system_operations_manager.cli.output.table import Table

__all__ = ["Table"]
