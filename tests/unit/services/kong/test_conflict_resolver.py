"""Unit tests for the conflict resolution service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityBase
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ConflictResolutionService,
    Resolution,
    ResolutionAction,
    ResolutionPreview,
    generate_entity_diff,
    generate_side_by_side_diff,
)

# ============================================================================
# Fixtures
# ============================================================================


class MockServiceEntity(KongEntityBase):
    """Mock Kong service entity for testing."""

    name: str | None = None
    host: str | None = None
    port: int | None = None
    protocol: str | None = None
    path: str | None = None


@pytest.fixture
def gateway_entity() -> MockServiceEntity:
    """Create a mock Gateway entity."""
    return MockServiceEntity(
        id="gw-123",
        name="test-service",
        host="gateway.example.com",
        port=8000,
        protocol="http",
    )


@pytest.fixture
def konnect_entity() -> MockServiceEntity:
    """Create a mock Konnect entity with drift."""
    return MockServiceEntity(
        id="kn-456",
        name="test-service",
        host="konnect.example.com",  # Different host
        port=8000,
        protocol="https",  # Different protocol
    )


@pytest.fixture
def unified_entity_with_drift(
    gateway_entity: MockServiceEntity, konnect_entity: MockServiceEntity
) -> UnifiedEntity[MockServiceEntity]:
    """Create a UnifiedEntity with drift between sources."""
    return UnifiedEntity(
        entity=gateway_entity,
        source=EntitySource.BOTH,
        gateway_id="gw-123",
        konnect_id="kn-456",
        has_drift=True,
        drift_fields=["host", "protocol"],
        gateway_entity=gateway_entity,
        konnect_entity=konnect_entity,
    )


@pytest.fixture
def unified_entity_no_drift(
    gateway_entity: MockServiceEntity,
) -> UnifiedEntity[MockServiceEntity]:
    """Create a UnifiedEntity without drift."""
    return UnifiedEntity(
        entity=gateway_entity,
        source=EntitySource.BOTH,
        gateway_id="gw-123",
        konnect_id="kn-456",
        has_drift=False,
        drift_fields=None,
        gateway_entity=gateway_entity,
        konnect_entity=gateway_entity,  # Same entity
    )


@pytest.fixture
def conflict(gateway_entity: MockServiceEntity, konnect_entity: MockServiceEntity) -> Conflict:
    """Create a sample Conflict for testing."""
    return Conflict(
        entity_type="services",
        entity_id="gw-123",
        entity_name="test-service",
        source_state=gateway_entity.model_dump(),
        target_state=konnect_entity.model_dump(),
        drift_fields=["host", "protocol"],
        source_system_id="gw-123",
        target_system_id="kn-456",
        direction="push",
    )


@pytest.fixture
def service() -> ConflictResolutionService:
    """Create a ConflictResolutionService instance."""
    return ConflictResolutionService()


# ============================================================================
# Conflict Model Tests
# ============================================================================


class TestConflict:
    """Tests for the Conflict model."""

    def test_source_label_push(self, conflict: Conflict) -> None:
        """Test source_label returns Gateway for push direction."""
        assert conflict.source_label == "Gateway"

    def test_target_label_push(self, conflict: Conflict) -> None:
        """Test target_label returns Konnect for push direction."""
        assert conflict.target_label == "Konnect"

    def test_source_label_pull(
        self, gateway_entity: MockServiceEntity, konnect_entity: MockServiceEntity
    ) -> None:
        """Test source_label returns Konnect for pull direction."""
        conflict = Conflict(
            entity_type="services",
            entity_id="kn-456",
            entity_name="test-service",
            source_state=konnect_entity.model_dump(),
            target_state=gateway_entity.model_dump(),
            drift_fields=["host"],
            direction="pull",
        )
        assert conflict.source_label == "Konnect"
        assert conflict.target_label == "Gateway"

    def test_from_unified_entity_push(
        self, unified_entity_with_drift: UnifiedEntity[MockServiceEntity]
    ) -> None:
        """Test creating Conflict from UnifiedEntity for push."""
        conflict = Conflict.from_unified_entity(unified_entity_with_drift, "services", "push")

        assert conflict.entity_type == "services"
        assert conflict.entity_name == "test-service"
        assert conflict.direction == "push"
        assert conflict.drift_fields == ["host", "protocol"]
        assert conflict.source_state["host"] == "gateway.example.com"
        assert conflict.target_state["host"] == "konnect.example.com"

    def test_from_unified_entity_pull(
        self, unified_entity_with_drift: UnifiedEntity[MockServiceEntity]
    ) -> None:
        """Test creating Conflict from UnifiedEntity for pull."""
        conflict = Conflict.from_unified_entity(unified_entity_with_drift, "services", "pull")

        assert conflict.direction == "pull"
        # For pull, source is Konnect, target is Gateway
        assert conflict.source_state["host"] == "konnect.example.com"
        assert conflict.target_state["host"] == "gateway.example.com"

    def test_from_unified_entity_no_drift_raises(
        self, unified_entity_no_drift: UnifiedEntity[MockServiceEntity]
    ) -> None:
        """Test that creating Conflict from entity without drift raises."""
        with pytest.raises(ValueError, match="does not have drift"):
            Conflict.from_unified_entity(unified_entity_no_drift, "services", "push")


# ============================================================================
# ResolutionAction Enum Tests
# ============================================================================


class TestResolutionAction:
    """Tests for the ResolutionAction enum."""

    def test_merge_action_exists(self) -> None:
        """Test that MERGE action exists in enum."""
        assert hasattr(ResolutionAction, "MERGE")

    def test_merge_action_value(self) -> None:
        """Test that MERGE action has correct value."""
        assert ResolutionAction.MERGE.value == "merge"

    def test_all_actions_exist(self) -> None:
        """Test that all expected actions exist."""
        assert ResolutionAction.KEEP_SOURCE.value == "keep_source"
        assert ResolutionAction.KEEP_TARGET.value == "keep_target"
        assert ResolutionAction.SKIP.value == "skip"
        assert ResolutionAction.MERGE.value == "merge"


# ============================================================================
# Resolution Model Tests
# ============================================================================


class TestResolution:
    """Tests for the Resolution model."""

    def test_entity_key(self, conflict: Conflict) -> None:
        """Test entity_key property."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        assert resolution.entity_key == "services:test-service"

    def test_will_modify_target_keep_source(self, conflict: Conflict) -> None:
        """Test will_modify_target is True for KEEP_SOURCE."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        assert resolution.will_modify_target is True

    def test_will_modify_target_keep_target(self, conflict: Conflict) -> None:
        """Test will_modify_target is False for KEEP_TARGET."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_TARGET)
        assert resolution.will_modify_target is False

    def test_will_modify_target_skip(self, conflict: Conflict) -> None:
        """Test will_modify_target is False for SKIP."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.SKIP)
        assert resolution.will_modify_target is False

    def test_resolved_at_default(self, conflict: Conflict) -> None:
        """Test resolved_at is set to current time by default."""
        before = datetime.now(UTC)
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        after = datetime.now(UTC)

        assert before <= resolution.resolved_at <= after

    def test_merged_state_field_optional(self, conflict: Conflict) -> None:
        """Test merged_state field is optional."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        assert resolution.merged_state is None

    def test_merged_state_stores_dict(self, conflict: Conflict) -> None:
        """Test merged_state can store a dictionary."""
        merged = {"host": "merged.example.com", "port": 8080}
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.MERGE,
            merged_state=merged,
        )
        assert resolution.merged_state == merged
        assert resolution.merged_state["host"] == "merged.example.com"

    def test_will_modify_target_true_for_merge(self, conflict: Conflict) -> None:
        """Test will_modify_target is True for MERGE action."""
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.MERGE,
            merged_state={"host": "merged.example.com"},
        )
        assert resolution.will_modify_target is True

    def test_entity_key_for_merge_resolution(self, conflict: Conflict) -> None:
        """Test entity_key works correctly for merge resolution."""
        resolution = Resolution(
            conflict=conflict,
            action=ResolutionAction.MERGE,
            merged_state={"host": "merged.example.com"},
        )
        assert resolution.entity_key == "services:test-service"


