"""Unit tests for UnifiedQueryService."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.enterprise import Vault
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.unified import EntitySource
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream
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


@pytest.fixture
def full_unified_service(
    mock_gateway_managers: dict[str, MagicMock],
    mock_konnect_managers: dict[str, MagicMock],
) -> Any:
    """Create UnifiedQueryService with all managers including optional ones."""
    return UnifiedQueryService(
        gateway_service_manager=mock_gateway_managers["service"],
        gateway_route_manager=mock_gateway_managers["route"],
        gateway_consumer_manager=mock_gateway_managers["consumer"],
        gateway_plugin_manager=mock_gateway_managers["plugin"],
        gateway_upstream_manager=mock_gateway_managers["upstream"],
        gateway_certificate_manager=MagicMock(),
        gateway_sni_manager=MagicMock(),
        gateway_ca_certificate_manager=MagicMock(),
        gateway_key_set_manager=MagicMock(),
        gateway_key_manager=MagicMock(),
        gateway_vault_manager=MagicMock(),
        konnect_service_manager=mock_konnect_managers["service"],
        konnect_route_manager=mock_konnect_managers["route"],
        konnect_consumer_manager=mock_konnect_managers["consumer"],
        konnect_plugin_manager=mock_konnect_managers["plugin"],
        konnect_upstream_manager=mock_konnect_managers["upstream"],
        konnect_certificate_manager=MagicMock(),
        konnect_sni_manager=MagicMock(),
        konnect_ca_certificate_manager=MagicMock(),
        konnect_key_set_manager=MagicMock(),
        konnect_key_manager=MagicMock(),
        konnect_vault_manager=MagicMock(),
    )


class TestUnifiedQueryServiceListTargets:
    """Tests for list_targets_for_upstream operations."""

    @pytest.mark.unit
    def test_list_targets_gateway_only(
        self,
        gateway_only_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
    ) -> None:
        """Should return targets from gateway only when Konnect not configured."""
        targets = [
            Target(id="gw-t1", target="10.0.0.1:8080"),
            Target(id="gw-t2", target="10.0.0.2:8080"),
        ]
        mock_gateway_managers["upstream"].list_targets.return_value = (targets, None)

        result = gateway_only_service.list_targets_for_upstream("my-upstream")

        assert len(result) == 2
        assert result.gateway_only_count == 2
        assert result.konnect_only_count == 0
        mock_gateway_managers["upstream"].list_targets.assert_called_once_with(
            "my-upstream", offset=None
        )

    @pytest.mark.unit
    def test_list_targets_both_sources(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should merge targets from both sources."""
        gateway_targets = [Target(id="gw-t1", target="10.0.0.1:8080")]
        konnect_targets = [Target(id="kon-t1", target="10.0.0.2:8080")]
        mock_gateway_managers["upstream"].list_targets.return_value = (gateway_targets, None)
        mock_konnect_managers["upstream"].list_targets.return_value = (konnect_targets, None)

        result = unified_service.list_targets_for_upstream("my-upstream")

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_targets_merged_by_target_field(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should merge targets that share the same target address."""
        shared_target_gw = Target(id="gw-t1", target="10.0.0.1:8080", weight=100)
        shared_target_kn = Target(id="kon-t1", target="10.0.0.1:8080", weight=100)
        mock_gateway_managers["upstream"].list_targets.return_value = (
            [shared_target_gw],
            None,
        )
        mock_konnect_managers["upstream"].list_targets.return_value = (
            [shared_target_kn],
            None,
        )

        result = unified_service.list_targets_for_upstream("my-upstream")

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_targets_with_pagination(
        self,
        gateway_only_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
    ) -> None:
        """Should handle gateway target pagination correctly."""
        page1 = [Target(id="gw-t1", target="10.0.0.1:8080")]
        page2 = [Target(id="gw-t2", target="10.0.0.2:8080")]
        mock_gateway_managers["upstream"].list_targets.side_effect = [
            (page1, "next-offset"),
            (page2, None),
        ]

        result = gateway_only_service.list_targets_for_upstream("my-upstream")

        assert len(result) == 2
        assert mock_gateway_managers["upstream"].list_targets.call_count == 2

    @pytest.mark.unit
    def test_list_targets_konnect_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should handle konnect target pagination correctly."""
        mock_gateway_managers["upstream"].list_targets.return_value = ([], None)
        page1 = [Target(id="kon-t1", target="10.0.0.1:8080")]
        page2 = [Target(id="kon-t2", target="10.0.0.2:8080")]
        mock_konnect_managers["upstream"].list_targets.side_effect = [
            (page1, "next-offset"),
            (page2, None),
        ]

        result = unified_service.list_targets_for_upstream("my-upstream")

        assert len(result) == 2
        assert mock_konnect_managers["upstream"].list_targets.call_count == 2


class TestUnifiedQueryServiceListCertificates:
    """Tests for list_certificates operations."""

    @pytest.mark.unit
    def test_list_certificates_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no certificate managers configured."""
        result = gateway_only_service.list_certificates()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_certificates_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return certificates from gateway when only gateway configured."""
        cert = Certificate(
            id="cert-1", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        full_unified_service._gateway_certificates.list.return_value = ([cert], None)
        full_unified_service._konnect_certificates = None

        result = full_unified_service.list_certificates()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_certificates_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge certificates from both sources."""
        gw_cert = Certificate(
            id="cert-gw-1", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        kn_cert = Certificate(
            id="cert-kn-1", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        full_unified_service._gateway_certificates.list.return_value = ([gw_cert], None)
        full_unified_service._konnect_certificates.list.return_value = ([kn_cert], None)

        result = full_unified_service.list_certificates()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_certificates_merged_by_id(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge certificates that share the same ID."""
        shared_id = "cert-shared-1"
        gw_cert = Certificate(
            id=shared_id, cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        kn_cert = Certificate(
            id=shared_id, cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        full_unified_service._gateway_certificates.list.return_value = ([gw_cert], None)
        full_unified_service._konnect_certificates.list.return_value = ([kn_cert], None)

        result = full_unified_service.list_certificates()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_certificates_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway certificate pagination correctly."""
        full_unified_service._konnect_certificates = None
        page1_cert = Certificate(
            id="cert-1", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        page2_cert = Certificate(
            id="cert-2", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        full_unified_service._gateway_certificates.list.side_effect = [
            ([page1_cert], "next-offset"),
            ([page2_cert], None),
        ]

        result = full_unified_service.list_certificates()

        assert len(result) == 2
        assert full_unified_service._gateway_certificates.list.call_count == 2

    @pytest.mark.unit
    def test_list_certificates_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect certificate pagination correctly."""
        full_unified_service._gateway_certificates = None
        page1_cert = Certificate(
            id="cert-1", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        page2_cert = Certificate(
            id="cert-2", cert="test-cert-data", key="test-key-data"
        )  # pragma: allowlist secret
        full_unified_service._konnect_certificates.list.side_effect = [
            ([page1_cert], "next-offset"),
            ([page2_cert], None),
        ]

        result = full_unified_service.list_certificates()

        assert len(result) == 2
        assert full_unified_service._konnect_certificates.list.call_count == 2


class TestUnifiedQueryServiceListSNIs:
    """Tests for list_snis operations."""

    @pytest.mark.unit
    def test_list_snis_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no SNI managers configured."""
        result = gateway_only_service.list_snis()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_snis_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return SNIs from gateway when only gateway manager configured."""
        cert_ref = KongEntityReference(id="cert-1")
        sni = SNI(id="sni-1", name="api.example.com", certificate=cert_ref)
        full_unified_service._gateway_snis.list.return_value = ([sni], None)
        full_unified_service._konnect_snis = None

        result = full_unified_service.list_snis()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_snis_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge SNIs from both sources."""
        cert_ref = KongEntityReference(id="cert-1")
        gw_sni = SNI(id="sni-gw-1", name="api.gateway.com", certificate=cert_ref)
        kn_sni = SNI(id="sni-kn-1", name="api.konnect.com", certificate=cert_ref)
        full_unified_service._gateway_snis.list.return_value = ([gw_sni], None)
        full_unified_service._konnect_snis.list.return_value = ([kn_sni], None)

        result = full_unified_service.list_snis()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_snis_merged_by_name(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge SNIs that share the same name."""
        cert_ref = KongEntityReference(id="cert-1")
        gw_sni = SNI(id="sni-gw-1", name="shared.example.com", certificate=cert_ref)
        kn_sni = SNI(id="sni-kn-1", name="shared.example.com", certificate=cert_ref)
        full_unified_service._gateway_snis.list.return_value = ([gw_sni], None)
        full_unified_service._konnect_snis.list.return_value = ([kn_sni], None)

        result = full_unified_service.list_snis()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_snis_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway SNI pagination correctly."""
        full_unified_service._konnect_snis = None
        cert_ref = KongEntityReference(id="cert-1")
        sni1 = SNI(id="sni-1", name="api1.example.com", certificate=cert_ref)
        sni2 = SNI(id="sni-2", name="api2.example.com", certificate=cert_ref)
        full_unified_service._gateway_snis.list.side_effect = [
            ([sni1], "next-offset"),
            ([sni2], None),
        ]

        result = full_unified_service.list_snis()

        assert len(result) == 2
        assert full_unified_service._gateway_snis.list.call_count == 2

    @pytest.mark.unit
    def test_list_snis_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect SNI pagination correctly."""
        full_unified_service._gateway_snis = None
        cert_ref = KongEntityReference(id="cert-1")
        sni1 = SNI(id="sni-1", name="api1.example.com", certificate=cert_ref)
        sni2 = SNI(id="sni-2", name="api2.example.com", certificate=cert_ref)
        full_unified_service._konnect_snis.list.side_effect = [
            ([sni1], "next-offset"),
            ([sni2], None),
        ]

        result = full_unified_service.list_snis()

        assert len(result) == 2
        assert full_unified_service._konnect_snis.list.call_count == 2


class TestUnifiedQueryServiceListCACertificates:
    """Tests for list_ca_certificates operations."""

    @pytest.mark.unit
    def test_list_ca_certificates_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no CA certificate managers configured."""
        result = gateway_only_service.list_ca_certificates()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_ca_certificates_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return CA certs from gateway when only gateway manager configured."""
        ca_cert = CACertificate(id="ca-1", cert="test-cert-data")
        full_unified_service._gateway_ca_certificates.list.return_value = ([ca_cert], None)
        full_unified_service._konnect_ca_certificates = None

        result = full_unified_service.list_ca_certificates()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_ca_certificates_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge CA certificates from both sources."""
        gw_ca = CACertificate(id="ca-gw-1", cert="test-cert-data")
        kn_ca = CACertificate(id="ca-kn-1", cert="test-cert-data")
        full_unified_service._gateway_ca_certificates.list.return_value = ([gw_ca], None)
        full_unified_service._konnect_ca_certificates.list.return_value = ([kn_ca], None)

        result = full_unified_service.list_ca_certificates()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_ca_certificates_merged_by_id(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge CA certificates that share the same ID."""
        shared_id = "ca-shared-1"
        gw_ca = CACertificate(id=shared_id, cert="test-cert-data")
        kn_ca = CACertificate(id=shared_id, cert="test-cert-data")
        full_unified_service._gateway_ca_certificates.list.return_value = ([gw_ca], None)
        full_unified_service._konnect_ca_certificates.list.return_value = ([kn_ca], None)

        result = full_unified_service.list_ca_certificates()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_ca_certificates_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway CA certificate pagination."""
        full_unified_service._konnect_ca_certificates = None
        ca1 = CACertificate(id="ca-1", cert="test-cert-data")
        ca2 = CACertificate(id="ca-2", cert="test-cert-data")
        full_unified_service._gateway_ca_certificates.list.side_effect = [
            ([ca1], "next-offset"),
            ([ca2], None),
        ]

        result = full_unified_service.list_ca_certificates()

        assert len(result) == 2
        assert full_unified_service._gateway_ca_certificates.list.call_count == 2

    @pytest.mark.unit
    def test_list_ca_certificates_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect CA certificate pagination."""
        full_unified_service._gateway_ca_certificates = None
        ca1 = CACertificate(id="ca-1", cert="test-cert-data")
        ca2 = CACertificate(id="ca-2", cert="test-cert-data")
        full_unified_service._konnect_ca_certificates.list.side_effect = [
            ([ca1], "next-offset"),
            ([ca2], None),
        ]

        result = full_unified_service.list_ca_certificates()

        assert len(result) == 2
        assert full_unified_service._konnect_ca_certificates.list.call_count == 2


class TestUnifiedQueryServiceListKeySets:
    """Tests for list_key_sets operations."""

    @pytest.mark.unit
    def test_list_key_sets_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no key set managers configured."""
        result = gateway_only_service.list_key_sets()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_key_sets_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return key sets from gateway when only gateway manager configured."""
        key_set = KeySet(id="ks-1", name="jwt-signing-keys")
        full_unified_service._gateway_key_sets.list.return_value = ([key_set], None)
        full_unified_service._konnect_key_sets = None

        result = full_unified_service.list_key_sets()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_key_sets_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge key sets from both sources."""
        gw_ks = KeySet(id="ks-gw-1", name="gw-signing-keys")
        kn_ks = KeySet(id="ks-kn-1", name="kn-signing-keys")
        full_unified_service._gateway_key_sets.list.return_value = ([gw_ks], None)
        full_unified_service._konnect_key_sets.list.return_value = ([kn_ks], None)

        result = full_unified_service.list_key_sets()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_key_sets_merged_by_name(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge key sets that share the same name."""
        gw_ks = KeySet(id="ks-gw-1", name="shared-signing-keys")
        kn_ks = KeySet(id="ks-kn-1", name="shared-signing-keys")
        full_unified_service._gateway_key_sets.list.return_value = ([gw_ks], None)
        full_unified_service._konnect_key_sets.list.return_value = ([kn_ks], None)

        result = full_unified_service.list_key_sets()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_key_sets_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway key set pagination."""
        full_unified_service._konnect_key_sets = None
        ks1 = KeySet(id="ks-1", name="signing-keys-1")
        ks2 = KeySet(id="ks-2", name="signing-keys-2")
        full_unified_service._gateway_key_sets.list.side_effect = [
            ([ks1], "next-offset"),
            ([ks2], None),
        ]

        result = full_unified_service.list_key_sets()

        assert len(result) == 2
        assert full_unified_service._gateway_key_sets.list.call_count == 2

    @pytest.mark.unit
    def test_list_key_sets_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect key set pagination."""
        full_unified_service._gateway_key_sets = None
        ks1 = KeySet(id="ks-1", name="signing-keys-1")
        ks2 = KeySet(id="ks-2", name="signing-keys-2")
        full_unified_service._konnect_key_sets.list.side_effect = [
            ([ks1], "next-offset"),
            ([ks2], None),
        ]

        result = full_unified_service.list_key_sets()

        assert len(result) == 2
        assert full_unified_service._konnect_key_sets.list.call_count == 2


class TestUnifiedQueryServiceListKeys:
    """Tests for list_keys operations."""

    @pytest.mark.unit
    def test_list_keys_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no key managers configured."""
        result = gateway_only_service.list_keys()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_keys_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return keys from gateway when only gateway manager configured."""
        key = Key(id="key-1", kid="my-key-id")
        full_unified_service._gateway_keys.list.return_value = ([key], None)
        full_unified_service._konnect_keys = None

        result = full_unified_service.list_keys()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_keys_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge keys from both sources."""
        gw_key = Key(id="key-gw-1", kid="gw-key-id")
        kn_key = Key(id="key-kn-1", kid="kn-key-id")
        full_unified_service._gateway_keys.list.return_value = ([gw_key], None)
        full_unified_service._konnect_keys.list.return_value = ([kn_key], None)

        result = full_unified_service.list_keys()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_keys_merged_by_kid(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge keys that share the same kid."""
        gw_key = Key(id="key-gw-1", kid="shared-key-id")
        kn_key = Key(id="key-kn-1", kid="shared-key-id")
        full_unified_service._gateway_keys.list.return_value = ([gw_key], None)
        full_unified_service._konnect_keys.list.return_value = ([kn_key], None)

        result = full_unified_service.list_keys()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_keys_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway key pagination."""
        full_unified_service._konnect_keys = None
        key1 = Key(id="key-1", kid="kid-1")
        key2 = Key(id="key-2", kid="kid-2")
        full_unified_service._gateway_keys.list.side_effect = [
            ([key1], "next-offset"),
            ([key2], None),
        ]

        result = full_unified_service.list_keys()

        assert len(result) == 2
        assert full_unified_service._gateway_keys.list.call_count == 2

    @pytest.mark.unit
    def test_list_keys_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect key pagination."""
        full_unified_service._gateway_keys = None
        key1 = Key(id="key-1", kid="kid-1")
        key2 = Key(id="key-2", kid="kid-2")
        full_unified_service._konnect_keys.list.side_effect = [
            ([key1], "next-offset"),
            ([key2], None),
        ]

        result = full_unified_service.list_keys()

        assert len(result) == 2
        assert full_unified_service._konnect_keys.list.call_count == 2


class TestUnifiedQueryServiceListVaults:
    """Tests for list_vaults operations."""

    @pytest.mark.unit
    def test_list_vaults_no_managers(
        self,
        gateway_only_service: UnifiedQueryService,
    ) -> None:
        """Should return empty list when no vault managers configured."""
        result = gateway_only_service.list_vaults()

        assert len(result) == 0

    @pytest.mark.unit
    def test_list_vaults_gateway_only(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should return vaults from gateway when only gateway manager configured."""
        vault = Vault(id="vault-1", name="env-vault", prefix="env")
        full_unified_service._gateway_vaults.list.return_value = ([vault], None)
        full_unified_service._konnect_vaults = None

        result = full_unified_service.list_vaults()

        assert len(result) == 1
        assert result.gateway_only_count == 1

    @pytest.mark.unit
    def test_list_vaults_both_sources(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge vaults from both sources."""
        gw_vault = Vault(id="vault-gw-1", name="gw-env-vault", prefix="gw-env")
        kn_vault = Vault(id="vault-kn-1", name="kn-env-vault", prefix="kn-env")
        full_unified_service._gateway_vaults.list.return_value = ([gw_vault], None)
        full_unified_service._konnect_vaults.list.return_value = ([kn_vault], None)

        result = full_unified_service.list_vaults()

        assert len(result) == 2
        assert result.gateway_only_count == 1
        assert result.konnect_only_count == 1

    @pytest.mark.unit
    def test_list_vaults_merged_by_name(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should merge vaults that share the same name."""
        gw_vault = Vault(id="vault-gw-1", name="shared-vault", prefix="env")
        kn_vault = Vault(id="vault-kn-1", name="shared-vault", prefix="env")
        full_unified_service._gateway_vaults.list.return_value = ([gw_vault], None)
        full_unified_service._konnect_vaults.list.return_value = ([kn_vault], None)

        result = full_unified_service.list_vaults()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_list_vaults_gateway_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle gateway vault pagination."""
        full_unified_service._konnect_vaults = None
        v1 = Vault(id="vault-1", name="vault-one", prefix="v1")
        v2 = Vault(id="vault-2", name="vault-two", prefix="v2")
        full_unified_service._gateway_vaults.list.side_effect = [
            ([v1], "next-offset"),
            ([v2], None),
        ]

        result = full_unified_service.list_vaults()

        assert len(result) == 2
        assert full_unified_service._gateway_vaults.list.call_count == 2

    @pytest.mark.unit
    def test_list_vaults_konnect_pagination(
        self,
        full_unified_service: Any,
    ) -> None:
        """Should handle konnect vault pagination."""
        full_unified_service._gateway_vaults = None
        v1 = Vault(id="vault-1", name="vault-one", prefix="v1")
        v2 = Vault(id="vault-2", name="vault-two", prefix="v2")
        full_unified_service._konnect_vaults.list.side_effect = [
            ([v1], "next-offset"),
            ([v2], None),
        ]

        result = full_unified_service.list_vaults()

        assert len(result) == 2
        assert full_unified_service._konnect_vaults.list.call_count == 2


class TestUnifiedQueryServicePluginMerge:
    """Tests for plugin merge key generation without instance_name."""

    @pytest.mark.unit
    def test_plugin_key_without_instance_name_global(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should generate key from name only for global plugins without instance_name."""
        gw_plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name=None,
            config={"minute": 100},
        )
        kn_plugin = KongPluginEntity(
            id="kn-1",
            name="rate-limiting",
            instance_name=None,
            config={"minute": 100},
        )
        mock_gateway_managers["plugin"].list.return_value = ([gw_plugin], None)
        mock_konnect_managers["plugin"].list.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins()

        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_plugin_key_with_service_scope_no_instance_name(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should generate key including service scope for scoped plugins without instance_name."""
        service_ref = KongEntityReference(id="svc-uuid-1")
        gw_plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name=None,
            service=service_ref,
        )
        kn_plugin = KongPluginEntity(
            id="kn-1",
            name="rate-limiting",
            instance_name=None,
            service=service_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = ([gw_plugin], None)
        mock_konnect_managers["plugin"].list.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins()

        # Same name + same service scope -> merged
        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_plugin_key_with_route_scope_no_instance_name(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should generate key including route scope for plugins without instance_name."""
        route_ref = KongEntityReference(id="rt-uuid-1")
        gw_plugin = KongPluginEntity(
            id="gw-1",
            name="key-auth",
            instance_name=None,
            route=route_ref,
        )
        kn_plugin = KongPluginEntity(
            id="kn-1",
            name="key-auth",
            instance_name=None,
            route=route_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = ([gw_plugin], None)
        mock_konnect_managers["plugin"].list.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins()

        # Same name + same route scope -> merged
        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_plugin_key_with_consumer_scope_no_instance_name(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should generate key including consumer scope for plugins without instance_name."""
        consumer_ref = KongEntityReference(id="con-uuid-1")
        gw_plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name=None,
            consumer=consumer_ref,
        )
        kn_plugin = KongPluginEntity(
            id="kn-1",
            name="rate-limiting",
            instance_name=None,
            consumer=consumer_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = ([gw_plugin], None)
        mock_konnect_managers["plugin"].list.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins()

        # Same name + same consumer scope -> merged
        assert len(result) == 1
        assert result.in_both_count == 1

    @pytest.mark.unit
    def test_plugin_different_scopes_not_merged(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should NOT merge plugins with same name but different scopes."""
        svc_ref = KongEntityReference(id="svc-uuid-1")
        route_ref = KongEntityReference(id="rt-uuid-1")
        plugin_on_svc = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name=None,
            service=svc_ref,
        )
        plugin_on_route = KongPluginEntity(
            id="gw-2",
            name="rate-limiting",
            instance_name=None,
            route=route_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = (
            [plugin_on_svc, plugin_on_route],
            None,
        )
        mock_konnect_managers["plugin"].list.return_value = ([], None)

        result = unified_service.list_plugins()

        # Different scopes generate different keys -> not merged
        assert len(result) == 2

    @pytest.mark.unit
    def test_plugin_key_service_scope_missing_id(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should use 'unknown' when service ref has no ID."""
        service_ref_no_id = KongEntityReference(name="my-service")
        plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name=None,
            service=service_ref_no_id,
        )
        mock_gateway_managers["plugin"].list.return_value = ([plugin], None)
        mock_konnect_managers["plugin"].list.return_value = ([], None)

        result = unified_service.list_plugins()

        # Plugin still returned, key uses 'unknown' for missing ID
        assert len(result) == 1
        assert result.gateway_only_count == 1


class TestUnifiedQueryServiceKonnectPagination:
    """Tests for Konnect pagination across multiple entity types."""

    @pytest.mark.unit
    def test_konnect_services_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate through all konnect services."""
        mock_gateway_managers["service"].list.return_value = ([], None)
        page1 = [Service(id="kn-1", name="service-1", host="s1.konnect")]
        page2 = [Service(id="kn-2", name="service-2", host="s2.konnect")]
        mock_konnect_managers["service"].list.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_services()

        assert len(result) == 2
        assert mock_konnect_managers["service"].list.call_count == 2

    @pytest.mark.unit
    def test_konnect_consumers_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate through all konnect consumers."""
        mock_gateway_managers["consumer"].list.return_value = ([], None)
        page1 = [Consumer(id="kn-1", username="user-1")]
        page2 = [Consumer(id="kn-2", username="user-2")]
        mock_konnect_managers["consumer"].list.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_consumers()

        assert len(result) == 2
        assert mock_konnect_managers["consumer"].list.call_count == 2

    @pytest.mark.unit
    def test_konnect_routes_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate through all konnect routes."""
        mock_gateway_managers["route"].list.return_value = ([], None)
        page1 = [Route(id="kn-1", name="route-1", paths=["/v1"])]
        page2 = [Route(id="kn-2", name="route-2", paths=["/v2"])]
        mock_konnect_managers["route"].list.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_routes()

        assert len(result) == 2
        assert mock_konnect_managers["route"].list.call_count == 2

    @pytest.mark.unit
    def test_konnect_routes_by_service_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate konnect routes filtered by service."""
        mock_gateway_managers["route"].list_by_service.return_value = ([], None)
        page1 = [Route(id="kn-1", name="route-1", paths=["/v1"])]
        page2 = [Route(id="kn-2", name="route-2", paths=["/v2"])]
        mock_konnect_managers["route"].list_by_service.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_routes(service_name_or_id="my-service")

        assert len(result) == 2
        assert mock_konnect_managers["route"].list_by_service.call_count == 2

    @pytest.mark.unit
    def test_konnect_upstreams_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate through all konnect upstreams."""
        mock_gateway_managers["upstream"].list.return_value = ([], None)
        page1 = [Upstream(id="kn-1", name="upstream-1")]
        page2 = [Upstream(id="kn-2", name="upstream-2")]
        mock_konnect_managers["upstream"].list.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_upstreams()

        assert len(result) == 2
        assert mock_konnect_managers["upstream"].list.call_count == 2

    @pytest.mark.unit
    def test_konnect_plugins_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate through all konnect plugins."""
        mock_gateway_managers["plugin"].list.return_value = ([], None)
        page1 = [KongPluginEntity(id="kn-1", name="rate-limiting", instance_name="rl-1")]
        page2 = [KongPluginEntity(id="kn-2", name="key-auth", instance_name="ka-1")]
        mock_konnect_managers["plugin"].list.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_plugins()

        assert len(result) == 2
        assert mock_konnect_managers["plugin"].list.call_count == 2


class TestUnifiedQueryServicePluginFiltering:
    """Tests for gateway plugin scope filtering and konnect list_by_route/list_by_consumer."""

    @pytest.mark.unit
    def test_gateway_plugins_filtered_by_route(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter gateway plugins by route scope locally."""
        route_ref = KongEntityReference(id="route-uuid-1")
        other_ref = KongEntityReference(id="route-uuid-2")
        matching_plugin = KongPluginEntity(
            id="gw-1",
            name="key-auth",
            instance_name="ka-route",
            route=route_ref,
        )
        non_matching_plugin = KongPluginEntity(
            id="gw-2",
            name="key-auth",
            instance_name="ka-other",
            route=other_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = (
            [matching_plugin, non_matching_plugin],
            None,
        )
        mock_konnect_managers["plugin"].list_by_route.return_value = ([], None)

        result = unified_service.list_plugins(route_name_or_id="route-uuid-1")

        assert len(result) == 1
        assert result.entities[0].entity.instance_name == "ka-route"
        mock_konnect_managers["plugin"].list_by_route.assert_called()

    @pytest.mark.unit
    def test_gateway_plugins_filtered_by_consumer(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter gateway plugins by consumer scope locally."""
        consumer_ref = KongEntityReference(id="consumer-uuid-1")
        other_ref = KongEntityReference(id="consumer-uuid-2")
        matching_plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name="rl-consumer",
            consumer=consumer_ref,
        )
        non_matching_plugin = KongPluginEntity(
            id="gw-2",
            name="rate-limiting",
            instance_name="rl-other",
            consumer=other_ref,
        )
        mock_gateway_managers["plugin"].list.return_value = (
            [matching_plugin, non_matching_plugin],
            None,
        )
        mock_konnect_managers["plugin"].list_by_consumer.return_value = ([], None)

        result = unified_service.list_plugins(consumer_name_or_id="consumer-uuid-1")

        assert len(result) == 1
        assert result.entities[0].entity.instance_name == "rl-consumer"
        mock_konnect_managers["plugin"].list_by_consumer.assert_called()

    @pytest.mark.unit
    def test_konnect_plugins_list_by_route(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should use list_by_route for Konnect when route filter specified."""
        mock_gateway_managers["plugin"].list.return_value = ([], None)
        kn_plugin = KongPluginEntity(id="kn-1", name="jwt", instance_name="jwt-route")
        mock_konnect_managers["plugin"].list_by_route.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins(route_name_or_id="my-route")

        assert len(result) == 1
        mock_konnect_managers["plugin"].list_by_route.assert_called_once()
        mock_konnect_managers["plugin"].list.assert_not_called()

    @pytest.mark.unit
    def test_konnect_plugins_list_by_consumer(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should use list_by_consumer for Konnect when consumer filter specified."""
        mock_gateway_managers["plugin"].list.return_value = ([], None)
        kn_plugin = KongPluginEntity(id="kn-1", name="rate-limiting", instance_name="rl-consumer")
        mock_konnect_managers["plugin"].list_by_consumer.return_value = ([kn_plugin], None)

        result = unified_service.list_plugins(consumer_name_or_id="my-consumer")

        assert len(result) == 1
        mock_konnect_managers["plugin"].list_by_consumer.assert_called_once()
        mock_konnect_managers["plugin"].list.assert_not_called()

    @pytest.mark.unit
    def test_gateway_plugins_filter_by_service_name(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should filter gateway plugins by service name (not just ID)."""
        service_ref_by_name = KongEntityReference(name="my-service")
        matching_plugin = KongPluginEntity(
            id="gw-1",
            name="rate-limiting",
            instance_name="rl-named-svc",
            service=service_ref_by_name,
        )
        mock_gateway_managers["plugin"].list.return_value = ([matching_plugin], None)
        mock_konnect_managers["plugin"].list_by_service.return_value = ([], None)

        result = unified_service.list_plugins(service_name_or_id="my-service")

        assert len(result) == 1
        assert result.entities[0].entity.instance_name == "rl-named-svc"

    @pytest.mark.unit
    def test_konnect_plugins_list_by_service_pagination(
        self,
        unified_service: UnifiedQueryService,
        mock_gateway_managers: dict[str, MagicMock],
        mock_konnect_managers: dict[str, MagicMock],
    ) -> None:
        """Should paginate konnect plugins filtered by service."""
        mock_gateway_managers["plugin"].list.return_value = ([], None)
        page1 = [KongPluginEntity(id="kn-1", name="rate-limiting", instance_name="rl-1")]
        page2 = [KongPluginEntity(id="kn-2", name="key-auth", instance_name="ka-1")]
        mock_konnect_managers["plugin"].list_by_service.side_effect = [
            (page1, "offset-page2"),
            (page2, None),
        ]

        result = unified_service.list_plugins(service_name_or_id="my-service")

        assert len(result) == 2
        assert mock_konnect_managers["plugin"].list_by_service.call_count == 2
