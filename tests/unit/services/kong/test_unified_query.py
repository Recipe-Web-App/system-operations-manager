"""Unit tests for UnifiedQueryService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import EntitySource
from system_operations_manager.integrations.kong.models.upstream import Upstream
from system_operations_manager.services.kong.unified_query import UnifiedQueryService


@pytest.fixture
def mock_gateway_managers() -> dict[str, MagicMock]:
    """Create mock gateway managers."""
    return {
        "service": MagicMock(),
        "route": MagicMock(),
        "consumer": MagicMock(),
        "plugin": MagicMock(),
        "upstream": MagicMock(),
    }


@pytest.fixture
def mock_konnect_managers() -> dict[str, MagicMock]:
    """Create mock Konnect managers."""
    return {
        "service": MagicMock(),
        "route": MagicMock(),
        "consumer": MagicMock(),
        "plugin": MagicMock(),
        "upstream": MagicMock(),
    }


@pytest.fixture
def unified_service(
    mock_gateway_managers: dict[str, MagicMock],
    mock_konnect_managers: dict[str, MagicMock],
) -> UnifiedQueryService:
    """Create a UnifiedQueryService with both gateway and Konnect managers."""
    return UnifiedQueryService(
        gateway_service_manager=mock_gateway_managers["service"],
        gateway_route_manager=mock_gateway_managers["route"],
        gateway_consumer_manager=mock_gateway_managers["consumer"],
        gateway_plugin_manager=mock_gateway_managers["plugin"],
        gateway_upstream_manager=mock_gateway_managers["upstream"],
        konnect_service_manager=mock_konnect_managers["service"],
        konnect_route_manager=mock_konnect_managers["route"],
        konnect_consumer_manager=mock_konnect_managers["consumer"],
        konnect_plugin_manager=mock_konnect_managers["plugin"],
        konnect_upstream_manager=mock_konnect_managers["upstream"],
    )


@pytest.fixture
def gateway_only_service(
    mock_gateway_managers: dict[str, MagicMock],
) -> UnifiedQueryService:
    """Create a UnifiedQueryService with only gateway managers."""
    return UnifiedQueryService(
        gateway_service_manager=mock_gateway_managers["service"],
        gateway_route_manager=mock_gateway_managers["route"],
        gateway_consumer_manager=mock_gateway_managers["consumer"],
        gateway_plugin_manager=mock_gateway_managers["plugin"],
        gateway_upstream_manager=mock_gateway_managers["upstream"],
    )


class TestUnifiedQueryServiceInit:
    """Tests for UnifiedQueryService initialization."""

    @pytest.mark.unit
    def test_initialization_with_all_managers(
        self,
        unified_service: UnifiedQueryService,
    ) -> None:
        """Should initialize with both gateway and Konnect managers."""
        assert unified_service.konnect_configured is True

    @pytest.mark.unit
    def test_initialization_gateway_only(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should initialize with gateway managers only."""
        assert gateway_only_service.konnect_configured is False