# ============================================================================
# ConflictResolutionService Tests
# ============================================================================


class TestConflictResolutionService:
    """Tests for ConflictResolutionService."""

    def test_collect_conflicts(
        self,
        service: ConflictResolutionService,
        unified_entity_with_drift: UnifiedEntity[MockServiceEntity],
        unified_entity_no_drift: UnifiedEntity[MockServiceEntity],
    ) -> None:
        """Test collecting conflicts from entity lists."""
        entity_lists = {
            "services": UnifiedEntityList(
                entities=[unified_entity_with_drift, unified_entity_no_drift]
            )
        }

        conflicts = service.collect_conflicts(entity_lists, "push")

        # Should only include entity with drift
        assert len(conflicts) == 1
        assert conflicts[0].entity_name == "test-service"

    def test_collect_conflicts_multiple_types(
        self,
        service: ConflictResolutionService,
        unified_entity_with_drift: UnifiedEntity[MockServiceEntity],
    ) -> None:
        """Test collecting conflicts from multiple entity types."""
        # Create another entity for routes
        route_entity = UnifiedEntity(
            entity=MockServiceEntity(id="rt-1", name="test-route", path="/api"),
            source=EntitySource.BOTH,
            gateway_id="rt-gw-1",
            konnect_id="rt-kn-1",
            has_drift=True,
            drift_fields=["path"],
            gateway_entity=MockServiceEntity(id="rt-1", name="test-route", path="/api"),
            konnect_entity=MockServiceEntity(id="rt-1", name="test-route", path="/api/v2"),
        )

        entity_lists = {
            "services": UnifiedEntityList(entities=[unified_entity_with_drift]),
            "routes": UnifiedEntityList(entities=[route_entity]),
        }

        conflicts = service.collect_conflicts(entity_lists, "push")

        assert len(conflicts) == 2
        entity_types = {c.entity_type for c in conflicts}
        assert entity_types == {"services", "routes"}

    def test_set_and_get_resolution(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test setting and getting a resolution."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        service.set_resolution(resolution)

        retrieved = service.get_resolution(conflict)
        assert retrieved is not None
        assert retrieved.action == ResolutionAction.KEEP_SOURCE

    def test_get_resolution_not_found(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test getting a resolution that doesn't exist."""
        retrieved = service.get_resolution(conflict)
        assert retrieved is None

    def test_get_all_resolutions(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test getting all resolutions."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        service.set_resolution(resolution)

        all_resolutions = service.get_all_resolutions()
        assert len(all_resolutions) == 1
        assert all_resolutions[0].action == ResolutionAction.KEEP_SOURCE

    def test_clear_resolutions(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test clearing all resolutions."""
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        service.set_resolution(resolution)

        service.clear_resolutions()

        assert service.get_resolution(conflict) is None
        assert len(service.get_all_resolutions()) == 0

    def test_get_conflict_summary(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test getting conflict summary."""
        # Create another conflict
        conflict2 = Conflict(
            entity_type="routes",
            entity_id="rt-1",
            entity_name="test-route",
            source_state={"path": "/api"},
            target_state={"path": "/api/v2"},
            drift_fields=["path"],
            direction="push",
        )

        conflicts = [conflict, conflict2]

        # Resolve one
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)
        service.set_resolution(resolution)

        summary = service.get_conflict_summary(conflicts)

        assert summary.total == 2
        assert summary.resolved == 1
        assert summary.pending == 1
        assert summary.by_type == {"services": 1, "routes": 1}

    def test_build_preview(self, service: ConflictResolutionService, conflict: Conflict) -> None:
        """Test building resolution preview."""
        conflict2 = Conflict(
            entity_type="routes",
            entity_id="rt-1",
            entity_name="test-route",
            source_state={},
            target_state={},
            drift_fields=["path"],
            direction="push",
        )

        resolutions = [
            Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE),
            Resolution(conflict=conflict2, action=ResolutionAction.SKIP),
        ]

        preview = service.build_preview(resolutions)

        assert preview.update_count == 1
        assert preview.skip_count == 1
        assert ("services", "test-service") in preview.will_update
        assert ("routes", "test-route") in preview.will_skip

    def test_apply_batch_resolution(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test applying batch resolution."""
        conflict2 = Conflict(
            entity_type="services",
            entity_id="svc-2",
            entity_name="another-service",
            source_state={},
            target_state={},
            drift_fields=["host"],
            direction="push",
        )

        conflicts = [conflict, conflict2]

        count = service.apply_batch_resolution(conflicts, ResolutionAction.KEEP_TARGET)

        assert count == 2
        res1 = service.get_resolution(conflict)
        res2 = service.get_resolution(conflict2)
        assert res1 is not None
        assert res2 is not None
        assert res1.action == ResolutionAction.KEEP_TARGET
        assert res2.action == ResolutionAction.KEEP_TARGET

    def test_apply_batch_resolution_with_type_filter(
        self, service: ConflictResolutionService, conflict: Conflict
    ) -> None:
        """Test applying batch resolution with entity type filter."""
        route_conflict = Conflict(
            entity_type="routes",
            entity_id="rt-1",
            entity_name="test-route",
            source_state={},
            target_state={},
            drift_fields=["path"],
            direction="push",
        )

        conflicts = [conflict, route_conflict]

        count = service.apply_batch_resolution(
            conflicts, ResolutionAction.KEEP_SOURCE, entity_type="services"
        )

        assert count == 1
        res = service.get_resolution(conflict)
        assert res is not None
        assert res.action == ResolutionAction.KEEP_SOURCE
        assert service.get_resolution(route_conflict) is None


# ============================================================================
# Diff Generation Tests
# ============================================================================


class TestDiffGeneration:
    """Tests for diff generation utilities."""

    def test_generate_entity_diff(self) -> None:
        """Test generating unified diff."""
        source = {"name": "test", "host": "new.example.com", "port": 8000}
        target = {"name": "test", "host": "old.example.com", "port": 8000}

        diff_lines = generate_entity_diff(source, target)

        # Should have diff header and changes
        assert len(diff_lines) > 0
        # Check for the changed line
        diff_text = "".join(diff_lines)
        assert "new.example.com" in diff_text
        assert "old.example.com" in diff_text

    def test_generate_entity_diff_no_changes(self) -> None:
        """Test generating diff when states are identical."""
        state = {"name": "test", "host": "example.com"}

        diff_lines = generate_entity_diff(state, state)

        # Should be empty or minimal (no changes)
        # unified_diff returns empty iterator when files are identical
        assert len(diff_lines) == 0

    def test_generate_side_by_side_diff(self) -> None:
        """Test generating side-by-side diff."""
        source = {"name": "test", "host": "new.example.com"}
        target = {"name": "test", "host": "old.example.com"}

        diff_lines = generate_side_by_side_diff(source, target)

        # Should have tuples of (left, marker, right)
        assert len(diff_lines) > 0
        assert all(len(line) == 3 for line in diff_lines)

        # Check markers
        markers = [line[1] for line in diff_lines]
        # Should have at least one difference marker
        assert "|" in markers or "<" in markers or ">" in markers

    def test_generate_side_by_side_diff_identical(self) -> None:
        """Test side-by-side diff with identical states."""
        state = {"name": "test", "host": "example.com"}

        diff_lines = generate_side_by_side_diff(state, state)

        # All markers should be space (equal)
        for left, marker, right in diff_lines:
            assert marker == " "
            assert left == right


# ============================================================================
# ResolutionPreview Tests
# ============================================================================


class TestResolutionPreview:
    """Tests for ResolutionPreview model."""

    def test_update_count(self) -> None:
        """Test update_count property."""
        preview = ResolutionPreview(
            will_update=[("services", "svc1"), ("services", "svc2")],
            will_skip=[("routes", "rt1")],
        )
        assert preview.update_count == 2

    def test_skip_count(self) -> None:
        """Test skip_count property."""
        preview = ResolutionPreview(
            will_update=[("services", "svc1")],
            will_skip=[("routes", "rt1"), ("routes", "rt2")],
        )
        assert preview.skip_count == 2

    def test_empty_preview(self) -> None:
        """Test empty preview."""
        preview = ResolutionPreview()
        assert preview.update_count == 0
        assert preview.skip_count == 0

    def test_merge_count(self) -> None:
        """Test merge_count property."""
        preview = ResolutionPreview(
            will_update=[("services", "svc1")],
            will_skip=[("routes", "rt1")],
            will_merge=[("services", "svc2"), ("services", "svc3")],
        )
        assert preview.merge_count == 2

    def test_will_merge_in_preview(self) -> None:
        """Test will_merge list in preview."""
        preview = ResolutionPreview(
            will_merge=[("services", "merged-service")],
        )
        assert ("services", "merged-service") in preview.will_merge
        assert preview.merge_count == 1
