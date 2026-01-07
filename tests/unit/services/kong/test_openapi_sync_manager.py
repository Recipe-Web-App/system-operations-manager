"""Unit tests for Kong OpenAPISyncManager."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.openapi import (
    OpenAPIOperation,
    OpenAPISpec,
    RouteMapping,
    SyncResult,
)
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.services.kong.openapi_sync_manager import (
    BreakingChangeError,
    OpenAPIParseError,
    OpenAPISyncManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def mock_route_manager() -> MagicMock:
    """Create a mock RouteManager."""
    return MagicMock()


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock ServiceManager."""
    return MagicMock()


@pytest.fixture
def manager(
    mock_client: MagicMock,
    mock_route_manager: MagicMock,
    mock_service_manager: MagicMock,
) -> OpenAPISyncManager:
    """Create an OpenAPISyncManager with mocked dependencies."""
    return OpenAPISyncManager(mock_client, mock_route_manager, mock_service_manager)


@pytest.fixture
def sample_openapi_yaml() -> str:
    """Sample OpenAPI 3.0 spec in YAML format."""
    return """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8080/api/v1
paths:
  /users:
    get:
      operationId: listUsers
      tags:
        - Users
      summary: List all users
    post:
      operationId: createUser
      tags:
        - Users
      summary: Create a user
  /users/{userId}:
    get:
      operationId: getUser
      tags:
        - Users
      summary: Get a user by ID
    put:
      operationId: updateUser
      tags:
        - Users
      summary: Update a user
    delete:
      operationId: deleteUser
      tags:
        - Users
      summary: Delete a user
  /health:
    get:
      summary: Health check
"""


