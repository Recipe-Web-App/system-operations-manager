"""Unit tests for Kong Service Registry models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from system_operations_manager.integrations.kong.models.service_registry import (
    RegistryNotFoundError,
    ServiceAlreadyExistsError,
    ServiceDeployDiff,
    ServiceDeployResult,
    ServiceDeploySummary,
    ServiceNotFoundError,
    ServiceRegistry,
    ServiceRegistryEntry,
)


class TestServiceRegistryEntry:
    """Tests for ServiceRegistryEntry model."""

    @pytest.mark.unit
    def test_create_minimal_entry(self) -> None:
        """Should create entry with required fields only."""
        entry = ServiceRegistryEntry(name="api", host="api.example.com")

        assert entry.name == "api"
        assert entry.host == "api.example.com"
        assert entry.port == 80
        assert entry.protocol == "http"
        assert entry.enabled is True
        assert entry.openapi_spec is None

    @pytest.mark.unit
    def test_create_full_entry(self) -> None:
        """Should create entry with all fields."""
        entry = ServiceRegistryEntry(
            name="api-service",
            host="api.internal.local",
            port=8080,
            protocol="https",
            path="/v1",
            tags=["prod", "api"],
            retries=3,
            connect_timeout=30000,
            write_timeout=60000,
            read_timeout=60000,
            enabled=True,
            openapi_spec="~/specs/api.yaml",
            path_prefix="/api/v1",
            strip_path=False,
        )

        assert entry.name == "api-service"
        assert entry.host == "api.internal.local"
        assert entry.port == 8080
        assert entry.protocol == "https"
        assert entry.path == "/v1"
        assert entry.tags == ["prod", "api"]
        assert entry.retries == 3
        assert entry.openapi_spec is not None
        assert entry.path_prefix == "/api/v1"
        assert entry.strip_path is False

    @pytest.mark.unit
    def test_name_validation_empty(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRegistryEntry(name="", host="api.example.com")

        errors = exc_info.value.errors()
        assert any("name" in str(e["loc"]) for e in errors)

    @pytest.mark.unit
    def test_name_validation_invalid_chars(self) -> None:
        """Should reject name with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRegistryEntry(name="api service", host="api.example.com")

        errors = exc_info.value.errors()
        assert any("name" in str(e["loc"]) for e in errors)

    @pytest.mark.unit
    def test_name_validation_valid_chars(self) -> None:
        """Should accept name with valid characters."""
        entry = ServiceRegistryEntry(name="api-service_v1.0~test", host="api.example.com")
        assert entry.name == "api-service_v1.0~test"

    @pytest.mark.unit
    def test_host_validation_empty(self) -> None:
        """Should reject empty host."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRegistryEntry(name="api", host="")

        errors = exc_info.value.errors()
        assert any("host" in str(e["loc"]) for e in errors)

    @pytest.mark.unit
    def test_port_validation_range(self) -> None:
        """Should validate port range."""
        # Valid ports
        entry = ServiceRegistryEntry(name="api", host="api.local", port=1)
        assert entry.port == 1

        entry = ServiceRegistryEntry(name="api", host="api.local", port=65535)
        assert entry.port == 65535

        # Invalid ports
        with pytest.raises(ValidationError):
            ServiceRegistryEntry(name="api", host="api.local", port=0)

        with pytest.raises(ValidationError):
            ServiceRegistryEntry(name="api", host="api.local", port=65536)

    @pytest.mark.unit
    def test_protocol_validation(self) -> None:
        """Should validate protocol values."""
        valid_protocols = ["http", "https", "grpc", "grpcs", "tcp", "tls"]
        for protocol in valid_protocols:
            entry = ServiceRegistryEntry(
                name="api",
                host="api.local",
                protocol=protocol,  # type: ignore[arg-type]
            )
            assert entry.protocol == protocol

        with pytest.raises(ValidationError):
            ServiceRegistryEntry(
                name="api",
                host="api.local",
                protocol="invalid",  # type: ignore[arg-type]
            )

    @pytest.mark.unit
    def test_protocol_lowercase(self) -> None:
        """Should lowercase protocol."""
        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            protocol="HTTP",  # type: ignore[arg-type]
        )
        assert entry.protocol == "http"

    @pytest.mark.unit
    def test_path_prefix_added(self) -> None:
        """Should add / prefix to path if missing."""
        entry = ServiceRegistryEntry(name="api", host="api.local", path="v1")
        assert entry.path == "/v1"

        entry = ServiceRegistryEntry(name="api", host="api.local", path="/v1")
        assert entry.path == "/v1"

    @pytest.mark.unit
    def test_openapi_spec_expansion(self) -> None:
        """Should expand ~ in openapi_spec path."""
        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec="~/specs/api.yaml")
        assert entry.openapi_spec is not None
        assert "~" not in entry.openapi_spec

    @pytest.mark.unit
    def test_to_kong_service_dict(self) -> None:
        """Should convert to Kong service dictionary."""
        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            port=8080,
            protocol="https",
            tags=["prod"],
            openapi_spec="./api.yaml",  # Should not be in Kong dict
        )

        kong_dict = entry.to_kong_service_dict()

        assert kong_dict["name"] == "api"
        assert kong_dict["host"] == "api.local"
        assert kong_dict["port"] == 8080
        assert kong_dict["protocol"] == "https"
        assert kong_dict["tags"] == ["prod"]
        assert "openapi_spec" not in kong_dict
        assert "path_prefix" not in kong_dict

    @pytest.mark.unit
    def test_to_kong_service_dict_omit_path_true(self) -> None:
        """omit_path=True should exclude path from Kong dict."""
        entry = ServiceRegistryEntry(name="api", host="api.local", path="/v1")
        kong_dict = entry.to_kong_service_dict(omit_path=True)
        assert "path" not in kong_dict
        assert kong_dict["name"] == "api"
        assert kong_dict["host"] == "api.local"

    @pytest.mark.unit
    def test_to_kong_service_dict_omit_path_false_default(self) -> None:
        """Default omit_path=False should include path in Kong dict."""
        entry = ServiceRegistryEntry(name="api", host="api.local", path="/v1")
        kong_dict = entry.to_kong_service_dict()
        assert kong_dict["path"] == "/v1"

    @pytest.mark.unit
    def test_to_kong_service_dict_omit_path_no_path_set(self) -> None:
        """omit_path=True with no path set should not error."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        kong_dict = entry.to_kong_service_dict(omit_path=True)
        assert "path" not in kong_dict

    @pytest.mark.unit
    def test_has_openapi_spec(self) -> None:
        """Should correctly report if OpenAPI spec is configured."""
        entry_without = ServiceRegistryEntry(name="api", host="api.local")
        assert entry_without.has_openapi_spec is False

        entry_with = ServiceRegistryEntry(name="api", host="api.local", openapi_spec="./api.yaml")
        assert entry_with.has_openapi_spec is True


