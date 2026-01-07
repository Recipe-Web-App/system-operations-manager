"""Integration tests for OpenAPISyncManager.

These tests verify OpenAPI sync operations against a real Kong container.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.openapi_sync_manager import (
    BreakingChangeError,
    OpenAPIParseError,
    OpenAPISyncManager,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.service_manager import ServiceManager


@pytest.fixture
def openapi_sync_manager(
    kong_client: KongAdminClient,
    route_manager: RouteManager,
    service_manager: ServiceManager,
) -> OpenAPISyncManager:
    """Create an OpenAPISyncManager instance."""
    return OpenAPISyncManager(kong_client, route_manager, service_manager)


@pytest.fixture
def sample_openapi_spec() -> str:
    """Sample OpenAPI 3.0 spec for testing."""
    return """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8080/api/v1
paths:
  /test:
    get:
      operationId: testEndpoint
      tags:
        - Test
      summary: Test endpoint
  /mock:
    get:
      operationId: getMock
      tags:
        - Mock
      summary: Get mock data
    post:
      operationId: createMock
      tags:
        - Mock
      summary: Create mock data
"""


@pytest.fixture
def sample_spec_file(sample_openapi_spec: str) -> Path:
    """Create a temporary OpenAPI spec file."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(sample_openapi_spec)
        f.flush()
        return Path(f.name)


