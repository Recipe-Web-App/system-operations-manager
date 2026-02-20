"""Unit tests for sync helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.plugins.kong.commands.sync import (
    _build_service_id_map,
    _pull_entity_type,
    _push_entity_type,
    _record_skipped_resolutions,
    _remap_route_service_ref,
)
from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    Resolution,
    ResolutionAction,
)

# ===========================================================================
# _record_skipped_resolutions
# ===========================================================================


@pytest.mark.unit
class TestRecordSkippedResolutions:
    """Tests for _record_skipped_resolutions."""

    def _make_conflict(
        self,
        entity_type: str = "services",
        entity_id: str = "svc-1",
        entity_name: str = "my-api",
        drift_fields: list[str] | None = None,
    ) -> Conflict:
        return Conflict(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            source_state={"name": entity_name},
            target_state={"name": entity_name},
            drift_fields=drift_fields or ["host"],
            direction="push",
        )

    def test_records_keep_target_resolutions(self) -> None:
        conflict = self._make_conflict()
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_TARGET)

        audit_service = MagicMock()
        _record_skipped_resolutions([resolution], "push", audit_service, "sync-123", dry_run=False)
        audit_service.record.assert_called_once()

    def test_records_skip_resolutions(self) -> None:
        conflict = self._make_conflict(
            entity_type="routes", entity_id="rt-1", entity_name="my-route"
        )
        resolution = Resolution(conflict=conflict, action=ResolutionAction.SKIP)

        audit_service = MagicMock()
        _record_skipped_resolutions([resolution], "pull", audit_service, "sync-456", dry_run=True)
        audit_service.record.assert_called_once()

    def test_ignores_keep_source_resolutions(self) -> None:
        conflict = self._make_conflict()
        resolution = Resolution(conflict=conflict, action=ResolutionAction.KEEP_SOURCE)

        audit_service = MagicMock()
        _record_skipped_resolutions([resolution], "push", audit_service, "sync-123", dry_run=False)
        audit_service.record.assert_not_called()

    def test_empty_resolutions(self) -> None:
        audit_service = MagicMock()
        _record_skipped_resolutions([], "push", audit_service, "sync-123", dry_run=False)
        audit_service.record.assert_not_called()


# ===========================================================================
# _build_service_id_map
# ===========================================================================


@pytest.mark.unit
class TestBuildServiceIdMap:
    """Tests for _build_service_id_map."""

    def test_maps_synced_services(self) -> None:
        mock_unified = MagicMock()
        synced_entity = MagicMock()
        synced_entity.gateway_id = "gw-svc-1"
        synced_entity.konnect_id = "k-svc-1"
        synced_entity.identifier = "my-api"

        services_list = MagicMock()
        services_list.synced = [synced_entity]
        services_list.with_drift = []
        services_list.konnect_only = []
        mock_unified.list_services.return_value = services_list

        result = _build_service_id_map(mock_unified)
        assert result["gw-svc-1"] == "k-svc-1"
        assert result["my-api"] == "k-svc-1"

    def test_maps_drifted_services(self) -> None:
        mock_unified = MagicMock()
        drifted_entity = MagicMock()
        drifted_entity.gateway_id = "gw-svc-2"
        drifted_entity.konnect_id = "k-svc-2"
        drifted_entity.identifier = "drifted-api"

        services_list = MagicMock()
        services_list.synced = []
        services_list.with_drift = [drifted_entity]
        services_list.konnect_only = []
        mock_unified.list_services.return_value = services_list

        result = _build_service_id_map(mock_unified)
        assert result["gw-svc-2"] == "k-svc-2"
        assert result["drifted-api"] == "k-svc-2"

    def test_maps_konnect_only_services(self) -> None:
        mock_unified = MagicMock()
        konnect_entity = MagicMock()
        konnect_entity.identifier = "konnect-only-api"
        konnect_entity.konnect_id = "k-svc-3"

        services_list = MagicMock()
        services_list.synced = []
        services_list.with_drift = []
        services_list.konnect_only = [konnect_entity]
        mock_unified.list_services.return_value = services_list

        result = _build_service_id_map(mock_unified)
        assert result["konnect-only-api"] == "k-svc-3"

    def test_empty_services(self) -> None:
        mock_unified = MagicMock()
        services_list = MagicMock()
        services_list.synced = []
        services_list.with_drift = []
        services_list.konnect_only = []
        mock_unified.list_services.return_value = services_list

        result = _build_service_id_map(mock_unified)
        assert result == {}


# ===========================================================================
# _remap_route_service_ref
# ===========================================================================


@pytest.mark.unit
class TestRemapRouteServiceRef:
    """Tests for _remap_route_service_ref."""

    def test_remaps_by_id(self) -> None:
        entity = MagicMock()
        entity.service.id = "gw-svc-1"
        entity.service.name = None

        service_map = {"gw-svc-1": "k-svc-1"}
        result = _remap_route_service_ref(entity, service_map)
        assert result.service is not None

    def test_remaps_by_name(self) -> None:
        entity = MagicMock()
        entity.service.id = None
        entity.service.name = "my-api"

        service_map = {"my-api": "k-svc-1"}
        result = _remap_route_service_ref(entity, service_map)
        assert result.service is not None

    def test_no_remap_when_no_match(self) -> None:
        entity = MagicMock()
        entity.service.id = "unknown-id"
        entity.service.name = "unknown-name"

        service_map = {"gw-svc-1": "k-svc-1"}
        original_service = entity.service
        result = _remap_route_service_ref(entity, service_map)
        # service should remain unchanged
        assert result.service is original_service

    def test_no_service_attribute(self) -> None:
        entity = MagicMock(spec=[])  # No attributes
        result = _remap_route_service_ref(entity, {"a": "b"})
        assert result is entity

    def test_service_is_none(self) -> None:
        entity = MagicMock()
        entity.service = None
        result = _remap_route_service_ref(entity, {"a": "b"})
        assert result is entity


# ===========================================================================
# _push_entity_type
# ===========================================================================


def _make_gateway_only_entity(
    entity_type: str = "services",
    gateway_id: str = "gw-1",
    name: str = "test-entity",
) -> UnifiedEntity[Service]:
    """Create a gateway-only unified entity."""
    svc = Service(id=gateway_id, name=name, host="local")
    return UnifiedEntity(
        entity=svc,
        source=EntitySource.GATEWAY,
        gateway_id=gateway_id,
        konnect_id=None,
        has_drift=False,
        gateway_entity=svc,
    )


def _make_drifted_entity(
    gateway_id: str = "gw-1",
    konnect_id: str = "k-1",
    name: str = "test-entity",
    drift_fields: list[str] | None = None,
) -> UnifiedEntity[Service]:
    """Create a drifted unified entity."""
    gw_svc = Service(id=gateway_id, name=name, host="new-host")
    k_svc = Service(id=konnect_id, name=name, host="old-host")
    return UnifiedEntity(
        entity=gw_svc,
        source=EntitySource.BOTH,
        gateway_id=gateway_id,
        konnect_id=konnect_id,
        has_drift=True,
        drift_fields=drift_fields or ["host"],
        gateway_entity=gw_svc,
        konnect_entity=k_svc,
    )


@pytest.mark.unit
class TestPushEntityType:
    """Tests for _push_entity_type."""

    def test_push_creates_gateway_only_entities(self) -> None:
        mock_unified = MagicMock()
        entity = _make_gateway_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.return_value = Service(name="created", host="local")
        konnect_managers = {"services": manager}

        created, updated, errors = _push_entity_type(
            "services", mock_unified, konnect_managers, dry_run=False
        )
        assert created == 1
        assert updated == 0
        assert errors == 0
        manager.create.assert_called_once()

    def test_push_dry_run(self) -> None:
        mock_unified = MagicMock()
        entity = _make_gateway_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        konnect_managers = {"services": manager}

        created, _updated, _errors = _push_entity_type(
            "services", mock_unified, konnect_managers, dry_run=True
        )
        assert created == 1
        manager.create.assert_not_called()

    def test_push_updates_drifted_entities(self) -> None:
        mock_unified = MagicMock()
        entity = _make_drifted_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.update.return_value = Service(name="updated", host="new-host")
        konnect_managers = {"services": manager}

        _created, updated, _errors = _push_entity_type(
            "services", mock_unified, konnect_managers, dry_run=False
        )
        assert updated == 1
        manager.update.assert_called_once()

    def test_push_update_dry_run_with_audit(self) -> None:
        mock_unified = MagicMock()
        entity = _make_drifted_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        konnect_managers = {"services": manager}
        audit_service = MagicMock()

        _created, updated, _errors = _push_entity_type(
            "services",
            mock_unified,
            konnect_managers,
            dry_run=True,
            audit_service=audit_service,
            sync_id="sync-123",
        )
        assert updated == 1
        audit_service.record.assert_called()

    def test_push_create_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_gateway_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.side_effect = RuntimeError("API error")
        konnect_managers = {"services": manager}

        created, _updated, errors = _push_entity_type(
            "services", mock_unified, konnect_managers, dry_run=False
        )
        assert errors == 1
        assert created == 0

    def test_push_update_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_drifted_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.update.side_effect = RuntimeError("API error")
        konnect_managers = {"services": manager}

        _created, updated, errors = _push_entity_type(
            "services", mock_unified, konnect_managers, dry_run=False
        )
        assert errors == 1
        assert updated == 0

    def test_push_no_manager_available(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_consumers.return_value = UnifiedEntityList(entities=[])

        created, updated, errors = _push_entity_type("consumers", mock_unified, {}, dry_run=False)
        assert created == 0 and updated == 0 and errors == 0

    def test_push_unknown_entity_type(self) -> None:
        mock_unified = MagicMock()
        created, updated, errors = _push_entity_type(
            "unknown_type", mock_unified, {}, dry_run=False
        )
        assert created == 0 and updated == 0 and errors == 0

    def test_push_consumers_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_consumers.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()

        _push_entity_type("consumers", mock_unified, {"consumers": manager}, dry_run=False)
        mock_unified.list_consumers.assert_called()

    def test_push_plugins_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_plugins.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()

        _push_entity_type("plugins", mock_unified, {"plugins": manager}, dry_run=False)
        mock_unified.list_plugins.assert_called()

    def test_push_upstreams_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_upstreams.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()

        _push_entity_type("upstreams", mock_unified, {"upstreams": manager}, dry_run=False)
        mock_unified.list_upstreams.assert_called()

    def test_push_certificates_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_certificates.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type("certificates", mock_unified, {"certificates": manager}, dry_run=False)
        mock_unified.list_certificates.assert_called()

    def test_push_snis_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_snis.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type("snis", mock_unified, {"snis": manager}, dry_run=False)
        mock_unified.list_snis.assert_called()

    def test_push_ca_certificates_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type(
            "ca_certificates", mock_unified, {"ca_certificates": manager}, dry_run=False
        )
        mock_unified.list_ca_certificates.assert_called()

    def test_push_key_sets_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_key_sets.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type("key_sets", mock_unified, {"key_sets": manager}, dry_run=False)
        mock_unified.list_key_sets.assert_called()

    def test_push_keys_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_keys.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type("keys", mock_unified, {"keys": manager}, dry_run=False)
        mock_unified.list_keys.assert_called()

    def test_push_vaults_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_vaults.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _push_entity_type("vaults", mock_unified, {"vaults": manager}, dry_run=False)
        mock_unified.list_vaults.assert_called()

    def test_push_routes_with_service_remap(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_routes.return_value = UnifiedEntityList(entities=[])
        # For routes, it also calls _build_service_id_map → list_services
        services_list = MagicMock()
        services_list.synced = []
        services_list.with_drift = []
        services_list.konnect_only = []
        mock_unified.list_services.return_value = services_list

        manager = MagicMock()
        _push_entity_type("routes", mock_unified, {"routes": manager}, dry_run=False)
        mock_unified.list_routes.assert_called()
        mock_unified.list_services.assert_called()

    def test_push_with_resolved_entities_skips_unresolved(self) -> None:
        mock_unified = MagicMock()
        entity = _make_drifted_entity(name="my-api")
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        konnect_managers = {"services": manager}

        # Only resolve a different entity, so "services:my-api" is skipped
        _created, updated, _errors = _push_entity_type(
            "services",
            mock_unified,
            konnect_managers,
            dry_run=False,
            resolved_entities={"services:other-api"},
        )
        assert updated == 0
        manager.update.assert_not_called()

    def test_push_with_audit_on_create_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_gateway_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.side_effect = RuntimeError("API error")
        konnect_managers = {"services": manager}
        audit_service = MagicMock()

        _push_entity_type(
            "services",
            mock_unified,
            konnect_managers,
            dry_run=False,
            audit_service=audit_service,
            sync_id="sync-123",
        )
        # Should record the error
        assert audit_service.record.call_count == 1

    def test_push_with_audit_on_update_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_drifted_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.update.side_effect = RuntimeError("API error")
        konnect_managers = {"services": manager}
        audit_service = MagicMock()

        _push_entity_type(
            "services",
            mock_unified,
            konnect_managers,
            dry_run=False,
            audit_service=audit_service,
            sync_id="sync-123",
        )
        assert audit_service.record.call_count == 1


# ===========================================================================
# _pull_entity_type
# ===========================================================================


def _make_konnect_only_entity(
    konnect_id: str = "k-1",
    name: str = "test-entity",
) -> UnifiedEntity[Service]:
    """Create a konnect-only unified entity."""
    svc = Service(id=konnect_id, name=name, host="remote")
    return UnifiedEntity(
        entity=svc,
        source=EntitySource.KONNECT,
        gateway_id=None,
        konnect_id=konnect_id,
        has_drift=False,
        konnect_entity=svc,
    )


@pytest.mark.unit
class TestPullEntityType:
    """Tests for _pull_entity_type."""

    def test_pull_creates_konnect_only_entities(self) -> None:
        mock_unified = MagicMock()
        entity = _make_konnect_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.return_value = Service(name="created", host="remote")
        gateway_managers = {"services": manager}

        created, _updated, _errors = _pull_entity_type(
            "services", mock_unified, gateway_managers, dry_run=False
        )
        assert created == 1
        manager.create.assert_called_once()

    def test_pull_dry_run(self) -> None:
        mock_unified = MagicMock()
        entity = _make_konnect_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        gateway_managers = {"services": manager}

        created, _updated, _errors = _pull_entity_type(
            "services", mock_unified, gateway_managers, dry_run=True
        )
        assert created == 1
        manager.create.assert_not_called()

    def test_pull_create_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_konnect_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.side_effect = RuntimeError("API error")
        gateway_managers = {"services": manager}

        created, _updated, errors = _pull_entity_type(
            "services", mock_unified, gateway_managers, dry_run=False
        )
        assert errors == 1
        assert created == 0

    def test_pull_unknown_entity_type(self) -> None:
        mock_unified = MagicMock()
        created, _updated, _errors = _pull_entity_type(
            "unknown_type", mock_unified, {}, dry_run=False
        )
        assert created == 0

    def test_pull_no_manager_available(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_services.return_value = UnifiedEntityList(entities=[])
        created, _updated, _errors = _pull_entity_type("services", mock_unified, {}, dry_run=False)
        assert created == 0

    def test_pull_consumers_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_consumers.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("consumers", mock_unified, {"consumers": manager}, dry_run=False)
        mock_unified.list_consumers.assert_called()

    def test_pull_plugins_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_plugins.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("plugins", mock_unified, {"plugins": manager}, dry_run=False)
        mock_unified.list_plugins.assert_called()

    def test_pull_upstreams_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_upstreams.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("upstreams", mock_unified, {"upstreams": manager}, dry_run=False)
        mock_unified.list_upstreams.assert_called()

    def test_pull_certificates_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_certificates.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("certificates", mock_unified, {"certificates": manager}, dry_run=False)
        mock_unified.list_certificates.assert_called()

    def test_pull_snis_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_snis.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("snis", mock_unified, {"snis": manager}, dry_run=False)
        mock_unified.list_snis.assert_called()

    def test_pull_ca_certificates_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type(
            "ca_certificates", mock_unified, {"ca_certificates": manager}, dry_run=False
        )
        mock_unified.list_ca_certificates.assert_called()

    def test_pull_key_sets_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_key_sets.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("key_sets", mock_unified, {"key_sets": manager}, dry_run=False)
        mock_unified.list_key_sets.assert_called()

    def test_pull_keys_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_keys.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("keys", mock_unified, {"keys": manager}, dry_run=False)
        mock_unified.list_keys.assert_called()

    def test_pull_vaults_entity_type(self) -> None:
        mock_unified = MagicMock()
        mock_unified.list_vaults.return_value = UnifiedEntityList(entities=[])
        manager = MagicMock()
        _pull_entity_type("vaults", mock_unified, {"vaults": manager}, dry_run=False)
        mock_unified.list_vaults.assert_called()

    def test_pull_with_drift_updates_entities(self) -> None:
        mock_unified = MagicMock()
        k_svc = Service(id="k-1", name="my-api", host="konnect-host")
        gw_svc = Service(id="gw-1", name="my-api", host="gateway-host")
        drifted = UnifiedEntity(
            entity=k_svc,
            source=EntitySource.BOTH,
            gateway_id="gw-1",
            konnect_id="k-1",
            has_drift=True,
            drift_fields=["host"],
            gateway_entity=gw_svc,
            konnect_entity=k_svc,
        )
        entity_list = UnifiedEntityList(entities=[drifted])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.update.return_value = Service(name="updated", host="konnect-host")
        gateway_managers = {"services": manager}

        _created, updated, _errors = _pull_entity_type(
            "services",
            mock_unified,
            gateway_managers,
            dry_run=False,
            with_drift=True,
        )
        assert updated == 1

    def test_pull_with_audit_on_create(self) -> None:
        mock_unified = MagicMock()
        entity = _make_konnect_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.return_value = Service(name="created", host="remote")
        gateway_managers = {"services": manager}
        audit_service = MagicMock()

        _pull_entity_type(
            "services",
            mock_unified,
            gateway_managers,
            dry_run=False,
            audit_service=audit_service,
            sync_id="sync-123",
        )
        audit_service.record.assert_called()

    def test_pull_with_audit_on_create_error(self) -> None:
        mock_unified = MagicMock()
        entity = _make_konnect_only_entity()
        entity_list = UnifiedEntityList(entities=[entity])
        mock_unified.list_services.return_value = entity_list

        manager = MagicMock()
        manager.create.side_effect = RuntimeError("API error")
        gateway_managers = {"services": manager}
        audit_service = MagicMock()

        _pull_entity_type(
            "services",
            mock_unified,
            gateway_managers,
            dry_run=False,
            audit_service=audit_service,
            sync_id="sync-123",
        )
        audit_service.record.assert_called()
