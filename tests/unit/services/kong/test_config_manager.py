"""Unit tests for Kong ConfigManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.config import (
    DeclarativeConfig,
)
from system_operations_manager.services.kong.config_manager import ConfigManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> ConfigManager:
    """Create a ConfigManager with mocked client."""
    return ConfigManager(mock_client)


class TestConfigManagerInit:
    """Tests for ConfigManager initialization."""

    @pytest.mark.unit
    def test_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = ConfigManager(mock_client)

        assert manager._client is mock_client


class TestConfigManagerExport:
    """Tests for export_state method."""

    @pytest.mark.unit
    def test_export_state_all_entities(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """export_state should fetch all entity types."""
        mock_client.get.side_effect = [
            {"data": [{"id": "svc-1", "name": "api", "host": "api.local"}]},
            {"data": [{"id": "up-1", "name": "upstream-1"}]},
            {"data": []},  # targets for upstream
            {"data": [{"id": "rt-1", "name": "route-1", "paths": ["/api"]}]},
            {"data": [{"id": "con-1", "username": "user1"}]},
            {"data": [{"id": "pl-1", "name": "rate-limiting"}]},
        ]

        config = manager.export_state()

        assert len(config.services) == 1
        assert len(config.upstreams) == 1
        assert len(config.routes) == 1
        assert len(config.consumers) == 1
        assert len(config.plugins) == 1

    @pytest.mark.unit
    def test_export_state_filtered_entities(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """export_state should filter to specified entity types."""
        mock_client.get.return_value = {
            "data": [{"id": "svc-1", "name": "api", "host": "api.local"}]
        }

        config = manager.export_state(only=["services"])

        assert len(config.services) == 1
        assert len(config.routes) == 0
        assert len(config.plugins) == 0

    @pytest.mark.unit
    def test_export_services_success(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """_export_services should fetch and clean services."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "svc-1",
                    "name": "api",
                    "host": "api.local",
                    "created_at": 1234567890,
                    "updated_at": 1234567890,
                }
            ]
        }

        services = manager._export_services()

        assert len(services) == 1
        assert "created_at" not in services[0]
        assert "updated_at" not in services[0]

    @pytest.mark.unit
    def test_export_routes_success(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """_export_routes should fetch and clean routes."""
        mock_client.get.return_value = {
            "data": [{"id": "rt-1", "name": "route-1", "paths": ["/api"]}]
        }

        routes = manager._export_routes()

        assert len(routes) == 1
        assert routes[0]["paths"] == ["/api"]

    @pytest.mark.unit
    def test_export_upstreams_with_targets(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_export_upstreams should embed targets."""
        mock_client.get.side_effect = [
            {"data": [{"id": "up-1", "name": "upstream-1"}]},
            {"data": [{"target": "192.168.1.1:8080", "weight": 100}]},
        ]

        upstreams = manager._export_upstreams()

        assert len(upstreams) == 1
        assert "targets" in upstreams[0]
        assert len(upstreams[0]["targets"]) == 1

    @pytest.mark.unit
    def test_export_upstreams_targets_error_handled(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_export_upstreams should handle target fetch errors gracefully."""
        mock_client.get.side_effect = [
            {"data": [{"id": "up-1", "name": "upstream-1"}]},
            Exception("Target fetch failed"),
        ]

        upstreams = manager._export_upstreams()

        assert len(upstreams) == 1
        assert "targets" not in upstreams[0]

    @pytest.mark.unit
    def test_export_consumers_without_credentials(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_export_consumers should work without credentials."""
        mock_client.get.return_value = {"data": [{"id": "con-1", "username": "user1"}]}

        consumers = manager._export_consumers(include_credentials=False)

        assert len(consumers) == 1
        assert consumers[0]["username"] == "user1"

    @pytest.mark.unit
    def test_export_consumers_with_credentials(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_export_consumers should include credentials when requested."""
        mock_client.get.side_effect = [
            {"data": [{"id": "con-1", "username": "user1"}]},
            {"data": [{"key": "api-key-123"}]},  # key-auth
            {"data": []},  # basic-auth
            {"data": []},  # jwt
            {"data": []},  # oauth2
            {"data": []},  # acls
        ]

        consumers = manager._export_consumers(include_credentials=True)

        assert len(consumers) == 1
        assert "key_auth" in consumers[0]

    @pytest.mark.unit
    def test_export_plugins_success(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """_export_plugins should fetch and clean plugins."""
        mock_client.get.return_value = {
            "data": [{"id": "pl-1", "name": "rate-limiting", "config": {"minute": 100}}]
        }

        plugins = manager._export_plugins()

        assert len(plugins) == 1
        assert plugins[0]["name"] == "rate-limiting"


class TestConfigManagerCleanEntities:
    """Tests for _clean_entities method."""

    @pytest.mark.unit
    def test_clean_entities_removes_timestamps(self, manager: ConfigManager) -> None:
        """_clean_entities should remove created_at and updated_at."""
        entities = [
            {
                "id": "1",
                "name": "test",
                "created_at": 1234567890,
                "updated_at": 1234567891,
            }
        ]

        cleaned = manager._clean_entities(entities)

        assert "created_at" not in cleaned[0]
        assert "updated_at" not in cleaned[0]
        assert cleaned[0]["id"] == "1"
        assert cleaned[0]["name"] == "test"

    @pytest.mark.unit
    def test_clean_entities_removes_none_values(self, manager: ConfigManager) -> None:
        """_clean_entities should remove None values."""
        entities = [{"id": "1", "name": "test", "optional": None}]

        cleaned = manager._clean_entities(entities)

        assert "optional" not in cleaned[0]


class TestConfigManagerValidation:
    """Tests for validate_config method."""

    @pytest.mark.unit
    def test_validate_config_valid(self, manager: ConfigManager) -> None:
        """validate_config should return valid for correct config."""
        config = DeclarativeConfig(
            services=[{"id": "svc-1", "name": "api", "host": "api.local"}],
            routes=[{"id": "rt-1", "paths": ["/api"], "service": {"id": "svc-1"}}],
        )

        result = manager.validate_config(config)

        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.unit
    def test_validate_config_invalid_route_service_ref(self, manager: ConfigManager) -> None:
        """validate_config should error on invalid route service reference."""
        config = DeclarativeConfig(
            services=[{"id": "svc-1", "name": "api", "host": "api.local"}],
            routes=[{"id": "rt-1", "paths": ["/api"], "service": {"id": "unknown-svc"}}],
        )

        result = manager.validate_config(config)

        assert result.valid is False
        assert len(result.errors) == 1
        assert "unknown service" in result.errors[0].message.lower()

    @pytest.mark.unit
    def test_validate_config_invalid_plugin_service_ref(self, manager: ConfigManager) -> None:
        """validate_config should error on invalid plugin service reference."""
        config = DeclarativeConfig(
            services=[{"id": "svc-1", "name": "api", "host": "api.local"}],
            plugins=[{"name": "rate-limiting", "service": {"id": "unknown-svc"}, "config": {}}],
        )

        result = manager.validate_config(config)

        assert result.valid is False
        assert any("service" in e.path for e in result.errors)

    @pytest.mark.unit
    def test_validate_config_invalid_plugin_route_ref(self, manager: ConfigManager) -> None:
        """validate_config should error on invalid plugin route reference."""
        config = DeclarativeConfig(
            routes=[{"id": "rt-1", "paths": ["/api"]}],
            plugins=[{"name": "rate-limiting", "route": {"id": "unknown-rt"}, "config": {}}],
        )

        result = manager.validate_config(config)

        assert result.valid is False
        assert any("route" in e.path for e in result.errors)

    @pytest.mark.unit
    def test_validate_config_invalid_plugin_consumer_ref(self, manager: ConfigManager) -> None:
        """validate_config should error on invalid plugin consumer reference."""
        config = DeclarativeConfig(
            consumers=[{"id": "con-1", "username": "user1"}],
            plugins=[{"name": "rate-limiting", "consumer": {"id": "unknown-con"}, "config": {}}],
        )

        result = manager.validate_config(config)

        assert result.valid is False
        assert any("consumer" in e.path for e in result.errors)

    @pytest.mark.unit
    def test_validate_config_warns_global_plugin(self, manager: ConfigManager) -> None:
        """validate_config should warn about global plugins."""
        config = DeclarativeConfig(
            plugins=[{"name": "rate-limiting", "config": {"minute": 100}}],
        )

        result = manager.validate_config(config)

        assert result.valid is True
        assert len(result.warnings) == 1
        assert "global" in result.warnings[0].message.lower()


class TestConfigManagerCollectIdentifiers:
    """Tests for _collect_identifiers method."""

    @pytest.mark.unit
    def test_collect_identifiers_by_id(self, manager: ConfigManager) -> None:
        """_collect_identifiers should collect IDs."""
        entities = [{"id": "id-1"}, {"id": "id-2"}]

        ids = manager._collect_identifiers(entities)

        assert "id-1" in ids
        assert "id-2" in ids

    @pytest.mark.unit
    def test_collect_identifiers_by_name(self, manager: ConfigManager) -> None:
        """_collect_identifiers should collect names."""
        entities = [{"name": "name-1"}, {"name": "name-2"}]

        ids = manager._collect_identifiers(entities)

        assert "name-1" in ids
        assert "name-2" in ids

    @pytest.mark.unit
    def test_collect_identifiers_by_username(self, manager: ConfigManager) -> None:
        """_collect_identifiers should collect usernames."""
        entities = [{"username": "user1"}, {"username": "user2"}]

        ids = manager._collect_identifiers(entities)

        assert "user1" in ids
        assert "user2" in ids


class TestConfigManagerDiff:
    """Tests for diff_config method."""

    @pytest.mark.unit
    def test_diff_config_no_changes(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """diff_config should return empty diff when no changes."""
        # Current state - includes is_dbless_mode check first
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": [{"id": "svc-1", "name": "api", "host": "api.local"}]},
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig(
            services=[{"id": "svc-1", "name": "api", "host": "api.local"}],
        )

        diff = manager.diff_config(desired)

        assert diff.total_changes == 0

    @pytest.mark.unit
    def test_diff_config_with_creates(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """diff_config should detect creates."""
        # Current state - empty (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": []},  # services
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig(
            services=[{"name": "api", "host": "api.local"}],
        )

        diff = manager.diff_config(desired)

        assert diff.total_changes == 1
        assert diff.creates.get("services", 0) == 1

    @pytest.mark.unit
    def test_diff_config_with_updates(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """diff_config should detect updates."""
        # Current state (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": [{"id": "svc-1", "name": "api", "host": "old.local"}]},
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig(
            services=[{"name": "api", "host": "new.local"}],
        )

        diff = manager.diff_config(desired)

        assert diff.total_changes == 1
        assert diff.updates.get("services", 0) == 1

    @pytest.mark.unit
    def test_diff_config_with_deletes(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """diff_config should detect deletes."""
        # Current state has a service (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": [{"id": "svc-1", "name": "api", "host": "api.local"}]},
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig()  # No services

        diff = manager.diff_config(desired)

        assert diff.total_changes == 1
        assert diff.deletes.get("services", 0) == 1


class TestConfigManagerDiffEntityList:
    """Tests for _diff_entity_list method."""

    @pytest.mark.unit
    def test_diff_entity_list_create(self, manager: ConfigManager) -> None:
        """_diff_entity_list should detect creates."""
        current: list[dict[str, Any]] = []
        desired = [{"name": "new-service", "host": "api.local"}]

        diffs = manager._diff_entity_list("services", current, desired)

        assert len(diffs) == 1
        assert diffs[0].operation == "create"

    @pytest.mark.unit
    def test_diff_entity_list_update(self, manager: ConfigManager) -> None:
        """_diff_entity_list should detect updates."""
        current = [{"name": "api", "host": "old.local"}]
        desired = [{"name": "api", "host": "new.local"}]

        diffs = manager._diff_entity_list("services", current, desired)

        assert len(diffs) == 1
        assert diffs[0].operation == "update"

    @pytest.mark.unit
    def test_diff_entity_list_delete(self, manager: ConfigManager) -> None:
        """_diff_entity_list should detect deletes."""
        current = [{"name": "api", "host": "api.local"}]
        desired: list[dict[str, Any]] = []

        diffs = manager._diff_entity_list("services", current, desired)

        assert len(diffs) == 1
        assert diffs[0].operation == "delete"


class TestConfigManagerEntityKey:
    """Tests for _entity_key method."""

    @pytest.mark.unit
    def test_entity_key_by_name(self, manager: ConfigManager) -> None:
        """_entity_key should prefer name."""
        entity = {"id": "id-1", "name": "name-1"}

        key = manager._entity_key(entity)

        assert key == "name-1"

    @pytest.mark.unit
    def test_entity_key_by_username(self, manager: ConfigManager) -> None:
        """_entity_key should use username for consumers."""
        entity = {"id": "id-1", "username": "user1"}

        key = manager._entity_key(entity)

        assert key == "user1"

    @pytest.mark.unit
    def test_entity_key_by_id(self, manager: ConfigManager) -> None:
        """_entity_key should fall back to id."""
        entity = {"id": "id-1"}

        key = manager._entity_key(entity)

        assert key == "id-1"

    @pytest.mark.unit
    def test_entity_key_fallback_hash(self, manager: ConfigManager) -> None:
        """_entity_key should use hash as last resort."""
        entity = {"host": "api.local"}

        key = manager._entity_key(entity)

        assert key is not None


class TestConfigManagerDiffEntity:
    """Tests for _diff_entity method."""

    @pytest.mark.unit
    def test_diff_entity_identical(self, manager: ConfigManager) -> None:
        """_diff_entity should return None for identical entities."""
        current = {"name": "api", "host": "api.local"}
        desired = {"name": "api", "host": "api.local"}

        changes = manager._diff_entity(current, desired)

        assert changes is None

    @pytest.mark.unit
    def test_diff_entity_field_changes(self, manager: ConfigManager) -> None:
        """_diff_entity should detect field changes."""
        current = {"name": "api", "host": "old.local"}
        desired = {"name": "api", "host": "new.local"}

        changes = manager._diff_entity(current, desired)

        assert changes is not None
        assert "host" in changes
        assert changes["host"] == ("old.local", "new.local")

    @pytest.mark.unit
    def test_diff_entity_ignores_server_fields(self, manager: ConfigManager) -> None:
        """_diff_entity should ignore server-assigned fields."""
        current = {"name": "api", "id": "id-1", "created_at": 1234567890}
        desired = {"name": "api", "id": "id-2", "created_at": 1234567891}

        changes = manager._diff_entity(current, desired)

        assert changes is None


class TestConfigManagerApply:
    """Tests for apply_config method."""

    @pytest.mark.unit
    def test_apply_config_dry_run(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """apply_config dry_run should not make API calls."""
        # Current state - empty (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": []},  # services
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig(
            services=[{"name": "api", "host": "api.local"}],
        )

        operations = manager.apply_config(desired, dry_run=True)

        assert len(operations) == 1
        assert operations[0].result == "success"
        # No POST calls for dry run
        mock_client.post.assert_not_called()

    @pytest.mark.unit
    def test_apply_config_creates_in_order(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """apply_config should create entities in dependency order."""
        # Current state - empty (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": []},  # services
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]
        mock_client.post.return_value = {"id": "new-id"}

        desired = DeclarativeConfig(
            services=[{"name": "api", "host": "api.local"}],
            routes=[{"name": "route-1", "paths": ["/api"]}],
        )

        operations = manager.apply_config(desired)

        assert len(operations) == 2
        # Services should be created before routes
        call_order = [call[0][0] for call in mock_client.post.call_args_list]
        assert call_order.index("services") < call_order.index("routes")

    @pytest.mark.unit
    def test_apply_config_updates_success(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """apply_config should update existing entities."""
        # Current state (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": [{"id": "svc-1", "name": "api", "host": "old.local"}]},
            {"data": []},  # upstreams
            {"data": []},  # routes
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]
        mock_client.patch.return_value = {"id": "svc-1", "host": "new.local"}

        desired = DeclarativeConfig(
            services=[{"name": "api", "host": "new.local"}],
        )

        operations = manager.apply_config(desired)

        assert len(operations) == 1
        assert operations[0].operation == "update"
        assert operations[0].result == "success"

    @pytest.mark.unit
    def test_apply_config_deletes_in_reverse_order(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """apply_config should delete entities in reverse dependency order."""
        # Current state has routes and services (includes is_dbless_mode check first)
        mock_client.get.side_effect = [
            {"configuration": {"database": "postgres"}},  # is_dbless_mode check
            {"data": [{"id": "svc-1", "name": "api", "host": "api.local"}]},
            {"data": []},  # upstreams
            {"data": [{"id": "rt-1", "name": "route-1", "paths": ["/api"]}]},
            {"data": []},  # consumers
            {"data": []},  # plugins
        ]

        desired = DeclarativeConfig()  # Empty - delete all

        operations = manager.apply_config(desired)

        # Should have 2 deletes
        delete_ops = [op for op in operations if op.operation == "delete"]
        assert len(delete_ops) == 2

        # Routes should be deleted before services
        delete_order = [op.entity_type for op in delete_ops]
        assert delete_order.index("routes") < delete_order.index("services")


class TestConfigManagerApplyEntity:
    """Tests for _apply_entity method."""

    @pytest.mark.unit
    def test_apply_entity_create_success(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_apply_entity should create entity via POST."""
        from system_operations_manager.integrations.kong.models.config import (
            ConfigDiff,
        )

        mock_client.post.return_value = {"id": "new-id"}

        diff = ConfigDiff(
            entity_type="services",
            operation="create",
            id_or_name="api",
            desired={"name": "api", "host": "api.local"},
        )

        result = manager._apply_entity("services", diff)

        assert result.result == "success"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_apply_entity_update_success(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_apply_entity should update entity via PATCH."""
        from system_operations_manager.integrations.kong.models.config import (
            ConfigDiff,
        )

        mock_client.patch.return_value = {"id": "svc-1"}

        diff = ConfigDiff(
            entity_type="services",
            operation="update",
            id_or_name="api",
            desired={"name": "api", "host": "new.local"},
        )

        result = manager._apply_entity("services", diff)

        assert result.result == "success"
        mock_client.patch.assert_called_once()

    @pytest.mark.unit
    def test_apply_entity_create_failure(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """_apply_entity should handle create failures."""
        from system_operations_manager.integrations.kong.models.config import (
            ConfigDiff,
        )

        mock_client.post.side_effect = Exception("Create failed")

        diff = ConfigDiff(
            entity_type="services",
            operation="create",
            id_or_name="api",
            desired={"name": "api", "host": "api.local"},
        )

        result = manager._apply_entity("services", diff)

        assert result.result == "failed"
        assert result.error is not None
        assert "Create failed" in result.error


class TestConfigManagerDeleteEntity:
    """Tests for _delete_entity method."""

    @pytest.mark.unit
    def test_delete_entity_success(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """_delete_entity should delete entity via DELETE."""
        from system_operations_manager.integrations.kong.models.config import (
            ConfigDiff,
        )

        diff = ConfigDiff(
            entity_type="services",
            operation="delete",
            id_or_name="api",
            current={"name": "api"},
        )

        result = manager._delete_entity("services", diff)

        assert result.result == "success"
        mock_client.delete.assert_called_once_with("services/api")

    @pytest.mark.unit
    def test_delete_entity_failure(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """_delete_entity should handle delete failures."""
        from system_operations_manager.integrations.kong.models.config import (
            ConfigDiff,
        )

        mock_client.delete.side_effect = Exception("Delete failed")

        diff = ConfigDiff(
            entity_type="services",
            operation="delete",
            id_or_name="api",
            current={"name": "api"},
        )

        result = manager._delete_entity("services", diff)

        assert result.result == "failed"
        assert result.error is not None
        assert "Delete failed" in result.error


class TestFlattenConfigNestedRoutes:
    """Tests for _flatten_config nested route extraction (lines 130-135)."""

    @pytest.mark.unit
    def test_flatten_config_extracts_routes_from_services(self, manager: ConfigManager) -> None:
        """Routes nested inside a service should be extracted to top level with service ref."""
        config = DeclarativeConfig(
            services=[
                {
                    "name": "my-service",
                    "host": "api.local",
                    "routes": [{"name": "route-a", "paths": ["/a"]}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert len(flattened.services) == 1
        assert "routes" not in flattened.services[0]
        assert len(flattened.routes) == 1
        assert flattened.routes[0]["name"] == "route-a"
        assert flattened.routes[0]["service"] == {"name": "my-service"}

    @pytest.mark.unit
    def test_flatten_config_route_keeps_existing_service_ref(self, manager: ConfigManager) -> None:
        """A nested route that already has a service ref should not be overwritten."""
        config = DeclarativeConfig(
            services=[
                {
                    "name": "my-service",
                    "host": "api.local",
                    "routes": [
                        {
                            "name": "route-a",
                            "paths": ["/a"],
                            "service": {"name": "other-service"},
                        }
                    ],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert flattened.routes[0]["service"] == {"name": "other-service"}

    @pytest.mark.unit
    def test_flatten_config_service_without_name_skips_ref(self, manager: ConfigManager) -> None:
        """A service with no name or id should not inject a service ref into routes."""
        config = DeclarativeConfig(
            services=[
                {
                    "host": "api.local",
                    "routes": [{"name": "route-a", "paths": ["/a"]}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "service" not in flattened.routes[0]


class TestFlattenConfigNestedServicePlugins:
    """Tests for _flatten_config nested plugin extraction from services (lines 139-144)."""

    @pytest.mark.unit
    def test_flatten_config_extracts_plugins_from_services(self, manager: ConfigManager) -> None:
        """Plugins nested inside a service should be extracted to top level with service ref."""
        config = DeclarativeConfig(
            services=[
                {
                    "name": "my-service",
                    "host": "api.local",
                    "plugins": [{"name": "rate-limiting", "config": {"minute": 10}}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "plugins" not in flattened.services[0]
        assert len(flattened.plugins) == 1
        assert flattened.plugins[0]["service"] == {"name": "my-service"}

    @pytest.mark.unit
    def test_flatten_config_service_plugin_keeps_existing_service_ref(
        self, manager: ConfigManager
    ) -> None:
        """A nested plugin that already has a service ref should not be overwritten."""
        config = DeclarativeConfig(
            services=[
                {
                    "name": "my-service",
                    "host": "api.local",
                    "plugins": [
                        {
                            "name": "rate-limiting",
                            "service": {"name": "explicit-service"},
                        }
                    ],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert flattened.plugins[0]["service"] == {"name": "explicit-service"}


class TestFlattenConfigUpstreams:
    """Tests for _flatten_config upstream processing (lines 150-153)."""

    @pytest.mark.unit
    def test_flatten_config_upstreams_kept_with_targets(self, manager: ConfigManager) -> None:
        """Upstreams with nested targets should be kept as-is (targets handled elsewhere)."""
        config = DeclarativeConfig(
            upstreams=[
                {
                    "name": "my-upstream",
                    "targets": [{"target": "10.0.0.1:80", "weight": 100}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert len(flattened.upstreams) == 1
        assert "targets" in flattened.upstreams[0]
        assert flattened.upstreams[0]["name"] == "my-upstream"

    @pytest.mark.unit
    def test_flatten_config_upstream_without_targets(self, manager: ConfigManager) -> None:
        """Upstreams without targets should be copied through unchanged."""
        config = DeclarativeConfig(upstreams=[{"name": "my-upstream", "algorithm": "round-robin"}])

        flattened = manager._flatten_config(config)

        assert len(flattened.upstreams) == 1
        assert flattened.upstreams[0]["algorithm"] == "round-robin"


class TestFlattenConfigNestedRoutePlugins:
    """Tests for _flatten_config nested plugin extraction from routes (lines 162-166)."""

    @pytest.mark.unit
    def test_flatten_config_extracts_plugins_from_routes(self, manager: ConfigManager) -> None:
        """Plugins nested inside a route should be extracted to top level with route ref."""
        config = DeclarativeConfig(
            routes=[
                {
                    "name": "my-route",
                    "paths": ["/api"],
                    "plugins": [{"name": "cors", "config": {}}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "plugins" not in flattened.routes[0]
        assert len(flattened.plugins) == 1
        assert flattened.plugins[0]["route"] == {"name": "my-route"}

    @pytest.mark.unit
    def test_flatten_config_route_plugin_keeps_existing_route_ref(
        self, manager: ConfigManager
    ) -> None:
        """A nested route plugin that already has a route ref should not be overwritten."""
        config = DeclarativeConfig(
            routes=[
                {
                    "name": "my-route",
                    "paths": ["/api"],
                    "plugins": [
                        {
                            "name": "cors",
                            "route": {"name": "other-route"},
                        }
                    ],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert flattened.plugins[0]["route"] == {"name": "other-route"}

    @pytest.mark.unit
    def test_flatten_config_route_without_name_skips_ref(self, manager: ConfigManager) -> None:
        """A route with no name or id should not inject a route ref into extracted plugins."""
        config = DeclarativeConfig(
            routes=[
                {
                    "paths": ["/api"],
                    "plugins": [{"name": "cors"}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "route" not in flattened.plugins[0]


class TestFlattenConfigNestedConsumerPlugins:
    """Tests for _flatten_config nested plugin/credential extraction from consumers (173-184)."""

    @pytest.mark.unit
    def test_flatten_config_extracts_plugins_from_consumers(self, manager: ConfigManager) -> None:
        """Plugins nested inside a consumer should be extracted with a consumer ref."""
        config = DeclarativeConfig(
            consumers=[
                {
                    "username": "alice",
                    "plugins": [{"name": "rate-limiting", "config": {}}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "plugins" not in flattened.consumers[0]
        assert len(flattened.plugins) == 1
        assert flattened.plugins[0]["consumer"] == {"username": "alice"}

    @pytest.mark.unit
    def test_flatten_config_consumer_plugin_keeps_existing_consumer_ref(
        self, manager: ConfigManager
    ) -> None:
        """A consumer-nested plugin that already has a consumer ref is not overwritten."""
        config = DeclarativeConfig(
            consumers=[
                {
                    "username": "alice",
                    "plugins": [
                        {
                            "name": "rate-limiting",
                            "consumer": {"username": "explicit-consumer"},
                        }
                    ],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert flattened.plugins[0]["consumer"] == {"username": "explicit-consumer"}

    @pytest.mark.unit
    def test_flatten_config_credentials_stay_nested_in_consumers(
        self, manager: ConfigManager
    ) -> None:
        """Credential fields inside a consumer should remain nested (handled in _apply_entity)."""
        config = DeclarativeConfig(
            consumers=[
                {
                    "username": "alice",
                    "keyauth_credentials": [{"key": "secret-key"}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "keyauth_credentials" in flattened.consumers[0]

    @pytest.mark.unit
    def test_flatten_config_consumer_without_username_skips_ref(
        self, manager: ConfigManager
    ) -> None:
        """A consumer with no username or id should not inject a consumer ref."""
        config = DeclarativeConfig(
            consumers=[
                {
                    "custom_id": "ext-1",
                    "plugins": [{"name": "rate-limiting"}],
                }
            ]
        )

        flattened = manager._flatten_config(config)

        assert "consumer" not in flattened.plugins[0]


class TestExportConsumersSkipAndException:
    """Tests for _export_consumers edge cases (lines 314, 324-326)."""

    @pytest.mark.unit
    def test_export_consumers_skips_consumer_without_id_or_username(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """A consumer lacking both id and username should be skipped when fetching credentials."""
        mock_client.get.return_value = {
            "data": [{"custom_id": "ext-1"}]  # no id, no username
        }

        consumers = manager._export_consumers(include_credentials=True)

        assert len(consumers) == 1
        # Only the initial consumers GET is made; no credential fetches happen
        assert mock_client.get.call_count == 1

    @pytest.mark.unit
    def test_export_consumers_silently_ignores_credential_exception(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Credential fetch exceptions should be silently caught (plugin not enabled)."""
        mock_client.get.side_effect = [
            {"data": [{"id": "con-1", "username": "user1"}]},
            Exception("plugin not enabled"),  # key-auth fails
            {"data": []},  # basic-auth
            {"data": []},  # jwt
            {"data": []},  # oauth2
            {"data": []},  # acls
        ]

        consumers = manager._export_consumers(include_credentials=True)

        assert len(consumers) == 1
        assert "key_auth" not in consumers[0]


class TestEntityKeyPluginCompoundKey:
    """Tests for _entity_key plugin compound key generation (lines 648-676)."""

    @pytest.mark.unit
    def test_entity_key_plugin_with_service_ref_dict(self, manager: ConfigManager) -> None:
        """Plugin scoped to a service via dict ref should produce a compound key."""
        entity = {"name": "rate-limiting", "service": {"name": "my-service"}}

        key = manager._entity_key(entity, "plugins")

        assert key == "rate-limiting@service:my-service"

    @pytest.mark.unit
    def test_entity_key_plugin_with_route_ref_dict(self, manager: ConfigManager) -> None:
        """Plugin scoped to a route via dict ref should produce a compound key."""
        entity = {"name": "cors", "route": {"name": "my-route"}}

        key = manager._entity_key(entity, "plugins")

        assert key == "cors@route:my-route"

    @pytest.mark.unit
    def test_entity_key_plugin_with_consumer_ref_dict(self, manager: ConfigManager) -> None:
        """Plugin scoped to a consumer via dict ref should produce a compound key."""
        entity = {"name": "rate-limiting", "consumer": {"username": "alice"}}

        key = manager._entity_key(entity, "plugins")

        assert key == "rate-limiting@consumer:alice"

    @pytest.mark.unit
    def test_entity_key_plugin_with_multiple_scopes(self, manager: ConfigManager) -> None:
        """Plugin scoped to both service and consumer should include both in the key."""
        entity = {
            "name": "rate-limiting",
            "service": {"name": "svc-a"},
            "consumer": {"username": "alice"},
        }

        key = manager._entity_key(entity, "plugins")

        assert "service:svc-a" in key
        assert "consumer:alice" in key
        assert key.startswith("rate-limiting@")

    @pytest.mark.unit
    def test_entity_key_global_plugin_with_id(self, manager: ConfigManager) -> None:
        """A global plugin (no scope) with an id should use the id as key."""
        entity = {"name": "prometheus", "id": "pl-uuid-1"}

        key = manager._entity_key(entity, "plugins")

        assert key == "pl-uuid-1"

    @pytest.mark.unit
    def test_entity_key_global_plugin_without_id(self, manager: ConfigManager) -> None:
        """A global plugin without an id should fall back to name@global."""
        entity = {"name": "prometheus"}

        key = manager._entity_key(entity, "plugins")

        assert key == "prometheus@global"

    @pytest.mark.unit
    def test_entity_key_plugin_with_service_ref_string(self, manager: ConfigManager) -> None:
        """Plugin with service ref as a plain string should still produce a compound key."""
        entity = {"name": "rate-limiting", "service": "my-service"}

        key = manager._entity_key(entity, "plugins")

        assert key == "rate-limiting@service:my-service"

    @pytest.mark.unit
    def test_entity_key_plugin_detected_by_known_name(self, manager: ConfigManager) -> None:
        """A known plugin name should trigger compound-key logic even without entity_type."""
        entity = {"name": "key-auth", "service": {"name": "svc"}}

        key = manager._entity_key(entity)

        assert key == "key-auth@service:svc"


class TestApplyEntityNestedHandling:
    """Tests for _apply_entity nested upstream targets and consumer credentials (lines 832, 836)."""

    @pytest.mark.unit
    def test_apply_entity_upstream_triggers_nested_targets(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Creating an upstream with nested targets should call _apply_nested_targets."""
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.config import ConfigDiff

        mock_client.post.return_value = {"id": "up-1"}

        diff = ConfigDiff(
            entity_type="upstreams",
            operation="create",
            id_or_name="my-upstream",
            desired={
                "name": "my-upstream",
                "targets": [{"target": "10.0.0.1:80", "weight": 100}],
            },
        )

        with patch.object(manager, "_apply_nested_targets") as mock_nested:
            result = manager._apply_entity("upstreams", diff)

        assert result.result == "success"
        mock_nested.assert_called_once_with(
            "my-upstream",
            diff.desired,
        )

    @pytest.mark.unit
    def test_apply_entity_consumer_triggers_credential_application(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Creating a consumer with credentials should call _apply_consumer_credentials."""
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.config import ConfigDiff

        mock_client.post.return_value = {"id": "con-1"}

        diff = ConfigDiff(
            entity_type="consumers",
            operation="create",
            id_or_name="alice",
            desired={
                "username": "alice",
                "keyauth_credentials": [{"key": "secret"}],
            },
        )

        with patch.object(manager, "_apply_consumer_credentials") as mock_creds:
            result = manager._apply_entity("consumers", diff)

        assert result.result == "success"
        mock_creds.assert_called_once_with("alice", diff.desired)


class TestGetEntityEndpointPlugins:
    """Tests for _get_entity_endpoint plugin scoping (lines 895-913, 918-921)."""

    @pytest.mark.unit
    def test_get_entity_endpoint_plugin_with_service_ref(self, manager: ConfigManager) -> None:
        """Plugin with service ref should use nested service endpoint."""
        entity_data: dict[str, Any] = {
            "name": "rate-limiting",
            "service": {"name": "my-service"},
        }

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "services/my-service/plugins"
        assert "service" not in entity_data

    @pytest.mark.unit
    def test_get_entity_endpoint_plugin_with_route_ref(self, manager: ConfigManager) -> None:
        """Plugin with route ref should use nested route endpoint."""
        entity_data: dict[str, Any] = {
            "name": "cors",
            "route": {"name": "my-route"},
        }

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "routes/my-route/plugins"
        assert "route" not in entity_data

    @pytest.mark.unit
    def test_get_entity_endpoint_plugin_with_consumer_ref(self, manager: ConfigManager) -> None:
        """Plugin with consumer ref should use nested consumer endpoint."""
        entity_data: dict[str, Any] = {
            "name": "rate-limiting",
            "consumer": {"username": "alice"},
        }

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "consumers/alice/plugins"
        assert "consumer" not in entity_data

    @pytest.mark.unit
    def test_get_entity_endpoint_plugin_service_ref_priority_over_route(
        self, manager: ConfigManager
    ) -> None:
        """When plugin has both service and route refs, service takes priority."""
        entity_data: dict[str, Any] = {
            "name": "rate-limiting",
            "service": {"name": "svc"},
            "route": {"name": "rt"},
        }

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "services/svc/plugins"

    @pytest.mark.unit
    def test_get_entity_endpoint_plugin_unresolvable_service_ref_falls_through(
        self, manager: ConfigManager
    ) -> None:
        """Plugin with a service ref that resolves to None falls through to global endpoint."""
        entity_data: dict[str, Any] = {
            "name": "rate-limiting",
            "service": {},  # empty dict, no name/id
        }

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "plugins"

    @pytest.mark.unit
    def test_get_entity_endpoint_global_plugin(self, manager: ConfigManager) -> None:
        """Plugin without any parent ref should use plain 'plugins' endpoint."""
        entity_data: dict[str, Any] = {"name": "prometheus"}

        endpoint = manager._get_entity_endpoint("plugins", entity_data)

        assert endpoint == "plugins"

    @pytest.mark.unit
    def test_get_entity_endpoint_route_with_service_ref(self, manager: ConfigManager) -> None:
        """Route with service ref should use nested service endpoint."""
        entity_data: dict[str, Any] = {
            "name": "my-route",
            "service": {"name": "my-service"},
        }

        endpoint = manager._get_entity_endpoint("routes", entity_data)

        assert endpoint == "services/my-service/routes"
        assert "service" not in entity_data

    @pytest.mark.unit
    def test_get_entity_endpoint_route_without_service_ref(self, manager: ConfigManager) -> None:
        """Route without service ref should use plain 'routes' endpoint."""
        entity_data: dict[str, Any] = {"name": "my-route", "paths": ["/api"]}

        endpoint = manager._get_entity_endpoint("routes", entity_data)

        assert endpoint == "routes"

    @pytest.mark.unit
    def test_get_entity_endpoint_non_plugin_non_route(self, manager: ConfigManager) -> None:
        """Non-plugin, non-route entities should always use their entity type."""
        entity_data: dict[str, Any] = {"name": "my-consumer"}

        endpoint = manager._get_entity_endpoint("consumers", entity_data)

        assert endpoint == "consumers"


class TestExtractRefName:
    """Tests for _extract_ref_name (lines 944-955)."""

    @pytest.mark.unit
    def test_extract_ref_name_none_returns_none(self, manager: ConfigManager) -> None:
        """None ref should return None."""
        assert manager._extract_ref_name(None) is None

    @pytest.mark.unit
    def test_extract_ref_name_string_returns_string(self, manager: ConfigManager) -> None:
        """A plain string ref should be returned directly."""
        assert manager._extract_ref_name("my-service") == "my-service"

    @pytest.mark.unit
    def test_extract_ref_name_dict_returns_name(self, manager: ConfigManager) -> None:
        """Dict ref should return the 'name' field by default."""
        assert manager._extract_ref_name({"name": "svc", "id": "uuid-1"}) == "svc"

    @pytest.mark.unit
    def test_extract_ref_name_dict_falls_back_to_id(self, manager: ConfigManager) -> None:
        """Dict ref without 'name' should fall back to 'id'."""
        assert manager._extract_ref_name({"id": "uuid-1"}) == "uuid-1"

    @pytest.mark.unit
    def test_extract_ref_name_dict_prefer_username(self, manager: ConfigManager) -> None:
        """With prefer_username=True, 'username' should be returned before 'name'."""
        ref = {"username": "alice", "name": "ALICE", "id": "uuid-1"}

        result = manager._extract_ref_name(ref, prefer_username=True)

        assert result == "alice"

    @pytest.mark.unit
    def test_extract_ref_name_dict_prefer_username_falls_back_to_name(
        self, manager: ConfigManager
    ) -> None:
        """With prefer_username=True and no username, should fall back to 'name'."""
        ref = {"name": "ALICE", "id": "uuid-1"}

        result = manager._extract_ref_name(ref, prefer_username=True)

        assert result == "ALICE"

    @pytest.mark.unit
    def test_extract_ref_name_dict_prefer_username_falls_back_to_id(
        self, manager: ConfigManager
    ) -> None:
        """With prefer_username=True and no username/name, should fall back to 'id'."""
        ref: dict[str, Any] = {"id": "uuid-1"}

        result = manager._extract_ref_name(ref, prefer_username=True)

        assert result == "uuid-1"

    @pytest.mark.unit
    def test_extract_ref_name_unsupported_type_returns_none(self, manager: ConfigManager) -> None:
        """An unsupported ref type (e.g. list) should return None."""
        assert manager._extract_ref_name(["svc"]) is None


class TestPrepareEntityForApi:
    """Tests for _prepare_entity_for_api (line 976)."""

    @pytest.mark.unit
    def test_prepare_entity_for_api_none_returns_empty_dict(self, manager: ConfigManager) -> None:
        """None entity should return an empty dict."""
        result = manager._prepare_entity_for_api("services", None)

        assert result == {}

    @pytest.mark.unit
    def test_prepare_entity_for_api_strips_nested_service_fields(
        self, manager: ConfigManager
    ) -> None:
        """Routes nested inside a service entity dict should be stripped."""
        entity = {
            "name": "my-service",
            "host": "api.local",
            "routes": [{"name": "r"}],
            "plugins": [{"name": "p"}],
        }

        result = manager._prepare_entity_for_api("services", entity)

        assert "routes" not in result
        assert "plugins" not in result
        assert result["name"] == "my-service"

    @pytest.mark.unit
    def test_prepare_entity_for_api_no_nested_fields_unchanged(
        self, manager: ConfigManager
    ) -> None:
        """Entity without nested fields should be returned unchanged."""
        entity = {"name": "my-service", "host": "api.local"}

        result = manager._prepare_entity_for_api("services", entity)

        assert result == entity


class TestApplyNestedTargets:
    """Tests for _apply_nested_targets (lines 1000-1014)."""

    @pytest.mark.unit
    def test_apply_nested_targets_posts_each_target(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Each target in upstream_data should be POSTed to the targets endpoint."""
        upstream_data = {
            "targets": [
                {"target": "10.0.0.1:80", "weight": 100},
                {"target": "10.0.0.2:80", "weight": 50},
            ]
        }

        manager._apply_nested_targets("my-upstream", upstream_data)

        assert mock_client.post.call_count == 2
        calls = [call[0][0] for call in mock_client.post.call_args_list]
        assert all(c == "upstreams/my-upstream/targets" for c in calls)

    @pytest.mark.unit
    def test_apply_nested_targets_strips_id_and_created_at(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """id and created_at fields should be stripped from each target before posting."""
        upstream_data = {
            "targets": [
                {
                    "id": "t-uuid",
                    "created_at": 1234567890,
                    "target": "10.0.0.1:80",
                    "weight": 100,
                }
            ]
        }

        manager._apply_nested_targets("my-upstream", upstream_data)

        posted_json = mock_client.post.call_args[1]["json"]
        assert "id" not in posted_json
        assert "created_at" not in posted_json
        assert posted_json["target"] == "10.0.0.1:80"

    @pytest.mark.unit
    def test_apply_nested_targets_no_targets_does_nothing(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Upstream with no targets list should make no POST calls."""
        manager._apply_nested_targets("my-upstream", {})

        mock_client.post.assert_not_called()

    @pytest.mark.unit
    def test_apply_nested_targets_empty_targets_does_nothing(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Upstream with empty targets list should make no POST calls."""
        manager._apply_nested_targets("my-upstream", {"targets": []})

        mock_client.post.assert_not_called()

    @pytest.mark.unit
    def test_apply_nested_targets_logs_warning_on_error(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """A POST failure for a target should be caught and logged as a warning."""
        mock_client.post.side_effect = Exception("target creation failed")

        upstream_data = {"targets": [{"target": "10.0.0.1:80", "weight": 100}]}

        # Should not raise - exception is swallowed with a warning
        manager._apply_nested_targets("my-upstream", upstream_data)

        mock_client.post.assert_called_once()


class TestApplyConsumerCredentials:
    """Tests for _apply_consumer_credentials (lines 1036-1065)."""

    @pytest.mark.unit
    def test_apply_consumer_credentials_posts_keyauth(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """keyauth_credentials should be posted to consumers/{name}/key-auth."""
        consumer_data = {"keyauth_credentials": [{"key": "my-api-key"}]}

        manager._apply_consumer_credentials("alice", consumer_data)

        mock_client.post.assert_called_once_with(
            "consumers/alice/key-auth",
            json={"key": "my-api-key"},
        )

    @pytest.mark.unit
    def test_apply_consumer_credentials_posts_basic_auth(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """basicauth_credentials should be posted to consumers/{name}/basic-auth."""
        consumer_data = {"basicauth_credentials": [{"username": "alice", "password": "secret"}]}

        manager._apply_consumer_credentials("alice", consumer_data)

        mock_client.post.assert_called_once_with(
            "consumers/alice/basic-auth",
            json={"username": "alice", "password": "secret"},
        )

    @pytest.mark.unit
    def test_apply_consumer_credentials_strips_id_created_at_consumer(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """id, created_at, and consumer fields should be stripped from credentials."""
        consumer_data = {
            "keyauth_credentials": [
                {
                    "id": "cred-uuid",
                    "created_at": 1234567890,
                    "consumer": {"id": "con-uuid"},
                    "key": "my-api-key",
                }
            ]
        }

        manager._apply_consumer_credentials("alice", consumer_data)

        posted_json = mock_client.post.call_args[1]["json"]
        assert "id" not in posted_json
        assert "created_at" not in posted_json
        assert "consumer" not in posted_json
        assert posted_json["key"] == "my-api-key"

    @pytest.mark.unit
    def test_apply_consumer_credentials_multiple_types(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Multiple credential types in the same consumer should each be posted."""
        consumer_data = {
            "keyauth_credentials": [{"key": "k1"}],
            "jwt_secrets": [{"secret": "s1"}],
        }

        manager._apply_consumer_credentials("alice", consumer_data)

        assert mock_client.post.call_count == 2
        endpoints = {call[0][0] for call in mock_client.post.call_args_list}
        assert "consumers/alice/key-auth" in endpoints
        assert "consumers/alice/jwt" in endpoints

    @pytest.mark.unit
    def test_apply_consumer_credentials_skips_empty_type(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Credential types with empty lists should not trigger any POST calls."""
        consumer_data: dict[str, list[dict[str, str]]] = {"keyauth_credentials": []}

        manager._apply_consumer_credentials("alice", consumer_data)

        mock_client.post.assert_not_called()

    @pytest.mark.unit
    def test_apply_consumer_credentials_logs_warning_on_error(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """A POST failure for a credential should be caught and logged as a warning."""
        mock_client.post.side_effect = Exception("cred creation failed")

        consumer_data = {"keyauth_credentials": [{"key": "my-api-key"}]}

        # Should not raise - exception is swallowed with a warning
        manager._apply_consumer_credentials("alice", consumer_data)

        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_apply_consumer_credentials_all_types_mapped(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """All six credential types should map to their correct endpoint suffixes."""
        consumer_data = {
            "keyauth_credentials": [{"key": "k"}],
            "basicauth_credentials": [{"username": "u", "password": "p"}],
            "jwt_secrets": [{"secret": "s"}],
            "oauth2_credentials": [{"name": "app"}],
            "acls": [{"group": "admins"}],
            "hmacauth_credentials": [{"username": "u", "secret": "s"}],
        }

        manager._apply_consumer_credentials("alice", consumer_data)

        assert mock_client.post.call_count == 6
        endpoints = {call[0][0] for call in mock_client.post.call_args_list}
        assert endpoints == {
            "consumers/alice/key-auth",
            "consumers/alice/basic-auth",
            "consumers/alice/jwt",
            "consumers/alice/oauth2",
            "consumers/alice/acls",
            "consumers/alice/hmac-auth",
        }


class TestSyncConfig:
    """Tests for sync_config DB-less mode method (lines 1152-1174)."""

    @pytest.mark.unit
    def test_sync_config_posts_to_config_endpoint(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """sync_config should POST the config dump to the /config endpoint."""
        mock_client.post.return_value = {"message": "OK"}

        config = DeclarativeConfig(services=[{"name": "api", "host": "api.local"}])

        result = manager.sync_config(config)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "config"
        assert result == {"message": "OK"}

    @pytest.mark.unit
    def test_sync_config_removes_internal_metadata_fields(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """Internal fields like _metadata and _info should be stripped before posting."""
        mock_client.post.return_value = {}

        config = DeclarativeConfig()

        manager.sync_config(config)

        posted_json = mock_client.post.call_args[1]["json"]
        assert "_metadata" not in posted_json
        assert "_info" not in posted_json
        assert "_comment" not in posted_json

    @pytest.mark.unit
    def test_sync_config_uses_by_alias_serialization(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """sync_config should serialize config with by_alias=True so _format_version is present."""
        mock_client.post.return_value = {}

        config = DeclarativeConfig()

        manager.sync_config(config)

        posted_json = mock_client.post.call_args[1]["json"]
        assert "_format_version" in posted_json

    @pytest.mark.unit
    def test_sync_config_returns_api_response(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """sync_config should return the raw response dict from the client."""
        expected = {"flattened": True, "entities": 5}
        mock_client.post.return_value = expected

        config = DeclarativeConfig()

        result = manager.sync_config(config)

        assert result is expected

    @pytest.mark.unit
    def test_sync_config_empty_config(self, manager: ConfigManager, mock_client: MagicMock) -> None:
        """sync_config with an empty config should still post successfully."""
        mock_client.post.return_value = {}

        result = manager.sync_config(DeclarativeConfig())

        mock_client.post.assert_called_once()
        assert result == {}


class TestIsDblessMode:
    """Tests for is_dbless_mode (lines 1187-1189)."""

    @pytest.mark.unit
    def test_is_dbless_mode_returns_true_when_database_off(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """is_dbless_mode should return True when database config is 'off'."""
        mock_client.get.return_value = {"configuration": {"database": "off"}}

        assert manager.is_dbless_mode() is True

    @pytest.mark.unit
    def test_is_dbless_mode_returns_false_when_database_postgres(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """is_dbless_mode should return False when database is 'postgres'."""
        mock_client.get.return_value = {"configuration": {"database": "postgres"}}

        assert manager.is_dbless_mode() is False

    @pytest.mark.unit
    def test_is_dbless_mode_returns_false_on_exception(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """is_dbless_mode should return False when the API call raises an exception."""
        mock_client.get.side_effect = Exception("connection refused")

        assert manager.is_dbless_mode() is False

    @pytest.mark.unit
    def test_is_dbless_mode_returns_false_when_configuration_missing(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """is_dbless_mode should return False when response has no configuration key."""
        mock_client.get.return_value = {}

        assert manager.is_dbless_mode() is False

    @pytest.mark.unit
    def test_is_dbless_mode_returns_false_when_database_key_absent(
        self, manager: ConfigManager, mock_client: MagicMock
    ) -> None:
        """is_dbless_mode should return False when database key is absent (defaults to postgres)."""
        mock_client.get.return_value = {"configuration": {}}

        assert manager.is_dbless_mode() is False
