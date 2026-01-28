"""Shared fixtures for Kong sync command tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_unified_service() -> MagicMock:
    """Create a mock UnifiedQueryService."""
    service = MagicMock()

    # Default sync summary (everything in sync)
    service.get_sync_summary.return_value = {
        "services": {"gateway_only": 0, "konnect_only": 0, "synced": 2, "drift": 0, "total": 2},
        "routes": {"gateway_only": 0, "konnect_only": 0, "synced": 1, "drift": 0, "total": 1},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }

    # Default list methods return empty lists with gateway_only and with_drift
    empty_list: UnifiedEntityList[Service] = UnifiedEntityList(entities=[])
    service.list_services.return_value = empty_list
    service.list_routes.return_value = empty_list
    service.list_consumers.return_value = empty_list
    service.list_plugins.return_value = empty_list
    service.list_upstreams.return_value = empty_list

    return service


@pytest.fixture
def mock_konnect_service_manager() -> MagicMock:
    """Create a mock Konnect service manager."""
    manager = MagicMock()
    manager.create.return_value = Service(name="created-service", host="localhost")
    manager.update.return_value = Service(name="updated-service", host="localhost")
    return manager


@pytest.fixture
def mock_konnect_route_manager() -> MagicMock:
    """Create a mock Konnect route manager."""
    return MagicMock()


@pytest.fixture
def mock_konnect_consumer_manager() -> MagicMock:
    """Create a mock Konnect consumer manager."""
    return MagicMock()


@pytest.fixture
def mock_konnect_plugin_manager() -> MagicMock:
    """Create a mock Konnect plugin manager."""
    return MagicMock()


@pytest.fixture
def mock_konnect_upstream_manager() -> MagicMock:
    """Create a mock Konnect upstream manager."""
    return MagicMock()


@pytest.fixture
def sample_gateway_only_services() -> UnifiedEntityList[Service]:
    """Sample services that exist only in Gateway."""
    service1 = Service(id="svc-1", name="new-api", host="api.local")
    service2 = Service(id="svc-2", name="another-api", host="other.local")

    entities = [
        UnifiedEntity(
            entity=service1,
            source=EntitySource.GATEWAY,
            gateway_id="svc-1",
            konnect_id=None,
            has_drift=False,
            gateway_entity=service1,
        ),
        UnifiedEntity(
            entity=service2,
            source=EntitySource.GATEWAY,
            gateway_id="svc-2",
            konnect_id=None,
            has_drift=False,
            gateway_entity=service2,
        ),
    ]
    return UnifiedEntityList(entities=entities)


@pytest.fixture
def sample_drifted_services() -> UnifiedEntityList[Service]:
    """Sample services with drift between Gateway and Konnect."""
    gateway_svc = Service(id="svc-1", name="my-api", host="new-host.local", port=8080)
    konnect_svc = Service(id="svc-1", name="my-api", host="old-host.local", port=80)

    entities = [
        UnifiedEntity(
            entity=gateway_svc,  # Use gateway version as primary
            source=EntitySource.BOTH,
            gateway_id="svc-1",
            konnect_id="konnect-svc-1",
            has_drift=True,
            drift_fields=["host", "port"],
            gateway_entity=gateway_svc,
            konnect_entity=konnect_svc,
        ),
    ]
    return UnifiedEntityList(entities=entities)


@pytest.fixture
def sync_summary_with_changes() -> dict[str, dict[str, int]]:
    """Sample sync summary with entities to push."""
    return {
        "services": {"gateway_only": 2, "konnect_only": 0, "synced": 1, "drift": 1, "total": 4},
        "routes": {"gateway_only": 1, "konnect_only": 0, "synced": 0, "drift": 0, "total": 1},
        "consumers": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "plugins": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
        "upstreams": {"gateway_only": 0, "konnect_only": 0, "synced": 0, "drift": 0, "total": 0},
    }


@pytest.fixture
def mock_gateway_upstream_manager() -> MagicMock:
    """Create a mock Gateway upstream manager."""
    manager = MagicMock()
    manager.add_target.return_value = Target(target="localhost:8080", weight=100)
    return manager


@pytest.fixture
def sample_upstreams() -> UnifiedEntityList[Upstream]:
    """Sample upstreams."""
    upstream1 = Upstream(id="up-1", name="backend-upstream")
    upstream2 = Upstream(id="up-2", name="api-upstream")

    entities = [
        UnifiedEntity(
            entity=upstream1,
            source=EntitySource.BOTH,
            gateway_id="up-1",
            konnect_id="konnect-up-1",
            has_drift=False,
            gateway_entity=upstream1,
            konnect_entity=upstream1,
        ),
        UnifiedEntity(
            entity=upstream2,
            source=EntitySource.BOTH,
            gateway_id="up-2",
            konnect_id="konnect-up-2",
            has_drift=False,
            gateway_entity=upstream2,
            konnect_entity=upstream2,
        ),
    ]
    return UnifiedEntityList(entities=entities)


@pytest.fixture
def sample_gateway_only_targets() -> UnifiedEntityList[Target]:
    """Sample targets that exist only in Gateway."""
    target1 = Target(id="t-1", target="server1.local:8080", weight=100)
    target2 = Target(id="t-2", target="server2.local:8080", weight=100)

    entities = [
        UnifiedEntity(
            entity=target1,
            source=EntitySource.GATEWAY,
            gateway_id="t-1",
            konnect_id=None,
            has_drift=False,
            gateway_entity=target1,
        ),
        UnifiedEntity(
            entity=target2,
            source=EntitySource.GATEWAY,
            gateway_id="t-2",
            konnect_id=None,
            has_drift=False,
            gateway_entity=target2,
        ),
    ]
    return UnifiedEntityList(entities=entities)


@pytest.fixture
def sample_konnect_only_targets() -> UnifiedEntityList[Target]:
    """Sample targets that exist only in Konnect."""
    target1 = Target(id="t-1", target="konnect-server1.local:8080", weight=50)
    target2 = Target(id="t-2", target="konnect-server2.local:8080", weight=75)

    entities = [
        UnifiedEntity(
            entity=target1,
            source=EntitySource.KONNECT,
            gateway_id=None,
            konnect_id="t-1",
            has_drift=False,
            konnect_entity=target1,
        ),
        UnifiedEntity(
            entity=target2,
            source=EntitySource.KONNECT,
            gateway_id=None,
            konnect_id="t-2",
            has_drift=False,
            konnect_entity=target2,
        ),
    ]
    return UnifiedEntityList(entities=entities)
