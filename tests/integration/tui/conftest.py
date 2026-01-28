"""Shared fixtures for TUI integration tests.

Provides reusable fixtures for conflict resolution TUI integration testing.
"""

from __future__ import annotations

from typing import Literal, Protocol

import pytest

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ConflictResolutionService,
)
from system_operations_manager.tui.apps.conflict_resolution.app import (
    ConflictResolutionApp,
)


class AppFactory(Protocol):
    """Protocol for the app_factory fixture."""

    def __call__(
        self,
        conflicts: list[Conflict],
        direction: Literal["push", "pull"] = "push",
        dry_run: bool = False,
    ) -> ConflictResolutionApp: ...


# ============================================================================
# Conflict Fixtures - Various scenarios
# ============================================================================


@pytest.fixture
def simple_conflict() -> Conflict:
    """Single-field drift conflict that is auto-mergeable.

    This conflict has only one field differing, making it suitable
    for auto-merge operations.
    """
    return Conflict(
        entity_type="services",
        entity_id="svc-simple",
        entity_name="simple-service",
        source_state={
            "host": "new.example.com",
            "port": 80,
            "name": "simple-service",
            "protocol": "http",
        },
        target_state={
            "host": "old.example.com",
            "port": 80,
            "name": "simple-service",
            "protocol": "http",
        },
        drift_fields=["host"],
        source_system_id="gw-svc-simple",
        target_system_id="kn-svc-simple",
        direction="push",
    )


@pytest.fixture
def multiple_field_conflict() -> Conflict:
    """Multiple-field drift conflict.

    This conflict has several fields differing, which may or may not
    be auto-mergeable depending on overlap.
    """
    return Conflict(
        entity_type="services",
        entity_id="svc-multi",
        entity_name="multi-field-service",
        source_state={"host": "api.new.com", "port": 8080, "timeout": 60},
        target_state={"host": "api.old.com", "port": 80, "timeout": 30},
        drift_fields=["host", "port", "timeout"],
        source_system_id="gw-svc-multi",
        target_system_id="kn-svc-multi",
        direction="push",
    )


@pytest.fixture
def overlapping_conflict() -> Conflict:
    """Conflict requiring manual merge due to overlapping changes.

    Both source and target have changed the same fields in different ways,
    requiring manual intervention to resolve.
    """
    return Conflict(
        entity_type="routes",
        entity_id="rt-overlap",
        entity_name="overlapping-route",
        source_state={"paths": ["/api/v2"], "hosts": ["api.new.com"]},
        target_state={"paths": ["/api/v1"], "hosts": ["api.old.com"]},
        drift_fields=["paths", "hosts"],
        source_system_id="gw-rt-overlap",
        target_system_id="kn-rt-overlap",
        direction="push",
    )


@pytest.fixture
def conflict_set_small() -> list[Conflict]:
    """Small set of 3 similar conflicts for multi-conflict tests.

    All conflicts are simple service conflicts that are individually
    auto-mergeable, useful for testing batch operations.
    """
    return [
        Conflict(
            entity_type="services",
            entity_id=f"svc-{i}",
            entity_name=f"service-{i}",
            source_state={
                "host": f"new-{i}.example.com",
                "port": 8000 + i,
                "name": f"service-{i}",
            },
            target_state={
                "host": f"old-{i}.example.com",
                "port": 80,
                "name": f"service-{i}",
            },
            drift_fields=["host", "port"],
            source_system_id=f"gw-svc-{i}",
            target_system_id=f"kn-svc-{i}",
            direction="push",
        )
        for i in range(3)
    ]


@pytest.fixture
def conflict_set_mixed() -> list[Conflict]:
    """Mixed conflict types for comprehensive testing.

    Includes a mix of auto-mergeable and non-auto-mergeable conflicts
    across different entity types.
    """
    return [
        # Service - simple auto-mergeable
        Conflict(
            entity_type="services",
            entity_id="svc-auto",
            entity_name="auto-merge-service",
            source_state={"host": "new.com", "port": 80, "timeout": 30},
            target_state={"host": "old.com", "port": 80, "timeout": 30},
            drift_fields=["host"],
            source_system_id="gw-svc-auto",
            target_system_id="kn-svc-auto",
            direction="push",
        ),
        # Route - multiple field differences
        Conflict(
            entity_type="routes",
            entity_id="rt-manual",
            entity_name="manual-merge-route",
            source_state={"paths": ["/new"], "methods": ["GET", "POST"]},
            target_state={"paths": ["/old"], "methods": ["GET"]},
            drift_fields=["paths", "methods"],
            source_system_id="gw-rt-manual",
            target_system_id="kn-rt-manual",
            direction="push",
        ),
        # Consumer - simple difference
        Conflict(
            entity_type="consumers",
            entity_id="con-simple",
            entity_name="simple-consumer",
            source_state={"username": "new-user", "custom_id": "id-123"},
            target_state={"username": "old-user", "custom_id": "id-123"},
            drift_fields=["username"],
            source_system_id="gw-con-simple",
            target_system_id="kn-con-simple",
            direction="push",
        ),
    ]


# ============================================================================
# App Factory Fixture
# ============================================================================


@pytest.fixture
def app_factory() -> AppFactory:
    """Factory fixture for creating ConflictResolutionApp instances.

    Usage:
        app = app_factory([conflict1, conflict2], direction="push")

    Returns:
        A callable that creates configured ConflictResolutionApp instances.
    """

    def _create_app(
        conflicts: list[Conflict],
        direction: Literal["push", "pull"] = "push",
        dry_run: bool = False,
    ) -> ConflictResolutionApp:
        return ConflictResolutionApp(
            conflicts=conflicts,
            direction=direction,
            dry_run=dry_run,
        )

    return _create_app


@pytest.fixture
def conflict_resolution_service() -> ConflictResolutionService:
    """Create a fresh ConflictResolutionService for testing."""
    return ConflictResolutionService()
