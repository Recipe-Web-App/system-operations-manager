"""Integration tests for KongPluginManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.plugin_manager import KongPluginManager


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerAvailable:
    """Test available plugin listing."""

    def test_list_available_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_available should return bundled plugins."""
        available = plugin_manager.list_available()

        # Core bundled plugins should be available
        assert "rate-limiting" in available
        assert "key-auth" in available
        assert "cors" in available
        assert "request-transformer" in available

    def test_list_available_plugins_include_auth_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_available should include authentication plugins."""
        available = plugin_manager.list_available()

        # Authentication plugins
        assert "basic-auth" in available
        assert "jwt" in available
        assert "oauth2" in available
        assert "hmac-auth" in available

    def test_list_available_plugins_include_traffic_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_available should include traffic control plugins."""
        available = plugin_manager.list_available()

        # Traffic control plugins
        assert "request-size-limiting" in available
        assert "response-ratelimiting" in available

    def test_list_enabled_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_enabled should return enabled plugins."""
        enabled = plugin_manager.list_enabled()

        # Bundled plugins are enabled by default
        assert isinstance(enabled, list)
        assert len(enabled) > 0


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerList:
    """Test plugin instance listing."""

    def test_list_all_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list should return plugin instances."""
        plugins, _ = plugin_manager.list()

        # Global correlation-id plugin from declarative config
        assert any(p.name == "correlation-id" for p in plugins)

    def test_list_with_pagination(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list should support pagination."""
        plugins, _ = plugin_manager.list(limit=10)

        assert isinstance(plugins, list)


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerGet:
    """Test plugin retrieval operations."""

    def test_get_plugin_by_id(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get should retrieve plugin by id."""
        # First list to get a plugin id
        plugins, _ = plugin_manager.list()
        assert len(plugins) >= 1

        plugin_id = plugins[0].id
        assert plugin_id is not None
        plugin = plugin_manager.get(plugin_id)

        assert plugin.id == plugin_id

    def test_get_nonexistent_plugin_raises(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get should raise KongNotFoundError for missing plugin."""
        with pytest.raises(KongNotFoundError):
            plugin_manager.get("00000000-0000-0000-0000-000000000000")


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerSchema:
    """Test plugin schema retrieval."""

    def test_get_plugin_schema(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get_schema should return plugin configuration schema."""
        schema = plugin_manager.get_schema("rate-limiting")

        assert schema.name == "rate-limiting"
        assert schema.fields is not None
        assert len(schema.fields) > 0

    def test_get_schema_for_key_auth(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get_schema should return key-auth plugin schema."""
        schema = plugin_manager.get_schema("key-auth")

        assert schema.name == "key-auth"
        assert schema.fields is not None

    def test_get_schema_for_cors(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get_schema should return cors plugin schema."""
        schema = plugin_manager.get_schema("cors")

        assert schema.name == "cors"
        assert schema.fields is not None

    def test_get_schema_nonexistent_plugin(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """get_schema for nonexistent plugin should raise error."""
        with pytest.raises(KongNotFoundError):
            plugin_manager.get_schema("nonexistent-plugin")


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerByScope:
    """Test plugin listing by scope."""

    def test_list_by_service(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_by_service should return service-scoped plugins."""
        plugins = plugin_manager.list_by_service("test-service")

        # May be empty if no plugins on service
        assert isinstance(plugins, list)

    def test_list_by_route(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_by_route should return route-scoped plugins."""
        plugins = plugin_manager.list_by_route("test-route")

        # May be empty if no plugins on route
        assert isinstance(plugins, list)

    def test_list_by_consumer(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """list_by_consumer should return consumer-scoped plugins."""
        plugins = plugin_manager.list_by_consumer("test-user")

        # May be empty if no plugins on consumer
        assert isinstance(plugins, list)


@pytest.mark.integration
@pytest.mark.kong
class TestPluginManagerCount:
    """Test plugin count operations."""

    def test_count_plugins(
        self,
        plugin_manager: KongPluginManager,
    ) -> None:
        """count should return total number of plugin instances."""
        count = plugin_manager.count()

        assert count >= 1  # At least correlation-id
