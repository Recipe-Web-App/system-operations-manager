"""Unit tests for Kong OpenAPI sync models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.openapi import (
    SyncChange,
    SyncResult,
)


class TestSyncChange:
    """Tests for SyncChange model."""

    @pytest.mark.unit
    def test_strip_path_defaults_to_true(self) -> None:
        """strip_path should default to True when not specified."""
        change = SyncChange(
            operation="create",
            route_name="svc-users",
            path="/users",
            methods=["GET"],
        )
        assert change.strip_path is True

    @pytest.mark.unit
    def test_strip_path_false_preserved(self) -> None:
        """strip_path=False should be preserved on the model."""
        change = SyncChange(
            operation="create",
            route_name="svc-users",
            path="/users",
            methods=["GET"],
            strip_path=False,
        )
        assert change.strip_path is False

    @pytest.mark.unit
    def test_required_fields(self) -> None:
        """operation, route_name, and path are required."""
        with pytest.raises(Exception):
            SyncChange()  # type: ignore[call-arg]

        with pytest.raises(Exception):
            SyncChange(operation="create")  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_field_changes_for_updates(self) -> None:
        """field_changes should store (old, new) tuples."""
        change = SyncChange(
            operation="update",
            route_name="svc-users",
            path="/users",
            methods=["GET", "POST"],
            field_changes={"methods": (["GET"], ["GET", "POST"])},
        )
        assert change.field_changes is not None
        assert change.field_changes["methods"] == (["GET"], ["GET", "POST"])

    @pytest.mark.unit
    def test_breaking_with_reason(self) -> None:
        """Breaking changes should carry a reason."""
        change = SyncChange(
            operation="delete",
            route_name="svc-old",
            path="/old",
            methods=["GET"],
            is_breaking=True,
            breaking_reason="Route will be deleted",
        )
        assert change.is_breaking is True
        assert change.breaking_reason == "Route will be deleted"


class TestSyncResult:
    """Tests for SyncResult model."""

    def _make_change(
        self,
        operation: str = "create",
        *,
        is_breaking: bool = False,
    ) -> SyncChange:
        """Helper to create a SyncChange."""
        return SyncChange(
            operation=operation,  # type: ignore[arg-type]
            route_name="svc-test",
            path="/test",
            methods=["GET"],
            is_breaking=is_breaking,
        )

    @pytest.mark.unit
    def test_total_changes(self) -> None:
        """total_changes should sum creates + updates + deletes."""
        result = SyncResult(
            creates=[self._make_change("create"), self._make_change("create")],
            updates=[self._make_change("update")],
            deletes=[self._make_change("delete")],
            service_name="svc",
        )
        assert result.total_changes == 4

    @pytest.mark.unit
    def test_has_changes_true_and_false(self) -> None:
        """has_changes should reflect whether any changes exist."""
        empty = SyncResult(service_name="svc")
        assert empty.has_changes is False

        non_empty = SyncResult(
            creates=[self._make_change()],
            service_name="svc",
        )
        assert non_empty.has_changes is True

    @pytest.mark.unit
    def test_breaking_changes_filters_correctly(self) -> None:
        """breaking_changes should return only is_breaking=True items."""
        result = SyncResult(
            creates=[self._make_change("create", is_breaking=False)],
            updates=[self._make_change("update", is_breaking=True)],
            deletes=[
                self._make_change("delete", is_breaking=True),
                self._make_change("delete", is_breaking=False),
            ],
            service_name="svc",
        )
        breaking = result.breaking_changes
        assert len(breaking) == 2
        assert all(c.is_breaking for c in breaking)

    @pytest.mark.unit
    def test_has_breaking_changes(self) -> None:
        """has_breaking_changes should be True when breaking items exist."""
        no_breaking = SyncResult(
            creates=[self._make_change("create", is_breaking=False)],
            service_name="svc",
        )
        assert no_breaking.has_breaking_changes is False

        with_breaking = SyncResult(
            deletes=[self._make_change("delete", is_breaking=True)],
            service_name="svc",
        )
        assert with_breaking.has_breaking_changes is True
