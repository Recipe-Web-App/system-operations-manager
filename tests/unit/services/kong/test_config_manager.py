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