class TestServiceRegistry:
    """Tests for ServiceRegistry model."""

    @pytest.mark.unit
    def test_create_empty_registry(self) -> None:
        """Should create empty registry."""
        registry = ServiceRegistry()
        assert len(registry.services) == 0
        assert len(registry) == 0

    @pytest.mark.unit
    def test_create_registry_with_services(self) -> None:
        """Should create registry with services."""
        registry = ServiceRegistry(
            services=[
                ServiceRegistryEntry(name="api", host="api.local"),
                ServiceRegistryEntry(name="web", host="web.local"),
            ]
        )

        assert len(registry) == 2

    @pytest.mark.unit
    def test_duplicate_names_rejected(self) -> None:
        """Should reject duplicate service names."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRegistry(
                services=[
                    ServiceRegistryEntry(name="api", host="api1.local"),
                    ServiceRegistryEntry(name="api", host="api2.local"),
                ]
            )

        errors = exc_info.value.errors()
        assert any("Duplicate" in str(e["msg"]) for e in errors)

    @pytest.mark.unit
    def test_get_service_found(self) -> None:
        """Should get service by name."""
        registry = ServiceRegistry(
            services=[
                ServiceRegistryEntry(name="api", host="api.local"),
                ServiceRegistryEntry(name="web", host="web.local"),
            ]
        )

        service = registry.get_service("api")
        assert service is not None
        assert service.name == "api"
        assert service.host == "api.local"

    @pytest.mark.unit
    def test_get_service_not_found(self) -> None:
        """Should return None for non-existent service."""
        registry = ServiceRegistry(services=[ServiceRegistryEntry(name="api", host="api.local")])

        service = registry.get_service("nonexistent")
        assert service is None

    @pytest.mark.unit
    def test_iteration(self) -> None:
        """Should iterate over services."""
        registry = ServiceRegistry(
            services=[
                ServiceRegistryEntry(name="api", host="api.local"),
                ServiceRegistryEntry(name="web", host="web.local"),
            ]
        )

        names = [s.name for s in registry]
        assert names == ["api", "web"]


class TestServiceDeployDiff:
    """Tests for ServiceDeployDiff model."""

    @pytest.mark.unit
    def test_create_diff(self) -> None:
        """Should create deploy diff for create operation."""
        diff = ServiceDeployDiff(
            service_name="api",
            operation="create",
            desired={"name": "api", "host": "api.local"},
        )

        assert diff.service_name == "api"
        assert diff.operation == "create"
        assert diff.current is None
        assert diff.desired is not None

    @pytest.mark.unit
    def test_update_diff(self) -> None:
        """Should create deploy diff for update operation."""
        diff = ServiceDeployDiff(
            service_name="api",
            operation="update",
            current={"name": "api", "host": "old.local"},
            desired={"name": "api", "host": "new.local"},
            changes={"host": ("old.local", "new.local")},
        )

        assert diff.operation == "update"
        assert diff.changes is not None
        assert "host" in diff.changes

    @pytest.mark.unit
    def test_unchanged_diff(self) -> None:
        """Should create deploy diff for unchanged operation."""
        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
        )

        assert diff.operation == "unchanged"
        assert diff.changes is None


class TestServiceDeploySummary:
    """Tests for ServiceDeploySummary model."""

    @pytest.mark.unit
    def test_empty_summary(self) -> None:
        """Should create empty summary."""
        summary = ServiceDeploySummary()

        assert summary.total_services == 0
        assert summary.creates == 0
        assert summary.updates == 0
        assert summary.unchanged == 0
        assert summary.has_changes is False

    @pytest.mark.unit
    def test_summary_with_changes(self) -> None:
        """Should report has_changes correctly."""
        summary = ServiceDeploySummary(total_services=3, creates=1, updates=1, unchanged=1)

        assert summary.has_changes is True

    @pytest.mark.unit
    def test_summary_no_changes(self) -> None:
        """Should report no changes when only unchanged."""
        summary = ServiceDeploySummary(total_services=2, creates=0, updates=0, unchanged=2)

        assert summary.has_changes is False


class TestServiceDeployResult:
    """Tests for ServiceDeployResult model."""

    @pytest.mark.unit
    def test_successful_create(self) -> None:
        """Should mark successful create as success."""
        result = ServiceDeployResult(
            service_name="api",
            service_status="created",
            routes_synced=5,
            routes_status="synced",
        )

        assert result.success is True
        assert result.service_status == "created"
        assert result.routes_synced == 5

    @pytest.mark.unit
    def test_failed_result(self) -> None:
        """Should mark failed as not success."""
        result = ServiceDeployResult(
            service_name="api",
            service_status="failed",
            error="Connection refused",
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    def test_unchanged_is_success(self) -> None:
        """Should mark unchanged as success."""
        result = ServiceDeployResult(
            service_name="api",
            service_status="unchanged",
        )

        assert result.success is True


class TestExceptions:
    """Tests for registry exceptions."""

    @pytest.mark.unit
    def test_registry_not_found_error(self) -> None:
        """Should create RegistryNotFoundError with path."""
        from pathlib import Path

        error = RegistryNotFoundError(Path("/config/services.yaml"))
        assert "/config/services.yaml" in str(error)
        assert error.path == Path("/config/services.yaml")

    @pytest.mark.unit
    def test_service_not_found_error(self) -> None:
        """Should create ServiceNotFoundError with name."""
        error = ServiceNotFoundError("api-service")
        assert "api-service" in str(error)
        assert error.name == "api-service"

    @pytest.mark.unit
    def test_service_already_exists_error(self) -> None:
        """Should create ServiceAlreadyExistsError with name."""
        error = ServiceAlreadyExistsError("api-service")
        assert "api-service" in str(error)
        assert error.name == "api-service"