@pytest.mark.integration
@pytest.mark.kong
class TestOpenAPISyncManagerParsing:
    """Test OpenAPI parsing operations against real Kong instance."""

    def test_parse_valid_yaml_spec(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """parse_openapi should successfully parse valid YAML spec."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)

        assert spec.title == "Test API"
        assert spec.version == "1.0.0"
        assert spec.base_path == "/api/v1"
        assert len(spec.operations) == 3  # GET /test, GET /mock, POST /mock

    def test_parse_spec_extracts_operation_ids(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """parse_openapi should extract operation IDs from spec."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)

        operation_ids = [op.operation_id for op in spec.operations]
        assert "testEndpoint" in operation_ids
        assert "getMock" in operation_ids
        assert "createMock" in operation_ids

    def test_parse_spec_extracts_tags(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """parse_openapi should extract all unique tags."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)

        assert "Test" in spec.all_tags
        assert "Mock" in spec.all_tags

    def test_parse_invalid_spec_raises_error(
        self,
        openapi_sync_manager: OpenAPISyncManager,
    ) -> None:
        """parse_openapi should raise OpenAPIParseError for invalid specs."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [")
            f.flush()

            with pytest.raises(OpenAPIParseError):
                openapi_sync_manager.parse_openapi(Path(f.name))


@pytest.mark.integration
@pytest.mark.kong
class TestOpenAPISyncManagerRouteMapping:
    """Test route mapping generation."""

    def test_generate_route_mappings(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """generate_route_mappings should create mappings from spec."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "test-service")

        # Should create 2 routes (one per path)
        assert len(mappings) == 2

        # Check route naming pattern
        route_names = [m.route_name for m in mappings]
        assert "test-service-testEndpoint" in route_names
        # Route name uses first operationId from /mock (order may vary)
        assert any(
            name in route_names for name in ["test-service-getMock", "test-service-createMock"]
        )

    def test_route_mappings_include_service_tag(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """Route mappings should include service name as tag."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "my-api")

        for mapping in mappings:
            assert "service:my-api" in mapping.tags

    def test_route_mappings_include_openapi_tags(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """Route mappings should include OpenAPI operation tags."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "api")

        # Find the /mock route which has Mock tag
        mock_route = next((m for m in mappings if "/mock" in m.path), None)
        assert mock_route is not None
        assert "Mock" in mock_route.tags

    def test_route_mappings_with_path_prefix(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """Route mappings should apply path prefix."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "api", path_prefix="/v2")

        for mapping in mappings:
            assert mapping.path.startswith("/v2/")


@pytest.mark.integration
@pytest.mark.kong
class TestOpenAPISyncManagerDiff:
    """Test diff calculation against real Kong instance."""

    def test_calculate_diff_with_existing_service(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """calculate_diff should work with existing Kong service."""
        # test-service exists from declarative config
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "test-service")

        result = openapi_sync_manager.calculate_diff("test-service", mappings)

        # Should identify creates for new routes
        assert result.service_name == "test-service"
        # The exact number depends on what routes already exist

    def test_calculate_diff_nonexistent_service_raises(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """calculate_diff should raise error for nonexistent service."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "nonexistent-service")

        with pytest.raises(KongNotFoundError):
            openapi_sync_manager.calculate_diff("nonexistent-service", mappings)

    def test_calculate_diff_identifies_creates(
        self,
        openapi_sync_manager: OpenAPISyncManager,
    ) -> None:
        """calculate_diff should identify routes to create."""
        # Create a minimal spec with a unique path
        spec_content = """
openapi: 3.0.0
info:
  title: New API
  version: 1.0.0
paths:
  /integration-test-unique:
    get:
      operationId: uniqueEndpoint
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(spec_content)
            f.flush()

            spec = openapi_sync_manager.parse_openapi(Path(f.name))
            mappings = openapi_sync_manager.generate_route_mappings(spec, "test-service")

            result = openapi_sync_manager.calculate_diff("test-service", mappings)

            # Should identify this as a create
            create_names = [c.route_name for c in result.creates]
            assert "test-service-uniqueEndpoint" in create_names


@pytest.mark.integration
@pytest.mark.kong
class TestOpenAPISyncManagerSync:
    """Test sync operations against real Kong instance."""

    def test_apply_sync_dry_run_no_changes(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        sample_spec_file: Path,
    ) -> None:
        """apply_sync with dry_run should not make changes."""
        spec = openapi_sync_manager.parse_openapi(sample_spec_file)
        mappings = openapi_sync_manager.generate_route_mappings(spec, "test-service")

        # Calculate diff
        sync_result = openapi_sync_manager.calculate_diff("test-service", mappings)

        # Apply with dry_run
        apply_result = openapi_sync_manager.apply_sync(sync_result, dry_run=True)

        # Should return empty operations list for dry run
        assert len(apply_result.operations) == 0

    def test_apply_sync_breaking_changes_require_force(
        self,
        openapi_sync_manager: OpenAPISyncManager,
        route_manager: RouteManager,
    ) -> None:
        """apply_sync should require force for breaking changes."""
        # First, check if there are any routes that could be deleted
        # Create a sync result with a breaking change
        from system_operations_manager.integrations.kong.models.openapi import (
            SyncChange,
            SyncResult,
        )

        sync_result = SyncResult(
            creates=[],
            updates=[],
            deletes=[
                SyncChange(
                    operation="delete",
                    route_name="test-route-to-delete",
                    path="/to-delete",
                    methods=["GET"],
                    is_breaking=True,
                    breaking_reason="Route will be deleted",
                ),
            ],
            service_name="test-service",
        )

        # Should raise without force
        with pytest.raises(BreakingChangeError):
            openapi_sync_manager.apply_sync(sync_result, force=False)


@pytest.mark.integration
@pytest.mark.kong
class TestOpenAPISyncManagerWithMockApi:
    """Test sync operations using mock-api service."""

    def test_calculate_diff_for_mock_api(
        self,
        openapi_sync_manager: OpenAPISyncManager,
    ) -> None:
        """Calculate diff for mock-api service."""
        spec_content = """
openapi: 3.0.0
info:
  title: Mock API
  version: 1.0.0
paths:
  /mock:
    get:
      operationId: getMockData
      tags:
        - Mock
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(spec_content)
            f.flush()

            spec = openapi_sync_manager.parse_openapi(Path(f.name))
            mappings = openapi_sync_manager.generate_route_mappings(spec, "mock-api")

            result = openapi_sync_manager.calculate_diff("mock-api", mappings)

            assert result.service_name == "mock-api"
            # Has changes since the new route name pattern differs from existing

    def test_generate_mappings_groups_methods_per_path(
        self,
        openapi_sync_manager: OpenAPISyncManager,
    ) -> None:
        """Multiple methods on same path should create one route."""
        spec_content = """
openapi: 3.0.0
info:
  title: CRUD API
  version: 1.0.0
paths:
  /items:
    get:
      operationId: listItems
    post:
      operationId: createItem
    delete:
      operationId: deleteItems
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(spec_content)
            f.flush()

            spec = openapi_sync_manager.parse_openapi(Path(f.name))
            mappings = openapi_sync_manager.generate_route_mappings(spec, "test-service")

            # Should create only 1 route for /items
            assert len(mappings) == 1
            assert set(mappings[0].methods) == {"GET", "POST", "DELETE"}
