"""Unit tests for unified entity models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
    detect_drift,
    merge_entities,
)


class TestEntitySource:
    """Tests for EntitySource enum."""

    @pytest.mark.unit
    def test_gateway_value(self) -> None:
        """GATEWAY should have value 'gateway'."""
        assert EntitySource.GATEWAY.value == "gateway"

    @pytest.mark.unit
    def test_konnect_value(self) -> None:
        """KONNECT should have value 'konnect'."""
        assert EntitySource.KONNECT.value == "konnect"

    @pytest.mark.unit
    def test_both_value(self) -> None:
        """BOTH should have value 'both'."""
        assert EntitySource.BOTH.value == "both"

    @pytest.mark.unit
    def test_string_conversion(self) -> None:
        """EntitySource should be usable as string."""
        assert str(EntitySource.GATEWAY) == "EntitySource.GATEWAY"
        assert EntitySource.GATEWAY.value == "gateway"


class TestUnifiedEntity:
    """Tests for UnifiedEntity model."""

    @pytest.mark.unit
    def test_create_gateway_entity(self) -> None:
        """Should create entity with gateway source."""
        service = Service(name="test-service", host="test.local")
        unified = UnifiedEntity(
            entity=service,
            source=EntitySource.GATEWAY,
            gateway_id="gw-123",
        )

        assert unified.entity.name == "test-service"
        assert unified.source == EntitySource.GATEWAY
        assert unified.gateway_id == "gw-123"
        assert unified.konnect_id is None
        assert unified.has_drift is False
        assert unified.drift_fields is None

    @pytest.mark.unit
    def test_create_konnect_entity(self) -> None:
        """Should create entity with konnect source."""
        service = Service(name="test-service", host="test.local")
        unified = UnifiedEntity(
            entity=service,
            source=EntitySource.KONNECT,
            konnect_id="kon-456",
        )

        assert unified.source == EntitySource.KONNECT
        assert unified.konnect_id == "kon-456"
        assert unified.gateway_id is None

    @pytest.mark.unit
    def test_create_both_entity_with_drift(self) -> None:
        """Should create entity with both sources and drift info."""
        service = Service(name="test-service", host="test.local")
        unified = UnifiedEntity(
            entity=service,
            source=EntitySource.BOTH,
            gateway_id="gw-123",
            konnect_id="kon-456",
            has_drift=True,
            drift_fields=["host", "port"],
        )

        assert unified.source == EntitySource.BOTH
        assert unified.gateway_id == "gw-123"
        assert unified.konnect_id == "kon-456"
        assert unified.has_drift is True
        assert unified.drift_fields == ["host", "port"]

    @pytest.mark.unit
    def test_name_property(self) -> None:
        """name property should return entity name if available."""
        service = Service(name="my-service", host="test.local")
        unified = UnifiedEntity(entity=service, source=EntitySource.GATEWAY)

        assert unified.name == "my-service"

    @pytest.mark.unit
    def test_identifier_returns_name(self) -> None:
        """identifier should return name when available."""
        service = Service(name="my-service", host="test.local")
        unified = UnifiedEntity(entity=service, source=EntitySource.GATEWAY)

        assert unified.identifier == "my-service"

    @pytest.mark.unit
    def test_identifier_returns_gateway_id(self) -> None:
        """identifier should return gateway_id when name not available."""
        service = Service(host="test.local")  # No name
        unified = UnifiedEntity(entity=service, source=EntitySource.GATEWAY, gateway_id="gw-123")

        assert unified.identifier == "gw-123"

    @pytest.mark.unit
    def test_identifier_returns_konnect_id(self) -> None:
        """identifier should return konnect_id as last resort."""
        service = Service(host="test.local")  # No name
        unified = UnifiedEntity(entity=service, source=EntitySource.KONNECT, konnect_id="kon-456")

        assert unified.identifier == "kon-456"


class TestUnifiedEntityList:
    """Tests for UnifiedEntityList model."""

    @pytest.fixture
    def sample_list(self) -> UnifiedEntityList[Service]:
        """Create a sample unified entity list."""
        gw_service = Service(name="gw-only", host="gw.local")
        kon_service = Service(name="kon-only", host="kon.local")
        both_synced = Service(name="synced", host="synced.local")
        both_drifted = Service(name="drifted", host="gateway.local")

        return UnifiedEntityList(
            entities=[
                UnifiedEntity(
                    entity=gw_service,
                    source=EntitySource.GATEWAY,
                    gateway_id="gw-1",
                ),
                UnifiedEntity(
                    entity=kon_service,
                    source=EntitySource.KONNECT,
                    konnect_id="kon-1",
                ),
                UnifiedEntity(
                    entity=both_synced,
                    source=EntitySource.BOTH,
                    gateway_id="gw-2",
                    konnect_id="kon-2",
                    has_drift=False,
                ),
                UnifiedEntity(
                    entity=both_drifted,
                    source=EntitySource.BOTH,
                    gateway_id="gw-3",
                    konnect_id="kon-3",
                    has_drift=True,
                    drift_fields=["host"],
                ),
            ]
        )

    @pytest.mark.unit
    def test_len(self, sample_list: UnifiedEntityList[Service]) -> None:
        """__len__ should return entity count."""
        assert len(sample_list) == 4

    @pytest.mark.unit
    def test_gateway_only(self, sample_list: UnifiedEntityList[Service]) -> None:
        """gateway_only should return only gateway entities."""
        gw_only = sample_list.gateway_only
        assert len(gw_only) == 1
        assert gw_only[0].entity.name == "gw-only"

    @pytest.mark.unit
    def test_konnect_only(self, sample_list: UnifiedEntityList[Service]) -> None:
        """konnect_only should return only konnect entities."""
        kon_only = sample_list.konnect_only
        assert len(kon_only) == 1
        assert kon_only[0].entity.name == "kon-only"

    @pytest.mark.unit
    def test_in_both(self, sample_list: UnifiedEntityList[Service]) -> None:
        """in_both should return entities in both sources."""
        in_both = sample_list.in_both
        assert len(in_both) == 2

    @pytest.mark.unit
    def test_with_drift(self, sample_list: UnifiedEntityList[Service]) -> None:
        """with_drift should return entities with drift."""
        drifted = sample_list.with_drift
        assert len(drifted) == 1
        assert drifted[0].entity.name == "drifted"

    @pytest.mark.unit
    def test_synced(self, sample_list: UnifiedEntityList[Service]) -> None:
        """synced should return entities in both without drift."""
        synced = sample_list.synced
        assert len(synced) == 1
        assert synced[0].entity.name == "synced"

    @pytest.mark.unit
    def test_counts(self, sample_list: UnifiedEntityList[Service]) -> None:
        """Count properties should return correct values."""
        assert sample_list.gateway_only_count == 1
        assert sample_list.konnect_only_count == 1
        assert sample_list.in_both_count == 2
        assert sample_list.drift_count == 1
        assert sample_list.synced_count == 1

    @pytest.mark.unit
    def test_filter_by_source_gateway(self, sample_list: UnifiedEntityList[Service]) -> None:
        """filter_by_source should filter by gateway."""
        filtered = sample_list.filter_by_source(EntitySource.GATEWAY)
        assert len(filtered) == 1
        assert filtered.entities[0].source == EntitySource.GATEWAY

    @pytest.mark.unit
    def test_filter_by_source_string(self, sample_list: UnifiedEntityList[Service]) -> None:
        """filter_by_source should accept string source."""
        filtered = sample_list.filter_by_source("konnect")
        assert len(filtered) == 1
        assert filtered.entities[0].source == EntitySource.KONNECT


class TestDetectDrift:
    """Tests for detect_drift function."""

    @pytest.mark.unit
    def test_no_drift_identical_entities(self) -> None:
        """Should detect no drift for identical entities."""
        gw = Service(name="test", host="test.local", port=80)
        kon = Service(name="test", host="test.local", port=80)

        has_drift, fields = detect_drift(gw, kon)

        assert has_drift is False
        assert fields == []

    @pytest.mark.unit
    def test_drift_different_host(self) -> None:
        """Should detect drift when host differs."""
        gw = Service(name="test", host="gateway.local", port=80)
        kon = Service(name="test", host="konnect.local", port=80)

        has_drift, fields = detect_drift(gw, kon)

        assert has_drift is True
        assert "host" in fields

    @pytest.mark.unit
    def test_drift_multiple_fields(self) -> None:
        """Should detect multiple differing fields."""
        gw = Service(name="test", host="gateway.local", port=80, protocol="http")
        kon = Service(name="test", host="konnect.local", port=8080, protocol="http")

        has_drift, fields = detect_drift(gw, kon)

        assert has_drift is True
        assert "host" in fields
        assert "port" in fields
        assert len(fields) == 2

    @pytest.mark.unit
    def test_no_drift_when_gateway_none(self) -> None:
        """Should return no drift when gateway entity is None."""
        kon = Service(name="test", host="test.local")

        has_drift, fields = detect_drift(None, kon)

        assert has_drift is False
        assert fields == []

    @pytest.mark.unit
    def test_no_drift_when_konnect_none(self) -> None:
        """Should return no drift when konnect entity is None."""
        gw = Service(name="test", host="test.local")

        has_drift, fields = detect_drift(gw, None)

        assert has_drift is False
        assert fields == []

    @pytest.mark.unit
    def test_excludes_id_field(self) -> None:
        """Should exclude id field from comparison."""
        gw = Service(id="gw-123", name="test", host="test.local")
        kon = Service(id="kon-456", name="test", host="test.local")

        has_drift, fields = detect_drift(gw, kon)

        assert has_drift is False
        assert "id" not in fields

    @pytest.mark.unit
    def test_compare_specific_fields(self) -> None:
        """Should only compare specified fields."""
        gw = Service(name="test", host="gateway.local", port=80)
        kon = Service(name="test", host="konnect.local", port=8080)

        # Only compare host
        has_drift, fields = detect_drift(gw, kon, compare_fields=["host"])

        assert has_drift is True
        assert fields == ["host"]
        assert "port" not in fields


class TestMergeEntities:
    """Tests for merge_entities function."""

    @pytest.mark.unit
    def test_merge_gateway_only(self) -> None:
        """Should include gateway-only entities."""
        gw_services = [Service(name="gw-only", host="gw.local")]
        kon_services: list[Service] = []

        result = merge_entities(gw_services, kon_services)

        assert len(result) == 1
        assert result.entities[0].source == EntitySource.GATEWAY
        assert result.entities[0].entity.name == "gw-only"

    @pytest.mark.unit
    def test_merge_konnect_only(self) -> None:
        """Should include konnect-only entities."""
        gw_services: list[Service] = []
        kon_services = [Service(name="kon-only", host="kon.local")]

        result = merge_entities(gw_services, kon_services)

        assert len(result) == 1
        assert result.entities[0].source == EntitySource.KONNECT
        assert result.entities[0].entity.name == "kon-only"

    @pytest.mark.unit
    def test_merge_matching_no_drift(self) -> None:
        """Should merge matching entities without drift."""
        gw_services = [Service(id="gw-1", name="shared", host="shared.local")]
        kon_services = [Service(id="kon-1", name="shared", host="shared.local")]

        result = merge_entities(gw_services, kon_services)

        assert len(result) == 1
        assert result.entities[0].source == EntitySource.BOTH
        assert result.entities[0].has_drift is False
        assert result.entities[0].gateway_id == "gw-1"
        assert result.entities[0].konnect_id == "kon-1"

    @pytest.mark.unit
    def test_merge_matching_with_drift(self) -> None:
        """Should merge matching entities with drift detection."""
        gw_services = [Service(id="gw-1", name="shared", host="gateway.local")]
        kon_services = [Service(id="kon-1", name="shared", host="konnect.local")]

        result = merge_entities(gw_services, kon_services)

        assert len(result) == 1
        assert result.entities[0].source == EntitySource.BOTH
        assert result.entities[0].has_drift is True
        assert "host" in (result.entities[0].drift_fields or [])

    @pytest.mark.unit
    def test_merge_mixed(self) -> None:
        """Should correctly merge mixed entity sets."""
        gw_services = [
            Service(id="gw-1", name="gw-only", host="gw.local"),
            Service(id="gw-2", name="shared", host="shared.local"),
        ]
        kon_services = [
            Service(id="kon-1", name="shared", host="shared.local"),
            Service(id="kon-2", name="kon-only", host="kon.local"),
        ]

        result = merge_entities(gw_services, kon_services)

        assert len(result) == 3
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_merge_sorted_by_key(self) -> None:
        """Should return entities sorted by key field."""
        gw_services = [
            Service(name="zebra", host="z.local"),
            Service(name="alpha", host="a.local"),
        ]
        kon_services: list[Service] = []

        result = merge_entities(gw_services, kon_services)

        names = [e.entity.name for e in result.entities]
        assert names == ["alpha", "zebra"]
