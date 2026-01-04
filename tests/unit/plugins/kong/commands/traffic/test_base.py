"""Unit tests for traffic command base utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer

from system_operations_manager.plugins.kong.commands.traffic.base import (
    find_plugin_for_scope,
    validate_scope,
)


class TestValidateScope:
    """Tests for validate_scope function."""

    @pytest.mark.unit
    def test_validate_scope_with_service(self) -> None:
        """validate_scope should pass when service is provided."""
        # Should not raise
        validate_scope(service="my-service", route=None)

    @pytest.mark.unit
    def test_validate_scope_with_route(self) -> None:
        """validate_scope should pass when route is provided."""
        # Should not raise
        validate_scope(service=None, route="my-route")

    @pytest.mark.unit
    def test_validate_scope_with_both(self) -> None:
        """validate_scope should pass when both are provided."""
        # Should not raise
        validate_scope(service="my-service", route="my-route")

    @pytest.mark.unit
    def test_validate_scope_without_either(self) -> None:
        """validate_scope should exit when neither is provided."""
        with pytest.raises(typer.Exit) as exc_info:
            validate_scope(service=None, route=None)
        assert exc_info.value.exit_code == 1


class TestFindPluginForScope:
    """Tests for find_plugin_for_scope function."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        """Create a mock plugin manager."""
        return MagicMock()

    @pytest.mark.unit
    def test_find_plugin_by_service_id(self, mock_manager: MagicMock) -> None:
        """find_plugin_for_scope should find plugin by service ID."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "service": {"id": "service-123"},
        }
        mock_manager.list.return_value = [mock_plugin]

        result = find_plugin_for_scope(mock_manager, "rate-limiting", service="service-123")

        assert result is not None
        assert result["id"] == "plugin-1"
        mock_manager.list.assert_called_once_with(name="rate-limiting")

    @pytest.mark.unit
    def test_find_plugin_by_service_name(self, mock_manager: MagicMock) -> None:
        """find_plugin_for_scope should find plugin by service name."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "service": {"id": "service-123", "name": "my-service"},
        }
        mock_manager.list.return_value = [mock_plugin]

        result = find_plugin_for_scope(mock_manager, "rate-limiting", service="my-service")

        assert result is not None
        assert result["id"] == "plugin-1"

    @pytest.mark.unit
    def test_find_plugin_by_route_id(self, mock_manager: MagicMock) -> None:
        """find_plugin_for_scope should find plugin by route ID."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "route": {"id": "route-456"},
        }
        mock_manager.list.return_value = [mock_plugin]

        result = find_plugin_for_scope(mock_manager, "rate-limiting", route="route-456")

        assert result is not None
        assert result["id"] == "plugin-1"

    @pytest.mark.unit
    def test_find_plugin_not_found(self, mock_manager: MagicMock) -> None:
        """find_plugin_for_scope should return None when not found."""
        mock_manager.list.return_value = []

        result = find_plugin_for_scope(mock_manager, "rate-limiting", service="nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_find_plugin_wrong_scope(self, mock_manager: MagicMock) -> None:
        """find_plugin_for_scope should return None for wrong scope."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "service": {"id": "different-service"},
        }
        mock_manager.list.return_value = [mock_plugin]

        result = find_plugin_for_scope(mock_manager, "rate-limiting", service="my-service")

        assert result is None
