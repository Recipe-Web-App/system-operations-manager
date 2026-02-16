"""Output formatters for Kong CLI commands.

This module implements the Strategy pattern for output formatting,
allowing commands to output data in table, JSON, or YAML formats
through a common interface.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypeVar

import yaml
from rich.console import Console

from system_operations_manager.cli.output import Table

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.models.base import KongEntityBase
    from system_operations_manager.integrations.kong.models.unified import (
        UnifiedEntityList,
    )

# TypeVar for entity types (used in format_unified_list)
T = TypeVar("T")


class OutputFormat(StrEnum):
    """Supported output formats for CLI commands."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


class OutputFormatter(ABC):
    """Abstract base class for output formatters.

    Formatters handle the presentation of Kong entity data in various
    formats. Each formatter implements the same interface but produces
    different output.
    """

    def __init__(self, console: Console) -> None:
        """Initialize the formatter.

        Args:
            console: Rich console for output.
        """
        self.console = console

    @abstractmethod
    def format_entity(self, entity: KongEntityBase, title: str = "") -> None:
        """Format and display a single entity.

        Args:
            entity: The entity model to display.
            title: Optional title for the output.
        """

    @abstractmethod
    def format_list(
        self,
        entities: Sequence[KongEntityBase],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format and display a list of entities.

        Args:
            entities: Sequence of entity models to display.
            columns: List of (field_name, display_header) tuples defining
                which fields to show and their column headers.
            title: Optional title for the table/output.
        """

    @abstractmethod
    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format and display a dictionary.

        Args:
            data: Dictionary data to display.
            title: Optional title for the output.
        """

    @abstractmethod
    def format_unified_list(
        self,
        unified: UnifiedEntityList[Any],
        columns: list[tuple[str, str]],
        title: str = "",
        show_drift: bool = False,
    ) -> None:
        """Format and display a unified entity list with source information.

        Args:
            unified: Unified entity list with source tracking.
            columns: List of (field_name, display_header) tuples.
            title: Optional title for the output.
            show_drift: Whether to show drift details for entities in both sources.
        """

    def format_success(self, message: str) -> None:
        """Format and display a success message.

        Args:
            message: Success message to display.
        """
        self.console.print(f"[green]{message}[/green]")

    def format_error(self, message: str) -> None:
        """Format and display an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[red]Error:[/red] {message}")


class TableFormatter(OutputFormatter):
    """Rich table output formatter.

    Produces nicely formatted tables using the Rich library.
    Best for human-readable terminal output.
    """

    def format_entity(self, entity: KongEntityBase, title: str = "") -> None:
        """Format entity as a two-column key-value table."""
        table = Table(title=title or "Entity Details", show_header=True)
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        for field, value in entity.model_dump(exclude_none=True).items():
            formatted_value = self._format_value(value)
            table.add_row(field, formatted_value)

        self.console.print(table)

    def format_list(
        self,
        entities: Sequence[KongEntityBase],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format entities as a multi-column table."""
        table = Table(title=title, show_header=True)

        # Add columns with styling for ID/Name columns
        for _field_name, header in columns:
            style = "cyan" if header.lower() in ("name", "id") else None
            table.add_column(header, style=style)

        # Add rows
        for entity in entities:
            data = entity.model_dump()
            row = []
            for field_name, _ in columns:
                value = self._get_nested_value(data, field_name)
                row.append(self._format_cell_value(value))
            table.add_row(*row)

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(entities)} entities[/dim]")

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format dictionary as a two-column table."""
        table = Table(title=title, show_header=True)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        for key, value in data.items():
            formatted_value = self._format_value(value)
            table.add_row(key, formatted_value)

        self.console.print(table)

    def format_unified_list(
        self,
        unified: UnifiedEntityList[Any],
        columns: list[tuple[str, str]],
        title: str = "",
        show_drift: bool = False,
    ) -> None:
        """Format unified entity list with source column."""
        from system_operations_manager.integrations.kong.models.unified import (
            EntitySource,
        )

        table = Table(title=title, show_header=True)

        # Add Source column first
        table.add_column("Source", style="magenta")

        # Add entity columns
        for _field_name, header in columns:
            style = "cyan" if header.lower() in ("name", "id") else None
            table.add_column(header, style=style)

        # Add Drift column if showing drift
        if show_drift:
            table.add_column("Drift", style="yellow")

        # Add rows
        for unified_entity in unified.entities:
            entity = unified_entity.entity
            data = entity.model_dump()

            # Source indicator with color
            if unified_entity.source == EntitySource.GATEWAY:
                source_cell = "[blue]gateway[/blue]"
            elif unified_entity.source == EntitySource.KONNECT:
                source_cell = "[green]konnect[/green]"
            else:
                source_cell = "[cyan]both[/cyan]"

            row = [source_cell]

            # Entity fields
            for field_name, _ in columns:
                value = self._get_nested_value(data, field_name)
                row.append(self._format_cell_value(value))

            # Drift indicator
            if show_drift:
                if unified_entity.has_drift and unified_entity.drift_fields:
                    drift_str = ", ".join(unified_entity.drift_fields)
                    row.append(f"[yellow]{drift_str}[/yellow]")
                elif unified_entity.source == EntitySource.BOTH:
                    row.append("[green]✓[/green]")
                else:
                    row.append("-")

            table.add_row(*row)

        self.console.print(table)

        # Summary
        summary_parts = [f"Total: {len(unified)}"]
        if unified.gateway_only_count > 0:
            summary_parts.append(f"Gateway only: {unified.gateway_only_count}")
        if unified.konnect_only_count > 0:
            summary_parts.append(f"Konnect only: {unified.konnect_only_count}")
        if unified.in_both_count > 0:
            summary_parts.append(f"Both: {unified.in_both_count}")
        if show_drift and unified.drift_count > 0:
            summary_parts.append(f"With drift: {unified.drift_count}")

        self.console.print(f"\n[dim]{' | '.join(summary_parts)}[/dim]")

    def _format_value(self, value: Any) -> str:
        """Format a value for display in a table cell.

        Args:
            value: The value to format.

        Returns:
            String representation suitable for display.
        """
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        elif isinstance(value, list):
            if len(value) == 0:
                return "[]"
            elif all(isinstance(v, str) for v in value):
                return ", ".join(value)
            else:
                return json.dumps(value, indent=2)
        elif isinstance(value, bool):
            return "[green]true[/green]" if value else "[red]false[/red]"
        elif value is None:
            return "[dim]-[/dim]"
        else:
            return str(value)

    def _format_cell_value(self, value: Any) -> str:
        """Format a value for a list table cell (more compact).

        Args:
            value: The value to format.

        Returns:
            Compact string representation.
        """
        if isinstance(value, dict):
            # For references, show ID or name
            if "id" in value:
                return str(value["id"])[:8] + "..."
            elif "name" in value:
                return str(value["name"])
            return json.dumps(value)
        elif isinstance(value, list):
            if len(value) == 0:
                return "-"
            # Show first few items with ellipsis
            items = [str(v) for v in value[:3]]
            result = ", ".join(items)
            if len(value) > 3:
                result += f" (+{len(value) - 3})"
            return result
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif value is None:
            return "-"
        else:
            return str(value)

    def _get_nested_value(self, data: dict[str, Any], field_path: str) -> Any:
        """Get a value from a nested dictionary using dot notation.

        Args:
            data: The dictionary to search.
            field_path: Field path, optionally with dots for nesting.

        Returns:
            The value at the path, or None if not found.
        """
        keys = field_path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value


class JsonFormatter(OutputFormatter):
    """JSON output formatter.

    Produces indented JSON output suitable for parsing by other tools.
    """

    def format_entity(self, entity: KongEntityBase, title: str = "") -> None:
        """Format entity as JSON."""
        self.console.print(json.dumps(entity.model_dump(exclude_none=True), indent=2, default=str))

    def format_list(
        self,
        entities: Sequence[KongEntityBase],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format entity list as JSON array with metadata."""
        data = [e.model_dump(exclude_none=True) for e in entities]
        output = {
            "data": data,
            "total": len(data),
        }
        self.console.print(json.dumps(output, indent=2, default=str))

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format dictionary as JSON."""
        self.console.print(json.dumps(data, indent=2, default=str))

    def format_unified_list(
        self,
        unified: UnifiedEntityList[Any],
        columns: list[tuple[str, str]],
        title: str = "",
        show_drift: bool = False,
    ) -> None:
        """Format unified entity list as JSON with source information."""
        items: list[dict[str, Any]] = []
        for unified_entity in unified.entities:
            entity_data = unified_entity.entity.model_dump(exclude_none=True)
            item: dict[str, Any] = {
                "source": unified_entity.source.value,
                "gateway_id": unified_entity.gateway_id,
                "konnect_id": unified_entity.konnect_id,
                "entity": entity_data,
            }
            if show_drift and unified_entity.has_drift:
                item["has_drift"] = True
                item["drift_fields"] = unified_entity.drift_fields
            items.append(item)

        output = {
            "data": items,
            "summary": {
                "total": len(unified),
                "gateway_only": unified.gateway_only_count,
                "konnect_only": unified.konnect_only_count,
                "in_both": unified.in_both_count,
                "synced": unified.synced_count,
                "with_drift": unified.drift_count,
            },
        }
        self.console.print(json.dumps(output, indent=2, default=str))


class YamlFormatter(OutputFormatter):
    """YAML output formatter.

    Produces YAML output, useful for configuration files and
    human-readable structured data.
    """

    def format_entity(self, entity: KongEntityBase, title: str = "") -> None:
        """Format entity as YAML."""
        self.console.print(
            yaml.dump(
                entity.model_dump(exclude_none=True),
                default_flow_style=False,
                sort_keys=False,
            )
        )

    def format_list(
        self,
        entities: Sequence[KongEntityBase],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format entity list as YAML."""
        data = [e.model_dump(exclude_none=True) for e in entities]
        self.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format dictionary as YAML."""
        self.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def format_unified_list(
        self,
        unified: UnifiedEntityList[Any],
        columns: list[tuple[str, str]],
        title: str = "",
        show_drift: bool = False,
    ) -> None:
        """Format unified entity list as YAML with source information."""
        items: list[dict[str, Any]] = []
        for unified_entity in unified.entities:
            entity_data = unified_entity.entity.model_dump(exclude_none=True)
            item: dict[str, Any] = {
                "source": unified_entity.source.value,
                "gateway_id": unified_entity.gateway_id,
                "konnect_id": unified_entity.konnect_id,
                "entity": entity_data,
            }
            if show_drift and unified_entity.has_drift:
                item["has_drift"] = True
                item["drift_fields"] = unified_entity.drift_fields
            items.append(item)

        output = {
            "data": items,
            "summary": {
                "total": len(unified),
                "gateway_only": unified.gateway_only_count,
                "konnect_only": unified.konnect_only_count,
                "in_both": unified.in_both_count,
                "synced": unified.synced_count,
                "with_drift": unified.drift_count,
            },
        }
        self.console.print(yaml.dump(output, default_flow_style=False, sort_keys=False))


def get_formatter(format_type: OutputFormat, console: Console | None = None) -> OutputFormatter:
    """Factory function to get the appropriate formatter.

    Args:
        format_type: The desired output format.
        console: Optional Rich console instance. If not provided,
            creates a new one.

    Returns:
        OutputFormatter instance for the requested format.

    Example:
        >>> formatter = get_formatter(OutputFormat.JSON)
        >>> formatter.format_entity(service)
    """
    if console is None:
        console = Console()

    formatters: dict[OutputFormat, type[OutputFormatter]] = {
        OutputFormat.TABLE: TableFormatter,
        OutputFormat.JSON: JsonFormatter,
        OutputFormat.YAML: YamlFormatter,
    }

    formatter_class = formatters.get(format_type, TableFormatter)
    return formatter_class(console)
