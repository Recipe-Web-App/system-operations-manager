"""Unit tests for KonnectPluginManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.plugin_manager import KonnectPluginManager


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock Konnect client."""
    return MagicMock()


@pytest.fixture
def plugin_manager(mock_konnect_client: MagicMock) -> KonnectPluginManager:
    """Create a KonnectPluginManager with mock client."""
    return KonnectPluginManager(mock_konnect_client, "cp-123")


class TestKonnectPluginManagerInit:
    """Tests for KonnectPluginManager initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_konnect_client: MagicMock) -> None:
        """Manager should initialize with client and control plane ID."""
        manager = KonnectPluginManager(mock_konnect_client, "cp-123")
        assert manager.control_plane_id == "cp-123"

    @pytest.mark.unit
    def test_control_plane_id_property(self, plugin_manager: KonnectPluginManager) -> None:
        """control_plane_id property should return the ID."""
        assert plugin_manager.control_plane_id == "cp-123"


class TestKonnectPluginManagerList:
    """Tests for list operations."""

    @pytest.mark.unit
    def test_list_plugins(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should return plugins from client."""
        expected_plugins = [
            KongPluginEntity(name="rate-limiting"),
            KongPluginEntity(name="key-auth"),
        ]
        mock_konnect_client.list_plugins.return_value = (expected_plugins, None)

        plugins, _next_offset = plugin_manager.list()

        assert len(plugins) == 2
        assert plugins[0].name == "rate-limiting"
        mock_konnect_client.list_plugins.assert_called_once_with(
            "cp-123", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_with_filters(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass filters to client."""
        mock_konnect_client.list_plugins.return_value = ([], None)

        plugin_manager.list(tags=["prod"], limit=10, offset="abc")

        mock_konnect_client.list_plugins.assert_called_once_with(
            "cp-123", tags=["prod"], limit=10, offset="abc"
        )

    @pytest.mark.unit
    def test_list_by_service(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list_by_service should filter plugins by service."""
        expected_plugins = [KongPluginEntity(name="rate-limiting")]
        mock_konnect_client.list_plugins.return_value = (expected_plugins, None)

        plugins, _next_offset = plugin_manager.list_by_service("my-service")

        assert len(plugins) == 1
        mock_konnect_client.list_plugins.assert_called_once_with(
            "cp-123", service_name_or_id="my-service", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_by_route(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list_by_route should filter plugins by route."""
        expected_plugins = [KongPluginEntity(name="key-auth")]
        mock_konnect_client.list_plugins.return_value = (expected_plugins, None)

        plugins, _next_offset = plugin_manager.list_by_route("my-route")

        assert len(plugins) == 1
        mock_konnect_client.list_plugins.assert_called_once_with(
            "cp-123", route_name_or_id="my-route", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_by_consumer(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list_by_consumer should filter plugins by consumer."""
        expected_plugins = [KongPluginEntity(name="acl")]
        mock_konnect_client.list_plugins.return_value = (expected_plugins, None)

        plugins, _next_offset = plugin_manager.list_by_consumer("my-consumer")

        assert len(plugins) == 1
        mock_konnect_client.list_plugins.assert_called_once_with(
            "cp-123", consumer_name_or_id="my-consumer", tags=None, limit=None, offset=None
        )


class TestKonnectPluginManagerGet:
    """Tests for get operations."""

    @pytest.mark.unit
    def test_get_plugin(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should return plugin from client."""
        expected = KongPluginEntity(id="plugin-123", name="rate-limiting")
        mock_konnect_client.get_plugin.return_value = expected

        result = plugin_manager.get("plugin-123")

        assert result.name == "rate-limiting"
        mock_konnect_client.get_plugin.assert_called_once_with("cp-123", "plugin-123")

    @pytest.mark.unit
    def test_get_plugin_not_found(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should raise NotFoundError when plugin doesn't exist."""
        mock_konnect_client.get_plugin.side_effect = KonnectNotFoundError(
            "Plugin not found", status_code=404
        )

        with pytest.raises(KonnectNotFoundError):
            plugin_manager.get("nonexistent")


class TestKonnectPluginManagerCreate:
    """Tests for create operations."""

    @pytest.mark.unit
    def test_create_plugin(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should create plugin via client."""
        plugin = KongPluginEntity(name="rate-limiting", config={"minute": 100})
        created = KongPluginEntity(id="plugin-new", name="rate-limiting", config={"minute": 100})
        mock_konnect_client.create_plugin.return_value = created

        result = plugin_manager.create(plugin)

        assert result.id == "plugin-new"
        mock_konnect_client.create_plugin.assert_called_once_with("cp-123", plugin)


class TestKonnectPluginManagerUpdate:
    """Tests for update operations."""

    @pytest.mark.unit
    def test_update_plugin(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should update plugin via client."""
        plugin = KongPluginEntity(name="rate-limiting", config={"minute": 200})
        updated = KongPluginEntity(id="plugin-1", name="rate-limiting", config={"minute": 200})
        mock_konnect_client.update_plugin.return_value = updated

        result = plugin_manager.update("plugin-1", plugin)

        assert result.config == {"minute": 200}
        mock_konnect_client.update_plugin.assert_called_once_with("cp-123", "plugin-1", plugin)


class TestKonnectPluginManagerDelete:
    """Tests for delete operations."""

    @pytest.mark.unit
    def test_delete_plugin(
        self,
        plugin_manager: KonnectPluginManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delete plugin via client."""
        plugin_manager.delete("plugin-123")

        mock_konnect_client.delete_plugin.assert_called_once_with("cp-123", "plugin-123")
