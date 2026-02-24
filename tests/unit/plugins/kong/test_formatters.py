"""Unit tests for Kong output formatters."""

from __future__ import annotations

import json
import re
from io import StringIO
from typing import Any, cast

import pytest
import yaml
from rich.console import Console

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unified_list(
    gateway_services: list[Service],
    konnect_services: list[Service],
    both_services: list[tuple[Service, bool, list[str] | None]],
) -> UnifiedEntityList[Service]:
    """Build a UnifiedEntityList from explicit per-source lists.

    Args:
        gateway_services: Services that only exist in the gateway.
        konnect_services: Services that only exist in Konnect.
        both_services: Tuples of (service, has_drift, drift_fields) for
            services present in both sources.
    """
    entities: list[UnifiedEntity[Service]] = []
    for svc in gateway_services:
        entities.append(
            UnifiedEntity(
                entity=svc,
                source=EntitySource.GATEWAY,
                gateway_id=svc.id,
            )
        )
    for svc in konnect_services:
        entities.append(
            UnifiedEntity(
                entity=svc,
                source=EntitySource.KONNECT,
                konnect_id=svc.id,
            )
        )
    for svc, has_drift, drift_fields in both_services:
        entities.append(
            UnifiedEntity(
                entity=svc,
                source=EntitySource.BOTH,
                gateway_id=svc.id,
                konnect_id=svc.id,
                has_drift=has_drift,
                drift_fields=drift_fields,
            )
        )
    return UnifiedEntityList(entities=entities)


# ---------------------------------------------------------------------------
# TableFormatter.format_unified_list
# ---------------------------------------------------------------------------


