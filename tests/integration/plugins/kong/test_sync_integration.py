"""Integration tests for sync commands.

These tests use mocked HTTP responses to simulate Kong Gateway and Konnect APIs,
allowing end-to-end testing of the sync commands without requiring real services.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)


@pytest.fixture
def mock_unified_service_for_push() -> MagicMock:
    """Create a mock UnifiedQueryService configured for push scenario."""
    service = MagicMock()

    # Service only in Gateway
    gateway_service = Service(id="svc-1", name="api-service", host="api.local", port=8080)

    service.get_sync_summary.return_value = {
        "services": {"gateway_only": 1, "konnect_only": 0, "synced": 0, "drift": 0, "total": 1},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }

    entity = UnifiedEntity(
        entity=gateway_service,
        source=EntitySource.GATEWAY,
        gateway_id="svc-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_service,
    )
    service.list_services.return_value = UnifiedEntityList(entities=[entity])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_for_pull() -> MagicMock:
    """Create a mock UnifiedQueryService configured for pull scenario."""
    service = MagicMock()

    # Service only in Konnect
    konnect_service = Service(
        id="konnect-svc-1", name="konnect-service", host="konnect.local", port=443
    )

    service.get_sync_summary.return_value = {
        "services": {"gateway_only": 0, "konnect_only": 1, "synced": 0, "drift": 0, "total": 1},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }

    entity = UnifiedEntity(
        entity=konnect_service,
        source=EntitySource.KONNECT,
        gateway_id=None,
        konnect_id="konnect-svc-1",
        has_drift=False,
        konnect_entity=konnect_service,
    )
    service.list_services.return_value = UnifiedEntityList(entities=[entity])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_konnect_service_manager() -> MagicMock:
    """Create a mock Konnect service manager."""
    manager = MagicMock()
    manager.create.return_value = Service(id="konnect-new", name="api-service", host="api.local")
    return manager


@pytest.fixture
def mock_gateway_service_manager() -> MagicMock:
    """Create a mock Gateway service manager."""
    manager = MagicMock()
    manager.create.return_value = Service(id="gw-new", name="konnect-service", host="konnect.local")
    return manager


@pytest.mark.integration
class TestSyncPushIntegration:
    """Integration tests for sync push command with mocked services."""

    def test_push_creates_service_in_konnect(
        self,
        mock_unified_service_for_push: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify push creates service in Konnect when only in Gateway."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        # Call the push helper directly with mocks
        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_push,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0
        mock_konnect_service_manager.create.assert_called_once()

    def test_push_dry_run_makes_no_changes(
        self,
        mock_unified_service_for_push: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify dry-run doesn't create services in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_push,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=True,
        )

        assert created == 1  # Reported as would-create
        assert updated == 0
        assert errors == 0
        mock_konnect_service_manager.create.assert_not_called()

    def test_push_handles_konnect_api_errors(
        self,
        mock_unified_service_for_push: MagicMock,
        mock_konnect_service_manager: MagicMock,
    ) -> None:
        """Verify push handles Konnect API errors gracefully."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        mock_konnect_service_manager.create.side_effect = Exception("Konnect API error")

        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_push,
            konnect_managers={"services": mock_konnect_service_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 1


@pytest.mark.integration
class TestSyncPullIntegration:
    """Integration tests for sync pull command with mocked services."""

    def test_pull_creates_service_in_gateway(
        self,
        mock_unified_service_for_pull: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify pull creates service in Gateway when only in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        created, updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_pull,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=False,
            with_drift=False,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0
        mock_gateway_service_manager.create.assert_called_once()

    def test_pull_dry_run_makes_no_changes(
        self,
        mock_unified_service_for_pull: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify dry-run doesn't create services in Gateway."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        created, updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_pull,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=True,
            with_drift=False,
        )

        assert created == 1  # Reported as would-create
        assert updated == 0
        assert errors == 0
        mock_gateway_service_manager.create.assert_not_called()

    def test_pull_handles_gateway_api_errors(
        self,
        mock_unified_service_for_pull: MagicMock,
        mock_gateway_service_manager: MagicMock,
    ) -> None:
        """Verify pull handles Gateway API errors gracefully."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        mock_gateway_service_manager.create.side_effect = Exception("Gateway API error")

        created, updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_unified_service_for_pull,
            gateway_managers={"services": mock_gateway_service_manager},
            dry_run=False,
            with_drift=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 1


@pytest.mark.integration
class TestSyncWithDriftIntegration:
    """Integration tests for sync with drift detection."""

    def test_push_updates_drifted_service(self) -> None:
        """Verify push updates service in Konnect when drift detected."""
        from system_operations_manager.integrations.kong.models.unified import (
            EntitySource,
            UnifiedEntity,
            UnifiedEntityList,
        )
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        # Create drifted services
        gateway_svc = Service(id="svc-1", name="api-service", host="new-host.local", port=8080)
        konnect_svc = Service(id="svc-1", name="api-service", host="old-host.local", port=80)

        drifted_entity = UnifiedEntity(
            entity=gateway_svc,
            source=EntitySource.BOTH,
            gateway_id="svc-1",
            konnect_id="konnect-svc-1",
            has_drift=True,
            drift_fields=["host", "port"],
            gateway_entity=gateway_svc,
            konnect_entity=konnect_svc,
        )

        mock_service = MagicMock()
        mock_service.list_services.return_value = UnifiedEntityList(entities=[drifted_entity])

        mock_konnect_manager = MagicMock()
        mock_konnect_manager.update.return_value = gateway_svc

        created, updated, errors = _push_entity_type(
            entity_type="services",
            unified_service=mock_service,
            konnect_managers={"services": mock_konnect_manager},
            dry_run=False,
        )

        assert created == 0
        assert updated == 1
        assert errors == 0
        mock_konnect_manager.update.assert_called_once_with("konnect-svc-1", gateway_svc)

    def test_pull_with_drift_updates_gateway(self) -> None:
        """Verify pull with --with-drift updates Gateway to match Konnect."""
        from system_operations_manager.integrations.kong.models.unified import (
            EntitySource,
            UnifiedEntity,
            UnifiedEntityList,
        )
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        # Create drifted services
        gateway_svc = Service(id="svc-1", name="api-service", host="old-host.local", port=80)
        konnect_svc = Service(id="svc-1", name="api-service", host="new-host.local", port=8080)

        drifted_entity = UnifiedEntity(
            entity=konnect_svc,  # Konnect is source of truth for pull
            source=EntitySource.BOTH,
            gateway_id="svc-1",
            konnect_id="konnect-svc-1",
            has_drift=True,
            drift_fields=["host", "port"],
            gateway_entity=gateway_svc,
            konnect_entity=konnect_svc,
        )

        mock_service = MagicMock()
        mock_service.list_services.return_value = UnifiedEntityList(entities=[drifted_entity])

        mock_gateway_manager = MagicMock()
        mock_gateway_manager.update.return_value = konnect_svc

        created, updated, errors = _pull_entity_type(
            entity_type="services",
            unified_service=mock_service,
            gateway_managers={"services": mock_gateway_manager},
            dry_run=False,
            with_drift=True,
        )

        assert created == 0
        assert updated == 1
        assert errors == 0
        mock_gateway_manager.update.assert_called_once_with("svc-1", konnect_svc)
