"""Output formatters for Kubernetes CLI commands.

Implements the Strategy pattern for output formatting,
allowing commands to output data in table, JSON, or YAML formats.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import StrEnum
from typing import Any

import yaml
from rich.console import Console

from system_operations_manager.cli.output import Table


class OutputFormat(StrEnum):
    """Supported output formats for CLI commands."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


class K8sFormatter(ABC):
    """Abstract base class for Kubernetes output formatters."""

    def __init__(self, console: Console) -> None:
        self.console = console

    @abstractmethod
    def format_resource(self, resource: Any, title: str = "") -> None:
        """Format and display a single resource."""

    @abstractmethod
    def format_list(
        self,
        resources: Sequence[Any],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format and display a list of resources."""

    @abstractmethod
    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format and display a dictionary."""

    def format_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[green]{message}[/green]")

    def format_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[red]Error:[/red] {message}")


class TableFormatter(K8sFormatter):
    """Rich table output formatter."""

    def format_resource(self, resource: Any, title: str = "") -> None:
        """Format resource as a two-column key-value table."""
        table = Table(title=title or "Resource Details", show_header=True)
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        data = (
            resource.model_dump(exclude_none=True) if hasattr(resource, "model_dump") else resource
        )
        for field, value in data.items():
            table.add_row(field, self._format_value(value))

        self.console.print(table)

    def format_list(
        self,
        resources: Sequence[Any],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        """Format resources as a multi-column table."""
        table = Table(title=title, show_header=True)

        for _field_name, header in columns:
            style = "cyan" if header.lower() in ("name", "namespace") else None
            table.add_column(header, style=style)

        for resource in resources:
            data = resource.model_dump() if hasattr(resource, "model_dump") else resource
            row = []
            for field_name, _ in columns:
                value = self._get_nested_value(data, field_name)
                row.append(self._format_cell_value(value))
            table.add_row(*row)

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(resources)} resources[/dim]")

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        """Format dictionary as a two-column table."""
        table = Table(title=title, show_header=True)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        for key, value in data.items():
            table.add_row(key, self._format_value(value))

        self.console.print(table)

    def _format_value(self, value: Any) -> str:
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
        if isinstance(value, dict):
            if "name" in value:
                return str(value["name"])
            return json.dumps(value)
        elif isinstance(value, list):
            if len(value) == 0:
                return "-"
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
        keys = field_path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value


class JsonFormatter(K8sFormatter):
    """JSON output formatter."""

    def format_resource(self, resource: Any, title: str = "") -> None:
        data = (
            resource.model_dump(exclude_none=True) if hasattr(resource, "model_dump") else resource
        )
        self.console.print(json.dumps(data, indent=2, default=str))

    def format_list(
        self,
        resources: Sequence[Any],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        data = [
            r.model_dump(exclude_none=True) if hasattr(r, "model_dump") else r for r in resources
        ]
        output = {"data": data, "total": len(data)}
        self.console.print(json.dumps(output, indent=2, default=str))

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        self.console.print(json.dumps(data, indent=2, default=str))


class YamlFormatter(K8sFormatter):
    """YAML output formatter."""

    def format_resource(self, resource: Any, title: str = "") -> None:
        data = (
            resource.model_dump(exclude_none=True) if hasattr(resource, "model_dump") else resource
        )
        self.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def format_list(
        self,
        resources: Sequence[Any],
        columns: list[tuple[str, str]],
        title: str = "",
    ) -> None:
        data = [
            r.model_dump(exclude_none=True) if hasattr(r, "model_dump") else r for r in resources
        ]
        self.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def format_dict(self, data: dict[str, Any], title: str = "") -> None:
        self.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))


def get_formatter(format_type: OutputFormat, console: Console | None = None) -> K8sFormatter:
    """Factory function to get the appropriate formatter."""
    if console is None:
        console = Console()

    formatters: dict[OutputFormat, type[K8sFormatter]] = {
        OutputFormat.TABLE: TableFormatter,
        OutputFormat.JSON: JsonFormatter,
        OutputFormat.YAML: YamlFormatter,
    }

    formatter_class = formatters.get(format_type, TableFormatter)
    return formatter_class(console)