class TestTableFormatterUnifiedList:
    """Tests for TableFormatter.format_unified_list (lines 208-249)."""

    @pytest.fixture
    def console(self) -> Console:
        """Capture-enabled console."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def formatter(self, console: Console) -> TableFormatter:
        """TableFormatter bound to capture console."""
        return TableFormatter(console)

    @pytest.mark.unit
    def test_format_unified_list_gateway_source_label(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Entities from gateway should show 'gateway' source label."""
        svc = Service(id="gw-1", name="gw-svc", host="gw.local")
        unified = _make_unified_list([svc], [], [])
        columns = [("name", "Name"), ("host", "Host")]

        formatter.format_unified_list(unified, columns, title="Unified")

        output = cast(StringIO, console.file).getvalue()
        assert "gateway" in output
        assert "gw-svc" in output

    @pytest.mark.unit
    def test_format_unified_list_konnect_source_label(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Entities from konnect should show 'konnect' source label."""
        svc = Service(id="kn-1", name="kn-svc", host="kn.local")
        unified = _make_unified_list([], [svc], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "konnect" in output
        assert "kn-svc" in output

    @pytest.mark.unit
    def test_format_unified_list_both_source_label(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Entities from both sources should show 'both' source label."""
        svc = Service(id="b-1", name="both-svc", host="both.local")
        unified = _make_unified_list([], [], [(svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "both" in output

    @pytest.mark.unit
    def test_format_unified_list_show_drift_with_drift_fields(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """show_drift=True should add Drift column and list differing fields."""
        svc = Service(id="d-1", name="drift-svc", host="drift.local")
        unified = _make_unified_list([], [], [(svc, True, ["host", "port"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        output = cast(StringIO, console.file).getvalue()
        assert "host" in output
        assert "port" in output
        assert "Drift" in output

    @pytest.mark.unit
    def test_format_unified_list_show_drift_synced_entity(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """show_drift=True on synced both-source entity should show checkmark."""
        svc = Service(id="s-1", name="synced-svc", host="synced.local")
        unified = _make_unified_list([], [], [(svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        output = cast(StringIO, console.file).getvalue()
        # Green checkmark or the text around it must appear
        assert "Drift" in output

    @pytest.mark.unit
    def test_format_unified_list_show_drift_gateway_only_dash(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """show_drift=True on gateway-only entity should show '-' for drift."""
        svc = Service(id="gw-2", name="gw-only", host="gw2.local")
        unified = _make_unified_list([svc], [], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        output = cast(StringIO, console.file).getvalue()
        assert "Drift" in output

    @pytest.mark.unit
    def test_format_unified_list_summary_gateway_only_count(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Summary should include 'Gateway only' when gateway_only_count > 0."""
        svc = Service(id="gw-3", name="gw-3", host="h.local")
        unified = _make_unified_list([svc], [], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "Gateway only" in output

    @pytest.mark.unit
    def test_format_unified_list_summary_konnect_only_count(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Summary should include 'Konnect only' when konnect_only_count > 0."""
        svc = Service(id="kn-2", name="kn-2", host="h.local")
        unified = _make_unified_list([], [svc], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "Konnect only" in output

    @pytest.mark.unit
    def test_format_unified_list_summary_in_both_count(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Summary should include 'Both' when in_both_count > 0."""
        svc = Service(id="b-2", name="b-2", host="h.local")
        unified = _make_unified_list([], [], [(svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "Both" in output

    @pytest.mark.unit
    def test_format_unified_list_summary_drift_count(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Summary should include 'With drift' when drift_count > 0 and show_drift=True."""
        svc = Service(id="d-2", name="d-2", host="h.local")
        unified = _make_unified_list([], [], [(svc, True, ["host"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        output = cast(StringIO, console.file).getvalue()
        assert "With drift" in output

    @pytest.mark.unit
    def test_format_unified_list_total_only_when_no_breakdowns(
        self,
        formatter: TableFormatter,
        console: Console,
    ) -> None:
        """Summary with only gateway entities should not include Konnect/Both lines."""
        svc = Service(id="gw-4", name="gw-4", host="h.local")
        unified = _make_unified_list([svc], [], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        output = cast(StringIO, console.file).getvalue()
        assert "Total:" in output
        assert "Konnect only" not in output


# ---------------------------------------------------------------------------
# TableFormatter._format_cell_value — uncovered branches (lines 293, 296)
# ---------------------------------------------------------------------------


class TestTableFormatterCellValueEdgeCases:
    """Tests for _format_cell_value edge cases (lines 293, 296)."""

    @pytest.fixture
    def console(self) -> Console:
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def formatter(self, console: Console) -> TableFormatter:
        return TableFormatter(console)

    @pytest.mark.unit
    def test_format_cell_value_dict_without_id_or_name(self, formatter: TableFormatter) -> None:
        """Dict without 'id' or 'name' key should be JSON-serialised (line 293)."""
        value: Any = {"foo": "bar", "count": 3}
        result = formatter._format_cell_value(value)
        parsed = json.loads(result)
        assert parsed == {"foo": "bar", "count": 3}

    @pytest.mark.unit
    def test_format_cell_value_empty_list_returns_dash(self, formatter: TableFormatter) -> None:
        """Empty list should return '-' (line 296)."""
        result = formatter._format_cell_value([])
        assert result == "-"


# ---------------------------------------------------------------------------
# JsonFormatter.format_unified_list (lines 366-391)
# ---------------------------------------------------------------------------


class TestJsonFormatterUnifiedList:
    """Tests for JsonFormatter.format_unified_list."""

    @pytest.fixture
    def console(self) -> Console:
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def formatter(self, console: Console) -> JsonFormatter:
        return JsonFormatter(console)

    @pytest.mark.unit
    def test_format_unified_list_structure(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """format_unified_list should output valid JSON with data and summary."""
        gw_svc = Service(id="gw-j1", name="gw-j1", host="h.local")
        kn_svc = Service(id="kn-j1", name="kn-j1", host="h.local")
        unified = _make_unified_list([gw_svc], [kn_svc], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        assert "data" in output
        assert "summary" in output
        assert output["summary"]["total"] == 2
        assert output["summary"]["gateway_only"] == 1
        assert output["summary"]["konnect_only"] == 1

    @pytest.mark.unit
    def test_format_unified_list_source_values(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """Each item should carry the correct 'source' value."""
        gw_svc = Service(id="gw-j2", name="gw-j2", host="h.local")
        unified = _make_unified_list([gw_svc], [], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        assert output["data"][0]["source"] == "gateway"

    @pytest.mark.unit
    def test_format_unified_list_includes_gateway_and_konnect_ids(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """Items should include gateway_id and konnect_id fields."""
        svc = Service(id="b-j1", name="b-j1", host="h.local")
        unified = _make_unified_list([], [], [(svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        item: Any = output["data"][0]
        assert "gateway_id" in item
        assert "konnect_id" in item

    @pytest.mark.unit
    def test_format_unified_list_show_drift_adds_drift_fields(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """show_drift=True should add has_drift and drift_fields when entity has drift."""
        svc = Service(id="d-j1", name="d-j1", host="h.local")
        unified = _make_unified_list([], [], [(svc, True, ["host", "port"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        item: Any = output["data"][0]
        assert item["has_drift"] is True
        assert "host" in item["drift_fields"]

    @pytest.mark.unit
    def test_format_unified_list_no_drift_fields_when_show_drift_false(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """show_drift=False should omit has_drift/drift_fields even for drifted entities."""
        svc = Service(id="d-j2", name="d-j2", host="h.local")
        unified = _make_unified_list([], [], [(svc, True, ["host"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=False)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        item: Any = output["data"][0]
        assert "has_drift" not in item

    @pytest.mark.unit
    def test_format_unified_list_summary_counts(
        self,
        formatter: JsonFormatter,
        console: Console,
    ) -> None:
        """Summary block should reflect synced and drift counts correctly."""
        synced_svc = Service(id="s-j1", name="s-j1", host="h.local")
        drift_svc = Service(id="d-j3", name="d-j3", host="h.local")
        unified = _make_unified_list(
            [], [], [(synced_svc, False, None), (drift_svc, True, ["host"])]
        )
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        output: Any = json.loads(raw)
        summary: Any = output["summary"]
        assert summary["in_both"] == 2
        assert summary["with_drift"] == 1
        assert summary["synced"] == 1


# ---------------------------------------------------------------------------
# YamlFormatter.format_unified_list (lines 433-458)
# ---------------------------------------------------------------------------


class TestYamlFormatterUnifiedList:
    """Tests for YamlFormatter.format_unified_list."""

    @pytest.fixture
    def console(self) -> Console:
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def formatter(self, console: Console) -> YamlFormatter:
        return YamlFormatter(console)

    @pytest.mark.unit
    def test_format_unified_list_valid_yaml(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """format_unified_list should produce parseable YAML."""
        gw_svc = Service(id="gw-y1", name="gw-y1", host="h.local")
        unified = _make_unified_list([gw_svc], [], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        assert "data" in parsed
        assert "summary" in parsed

    @pytest.mark.unit
    def test_format_unified_list_source_value_in_yaml(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """Each YAML item should carry the correct source value."""
        kn_svc = Service(id="kn-y1", name="kn-y1", host="h.local")
        unified = _make_unified_list([], [kn_svc], [])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        items: Any = parsed["data"]
        assert items[0]["source"] == "konnect"

    @pytest.mark.unit
    def test_format_unified_list_show_drift_adds_drift_info(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """show_drift=True should add has_drift and drift_fields to drifted items."""
        svc = Service(id="d-y1", name="d-y1", host="h.local")
        unified = _make_unified_list([], [], [(svc, True, ["host"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=True)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        item: Any = parsed["data"][0]
        assert item["has_drift"] is True
        assert "host" in item["drift_fields"]

    @pytest.mark.unit
    def test_format_unified_list_no_drift_info_when_show_drift_false(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """show_drift=False should omit drift fields from output."""
        svc = Service(id="d-y2", name="d-y2", host="h.local")
        unified = _make_unified_list([], [], [(svc, True, ["host"])])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns, show_drift=False)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        item: Any = parsed["data"][0]
        assert "has_drift" not in item

    @pytest.mark.unit
    def test_format_unified_list_summary_counts(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """YAML summary block should reflect all counters correctly."""
        gw_svc = Service(id="gw-y2", name="gw-y2", host="h.local")
        kn_svc = Service(id="kn-y2", name="kn-y2", host="h.local")
        both_svc = Service(id="b-y1", name="b-y1", host="h.local")
        unified = _make_unified_list([gw_svc], [kn_svc], [(both_svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        summary: Any = parsed["summary"]
        assert summary["total"] == 3
        assert summary["gateway_only"] == 1
        assert summary["konnect_only"] == 1
        assert summary["in_both"] == 1

    @pytest.mark.unit
    def test_format_unified_list_includes_gateway_and_konnect_ids(
        self,
        formatter: YamlFormatter,
        console: Console,
    ) -> None:
        """YAML items should include gateway_id and konnect_id fields."""
        svc = Service(id="b-y2", name="b-y2", host="h.local")
        unified = _make_unified_list([], [], [(svc, False, None)])
        columns = [("name", "Name")]

        formatter.format_unified_list(unified, columns)

        raw = strip_ansi(cast(StringIO, console.file).getvalue())
        parsed: Any = yaml.safe_load(raw)
        item: Any = parsed["data"][0]
        assert "gateway_id" in item
        assert "konnect_id" in item