class TestUnifiedQueryServiceListServices:
    """Tests for list_services operations."""

    @pytest.mark.unit
    def test_list_services_gateway_only(
        self,
        gateway_only_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
    ) -> None:
        """Should return services from gateway only when Konnect not configured."""
        gateway_services = [
            Service(id="gw-1", name="service-1", host="gw1.local"),
            Service(id="gw-2", name="service-2", host="gw2.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)

        result = gateway_only_service.list_services()

        assert len(result) == 2
        assert result.gateway_only_count == 2
        assert result.konnect_only_count == 0

    @pytest.mark.unit
    def test_list_services_both_sources(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should merge services from both sources."""
        gateway_services = [
            Service(id="gw-1", name="shared-service", host="gateway.local"),
            Service(id="gw-2", name="gw-only", host="gw.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="shared-service", host="gateway.local"),
            Service(id="kon-2", name="kon-only", host="kon.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.list_services()

        assert len(result) == 3
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_services_with_drift(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should detect drift in matching services."""
        gateway_services = [
            Service(id="gw-1", name="service-1", host="gateway.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="service-1", host="konnect.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.list_services()

        assert len(result) == 1
        assert result.drift_count == 1
        assert result.entities[0].has_drift is True
        assert "host" in (result.entities[0].drift_fields or [])

    @pytest.mark.unit
    def test_list_services_pagination(
        self,
        gateway_only_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
    ) -> None:
        """Should handle pagination correctly."""
        page1 = [Service(id="gw-1", name="service-1", host="s1.local")]
        page2 = [Service(id="gw-2", name="service-2", host="s2.local")]

        mock_gateway_managers["service"].list.side_effect = [
            (page1, "offset-2"),
            (page2, None),
        ]

        result = gateway_only_service.list_services()

        assert len(result) == 2
        assert mock_gateway_managers["service"].list.call_count == 2


class TestUnifiedQueryServiceListRoutes:
    """Tests for list_routes operations."""

    @pytest.mark.unit
    def test_list_routes_basic(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should list routes from both sources."""
        gateway_routes = [Route(id="gw-1", name="route-1", paths=["/api"])]
        konnect_routes = [Route(id="kon-1", name="route-2", paths=["/v2"])]
        mock_gateway_managers["route"].list.return_value = (gateway_routes, None)
        mock_konnect_managers["route"].list.return_value = (konnect_routes, None)

        result = unified_service.list_routes()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_routes_by_service(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter routes by service."""
        gateway_routes = [Route(id="gw-1", name="route-1", paths=["/api"])]
        konnect_routes = [Route(id="kon-1", name="route-1", paths=["/api"])]
        mock_gateway_managers["route"].list_by_service.return_value = (
            gateway_routes,
            None,
        )
        mock_konnect_managers["route"].list_by_service.return_value = (
            konnect_routes,
            None,
        )

        result = unified_service.list_routes(service_name_or_id="my-service")

        assert len(result) == 1
        assert result.in_both_count == 1
        mock_gateway_managers["route"].list_by_service.assert_called()
        mock_konnect_managers["route"].list_by_service.assert_called()


class TestUnifiedQueryServiceListConsumers:
    """Tests for list_consumers operations."""

    @pytest.mark.unit
    def test_list_consumers_basic(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should list consumers from both sources."""
        gateway_consumers = [Consumer(id="gw-1", username="user-1")]
        konnect_consumers = [Consumer(id="kon-1", username="user-2")]
        mock_gateway_managers["consumer"].list.return_value = (gateway_consumers, None)
        mock_konnect_managers["consumer"].list.return_value = (konnect_consumers, None)

        result = unified_service.list_consumers()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_consumers_merged(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should merge consumers by username."""
        gateway_consumers = [Consumer(id="gw-1", username="shared-user", custom_id="gw-custom")]
        konnect_consumers = [Consumer(id="kon-1", username="shared-user", custom_id="gw-custom")]
        mock_gateway_managers["consumer"].list.return_value = (gateway_consumers, None)
        mock_konnect_managers["consumer"].list.return_value = (konnect_consumers, None)

        result = unified_service.list_consumers()

        assert len(result) == 1
        assert result.in_both_count == 1
        assert result.synced_count == 1


class TestUnifiedQueryServiceListPlugins:
    """Tests for list_plugins operations."""

    @pytest.mark.unit
    def test_list_plugins_basic(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should list plugins from both sources."""
        gateway_plugins = [
            KongPluginEntity(id="gw-1", name="rate-limiting", instance_name="rl-global")
        ]
        konnect_plugins = [KongPluginEntity(id="kon-1", name="key-auth", instance_name="ka-global")]
        mock_gateway_managers["plugin"].list.return_value = (gateway_plugins, None)
        mock_konnect_managers["plugin"].list.return_value = (konnect_plugins, None)

        result = unified_service.list_plugins()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_plugins_merged_by_instance_name(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should merge plugins by instance_name."""
        gateway_plugins = [
            KongPluginEntity(
                id="gw-1",
                name="rate-limiting",
                instance_name="rl-global",
                config={"minute": 100},
            )
        ]
        konnect_plugins = [
            KongPluginEntity(
                id="kon-1",
                name="rate-limiting",
                instance_name="rl-global",
                config={"minute": 100},
            )
        ]
        mock_gateway_managers["plugin"].list.return_value = (gateway_plugins, None)
        mock_konnect_managers["plugin"].list.return_value = (konnect_plugins, None)

        result = unified_service.list_plugins()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_plugins_with_drift(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should detect drift in plugin config."""
        gateway_plugins = [
            KongPluginEntity(
                id="gw-1",
                name="rate-limiting",
                instance_name="rl-global",
                config={"minute": 100},
            )
        ]
        konnect_plugins = [
            KongPluginEntity(
                id="kon-1",
                name="rate-limiting",
                instance_name="rl-global",
                config={"minute": 200},
            )
        ]
        mock_gateway_managers["plugin"].list.return_value = (gateway_plugins, None)
        mock_konnect_managers["plugin"].list.return_value = (konnect_plugins, None)

        result = unified_service.list_plugins()

        assert len(result) == 1
        assert result.drift_count == 1
        assert result.entities[0].has_drift is True

    @pytest.mark.unit
    def test_list_plugins_by_service(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter plugins by service scope."""
        gateway_plugins = [
            KongPluginEntity(id="gw-1", name="rate-limiting", instance_name="rl-svc")
        ]
        mock_gateway_managers["plugin"].list.return_value = (gateway_plugins, None)
        mock_konnect_managers["plugin"].list_by_service.return_value = ([], None)

        unified_service.list_plugins(service_name_or_id="my-service")

        # Gateway filters locally, Konnect uses API filter
        mock_konnect_managers["plugin"].list_by_service.assert_called()


class TestUnifiedQueryServiceListUpstreams:
    """Tests for list_upstreams operations."""

    @pytest.mark.unit
    def test_list_upstreams_basic(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should list upstreams from both sources."""
        gateway_upstreams = [Upstream(id="gw-1", name="upstream-1")]
        konnect_upstreams = [Upstream(id="kon-1", name="upstream-2")]
        mock_gateway_managers["upstream"].list.return_value = (gateway_upstreams, None)
        mock_konnect_managers["upstream"].list.return_value = (konnect_upstreams, None)

        result = unified_service.list_upstreams()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_upstreams_merged_with_drift(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should detect drift in upstream config."""
        gateway_upstreams = [Upstream(id="gw-1", name="upstream-1", slots=1000)]
        konnect_upstreams = [Upstream(id="kon-1", name="upstream-1", slots=2000)]
        mock_gateway_managers["upstream"].list.return_value = (gateway_upstreams, None)
        mock_konnect_managers["upstream"].list.return_value = (konnect_upstreams, None)

        result = unified_service.list_upstreams()

        assert len(result) == 1
        assert result.drift_count == 1
        assert "slots" in (result.entities[0].drift_fields or [])


class TestUnifiedQueryServiceGetSyncSummary:
    """Tests for get_sync_summary operations."""

    @pytest.mark.unit
    def test_get_sync_summary_all_types(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should return summary for all entity types."""
        # Set up mocks to return empty lists
        mock_gateway_managers["service"].list.return_value = ([], None)
        mock_konnect_managers["service"].list.return_value = ([], None)
        mock_gateway_managers["route"].list.return_value = ([], None)
        mock_konnect_managers["route"].list.return_value = ([], None)
        mock_gateway_managers["consumer"].list.return_value = ([], None)
        mock_konnect_managers["consumer"].list.return_value = ([], None)
        mock_gateway_managers["plugin"].list.return_value = ([], None)
        mock_konnect_managers["plugin"].list.return_value = ([], None)
        mock_gateway_managers["upstream"].list.return_value = ([], None)
        mock_konnect_managers["upstream"].list.return_value = ([], None)

        result = unified_service.get_sync_summary()

        assert "services" in result
        assert "routes" in result
        assert "consumers" in result
        assert "plugins" in result
        assert "upstreams" in result

    @pytest.mark.unit
    def test_get_sync_summary_specific_types(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should return summary for specific entity types."""
        mock_gateway_managers["service"].list.return_value = ([], None)
        mock_konnect_managers["service"].list.return_value = ([], None)

        result = unified_service.get_sync_summary(entity_types=["services"])

        assert "services" in result
        assert "routes" not in result

    @pytest.mark.unit
    def test_get_sync_summary_counts(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should return correct counts in summary."""
        gateway_services = [
            Service(id="gw-1", name="gw-only", host="gw.local"),
            Service(id="gw-2", name="shared", host="shared.local"),
            Service(id="gw-3", name="drifted", host="gateway.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="shared", host="shared.local"),
            Service(id="kon-2", name="drifted", host="konnect.local"),
            Service(id="kon-3", name="kon-only", host="kon.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.get_sync_summary(entity_types=["services"])

        service_stats = result["services"]
        assert service_stats["gateway_only"] == 1
        assert service_stats["konnect_only"] == 1
        assert service_stats["synced"] == 1
        assert service_stats["drift"] == 1
        assert service_stats["total"] == 4


class TestUnifiedQueryServiceSourceFiltering:
    """Tests for source filtering in unified results."""

    @pytest.mark.unit
    def test_filter_by_gateway_source(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter unified list by gateway source."""
        gateway_services = [
            Service(id="gw-1", name="gw-only", host="gw.local"),
            Service(id="gw-2", name="shared", host="shared.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="shared", host="shared.local"),
            Service(id="kon-2", name="kon-only", host="kon.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.list_services()
        filtered = result.filter_by_source(EntitySource.GATEWAY)

        assert len(filtered) == 2
        names = {e.entity.name for e in filtered.entities}
        assert names == {"gw-only", "shared"}

    @pytest.mark.unit
    def test_filter_by_konnect_source(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter unified list by konnect source."""
        gateway_services = [
            Service(id="gw-1", name="gw-only", host="gw.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="kon-only", host="kon.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.list_services()
        filtered = result.filter_by_source("konnect")

        assert len(filtered) == 1
        assert filtered.entities[0].entity.name == "kon-only"

    @pytest.mark.unit
    def test_filter_by_both_source(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter unified list by both source."""
        gateway_services = [
            Service(id="gw-1", name="shared", host="shared.local"),
        ]
        konnect_services = [
            Service(id="kon-1", name="shared", host="shared.local"),
        ]
        mock_gateway_managers["service"].list.return_value = (gateway_services, None)
        mock_konnect_managers["service"].list.return_value = (konnect_services, None)

        result = unified_service.list_services()
        filtered = result.filter_by_source(EntitySource.BOTH)

        assert len(filtered) == 1
        assert filtered.entities[0].source == EntitySource.BOTH
