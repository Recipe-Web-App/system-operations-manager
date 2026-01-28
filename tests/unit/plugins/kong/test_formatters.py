"""Unit tests for Kong output formatters."""

from __future__ import annotations

import json
import re
from io import StringIO
from typing import cast

import pytest
from rich.console import Console

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.plugins.kong.formatters import (
    JsonFormatter,
    OutputFormat,
    TableFormatter,
    YamlFormatter,
    get_formatter,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


@pytest.fixture
def console() -> Console:
    """Create a console that captures output."""
    return Console(file=StringIO(), force_terminal=True, width=120)


@pytest.fixture
def sample_service() -> Service:
    """Create a sample service entity."""
    return Service(
        id="svc-123",
        name="my-api",
        host="api.example.com",
        port=8080,
        protocol="https",
        enabled=True,
    )


@pytest.fixture
def sample_services() -> list[Service]:
    """Create sample service entities."""
    return [
        Service(id="svc-1", name="api-1", host="api1.local", port=80),
        Service(id="svc-2", name="api-2", host="api2.local", port=8080),
    ]


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    @pytest.mark.unit
    def test_output_format_values(self) -> None:
        """OutputFormat should have expected values."""
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.YAML.value == "yaml"


class TestGetFormatter:
    """Tests for get_formatter factory function."""

    @pytest.mark.unit
    def test_get_table_formatter(self) -> None:
        """get_formatter should return TableFormatter for TABLE."""
        formatter = get_formatter(OutputFormat.TABLE)
        assert isinstance(formatter, TableFormatter)

    @pytest.mark.unit
    def test_get_json_formatter(self) -> None:
        """get_formatter should return JsonFormatter for JSON."""
        formatter = get_formatter(OutputFormat.JSON)
        assert isinstance(formatter, JsonFormatter)

    @pytest.mark.unit
    def test_get_yaml_formatter(self) -> None:
        """get_formatter should return YamlFormatter for YAML."""
        formatter = get_formatter(OutputFormat.YAML)
        assert isinstance(formatter, YamlFormatter)

    @pytest.mark.unit
    def test_get_formatter_with_console(self, console: Console) -> None:
        """get_formatter should use provided console."""
        formatter = get_formatter(OutputFormat.TABLE, console)
        assert formatter.console is console


class TestTableFormatter:
    """Tests for TableFormatter."""

    @pytest.fixture
    def formatter(self, console: Console) -> TableFormatter:
        """Create a TableFormatter."""
        return TableFormatter(console)

    @pytest.mark.unit
    def test_format_entity(
        self,
        formatter: TableFormatter,
        sample_service: Service,
        console: Console,
    ) -> None:
        """format_entity should output a table."""
        formatter.format_entity(sample_service, title="Service Details")

        output = cast(StringIO, console.file).getvalue()
        assert "Service Details" in output
        assert "my-api" in output

    @pytest.mark.unit
    def test_format_list(
        self,
        formatter: TableFormatter,
        sample_services: list[Service],
        console: Console,
    ) -> None:
        """format_list should output a table with columns."""
        columns = [
            ("name", "Name"),
            ("host", "Host"),
            ("port", "Port"),
        ]

        formatter.format_list(sample_services, columns, title="Services")

        output = cast(StringIO, console.file).getvalue()
        assert "Services" in output
        assert "api-1" in output
        assert "api-2" in output
        # Check for total (ANSI codes may split "Total:" from "2")
        assert "Total:" in output
        assert "2" in output

    @pytest.mark.unit
    def test_format_dict(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """format_dict should output a key-value table."""
        data = {"version": "3.0.0", "hostname": "kong-node"}

        formatter.format_dict(data, title="Info")

        output = cast(StringIO, console.file).getvalue()
        assert "Info" in output
        assert "version" in output
        assert "3.0.0" in output

    @pytest.mark.unit
    def test_format_success(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """format_success should output green message."""
        formatter.format_success("Operation completed")

        output = cast(StringIO, console.file).getvalue()
        assert "Operation completed" in output

    @pytest.mark.unit
    def test_format_error(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """format_error should output error message."""
        formatter.format_error("Something went wrong")

        output = cast(StringIO, console.file).getvalue()
        assert "Error:" in output
        assert "Something went wrong" in output


class TestTableFormatterValueFormatting:
    """Tests for TableFormatter value formatting helpers."""

    @pytest.fixture
    def formatter(self, console: Console) -> TableFormatter:
        """Create a TableFormatter."""
        return TableFormatter(console)

    @pytest.mark.unit
    def test_format_value_dict(self, formatter: TableFormatter) -> None:
        """_format_value should JSON-format dicts."""
        result = formatter._format_value({"key": "value"})
        assert "key" in result
        assert "value" in result

    @pytest.mark.unit
    def test_format_value_list_of_strings(self, formatter: TableFormatter) -> None:
        """_format_value should comma-join string lists."""
        result = formatter._format_value(["a", "b", "c"])
        assert result == "a, b, c"

    @pytest.mark.unit
    def test_format_value_empty_list(self, formatter: TableFormatter) -> None:
        """_format_value should handle empty lists."""
        result = formatter._format_value([])
        assert result == "[]"

    @pytest.mark.unit
    def test_format_value_bool_true(self, formatter: TableFormatter) -> None:
        """_format_value should format True as green."""
        result = formatter._format_value(True)
        assert "true" in result
        assert "green" in result

    @pytest.mark.unit
    def test_format_value_bool_false(self, formatter: TableFormatter) -> None:
        """_format_value should format False as red."""
        result = formatter._format_value(False)
        assert "false" in result
        assert "red" in result

    @pytest.mark.unit
    def test_format_value_none(self, formatter: TableFormatter) -> None:
        """_format_value should format None as dash."""
        result = formatter._format_value(None)
        assert "-" in result

    @pytest.mark.unit
    def test_format_cell_value_with_id(self, formatter: TableFormatter) -> None:
        """_format_cell_value should truncate IDs."""
        result = formatter._format_cell_value({"id": "550e8400-e29b-41d4-a716-446655440000"})
        assert result.endswith("...")
        assert len(result) < 40

    @pytest.mark.unit
    def test_format_cell_value_with_name(self, formatter: TableFormatter) -> None:
        """_format_cell_value should show name for references."""
        result = formatter._format_cell_value({"name": "my-service"})
        assert result == "my-service"

    @pytest.mark.unit
    def test_format_cell_value_list_truncation(self, formatter: TableFormatter) -> None:
        """_format_cell_value should truncate long lists."""
        result = formatter._format_cell_value(["a", "b", "c", "d", "e"])
        assert "(+2)" in result

    @pytest.mark.unit
    def test_get_nested_value(self, formatter: TableFormatter) -> None:
        """_get_nested_value should access nested dict keys."""
        data = {"service": {"id": "svc-1"}}
        result = formatter._get_nested_value(data, "service.id")
        assert result == "svc-1"

    @pytest.mark.unit
    def test_get_nested_value_missing(self, formatter: TableFormatter) -> None:
        """_get_nested_value should return None for missing keys."""
        data = {"service": {"id": "svc-1"}}
        result = formatter._get_nested_value(data, "route.id")
        assert result is None


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    @pytest.fixture
    def formatter(self, console: Console) -> JsonFormatter:
        """Create a JsonFormatter."""
        return JsonFormatter(console)

    @pytest.mark.unit
    def test_format_entity(
        self,
        formatter: JsonFormatter,
        sample_service: Service,
        console: Console,
    ) -> None:
        """format_entity should output valid JSON."""
        formatter.format_entity(sample_service)

        output = strip_ansi(cast(StringIO, console.file).getvalue())
        data = json.loads(output)
        assert data["name"] == "my-api"
        assert data["host"] == "api.example.com"

    @pytest.mark.unit
    def test_format_list(
        self,
        formatter: JsonFormatter,
        sample_services: list[Service],
        console: Console,
    ) -> None:
        """format_list should output JSON with data array and total."""
        columns = [("name", "Name")]

        formatter.format_list(sample_services, columns)

        output = strip_ansi(cast(StringIO, console.file).getvalue())
        data = json.loads(output)
        assert "data" in data
        assert "total" in data
        assert data["total"] == 2

    @pytest.mark.unit
    def test_format_dict(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """format_dict should output valid JSON."""
        formatter.format_dict({"key": "value"})

        output = strip_ansi(cast(StringIO, console.file).getvalue())
        data = json.loads(output)
        assert data["key"] == "value"


class TestYamlFormatter:
    """Tests for YamlFormatter."""

    @pytest.fixture
    def formatter(self, console: Console) -> YamlFormatter:
        """Create a YamlFormatter."""
        return YamlFormatter(console)

    @pytest.mark.unit
    def test_format_entity(
        self,
        formatter: YamlFormatter,
        sample_service: Service,
        console: Console,
    ) -> None:
        """format_entity should output YAML."""
        formatter.format_entity(sample_service)

        output = cast(StringIO, console.file).getvalue()
        assert "name: my-api" in output
        assert "host: api.example.com" in output

    @pytest.mark.unit
    def test_format_list(
        self,
        formatter: YamlFormatter,
        sample_services: list[Service],
        console: Console,
    ) -> None:
        """format_list should output YAML list."""
        columns = [("name", "Name")]

        formatter.format_list(sample_services, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "- name: api-1" in output or "- id:" in output

    @pytest.mark.unit
    def test_format_dict(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """format_dict should output YAML."""
        formatter.format_dict({"key": "value"})

        output = cast(StringIO, console.file).getvalue()
        assert "key: value" in output
