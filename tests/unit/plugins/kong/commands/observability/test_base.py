"""Unit tests for observability base utilities."""

from __future__ import annotations

import pytest
import typer

from system_operations_manager.plugins.kong.commands.observability.base import (
    validate_scope,
    validate_scope_optional,
)


@pytest.mark.unit
class TestValidateScope:
    """Tests for validate_scope function."""

    def test_raises_exit_when_no_scope_provided(self) -> None:
        """validate_scope should exit when no service, route, or global given."""
        with pytest.raises(typer.Exit) as exc_info:
            validate_scope(service=None, route=None, global_scope=False)
        assert exc_info.value.exit_code == 1

    def test_passes_when_service_provided(self) -> None:
        """validate_scope should not raise when service is provided."""
        validate_scope(service="my-service", route=None, global_scope=False)

    def test_passes_when_route_provided(self) -> None:
        """validate_scope should not raise when route is provided."""
        validate_scope(service=None, route="my-route", global_scope=False)

    def test_passes_when_global_scope_provided(self) -> None:
        """validate_scope should not raise when global_scope is True."""
        validate_scope(service=None, route=None, global_scope=True)


@pytest.mark.unit
class TestValidateScopeOptional:
    """Tests for validate_scope_optional function."""

    def test_raises_exit_when_neither_provided(self) -> None:
        """validate_scope_optional should exit when neither service nor route given."""
        with pytest.raises(typer.Exit) as exc_info:
            validate_scope_optional(service=None, route=None)
        assert exc_info.value.exit_code == 1

    def test_passes_when_service_provided(self) -> None:
        """validate_scope_optional should not raise when service is provided."""
        validate_scope_optional(service="my-service", route=None)

    def test_passes_when_route_provided(self) -> None:
        """validate_scope_optional should not raise when route is provided."""
        validate_scope_optional(service=None, route="my-route")

    def test_passes_when_both_provided(self) -> None:
        """validate_scope_optional should not raise when both are provided."""
        validate_scope_optional(service="my-service", route="my-route")
