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
            "data": {},
        }

        health = manager.get_health("my-upstream")

        assert health.health == "HEALTHY"


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
