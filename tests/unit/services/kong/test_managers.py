"""Unit tests for Kong entity managers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.services.kong.consumer_manager import ConsumerManager
from system_operations_manager.services.kong.plugin_manager import KongPluginManager
from system_operations_manager.services.kong.route_manager import RouteManager
from system_operations_manager.services.kong.service_manager import ServiceManager
from system_operations_manager.services.kong.upstream_manager import UpstreamManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


class TestServiceManager:
    """Tests for ServiceManager."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> ServiceManager:
        """Create a ServiceManager with mock client."""
        return ServiceManager(mock_client)

    @pytest.mark.unit
    def test_list_services(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list should return services and pagination offset."""
        mock_client.get.return_value = {
            "data": [
                {"id": "svc-1", "name": "api", "host": "api.local", "port": 80},
                {"id": "svc-2", "name": "web", "host": "web.local", "port": 80},
            ],
            "offset": "next-page",
        }

        services, offset = manager.list()

        assert len(services) == 2
        assert services[0].name == "api"
        assert offset == "next-page"

    @pytest.mark.unit
    def test_list_with_tags(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list should pass tags parameter."""
        mock_client.get.return_value = {"data": [], "offset": None}

        manager.list(tags=["production", "v2"])

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "production,v2" in str(call_args)

    @pytest.mark.unit
    def test_get_service(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """get should return a single service."""
        mock_client.get.return_value = {
            "id": "svc-1",
            "name": "api",
            "host": "api.local",
            "port": 8080,
        }

        service = manager.get("api")

        assert service.name == "api"
        assert service.port == 8080

    @pytest.mark.unit
    def test_create_service(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """create should POST and return created service."""
        mock_client.post.return_value = {
            "id": "new-id",
            "name": "new-api",
            "host": "api.example.com",
            "port": 80,
        }

        service = Service(name="new-api", host="api.example.com")
        created = manager.create(service)

        assert created.id == "new-id"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_update_service(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """update should PATCH and return updated service."""
        mock_client.patch.return_value = {
            "id": "svc-1",
            "name": "api",
            "host": "new-host.local",
            "port": 80,
        }

        service = Service(host="new-host.local")
        updated = manager.update("svc-1", service)

        assert updated.host == "new-host.local"

    @pytest.mark.unit
    def test_delete_service(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """delete should call DELETE endpoint."""
        manager.delete("svc-1")

        mock_client.delete.assert_called_once_with("services/svc-1")

    @pytest.mark.unit
    def test_get_routes(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """get_routes should return routes for a service."""
        mock_client.get.return_value = {
            "data": [
                {"id": "route-1", "paths": ["/api"]},
            ],
        }

        routes = manager.get_routes("my-service")

        assert len(routes) == 1
        assert routes[0].paths == ["/api"]

    @pytest.mark.unit
    def test_exists_returns_true(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """exists should return True for existing service."""
        mock_client.get.return_value = {"id": "svc-1", "name": "api"}

        assert manager.exists("api") is True

    @pytest.mark.unit
    def test_exists_returns_false(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """exists should return False for non-existing service."""
        mock_client.get.side_effect = KongNotFoundError("Not found", "services/none")

        assert manager.exists("none") is False


class TestRouteManager:
    """Tests for RouteManager."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> RouteManager:
        """Create a RouteManager with mock client."""
        return RouteManager(mock_client)

    @pytest.mark.unit
    def test_list_routes(
        self,
        manager: RouteManager,
        mock_client: MagicMock,
    ) -> None:
        """list should return routes."""
        mock_client.get.return_value = {
            "data": [
                {"id": "route-1", "paths": ["/api"]},
            ],
        }

        routes, _ = manager.list()

        assert len(routes) == 1

    @pytest.mark.unit
    def test_list_by_service(
        self,
        manager: RouteManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_service should filter by service."""
        mock_client.get.return_value = {
            "data": [
                {"id": "route-1", "paths": ["/api"]},
            ],
        }

        routes, _ = manager.list_by_service("my-service")

        # Check that the call was made with service routes endpoint
        call_args = mock_client.get.call_args
        assert "services/my-service/routes" in str(call_args)
        assert len(routes) == 1

    @pytest.mark.unit
    def test_create_for_service(
        self,
        manager: RouteManager,
        mock_client: MagicMock,
    ) -> None:
        """create_for_service should create route under service."""
        mock_client.post.return_value = {
            "id": "new-route",
            "paths": ["/api"],
            "service": {"id": "svc-1"},
        }

        route = Route(paths=["/api"])
        created = manager.create_for_service("svc-1", route)

        assert created.id == "new-route"
        mock_client.post.assert_called_once()


class TestConsumerManager:
    """Tests for ConsumerManager."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> ConsumerManager:
        """Create a ConsumerManager with mock client."""
        return ConsumerManager(mock_client)

    @pytest.mark.unit
    def test_list_consumers(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """list should return consumers."""
        mock_client.get.return_value = {
            "data": [
                {"id": "consumer-1", "username": "user1"},
            ],
        }

        consumers, _ = manager.list()

        assert len(consumers) == 1
        assert consumers[0].username == "user1"

    @pytest.mark.unit
    def test_list_credentials(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """list_credentials should return typed credentials."""
        mock_client.get.return_value = {
            "data": [
                {"id": "cred-1", "key": "my-key"},
            ],
        }

        creds = manager.list_credentials("user1", "key-auth")

        assert len(creds) == 1

    @pytest.mark.unit
    def test_add_credential(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """add_credential should POST credential."""
        mock_client.post.return_value = {
            "id": "new-cred",
            "key": "generated-key",
        }

        cred = manager.add_credential("user1", "key-auth", {})

        assert cred.id == "new-cred"

    @pytest.mark.unit
    def test_delete_credential(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """delete_credential should DELETE credential."""
        manager.delete_credential("user1", "key-auth", "cred-1")

        mock_client.delete.assert_called_once()

    @pytest.mark.unit
    def test_list_acl_groups(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """list_acl_groups should return ACL groups."""
        mock_client.get.return_value = {
            "data": [
                {"id": "acl-1", "group": "admin"},
            ],
        }

        acls = manager.list_acl_groups("user1")

        assert len(acls) == 1
        assert acls[0].group == "admin"

    @pytest.mark.unit
    def test_add_to_acl_group(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """add_to_acl_group should POST ACL group."""
        mock_client.post.return_value = {
            "id": "new-acl",
            "group": "admin",
        }

        acl = manager.add_to_acl_group("user1", "admin")

        assert acl.group == "admin"


class TestUpstreamManager:
    """Tests for UpstreamManager."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> UpstreamManager:
        """Create an UpstreamManager with mock client."""
        return UpstreamManager(mock_client)

    @pytest.mark.unit
    def test_list_upstreams(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """list should return upstreams."""
        mock_client.get.return_value = {
            "data": [
                {"id": "upstream-1", "name": "my-upstream"},
            ],
        }

        upstreams, _ = manager.list()

        assert len(upstreams) == 1

    @pytest.mark.unit
    def test_list_targets(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """list_targets should return targets for upstream."""
        mock_client.get.return_value = {
            "data": [
                {"id": "target-1", "target": "192.168.1.1:8080", "weight": 100},
            ],
        }

        targets, _ = manager.list_targets("my-upstream")

        assert len(targets) == 1
        assert targets[0].target == "192.168.1.1:8080"

    @pytest.mark.unit
    def test_add_target(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """add_target should POST target."""
        mock_client.post.return_value = {
            "id": "new-target",
            "target": "192.168.1.2:8080",
            "weight": 100,
        }

        target = manager.add_target("my-upstream", "192.168.1.2:8080")

        assert target.target == "192.168.1.2:8080"

    @pytest.mark.unit
    def test_delete_target(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """delete_target should DELETE target."""
        manager.delete_target("my-upstream", "target-1")

        mock_client.delete.assert_called_once()

    @pytest.mark.unit
    def test_get_health(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """get_health should return upstream health."""
        mock_client.get.return_value = {
            "id": "upstream-1",
            "health": "HEALTHY",
            "data": [],
        }

        health = manager.get_health("my-upstream")

        assert health.health == "HEALTHY"


class TestBaseEntityManagerEdgeCases:
    """Edge case tests for BaseEntityManager functionality."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> ServiceManager:
        """Create a ServiceManager with mock client for testing base features."""
        return ServiceManager(mock_client)

    @pytest.mark.unit
    def test_endpoint_property(self, manager: ServiceManager) -> None:
        """endpoint property should return the API endpoint."""
        assert manager.endpoint == "services"

    @pytest.mark.unit
    def test_list_with_all_pagination_params(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list should pass limit and offset parameters."""
        mock_client.get.return_value = {"data": [], "offset": None}

        manager.list(limit=50, offset="abc123")

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["size"] == 50
        assert call_args[1]["params"]["offset"] == "abc123"

    @pytest.mark.unit
    def test_list_with_custom_filters(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list should pass custom filter parameters."""
        mock_client.get.return_value = {"data": [], "offset": None}

        manager.list(host="api.example.com", protocol="https")

        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["host"] == "api.example.com"
        assert call_args[1]["params"]["protocol"] == "https"

    @pytest.mark.unit
    def test_list_empty_response(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list should handle empty response."""
        mock_client.get.return_value = {}

        entities, offset = manager.list()

        assert entities == []
        assert offset is None

    @pytest.mark.unit
    def test_upsert_creates_entity(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """upsert should create entity if it doesn't exist."""
        mock_client.put.return_value = {
            "id": "svc-new",
            "name": "new-service",
            "host": "api.example.com",
            "port": 80,
        }

        service = Service(name="new-service", host="api.example.com")
        result = manager.upsert("new-service", service)

        assert result.id == "svc-new"
        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert call_args[0][0] == "services/new-service"

    @pytest.mark.unit
    def test_upsert_updates_entity(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """upsert should update entity if it exists."""
        mock_client.put.return_value = {
            "id": "svc-1",
            "name": "existing-service",
            "host": "new-host.example.com",
            "port": 80,
        }

        service = Service(name="existing-service", host="new-host.example.com")
        result = manager.upsert("existing-service", service)

        assert result.host == "new-host.example.com"

    @pytest.mark.unit
    def test_count_single_page(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """count should return count for single page of results."""
        mock_client.get.return_value = {
            "data": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "offset": None,
        }

        result = manager.count()

        assert result == 3

    @pytest.mark.unit
    def test_count_multiple_pages(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """count should paginate through all results."""
        mock_client.get.side_effect = [
            {"data": [{"id": "1"}, {"id": "2"}], "offset": "page2"},
            {"data": [{"id": "3"}, {"id": "4"}], "offset": "page3"},
            {"data": [{"id": "5"}], "offset": None},
        ]

        result = manager.count()

        assert result == 5
        assert mock_client.get.call_count == 3

    @pytest.mark.unit
    def test_count_with_tags(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """count should filter by tags."""
        mock_client.get.return_value = {
            "data": [{"id": "1"}],
            "offset": None,
        }

        result = manager.count(tags=["production"])

        assert result == 1
        call_args = mock_client.get.call_args
        assert "production" in str(call_args)

    @pytest.mark.unit
    def test_count_empty(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """count should return 0 for empty results."""
        mock_client.get.return_value = {"data": [], "offset": None}

        result = manager.count()

        assert result == 0


class TestKongPluginManager:
    """Tests for KongPluginManager."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> KongPluginManager:
        """Create a KongPluginManager with mock client."""
        return KongPluginManager(mock_client)

    @pytest.mark.unit
    def test_list_plugins(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list should return plugins."""
        mock_client.get.return_value = {
            "data": [
                {"id": "plugin-1", "name": "rate-limiting", "enabled": True},
            ],
        }

        plugins, _ = manager.list()

        assert len(plugins) == 1
        assert plugins[0].name == "rate-limiting"

    @pytest.mark.unit
    def test_list_available(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_available should return available plugins."""
        mock_client.get_info.return_value = {
            "plugins": {
                "available_on_server": {
                    "rate-limiting": {"version": "3.0.0", "priority": 901},
                    "key-auth": {"version": "3.0.0", "priority": 1003},
                },
            },
        }

        available = manager.list_available()

        assert "rate-limiting" in available
        assert "key-auth" in available
        assert available["rate-limiting"].version == "3.0.0"

    @pytest.mark.unit
    def test_list_enabled(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_enabled should return enabled plugin names."""
        mock_client.get_info.return_value = {
            "plugins": {
                "enabled_in_cluster": ["rate-limiting", "key-auth"],
            },
        }

        enabled = manager.list_enabled()

        assert "rate-limiting" in enabled
        assert "key-auth" in enabled

    @pytest.mark.unit
    def test_enable_plugin_globally(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """enable should create global plugin."""
        mock_client.post.return_value = {
            "id": "new-plugin",
            "name": "rate-limiting",
            "enabled": True,
            "config": {"minute": 100},
        }

        plugin = manager.enable("rate-limiting", config={"minute": 100})

        assert plugin.name == "rate-limiting"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_enable_plugin_for_service(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """enable should scope plugin to service."""
        mock_client.post.return_value = {
            "id": "new-plugin",
            "name": "key-auth",
            "enabled": True,
            "service": {"id": "svc-1"},
        }

        manager.enable("key-auth", service="svc-1")

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["service"] == {"id": "svc-1"}

    @pytest.mark.unit
    def test_disable_plugin(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """disable should delete plugin."""
        manager.disable("plugin-1")

        mock_client.delete.assert_called_once_with("plugins/plugin-1")

    @pytest.mark.unit
    def test_update_config(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """update_config should PATCH plugin configuration."""
        mock_client.patch.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "enabled": True,
            "config": {"minute": 200},
        }

        plugin = manager.update_config("plugin-1", {"minute": 200})

        assert plugin.config == {"minute": 200}

    @pytest.mark.unit
    def test_toggle(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """toggle should enable/disable plugin."""
        mock_client.patch.return_value = {
            "id": "plugin-1",
            "name": "rate-limiting",
            "enabled": False,
        }

        plugin = manager.toggle("plugin-1", False)

        assert plugin.enabled is False

    @pytest.mark.unit
    def test_get_schema(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """get_schema should return plugin schema."""
        mock_client.get.return_value = {
            "fields": [{"config": {"type": "record"}}],
        }

        schema = manager.get_schema("rate-limiting")

        assert schema.name == "rate-limiting"
        assert schema.fields is not None
        assert len(schema.fields) == 1

    @pytest.mark.unit
    def test_list_by_service(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_service should filter by service."""
        mock_client.get.return_value = {
            "data": [
                {"id": "plugin-1", "name": "rate-limiting", "enabled": True},
            ],
        }

        plugins = manager.list_by_service("my-service")

        mock_client.get.assert_called_with("services/my-service/plugins")
        assert len(plugins) == 1

    @pytest.mark.unit
    def test_list_available_non_dict_data(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_available should handle non-dict plugin data (booleans)."""
        mock_client.get_info.return_value = {
            "plugins": {
                "available_on_server": {
                    "basic-auth": True,
                    "key-auth": {"version": "1.0"},
                }
            }
        }
        available = manager.list_available()
        assert "basic-auth" in available
        assert available["basic-auth"].name == "basic-auth"

    @pytest.mark.unit
    def test_list_by_route(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_route should filter by route."""
        mock_client.get.return_value = {"data": [{"id": "p1", "name": "cors", "enabled": True}]}
        plugins = manager.list_by_route("my-route")
        assert len(plugins) == 1
        mock_client.get.assert_called_with("routes/my-route/plugins")

    @pytest.mark.unit
    def test_list_by_consumer(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_consumer should filter by consumer."""
        mock_client.get.return_value = {
            "data": [{"id": "p1", "name": "rate-limiting", "enabled": True}]
        }
        plugins = manager.list_by_consumer("my-consumer")
        assert len(plugins) == 1
        mock_client.get.assert_called_with("consumers/my-consumer/plugins")

    @pytest.mark.unit
    def test_enable_with_all_params(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """enable should pass route, consumer, protocols, and instance_name."""
        mock_client.post.return_value = {
            "id": "p1",
            "name": "rate-limiting",
            "enabled": True,
        }
        manager.enable(
            "rate-limiting",
            route="r1",
            consumer="c1",
            protocols=["http"],
            instance_name="rl-1",
        )
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["route"] == {"id": "r1"}
        assert payload["consumer"] == {"id": "c1"}
        assert payload["protocols"] == ["http"]
        assert payload["instance_name"] == "rl-1"

    @pytest.mark.unit
    def test_update_config_with_enabled(
        self,
        manager: KongPluginManager,
        mock_client: MagicMock,
    ) -> None:
        """update_config should pass enabled param when provided."""
        mock_client.patch.return_value = {
            "id": "p1",
            "name": "rl",
            "enabled": False,
            "config": {"minute": 10},
        }
        plugin = manager.update_config("p1", {"minute": 10}, enabled=False)
        call_args = mock_client.patch.call_args
        assert call_args[1]["json"]["enabled"] is False
        assert plugin.enabled is False


class TestServiceManagerExtended:
    """Additional tests for ServiceManager missing coverage."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> ServiceManager:
        """Create a ServiceManager with mock client."""
        return ServiceManager(mock_client)

    @pytest.mark.unit
    def test_get_plugins(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """get_plugins should return list of plugin dicts for a service."""
        mock_client.get.return_value = {"data": [{"id": "p1", "name": "rate-limiting"}]}
        plugins = manager.get_plugins("my-service")
        assert len(plugins) == 1
        mock_client.get.assert_called_once_with("services/my-service/plugins")

    @pytest.mark.unit
    def test_list_by_tag(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_tag should return services filtered by a single tag."""
        mock_client.get.return_value = {
            "data": [{"id": "s1", "name": "svc", "host": "h.local"}],
            "offset": None,
        }
        services = manager.list_by_tag("production")
        assert len(services) == 1

    @pytest.mark.unit
    def test_enable(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """enable should call update with enabled=True."""
        mock_client.patch.return_value = {
            "id": "s1",
            "name": "svc",
            "host": "h.local",
            "enabled": True,
        }
        result = manager.enable("svc")
        assert result.enabled is True

    @pytest.mark.unit
    def test_disable(
        self,
        manager: ServiceManager,
        mock_client: MagicMock,
    ) -> None:
        """disable should call update with enabled=False."""
        mock_client.patch.return_value = {
            "id": "s1",
            "name": "svc",
            "host": "h.local",
            "enabled": False,
        }
        result = manager.disable("svc")
        assert result.enabled is False


class TestRouteManagerExtended:
    """Additional tests for RouteManager missing coverage."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> RouteManager:
        """Create a RouteManager with mock client."""
        return RouteManager(mock_client)

    @pytest.mark.unit
    def test_list_by_service_with_params(
        self,
        manager: RouteManager,
        mock_client: MagicMock,
    ) -> None:
        """list_by_service should pass tags, limit, and offset params."""
        mock_client.get.return_value = {"data": [], "offset": None}
        manager.list_by_service("svc", tags=["prod"], limit=50, offset="abc")
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["tags"] == "prod"
        assert call_args[1]["params"]["size"] == 50
        assert call_args[1]["params"]["offset"] == "abc"

    @pytest.mark.unit
    def test_get_plugins(
        self,
        manager: RouteManager,
        mock_client: MagicMock,
    ) -> None:
        """get_plugins should return list of plugin dicts for a route."""
        mock_client.get.return_value = {"data": [{"id": "p1", "name": "key-auth"}]}
        plugins = manager.get_plugins("my-route")
        assert len(plugins) == 1
        mock_client.get.assert_called_once_with("routes/my-route/plugins")


class TestConsumerManagerExtended:
    """Additional tests for ConsumerManager missing coverage."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> ConsumerManager:
        """Create a ConsumerManager with mock client."""
        return ConsumerManager(mock_client)

    @pytest.mark.unit
    def test_get_credential(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """get_credential should return a specific credential."""
        mock_client.get.return_value = {"id": "cred-1", "key": "my-key"}
        cred = manager.get_credential("user1", "key-auth", "cred-1")
        assert cred.id == "cred-1"

    @pytest.mark.unit
    def test_add_to_acl_group_with_tags(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """add_to_acl_group should pass tags in the payload."""
        mock_client.post.return_value = {"id": "acl-1", "group": "admin"}
        acl = manager.add_to_acl_group("user1", "admin", tags=["env:prod"])
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["tags"] == ["env:prod"]
        assert acl.group == "admin"

    @pytest.mark.unit
    def test_remove_from_acl_group(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """remove_from_acl_group should DELETE the ACL entry."""
        manager.remove_from_acl_group("user1", "acl-1")
        mock_client.delete.assert_called_once_with("consumers/user1/acls/acl-1")

    @pytest.mark.unit
    def test_get_plugins(
        self,
        manager: ConsumerManager,
        mock_client: MagicMock,
    ) -> None:
        """get_plugins should return list of plugin dicts for a consumer."""
        mock_client.get.return_value = {"data": [{"id": "p1", "name": "rate-limiting"}]}
        plugins = manager.get_plugins("user1")
        assert len(plugins) == 1
        mock_client.get.assert_called_once_with("consumers/user1/plugins")

    @pytest.mark.unit
    def test_unknown_credential_type(
        self,
        manager: ConsumerManager,
    ) -> None:
        """_get_credential_endpoint should raise ValueError for unknown type."""
        with pytest.raises(ValueError, match="Unknown credential type"):
            manager._get_credential_endpoint("invalid-type")


class TestUpstreamManagerExtended:
    """Additional tests for UpstreamManager missing coverage."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> UpstreamManager:
        """Create an UpstreamManager with mock client."""
        return UpstreamManager(mock_client)

    @pytest.mark.unit
    def test_list_targets_with_params(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """list_targets should pass limit and offset params."""
        mock_client.get.return_value = {"data": [], "offset": "next"}
        _targets, offset = manager.list_targets("ups", limit=10, offset="abc")
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["size"] == 10
        assert call_args[1]["params"]["offset"] == "abc"
        assert offset == "next"

    @pytest.mark.unit
    def test_get_target(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """get_target should return a specific target by ID."""
        mock_client.get.return_value = {
            "id": "t1",
            "target": "10.0.0.1:8080",
            "weight": 100,
        }
        target = manager.get_target("ups", "t1")
        assert target.target == "10.0.0.1:8080"
        mock_client.get.assert_called_once_with("upstreams/ups/targets/t1")

    @pytest.mark.unit
    def test_add_target_with_tags(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """add_target should include tags and weight in the payload."""
        mock_client.post.return_value = {
            "id": "t1",
            "target": "10.0.0.1:8080",
            "weight": 50,
        }
        target = manager.add_target("ups", "10.0.0.1:8080", weight=50, tags=["canary"])
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["tags"] == ["canary"]
        assert call_args[1]["json"]["weight"] == 50
        assert target.weight == 50

    @pytest.mark.unit
    def test_update_target_with_weight(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """update_target should PATCH with the new weight."""
        mock_client.patch.return_value = {
            "id": "t1",
            "target": "10.0.0.1:8080",
            "weight": 200,
        }
        target = manager.update_target("ups", "t1", weight=200)
        assert target.weight == 200

    @pytest.mark.unit
    def test_update_target_with_tags(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """update_target should PATCH with the new tags."""
        mock_client.patch.return_value = {
            "id": "t1",
            "target": "10.0.0.1:8080",
            "weight": 100,
        }
        manager.update_target("ups", "t1", tags=["new-tag"])
        call_args = mock_client.patch.call_args
        assert call_args[1]["json"]["tags"] == ["new-tag"]

    @pytest.mark.unit
    def test_update_target_no_changes(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """update_target with no args should return current target without PATCHing."""
        mock_client.get.return_value = {
            "id": "t1",
            "target": "10.0.0.1:8080",
            "weight": 100,
        }
        target = manager.update_target("ups", "t1")
        mock_client.patch.assert_not_called()
        assert target.target == "10.0.0.1:8080"

    @pytest.mark.unit
    def test_get_targets_health(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """get_targets_health should return list of target health data."""
        mock_client.get.return_value = {"data": [{"target": "10.0.0.1:8080", "health": "HEALTHY"}]}
        data = manager.get_targets_health("ups")
        assert len(data) == 1

    @pytest.mark.unit
    def test_set_target_healthy(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """set_target_healthy should PUT to the /healthy endpoint."""
        manager.set_target_healthy("ups", "t1")
        mock_client.put.assert_called_once_with("upstreams/ups/targets/t1/healthy", json={})

    @pytest.mark.unit
    def test_set_target_unhealthy(
        self,
        manager: UpstreamManager,
        mock_client: MagicMock,
    ) -> None:
        """set_target_unhealthy should PUT to the /unhealthy endpoint."""
        manager.set_target_unhealthy("ups", "t1")
        mock_client.put.assert_called_once_with("upstreams/ups/targets/t1/unhealthy", json={})
