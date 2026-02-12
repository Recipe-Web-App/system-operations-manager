"""Unit tests for Kubernetes output formatters."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock

import pytest
import yaml
from rich.console import Console

from system_operations_manager.plugins.kubernetes.formatters import (
    JsonFormatter,
    OutputFormat,
    TableFormatter,
    YamlFormatter,
    get_formatter,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self) -> None:
        """OutputFormat should have TABLE, JSON, YAML values."""
        assert OutputFormat.TABLE == "table"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.YAML == "yaml"

    def test_output_format_is_str_subclass(self) -> None:
        """OutputFormat should be a string subclass."""
        assert isinstance(OutputFormat.TABLE, str)
        assert isinstance(OutputFormat.JSON, str)
        assert isinstance(OutputFormat.YAML, str)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetFormatter:
    """Tests for get_formatter factory function."""

    def test_get_formatter_table(self) -> None:
        """get_formatter should return TableFormatter for TABLE format."""
        console = Console()
        formatter = get_formatter(OutputFormat.TABLE, console)
        assert isinstance(formatter, TableFormatter)
        assert formatter.console is console

    def test_get_formatter_json(self) -> None:
        """get_formatter should return JsonFormatter for JSON format."""
        console = Console()
        formatter = get_formatter(OutputFormat.JSON, console)
        assert isinstance(formatter, JsonFormatter)
        assert formatter.console is console

    def test_get_formatter_yaml(self) -> None:
        """get_formatter should return YamlFormatter for YAML format."""
        console = Console()
        formatter = get_formatter(OutputFormat.YAML, console)
        assert isinstance(formatter, YamlFormatter)
        assert formatter.console is console

    def test_get_formatter_defaults_to_console(self) -> None:
        """get_formatter should create default Console if none provided."""
        formatter = get_formatter(OutputFormat.TABLE)
        assert isinstance(formatter, TableFormatter)
        assert formatter.console is not None

    def test_get_formatter_unknown_defaults_to_table(self) -> None:
        """get_formatter should default to TableFormatter for unknown format."""
        console = Console()
        # Cast to OutputFormat to test fallback behavior
        formatter = get_formatter("unknown", console)
        assert isinstance(formatter, TableFormatter)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestTableFormatter:
    """Tests for TableFormatter."""

    @pytest.fixture
    def console_output(self) -> StringIO:
        """Create StringIO for capturing console output."""
        return StringIO()

    @pytest.fixture
    def console(self, console_output: StringIO) -> Console:
        """Create Console that writes to StringIO."""
        return Console(file=console_output, force_terminal=False, width=120)

    @pytest.fixture
    def formatter(self, console: Console) -> TableFormatter:
        """Create TableFormatter instance."""
        return TableFormatter(console)

    def test_format_resource_with_model_dump(
        self, formatter: TableFormatter, console_output: StringIO
    ) -> None:
        """format_resource should format resource with model_dump method."""
        resource = MagicMock()
        resource.model_dump.return_value = {
            "name": "test-pod",
            "namespace": "default",
            "status": "Running",
        }

        formatter.format_resource(resource, title="Pod Details")
        output = console_output.getvalue()

        assert "Pod Details" in output
        assert "name" in output
        assert "test-pod" in output
        assert resource.model_dump.called

    def test_format_resource_with_dict(
        self, formatter: TableFormatter, console_output: StringIO
    ) -> None:
        """format_resource should format plain dict resource."""
        resource = {"name": "test-svc", "port": 80}

        formatter.format_resource(resource, title="Service")
        output = console_output.getvalue()

        assert "Service" in output or "name" in output

    def test_format_list_with_columns(
        self, formatter: TableFormatter, console_output: StringIO
    ) -> None:
        """format_list should format resources with specified columns."""
        resources = [
            MagicMock(model_dump=lambda **kwargs: {"name": "pod-1", "status": "Running"}),
            MagicMock(model_dump=lambda **kwargs: {"name": "pod-2", "status": "Pending"}),
        ]
        columns = [("name", "Name"), ("status", "Status")]

        formatter.format_list(resources, columns, title="Pods")
        output = console_output.getvalue()

        assert "pod-1" in output or "pod-2" in output or "Total: 2" in output

    def test_format_list_empty(self, formatter: TableFormatter, console_output: StringIO) -> None:
        """format_list should handle empty list."""
        formatter.format_list([], [("name", "Name")], title="Empty")
        output = console_output.getvalue()

        assert "Total: 0" in output

    def test_format_dict(self, formatter: TableFormatter, console_output: StringIO) -> None:
        """format_dict should format dictionary as table."""
        data = {"context": "minikube", "namespace": "default", "connected": "yes"}

        formatter.format_dict(data, title="Status")
        output = console_output.getvalue()

        assert "Status" in output or "context" in output

    def test_format_value_dict(self, formatter: TableFormatter) -> None:
        """_format_value should format dict as JSON."""
        result = formatter._format_value({"key": "value", "nested": {"data": 123}})
        assert "key" in result
        assert "value" in result

    def test_format_value_list_of_strings(self, formatter: TableFormatter) -> None:
        """_format_value should format list of strings as comma-separated."""
        result = formatter._format_value(["one", "two", "three"])
        assert result == "one, two, three"

    def test_format_value_empty_list(self, formatter: TableFormatter) -> None:
        """_format_value should format empty list as []."""
        result = formatter._format_value([])
        assert result == "[]"

    def test_format_value_list_of_objects(self, formatter: TableFormatter) -> None:
        """_format_value should format list of objects as JSON."""
        result = formatter._format_value([{"id": 1}, {"id": 2}])
        assert "id" in result

    def test_format_value_bool_true(self, formatter: TableFormatter) -> None:
        """_format_value should format True with green markup."""
        result = formatter._format_value(True)
        assert "true" in result.lower()

    def test_format_value_bool_false(self, formatter: TableFormatter) -> None:
        """_format_value should format False with red markup."""
        result = formatter._format_value(False)
        assert "false" in result.lower()

    def test_format_value_none(self, formatter: TableFormatter) -> None:
        """_format_value should format None as dim dash."""
        result = formatter._format_value(None)
        assert "-" in result

    def test_format_value_string(self, formatter: TableFormatter) -> None:
        """_format_value should format string as-is."""
        result = formatter._format_value("test-string")
        assert result == "test-string"

    def test_format_cell_value_dict_with_name(self, formatter: TableFormatter) -> None:
        """_format_cell_value should extract name from dict."""
        result = formatter._format_cell_value({"name": "my-resource", "id": "123"})
        assert result == "my-resource"

    def test_format_cell_value_dict_without_name(self, formatter: TableFormatter) -> None:
        """_format_cell_value should format dict as JSON when no name."""
        result = formatter._format_cell_value({"key": "value"})
        assert "key" in result

    def test_format_cell_value_list_truncation(self, formatter: TableFormatter) -> None:
        """_format_cell_value should truncate lists > 3 items."""
        result = formatter._format_cell_value(["a", "b", "c", "d", "e"])
        assert "a, b, c" in result
        assert "+2" in result

    def test_format_cell_value_empty_list(self, formatter: TableFormatter) -> None:
        """_format_cell_value should format empty list as dash."""
        result = formatter._format_cell_value([])
        assert result == "-"

    def test_format_cell_value_bool_true(self, formatter: TableFormatter) -> None:
        """_format_cell_value should format True as 'Yes'."""
        result = formatter._format_cell_value(True)
        assert result == "Yes"

    def test_format_cell_value_bool_false(self, formatter: TableFormatter) -> None:
        """_format_cell_value should format False as 'No'."""
        result = formatter._format_cell_value(False)
        assert result == "No"

    def test_format_cell_value_none(self, formatter: TableFormatter) -> None:
        """_format_cell_value should format None as dash."""
        result = formatter._format_cell_value(None)
        assert result == "-"

    def test_get_nested_value_single_level(self, formatter: TableFormatter) -> None:
        """_get_nested_value should retrieve single-level value."""
        data = {"name": "test"}
        result = formatter._get_nested_value(data, "name")
        assert result == "test"

    def test_get_nested_value_nested(self, formatter: TableFormatter) -> None:
        """_get_nested_value should retrieve nested value with dot notation."""
        data = {"metadata": {"name": "test-pod", "namespace": "default"}}
        result = formatter._get_nested_value(data, "metadata.name")
        assert result == "test-pod"

    def test_get_nested_value_missing_key(self, formatter: TableFormatter) -> None:
        """_get_nested_value should return None for missing key."""
        data = {"name": "test"}
        result = formatter._get_nested_value(data, "missing.key")
        assert result is None

    def test_format_success(self, formatter: TableFormatter, console_output: StringIO) -> None:
        """format_success should display green success message."""
        formatter.format_success("Operation succeeded")
        output = console_output.getvalue()
        assert "Operation succeeded" in output

    def test_format_error(self, formatter: TableFormatter, console_output: StringIO) -> None:
        """format_error should display red error message."""
        formatter.format_error("Something failed")
        output = console_output.getvalue()
        assert "Something failed" in output or "Error" in output


@pytest.mark.unit
@pytest.mark.kubernetes
class TestJsonFormatter:
    """Tests for JsonFormatter."""

    @pytest.fixture
    def console_output(self) -> StringIO:
        """Create StringIO for capturing console output."""
        return StringIO()

    @pytest.fixture
    def console(self, console_output: StringIO) -> Console:
        """Create Console that writes to StringIO."""
        return Console(file=console_output, force_terminal=False)

    @pytest.fixture
    def formatter(self, console: Console) -> JsonFormatter:
        """Create JsonFormatter instance."""
        return JsonFormatter(console)

    def test_format_resource_with_model_dump(
        self, formatter: JsonFormatter, console_output: StringIO
    ) -> None:
        """format_resource should output valid JSON for resource with model_dump."""
        resource = MagicMock()
        resource.model_dump.return_value = {"name": "test", "status": "active"}

        formatter.format_resource(resource)
        output = console_output.getvalue()

        data = json.loads(output)
        assert data["name"] == "test"
        assert data["status"] == "active"

    def test_format_resource_with_dict(
        self, formatter: JsonFormatter, console_output: StringIO
    ) -> None:
        """format_resource should output valid JSON for dict resource."""
        resource = {"name": "test", "value": 42}

        formatter.format_resource(resource)
        output = console_output.getvalue()

        data = json.loads(output)
        assert data["name"] == "test"
        assert data["value"] == 42

    def test_format_list(self, formatter: JsonFormatter, console_output: StringIO) -> None:
        """format_list should output valid JSON with data and total."""
        resources = [
            MagicMock(model_dump=lambda **kwargs: {"name": "item1"}),
            MagicMock(model_dump=lambda **kwargs: {"name": "item2"}),
        ]

        formatter.format_list(resources, [], title="Items")
        output = console_output.getvalue()

        data = json.loads(output)
        assert "data" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["data"]) == 2

    def test_format_dict(self, formatter: JsonFormatter, console_output: StringIO) -> None:
        """format_dict should output valid JSON."""
        data_dict = {"key1": "value1", "key2": 123}

        formatter.format_dict(data_dict)
        output = console_output.getvalue()

        data = json.loads(output)
        assert data["key1"] == "value1"
        assert data["key2"] == 123


@pytest.mark.unit
@pytest.mark.kubernetes
class TestYamlFormatter:
    """Tests for YamlFormatter."""

    @pytest.fixture
    def console_output(self) -> StringIO:
        """Create StringIO for capturing console output."""
        return StringIO()

    @pytest.fixture
    def console(self, console_output: StringIO) -> Console:
        """Create Console that writes to StringIO."""
        return Console(file=console_output, force_terminal=False)

    @pytest.fixture
    def formatter(self, console: Console) -> YamlFormatter:
        """Create YamlFormatter instance."""
        return YamlFormatter(console)

    def test_format_resource_with_model_dump(
        self, formatter: YamlFormatter, console_output: StringIO
    ) -> None:
        """format_resource should output valid YAML for resource with model_dump."""
        resource = MagicMock()
        resource.model_dump.return_value = {"name": "test", "status": "active"}

        formatter.format_resource(resource)
        output = console_output.getvalue()

        data = yaml.safe_load(output)
        assert data["name"] == "test"
        assert data["status"] == "active"

    def test_format_resource_with_dict(
        self, formatter: YamlFormatter, console_output: StringIO
    ) -> None:
        """format_resource should output valid YAML for dict resource."""
        resource = {"name": "test", "value": 42}

        formatter.format_resource(resource)
        output = console_output.getvalue()

        data = yaml.safe_load(output)
        assert data["name"] == "test"
        assert data["value"] == 42

    def test_format_list(self, formatter: YamlFormatter, console_output: StringIO) -> None:
        """format_list should output valid YAML list."""
        resources = [
            MagicMock(model_dump=lambda **kwargs: {"name": "item1"}),
            MagicMock(model_dump=lambda **kwargs: {"name": "item2"}),
        ]

        formatter.format_list(resources, [], title="Items")
        output = console_output.getvalue()

        data = yaml.safe_load(output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_format_dict(self, formatter: YamlFormatter, console_output: StringIO) -> None:
        """format_dict should output valid YAML."""
        data_dict = {"key1": "value1", "key2": 123}

        formatter.format_dict(data_dict)
        output = console_output.getvalue()

        data = yaml.safe_load(output)
        assert data["key1"] == "value1"
        assert data["key2"] == 123
