"""Unit tests for Kubernetes TUI resource create screen."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.tui.apps.kubernetes.create_screen import (
    RESOURCE_FIELD_SPECS,
    ResourceCreateScreen,
    _parse_key_value_lines,
    _parse_port_lines,
)
from system_operations_manager.tui.apps.kubernetes.types import (
    CREATABLE_TYPES,
    ResourceType,
)


class TestParseKeyValueLines:
    @pytest.mark.unit
    def test_parse_simple(self) -> None:
        result = _parse_key_value_lines("key1=value1\nkey2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_empty(self) -> None:
        assert _parse_key_value_lines("") == {}

    @pytest.mark.unit
    def test_parse_skips_blank_lines(self) -> None:
        result = _parse_key_value_lines("key1=value1\n\nkey2=value2\n")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_skips_invalid_lines(self) -> None:
        result = _parse_key_value_lines("key1=value1\ninvalid_line\nkey2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_handles_equals_in_value(self) -> None:
        result = _parse_key_value_lines("key=val=ue")
        assert result == {"key": "val=ue"}


class TestParsePortLines:
    @pytest.mark.unit
    def test_parse_simple_port(self) -> None:
        result = _parse_port_lines("port=80")
        assert len(result) == 1
        assert result[0]["port"] == 80

    @pytest.mark.unit
    def test_parse_full_port(self) -> None:
        result = _parse_port_lines("port=80,target_port=8080,protocol=TCP,name=http")
        assert len(result) == 1
        assert result[0] == {"port": 80, "target_port": 8080, "protocol": "TCP", "name": "http"}

    @pytest.mark.unit
    def test_parse_multiple_ports(self) -> None:
        result = _parse_port_lines("port=80\nport=443")
        assert len(result) == 2

    @pytest.mark.unit
    def test_parse_empty(self) -> None:
        assert _parse_port_lines("") == []

    @pytest.mark.unit
    def test_parse_skips_lines_without_port(self) -> None:
        result = _parse_port_lines("target_port=8080")
        assert result == []


class TestResourceFieldSpecs:
    @pytest.mark.unit
    def test_all_creatable_types_have_specs(self) -> None:
        for rt in CREATABLE_TYPES:
            assert rt in RESOURCE_FIELD_SPECS, f"{rt} missing from RESOURCE_FIELD_SPECS"

    @pytest.mark.unit
    def test_each_type_has_name_field(self) -> None:
        for rt, specs in RESOURCE_FIELD_SPECS.items():
            names = [s.name for s in specs]
            assert "name" in names, f"{rt} missing 'name' field"

    @pytest.mark.unit
    def test_name_field_is_required(self) -> None:
        for rt, specs in RESOURCE_FIELD_SPECS.items():
            name_spec = next(s for s in specs if s.name == "name")
            assert name_spec.required, f"{rt} 'name' field should be required"


class TestResourceCreateScreen:
    @pytest.mark.unit
    def test_screen_stores_resource_type(self) -> None:
        mock_client = MagicMock()
        mock_client.default_namespace = "default"
        screen = ResourceCreateScreen(ResourceType.DEPLOYMENTS, mock_client)
        assert screen._resource_type == ResourceType.DEPLOYMENTS

    @pytest.mark.unit
    def test_resource_created_message(self) -> None:
        msg = ResourceCreateScreen.ResourceCreated(ResourceType.PODS, "test-pod")
        assert msg.resource_type == ResourceType.PODS
        assert msg.resource_name == "test-pod"