class TestOpenAPISyncManagerInit:
    """Tests for OpenAPISyncManager initialization."""

    @pytest.mark.unit
    def test_manager_initialization(
        self,
        mock_client: MagicMock,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Manager should initialize with all dependencies."""
        manager = OpenAPISyncManager(mock_client, mock_route_manager, mock_service_manager)

        assert manager._client is mock_client
        assert manager._route_manager is mock_route_manager
        assert manager._service_manager is mock_service_manager


class TestOpenAPISpecParsing:
    """Tests for OpenAPI spec parsing."""

    @pytest.mark.unit
    def test_parse_yaml_spec(
        self,
        manager: OpenAPISyncManager,
        sample_openapi_yaml: str,
    ) -> None:
        """Should parse a valid YAML OpenAPI spec."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_openapi_yaml)
            f.flush()

            spec = manager.parse_openapi(Path(f.name))

            assert spec.title == "Test API"
            assert spec.version == "1.0.0"
            assert spec.base_path == "/api/v1"
            assert len(spec.operations) == 6
            assert "Users" in spec.all_tags

    @pytest.mark.unit
    def test_parse_json_spec(self, manager: OpenAPISyncManager) -> None:
        """Should parse a valid JSON OpenAPI spec."""
        json_content = """
{
    "openapi": "3.0.0",
    "info": {"title": "JSON API", "version": "2.0.0"},
    "paths": {
        "/items": {
            "get": {"operationId": "listItems"}
        }
    }
}
"""
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            f.flush()

            spec = manager.parse_openapi(Path(f.name))

            assert spec.title == "JSON API"
            assert spec.version == "2.0.0"
            assert len(spec.operations) == 1

    @pytest.mark.unit
    def test_parse_file_not_found(self, manager: OpenAPISyncManager) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            manager.parse_openapi(Path("/nonexistent/file.yaml"))

    @pytest.mark.unit
    def test_parse_invalid_yaml(self, manager: OpenAPISyncManager) -> None:
        """Should raise OpenAPIParseError for invalid YAML."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(OpenAPIParseError):
                manager.parse_openapi(Path(f.name))

    @pytest.mark.unit
    def test_parse_swagger_2_rejected(self, manager: OpenAPISyncManager) -> None:
        """Should reject Swagger 2.0 specs."""
        swagger_content = """
swagger: "2.0"
info:
  title: Old API
  version: 1.0.0
paths: {}
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(swagger_content)
            f.flush()

            with pytest.raises(OpenAPIParseError, match=r"Swagger.*not supported"):
                manager.parse_openapi(Path(f.name))

    @pytest.mark.unit
    def test_parse_missing_openapi_version(self, manager: OpenAPISyncManager) -> None:
        """Should reject specs without openapi version."""
        invalid_content = """
info:
  title: No Version
  version: 1.0.0
paths: {}
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_content)
            f.flush()

            with pytest.raises(OpenAPIParseError, match=r"missing.*openapi"):
                manager.parse_openapi(Path(f.name))


class TestRouteMapping:
    """Tests for route mapping generation."""

    @pytest.mark.unit
    def test_generate_route_mappings(self, manager: OpenAPISyncManager) -> None:
        """Should generate route mappings from OpenAPI operations."""
        spec = OpenAPISpec(
            title="Test API",
            version="1.0.0",
            operations=[
                OpenAPIOperation(
                    path="/users",
                    method="GET",
                    operation_id="listUsers",
                    tags=["Users"],
                ),
                OpenAPIOperation(
                    path="/users",
                    method="POST",
                    operation_id="createUser",
                    tags=["Users"],
                ),
                OpenAPIOperation(
                    path="/users/{userId}",
                    method="GET",
                    operation_id="getUser",
                    tags=["Users"],
                ),
            ],
            all_tags=["Users"],
        )

        mappings = manager.generate_route_mappings(spec, "test-service")

        # Should create 2 routes: one for /users, one for /users/{userId}
        assert len(mappings) == 2

        # Find the /users route
        users_route = next((m for m in mappings if m.path == "/users"), None)
        assert users_route is not None
        assert users_route.route_name == "test-service-listUsers"
        assert set(users_route.methods) == {"GET", "POST"}
        assert "service:test-service" in users_route.tags
        assert "Users" in users_route.tags

    @pytest.mark.unit
    def test_route_naming_with_operation_id(self, manager: OpenAPISyncManager) -> None:
        """Should use operationId for route naming."""
        spec = OpenAPISpec(
            title="Test",
            version="1.0.0",
            operations=[
                OpenAPIOperation(
                    path="/items",
                    method="GET",
                    operation_id="getAllItems",
                    tags=[],
                ),
            ],
            all_tags=[],
        )

        mappings = manager.generate_route_mappings(spec, "my-service")

        assert mappings[0].route_name == "my-service-getAllItems"

    @pytest.mark.unit
    def test_route_naming_without_operation_id(self, manager: OpenAPISyncManager) -> None:
        """Should generate path-based name when operationId is missing."""
        spec = OpenAPISpec(
            title="Test",
            version="1.0.0",
            operations=[
                OpenAPIOperation(
                    path="/users/{userId}/profile",
                    method="GET",
                    operation_id=None,
                    tags=[],
                ),
            ],
            all_tags=[],
        )

        mappings = manager.generate_route_mappings(spec, "api")

        assert mappings[0].route_name == "api-users-userid-profile"

    @pytest.mark.unit
    def test_route_mapping_with_path_prefix(self, manager: OpenAPISyncManager) -> None:
        """Should add path prefix to routes."""
        spec = OpenAPISpec(
            title="Test",
            version="1.0.0",
            operations=[
                OpenAPIOperation(path="/users", method="GET", operation_id="list"),
            ],
            all_tags=[],
        )

        mappings = manager.generate_route_mappings(spec, "service", path_prefix="/api/v2")

        assert mappings[0].path == "/api/v2/users"

    @pytest.mark.unit
    def test_route_mapping_strip_path(self, manager: OpenAPISyncManager) -> None:
        """Should respect strip_path setting."""
        spec = OpenAPISpec(
            title="Test",
            version="1.0.0",
            operations=[
                OpenAPIOperation(path="/items", method="GET", operation_id="list"),
            ],
            all_tags=[],
        )

        mappings_strip = manager.generate_route_mappings(spec, "svc", strip_path=True)
        mappings_no_strip = manager.generate_route_mappings(spec, "svc", strip_path=False)

        assert mappings_strip[0].strip_path is True
        assert mappings_no_strip[0].strip_path is False


class TestDiffCalculation:
    """Tests for diff calculation."""

    @pytest.mark.unit
    def test_calculate_diff_creates(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should identify new routes to create."""
        mock_service_manager.get.return_value = MagicMock()
        mock_route_manager.list_by_service.return_value = ([], None)

        mappings = [
            RouteMapping(
                route_name="svc-listUsers",
                path="/users",
                methods=["GET"],
                tags=["service:svc"],
            ),
        ]

        result = manager.calculate_diff("svc", mappings)

        assert len(result.creates) == 1
        assert result.creates[0].route_name == "svc-listUsers"
        assert result.creates[0].is_breaking is False

    @pytest.mark.unit
    def test_calculate_diff_updates(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should identify routes that need updates."""
        mock_service_manager.get.return_value = MagicMock()

        # Existing route with different methods
        existing_route = Route(
            id="route-1",
            name="svc-listUsers",
            paths=["/users"],
            methods=["GET"],
            tags=["service:svc"],
        )
        mock_route_manager.list_by_service.return_value = ([existing_route], None)

        # Mapping with additional method
        mappings = [
            RouteMapping(
                route_name="svc-listUsers",
                path="/users",
                methods=["GET", "POST"],  # Added POST
                tags=["service:svc"],
            ),
        ]

        result = manager.calculate_diff("svc", mappings)

        assert len(result.updates) == 1
        assert result.updates[0].route_name == "svc-listUsers"
        assert "methods" in (result.updates[0].field_changes or {})

    @pytest.mark.unit
    def test_calculate_diff_deletes(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should identify routes to delete."""
        mock_service_manager.get.return_value = MagicMock()

        # Existing route that's not in mappings
        existing_route = Route(
            id="route-1",
            name="svc-oldRoute",
            paths=["/old"],
            methods=["GET"],
            tags=[],
        )
        mock_route_manager.list_by_service.return_value = ([existing_route], None)

        # Empty mappings - should delete the existing route
        mappings: list[RouteMapping] = []

        result = manager.calculate_diff("svc", mappings)

        assert len(result.deletes) == 1
        assert result.deletes[0].route_name == "svc-oldRoute"
        assert result.deletes[0].is_breaking is True

    @pytest.mark.unit
    def test_calculate_diff_no_changes(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should identify when no changes are needed."""
        mock_service_manager.get.return_value = MagicMock()

        existing_route = Route(
            id="route-1",
            name="svc-listUsers",
            paths=["/users"],
            methods=["GET"],
            tags=["service:svc"],
            strip_path=True,
        )
        mock_route_manager.list_by_service.return_value = ([existing_route], None)

        mappings = [
            RouteMapping(
                route_name="svc-listUsers",
                path="/users",
                methods=["GET"],
                tags=["service:svc"],
                strip_path=True,
            ),
        ]

        result = manager.calculate_diff("svc", mappings)

        assert result.has_changes is False


class TestBreakingChangeDetection:
    """Tests for breaking change detection."""

    @pytest.mark.unit
    def test_detect_method_removal_as_breaking(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Removing HTTP methods should be detected as breaking."""
        mock_service_manager.get.return_value = MagicMock()

        existing_route = Route(
            id="route-1",
            name="svc-users",
            paths=["/users"],
            methods=["GET", "POST", "DELETE"],
            tags=[],
        )
        mock_route_manager.list_by_service.return_value = ([existing_route], None)

        # Remove DELETE method
        mappings = [
            RouteMapping(
                route_name="svc-users",
                path="/users",
                methods=["GET", "POST"],
                tags=[],
            ),
        ]

        result = manager.calculate_diff("svc", mappings)

        assert result.has_breaking_changes
        assert len(result.updates) == 1
        assert result.updates[0].is_breaking
        assert "DELETE" in (result.updates[0].breaking_reason or "")

    @pytest.mark.unit
    def test_deletion_always_breaking(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
        mock_service_manager: MagicMock,
    ) -> None:
        """Route deletion should always be marked as breaking."""
        mock_service_manager.get.return_value = MagicMock()

        existing_route = Route(
            id="route-1",
            name="svc-deprecated",
            paths=["/deprecated"],
            methods=["GET"],
            tags=[],
        )
        mock_route_manager.list_by_service.return_value = ([existing_route], None)

        result = manager.calculate_diff("svc", [])

        assert result.has_breaking_changes
        assert result.deletes[0].is_breaking


class TestSyncApply:
    """Tests for sync apply operations."""

    @pytest.mark.unit
    def test_apply_sync_dry_run(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
    ) -> None:
        """Dry run should not make any changes."""
        sync_result = SyncResult(
            creates=[],
            updates=[],
            deletes=[],
            service_name="test",
        )

        result = manager.apply_sync(sync_result, dry_run=True)

        assert len(result.operations) == 0
        mock_route_manager.create_for_service.assert_not_called()
        mock_route_manager.update.assert_not_called()
        mock_route_manager.delete.assert_not_called()

    @pytest.mark.unit
    def test_apply_sync_breaking_without_force(
        self,
        manager: OpenAPISyncManager,
    ) -> None:
        """Should raise error for breaking changes without force."""
        from system_operations_manager.integrations.kong.models.openapi import (
            SyncChange,
        )

        sync_result = SyncResult(
            creates=[],
            updates=[],
            deletes=[
                SyncChange(
                    operation="delete",
                    route_name="svc-old",
                    path="/old",
                    methods=["GET"],
                    is_breaking=True,
                    breaking_reason="Route will be deleted",
                ),
            ],
            service_name="test",
        )

        with pytest.raises(BreakingChangeError):
            manager.apply_sync(sync_result, force=False)

    @pytest.mark.unit
    def test_apply_sync_creates(
        self,
        manager: OpenAPISyncManager,
        mock_route_manager: MagicMock,
    ) -> None:
        """Should create routes successfully."""
        from system_operations_manager.integrations.kong.models.openapi import (
            SyncChange,
        )

        sync_result = SyncResult(
            creates=[
                SyncChange(
                    operation="create",
                    route_name="svc-new",
                    path="/new",
                    methods=["GET"],
                    tags=["service:svc"],
                ),
            ],
            updates=[],
            deletes=[],
            service_name="svc",
        )

        mock_route_manager.create_for_service.return_value = MagicMock()

        result = manager.apply_sync(sync_result)

        assert len(result.succeeded) == 1
        mock_route_manager.create_for_service.assert_called_once()


class TestPathSanitization:
    """Tests for path sanitization."""

    @pytest.mark.unit
    def test_sanitize_simple_path(self, manager: OpenAPISyncManager) -> None:
        """Should sanitize simple paths."""
        result = manager._sanitize_path_for_name("/users")
        assert result == "users"

    @pytest.mark.unit
    def test_sanitize_path_with_params(self, manager: OpenAPISyncManager) -> None:
        """Should remove path parameter braces."""
        result = manager._sanitize_path_for_name("/users/{userId}/profile")
        assert result == "users-userid-profile"

    @pytest.mark.unit
    def test_sanitize_path_with_special_chars(self, manager: OpenAPISyncManager) -> None:
        """Should replace special characters with hyphens."""
        result = manager._sanitize_path_for_name("/api/v1.0/users")
        assert result == "api-v1-0-users"
