"""Unit tests for Kong Registry Manager."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.service_registry import (
    ServiceAlreadyExistsError,
    ServiceNotFoundError,
    ServiceRegistryEntry,
)
from system_operations_manager.services.kong.registry_manager import RegistryManager


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory."""
    config_dir = tmp_path / "ops" / "kong"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def registry_manager(temp_config_dir: Path) -> RegistryManager:
    """Create a registry manager with temp config."""
    return RegistryManager(config_dir=temp_config_dir)


@pytest.fixture
def sample_registry_yaml() -> str:
    """Sample registry YAML content."""
    return """services:
  - name: api-service
    host: api.local
    port: 8080
    protocol: http
    tags:
      - api
      - prod
  - name: web-service
    host: web.local
    port: 80
"""


class TestRegistryManagerLoad:
    """Tests for RegistryManager.load()."""

    @pytest.mark.unit
    def test_load_empty_registry(self, registry_manager: RegistryManager) -> None:
        """Should return empty registry when file doesn't exist."""
        registry = registry_manager.load()
        assert len(registry.services) == 0

    @pytest.mark.unit
    def test_load_valid_registry(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should load registry from valid YAML file."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        registry = registry_manager.load()

        assert len(registry.services) == 2
        assert registry.services[0].name == "api-service"
        assert registry.services[0].host == "api.local"
        assert registry.services[0].port == 8080
        assert registry.services[1].name == "web-service"

    @pytest.mark.unit
    def test_load_empty_file(self, registry_manager: RegistryManager) -> None:
        """Should return empty registry for empty file."""
        registry_manager.config_path.write_text("")

        registry = registry_manager.load()
        assert len(registry.services) == 0

    @pytest.mark.unit
    def test_load_yaml_only_whitespace(self, registry_manager: RegistryManager) -> None:
        """Should return empty registry for whitespace-only file."""
        registry_manager.config_path.write_text("   \n  \n")

        registry = registry_manager.load()
        assert len(registry.services) == 0


class TestRegistryManagerSave:
    """Tests for RegistryManager.save()."""

    @pytest.mark.unit
    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Should create config directory if it doesn't exist."""
        config_dir = tmp_path / "new" / "nested" / "path"
        manager = RegistryManager(config_dir=config_dir)

        entry = ServiceRegistryEntry(name="api", host="api.local")
        manager.add_service(entry)

        assert config_dir.exists()
        assert manager.config_path.exists()

    @pytest.mark.unit
    def test_save_valid_yaml(self, registry_manager: RegistryManager) -> None:
        """Should save valid YAML that can be loaded."""
        entry1 = ServiceRegistryEntry(name="api", host="api.local", port=8080)
        entry2 = ServiceRegistryEntry(name="web", host="web.local")

        registry_manager.add_service(entry1)
        registry_manager.add_service(entry2)

        # Load and verify
        registry = registry_manager.load()
        assert len(registry.services) == 2
        assert registry.services[0].name == "api"
        assert registry.services[1].name == "web"


class TestRegistryManagerAddService:
    """Tests for RegistryManager.add_service()."""

    @pytest.mark.unit
    def test_add_service_to_empty(self, registry_manager: RegistryManager) -> None:
        """Should add service to empty registry."""
        entry = ServiceRegistryEntry(name="api", host="api.local")

        registry_manager.add_service(entry)

        registry = registry_manager.load()
        assert len(registry.services) == 1
        assert registry.services[0].name == "api"

    @pytest.mark.unit
    def test_add_service_to_existing(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should add service to existing registry."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        entry = ServiceRegistryEntry(name="new-service", host="new.local")
        registry_manager.add_service(entry)

        registry = registry_manager.load()
        assert len(registry.services) == 3

    @pytest.mark.unit
    def test_add_duplicate_service(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should raise error for duplicate service name."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        entry = ServiceRegistryEntry(name="api-service", host="different.local")

        with pytest.raises(ServiceAlreadyExistsError) as exc_info:
            registry_manager.add_service(entry)

        assert "api-service" in str(exc_info.value)


class TestRegistryManagerUpdateService:
    """Tests for RegistryManager.update_service()."""

    @pytest.mark.unit
    def test_update_existing_service(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should update existing service."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        updated = ServiceRegistryEntry(name="api-service", host="new-api.local", port=9090)
        registry_manager.update_service(updated)

        registry = registry_manager.load()
        service = registry.get_service("api-service")
        assert service is not None
        assert service.host == "new-api.local"
        assert service.port == 9090

    @pytest.mark.unit
    def test_update_nonexistent_service(self, registry_manager: RegistryManager) -> None:
        """Should raise error for non-existent service."""
        entry = ServiceRegistryEntry(name="nonexistent", host="api.local")

        with pytest.raises(ServiceNotFoundError) as exc_info:
            registry_manager.update_service(entry)

        assert "nonexistent" in str(exc_info.value)


class TestRegistryManagerRemoveService:
    """Tests for RegistryManager.remove_service()."""

    @pytest.mark.unit
    def test_remove_existing_service(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should remove existing service."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        registry_manager.remove_service("api-service")

        registry = registry_manager.load()
        assert len(registry.services) == 1
        assert registry.get_service("api-service") is None

    @pytest.mark.unit
    def test_remove_nonexistent_service(self, registry_manager: RegistryManager) -> None:
        """Should raise error for non-existent service."""
        with pytest.raises(ServiceNotFoundError) as exc_info:
            registry_manager.remove_service("nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestRegistryManagerGetService:
    """Tests for RegistryManager.get_service()."""

    @pytest.mark.unit
    def test_get_existing_service(
        self, registry_manager: RegistryManager, sample_registry_yaml: str
    ) -> None:
        """Should get existing service."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        service = registry_manager.get_service("api-service")

        assert service is not None
        assert service.name == "api-service"
        assert service.host == "api.local"

    @pytest.mark.unit
    def test_get_nonexistent_service(self, registry_manager: RegistryManager) -> None:
        """Should return None for non-existent service."""
        service = registry_manager.get_service("nonexistent")
        assert service is None


class TestRegistryManagerImport:
    """Tests for RegistryManager.import_from_file()."""

    @pytest.mark.unit
    def test_import_to_empty(self, registry_manager: RegistryManager, tmp_path: Path) -> None:
        """Should import services to empty registry."""
        import_file = tmp_path / "import.yaml"
        import_file.write_text(
            """services:
  - name: imported-api
    host: api.imported.local
    port: 8080
"""
        )

        count = registry_manager.import_from_file(import_file)

        assert count == 1
        registry = registry_manager.load()
        assert len(registry.services) == 1
        assert registry.services[0].name == "imported-api"

    @pytest.mark.unit
    def test_import_merge_new(
        self,
        registry_manager: RegistryManager,
        sample_registry_yaml: str,
        tmp_path: Path,
    ) -> None:
        """Should merge new services during import."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        import_file = tmp_path / "import.yaml"
        import_file.write_text(
            """services:
  - name: new-service
    host: new.local
"""
        )

        count = registry_manager.import_from_file(import_file)

        assert count == 1
        registry = registry_manager.load()
        assert len(registry.services) == 3

    @pytest.mark.unit
    def test_import_update_existing(
        self,
        registry_manager: RegistryManager,
        sample_registry_yaml: str,
        tmp_path: Path,
    ) -> None:
        """Should update existing services during import."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        import_file = tmp_path / "import.yaml"
        import_file.write_text(
            """services:
  - name: api-service
    host: updated-api.local
    port: 9999
"""
        )

        count = registry_manager.import_from_file(import_file)

        assert count == 1
        registry = registry_manager.load()
        assert len(registry.services) == 2  # No new services added
        service = registry.get_service("api-service")
        assert service is not None
        assert service.host == "updated-api.local"
        assert service.port == 9999


class TestRegistryManagerCalculateDiff:
    """Tests for RegistryManager.calculate_diff()."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        """Create mock service manager."""
        return MagicMock()

    @pytest.mark.unit
    def test_diff_create_new_service(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should detect new services to create."""
        entry = ServiceRegistryEntry(name="new-api", host="api.local")
        registry_manager.add_service(entry)

        # Service doesn't exist in Kong
        mock_service_manager.get.side_effect = KongNotFoundError("service", "new-api", "Not found")

        summary = registry_manager.calculate_diff(mock_service_manager)

        assert summary.creates == 1
        assert summary.updates == 0
        assert summary.unchanged == 0
        assert summary.has_changes is True

    @pytest.mark.unit
    def test_diff_update_existing_service(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should detect services to update."""
        entry = ServiceRegistryEntry(name="api", host="new-api.local", port=9090)
        registry_manager.add_service(entry)

        # Service exists in Kong with different values
        existing = Service(name="api", host="old-api.local", port=8080)
        mock_service_manager.get.return_value = existing

        summary = registry_manager.calculate_diff(mock_service_manager)

        assert summary.creates == 0
        assert summary.updates == 1
        assert summary.unchanged == 0
        assert len(summary.diffs) == 1
        assert summary.diffs[0].changes is not None
        assert "host" in summary.diffs[0].changes

    @pytest.mark.unit
    def test_diff_unchanged_service(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
    ) -> None:
        """Should detect unchanged services."""
        entry = ServiceRegistryEntry(name="api", host="api.local", port=8080)
        registry_manager.add_service(entry)

        # Service exists in Kong with same values
        existing = Service(name="api", host="api.local", port=8080)
        mock_service_manager.get.return_value = existing

        summary = registry_manager.calculate_diff(mock_service_manager)

        assert summary.creates == 0
        assert summary.updates == 0
        assert summary.unchanged == 1
        assert summary.has_changes is False

    @pytest.mark.unit
    def test_diff_filter_by_service_names(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        sample_registry_yaml: str,
    ) -> None:
        """Should filter diff by specific service names."""
        registry_manager.config_path.write_text(sample_registry_yaml)

        mock_service_manager.get.side_effect = KongNotFoundError(
            "service", "api-service", "Not found"
        )

        summary = registry_manager.calculate_diff(
            mock_service_manager, service_names=["api-service"]
        )

        assert summary.total_services == 1
        assert summary.creates == 1
        # web-service should not be checked
        assert mock_service_manager.get.call_count == 1


class TestRegistryManagerDeploy:
    """Tests for RegistryManager.deploy()."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        """Create mock service manager."""
        manager = MagicMock()
        manager.create.return_value = Service(name="api", host="api.local")
        manager.update.return_value = Service(name="api", host="api.local")
        return manager

    @pytest.fixture
    def mock_openapi_manager(self) -> MagicMock:
        """Create mock OpenAPI sync manager."""
        return MagicMock()

    @pytest.mark.unit
    def test_deploy_creates_service(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """Should create new service."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert len(results.gateway) == 1
        assert results.gateway[0].service_status == "created"
        assert results.gateway[0].success is True
        mock_service_manager.create.assert_called_once()

    @pytest.mark.unit
    def test_deploy_updates_service(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """Should update existing service."""
        entry = ServiceRegistryEntry(name="api", host="new-api.local")
        registry_manager.add_service(entry)

        existing = Service(name="api", host="old-api.local")
        mock_service_manager.get.return_value = existing

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert len(results.gateway) == 1
        assert results.gateway[0].service_status == "updated"
        mock_service_manager.update.assert_called_once()

    @pytest.mark.unit
    def test_deploy_skips_unchanged(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """Should skip unchanged services."""
        entry = ServiceRegistryEntry(name="api", host="api.local", port=80)
        registry_manager.add_service(entry)

        existing = Service(name="api", host="api.local", port=80)
        mock_service_manager.get.return_value = existing

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert len(results.gateway) == 1
        assert results.gateway[0].service_status == "unchanged"
        mock_service_manager.create.assert_not_called()
        mock_service_manager.update.assert_not_called()

    @pytest.mark.unit
    def test_deploy_skip_routes_flag(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """Should skip route sync when skip_routes=True."""
        entry = ServiceRegistryEntry(
            name="api", host="api.local", openapi_spec="/path/to/spec.yaml"
        )
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert results.gateway[0].routes_status == "skipped"
        mock_openapi_manager.parse_openapi.assert_not_called()

    @pytest.mark.unit
    def test_deploy_handles_create_failure(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """Should handle service creation failure."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")
        mock_service_manager.create.side_effect = Exception("Connection refused")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert len(results.gateway) == 1
        assert results.gateway[0].service_status == "failed"
        assert results.gateway[0].success is False
        assert "Connection refused" in (results.gateway[0].error or "")

    @pytest.mark.unit
    def test_deploy_omits_service_path_when_path_prefix_set(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Service path should be omitted when entry has path_prefix."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncResult,
        )

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: 3.0.0")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            path="/api/v1",
            openapi_spec=str(spec_file),
            path_prefix="/api/v1",
        )
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(title="Test", version="1.0")
        mock_openapi_manager.generate_route_mappings.return_value = []
        mock_openapi_manager.calculate_diff.return_value = SyncResult(service_name="api")
        mock_openapi_manager.apply_sync.return_value = SyncApplyResult(service_name="api")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        assert results.gateway[0].service_status == "created"
        create_call = mock_service_manager.create.call_args[0][0]
        # The path should NOT be /api/v1 — it should be omitted
        assert create_call.path != "/api/v1"

    @pytest.mark.unit
    def test_deploy_omits_service_path_when_spec_has_base_path(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Service path should be omitted when OpenAPI spec has base_path."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncResult,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            path="/api/v1",
            openapi_spec=str(spec_file),
        )
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(
            title="Test", version="1.0", base_path="/api/v1"
        )
        mock_openapi_manager.generate_route_mappings.return_value = []
        mock_openapi_manager.calculate_diff.return_value = SyncResult(service_name="api")
        mock_openapi_manager.apply_sync.return_value = SyncApplyResult(service_name="api")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        assert results.gateway[0].service_status == "created"
        create_call = mock_service_manager.create.call_args[0][0]
        assert create_call.path != "/api/v1"

    @pytest.mark.unit
    def test_deploy_unchanged_service_clears_path_when_omit_needed(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Unchanged service should have path cleared to '/' when omit_service_path is True."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncResult,
        )

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: 3.0.0")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            port=80,
            path="/api/v1",
            openapi_spec=str(spec_file),
            path_prefix="/api/v1",
        )
        registry_manager.add_service(entry)

        existing = Service(name="api", host="api.local", port=80, path="/api/v1")
        mock_service_manager.get.return_value = existing
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(title="Test", version="1.0")
        mock_openapi_manager.generate_route_mappings.return_value = []
        mock_openapi_manager.calculate_diff.return_value = SyncResult(service_name="api")
        mock_openapi_manager.apply_sync.return_value = SyncApplyResult(service_name="api")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        # Service was "unchanged" but path needed clearing
        assert results.gateway[0].service_status == "updated"
        update_call = mock_service_manager.update.call_args[0][1]
        assert update_call.path == "/"

    @pytest.mark.unit
    def test_deploy_unchanged_service_still_syncs_routes(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Route sync should proceed even when service is unchanged."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncResult,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            port=80,
            openapi_spec=str(spec_file),
        )
        registry_manager.add_service(entry)

        existing = Service(name="api", host="api.local", port=80)
        mock_service_manager.get.return_value = existing

        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(title="Test", version="1.0")
        mock_openapi_manager.generate_route_mappings.return_value = []
        mock_openapi_manager.calculate_diff.return_value = SyncResult(
            service_name="api",
        )
        mock_openapi_manager.apply_sync.return_value = SyncApplyResult(
            service_name="api",
        )

        registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        # Route sync should have been attempted (parse called for route sync)
        mock_openapi_manager.parse_openapi.assert_called()


class TestRegistryManagerDualDeploy:
    """Tests for dual deployment (Gateway + Konnect)."""

    @pytest.fixture
    def registry_manager(self, tmp_path: Path) -> RegistryManager:
        """Create registry manager with temp config path."""
        config_dir = tmp_path / "ops" / "kong"
        config_dir.mkdir(parents=True)
        return RegistryManager(config_dir)

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        """Create mock service manager for Gateway."""
        return MagicMock()

    @pytest.fixture
    def mock_openapi_manager(self) -> MagicMock:
        """Create mock OpenAPI sync manager."""
        return MagicMock()

    @pytest.fixture
    def mock_konnect_client(self) -> MagicMock:
        """Create mock Konnect client."""
        return MagicMock()

    @pytest.mark.unit
    def test_deploy_returns_deployment_result(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """deploy should return DeploymentResult."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            DeploymentResult,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert isinstance(result, DeploymentResult)
        assert result.gateway is not None
        assert result.konnect is None
        assert result.konnect_skipped is True

    @pytest.mark.unit
    def test_deploy_gateway_only_skips_konnect(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        mock_konnect_client: MagicMock,
    ) -> None:
        """deploy with gateway_only=True should skip Konnect."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
            konnect_client=mock_konnect_client,
            control_plane_id="cp-123",
        )

        assert result.konnect_skipped is True
        assert result.konnect is None
        # Konnect client should not be called
        mock_konnect_client.list_services.assert_not_called()
        mock_konnect_client.create_service.assert_not_called()

    @pytest.mark.unit
    def test_deploy_to_both_targets(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        mock_konnect_client: MagicMock,
    ) -> None:
        """deploy should deploy to both Gateway and Konnect."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        # Gateway: service doesn't exist
        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        # Konnect: simulate service doesn't exist
        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectNotFoundError,
        )

        mock_konnect_client.get_service.side_effect = KonnectNotFoundError(
            "Not found", status_code=404
        )

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=False,
            konnect_client=mock_konnect_client,
            control_plane_id="cp-123",
        )

        # Gateway should have results
        assert len(result.gateway) == 1
        assert result.gateway[0].service_status == "created"

        # Konnect should have results
        assert result.konnect is not None
        assert len(result.konnect) == 1
        assert result.konnect[0].service_status == "created"

    @pytest.mark.unit
    def test_deploy_without_konnect_client(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """deploy without konnect_client should only deploy to Gateway."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=False,  # Not gateway_only, but no konnect_client
            konnect_client=None,
            control_plane_id=None,
        )

        assert len(result.gateway) == 1
        assert result.konnect is None
        assert result.konnect_skipped is False  # Not explicitly skipped

    @pytest.mark.unit
    def test_deployment_result_all_success(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        mock_konnect_client: MagicMock,
    ) -> None:
        """DeploymentResult.all_success should return True when all succeed."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        from system_operations_manager.integrations.konnect.exceptions import (
            KonnectNotFoundError,
        )

        mock_konnect_client.get_service.side_effect = KonnectNotFoundError(
            "Not found", status_code=404
        )

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            konnect_client=mock_konnect_client,
            control_plane_id="cp-123",
        )

        assert result.all_success is True

    @pytest.mark.unit
    def test_deployment_result_gateway_summary(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """DeploymentResult should provide gateway summary."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        result = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        summary = result.gateway_summary
        assert summary["created"] == 1
        assert summary["updated"] == 0
        assert summary["unchanged"] == 0
        assert summary["failed"] == 0


class TestLoadNullYaml:
    """Tests for load() with YAML that parses to None (line 113)."""

    @pytest.mark.unit
    def test_load_yaml_only_comments_returns_empty_registry(
        self, registry_manager: RegistryManager
    ) -> None:
        """Should return empty registry when YAML file contains only comments (data is None)."""
        # yaml.safe_load of a comment-only file returns None, triggering line 113
        registry_manager.config_path.write_text("# just a comment\n# no data here\n")

        registry = registry_manager.load()

        assert len(registry.services) == 0

    @pytest.mark.unit
    def test_load_yaml_null_value_returns_empty_registry(
        self, registry_manager: RegistryManager
    ) -> None:
        """Should return empty registry when YAML file contains explicit null."""
        # 'null' is a valid YAML null; yaml.safe_load returns None
        registry_manager.config_path.write_text("null\n")

        registry = registry_manager.load()

        assert len(registry.services) == 0


class TestDeployEntryIsNone:
    """Tests for deploy() entry-is-None continue paths (lines 377 and 409)."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_openapi_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.unit
    def test_deploy_gateway_skips_when_entry_not_in_registry(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """deploy() Phase 1 loop must skip diffs whose service no longer exists in registry.

        We patch calculate_diff to return a diff for a name that is absent from
        the registry so the ``if entry is None: continue`` branch (line 377) fires.
        """
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
            ServiceDeploySummary,
        )

        # Registry is empty — no services at all
        ghost_diff = ServiceDeployDiff(
            service_name="ghost-service",
            operation="create",
            desired={"name": "ghost-service", "host": "ghost.local"},
        )
        fake_summary = ServiceDeploySummary(
            total_services=1,
            creates=1,
            diffs=[ghost_diff],
        )

        with patch.object(registry_manager, "calculate_diff", return_value=fake_summary):
            result = registry_manager.deploy(
                mock_service_manager,
                mock_openapi_manager,
                skip_routes=True,
                gateway_only=True,
            )

        # The ghost service diff was skipped; no gateway results
        assert result.gateway == []
        mock_service_manager.create.assert_not_called()

    @pytest.mark.unit
    def test_deploy_konnect_skips_when_entry_not_in_registry(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """deploy() Phase 2 loop skips diffs whose service is absent from registry (line 409)."""
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
            ServiceDeploySummary,
        )

        ghost_diff = ServiceDeployDiff(
            service_name="ghost-konnect",
            operation="create",
            desired={"name": "ghost-konnect", "host": "ghost.local"},
        )
        fake_summary = ServiceDeploySummary(
            total_services=1,
            creates=1,
            diffs=[ghost_diff],
        )

        mock_konnect_client = MagicMock()

        with (
            patch.object(registry_manager, "calculate_diff", return_value=fake_summary),
            patch(
                "system_operations_manager.services.konnect.service_manager.KonnectServiceManager"
            ) as MockKSM,
            patch(
                "system_operations_manager.services.konnect.route_manager.KonnectRouteManager"
            ) as MockKRM,
        ):
            MockKSM.return_value = MagicMock()
            MockKRM.return_value = MagicMock()

            result = registry_manager.deploy(
                mock_service_manager,
                mock_openapi_manager,
                skip_routes=True,
                gateway_only=False,
                konnect_client=mock_konnect_client,
                control_plane_id="cp-123",
            )

        # Konnect results list is initialised but the ghost diff is skipped
        assert result.konnect == []


class TestDeployKonnectPhaseException:
    """Tests for lines 420-422: outer exception handler in Konnect phase of deploy()."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_openapi_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.unit
    def test_deploy_konnect_outer_exception_sets_konnect_error(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """When KonnectServiceManager/KonnectRouteManager construction raises, konnect_error is set."""
        from unittest.mock import patch

        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        mock_konnect_client = MagicMock()

        with patch(
            "system_operations_manager.services.konnect.service_manager.KonnectServiceManager",
            side_effect=RuntimeError("manager init failed"),
        ):
            result = registry_manager.deploy(
                mock_service_manager,
                mock_openapi_manager,
                skip_routes=True,
                gateway_only=False,
                konnect_client=mock_konnect_client,
                control_plane_id="cp-123",
            )

        assert result.konnect_error is not None
        assert "manager init failed" in result.konnect_error
        # konnect_results is set to [] before the try block, so after the exception
        # the list is empty (not None) but konnect_error captures the failure
        assert result.konnect == []


class TestDeploySingleServiceEdgeCases:
    """Tests for uncovered branches in _deploy_single_service() (lines 471-526)."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        manager = MagicMock()
        manager.create.return_value = Service(name="api", host="api.local")
        manager.update.return_value = Service(name="api", host="api.local")
        return manager

    @pytest.fixture
    def mock_openapi_manager(self) -> MagicMock:
        return MagicMock()

    # ------------------------------------------------------------------
    # Lines 471-472: omit_service_path branch — spec parse silently fails
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_deploy_spec_parse_fails_silently_during_omit_check(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When parse_openapi raises during omit_service_path check, error is swallowed (pass)."""
        spec_file = tmp_path / "bad.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            path="/api",
            openapi_spec=str(spec_file),
            # No path_prefix — triggers the spec-parse branch (lines 465-472)
        )
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")
        # Raise during the omit_service_path check; the exception must be swallowed
        mock_openapi_manager.parse_openapi.side_effect = [
            Exception("corrupt spec"),  # first call: omit check
            Exception("corrupt spec"),  # second call if route sync runs
        ]

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        # Service was still created despite the parse error
        assert results.gateway[0].service_status == "created"
        mock_service_manager.create.assert_called_once()

    # ------------------------------------------------------------------
    # Lines 486-487: unchanged path-clear update raises — warning logged
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_deploy_unchanged_path_clear_failure_is_warned(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When clearing the stale path on an unchanged service fails, status stays 'unchanged'.

        omit_service_path is only computed when skip_routes=False, so we must use that
        flag here. After the path-clear update fails (warning logged), flow continues to
        route sync — we stub _sync_routes to avoid testing it here.
        """
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.openapi import OpenAPISpec

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            port=80,
            path="/api/v1",
            openapi_spec=str(spec_file),
            path_prefix="/api/v1",  # triggers omit_service_path=True without spec parse
        )
        registry_manager.add_service(entry)

        # Service is "unchanged" in Kong — the diff must be "unchanged" so the code
        # enters the path-clear try/except block (lines 479-487).
        existing = Service(name="api", host="api.local", port=80, path="/api/v1")
        mock_service_manager.get.return_value = existing

        # parse_openapi not needed because path_prefix is set (omit check short-circuits)
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(title="T", version="1.0")
        # update() raises during path-clear — triggers lines 486-487
        mock_service_manager.update.side_effect = Exception("update failed")

        # skip_routes=False is required so omit_service_path logic executes.
        # Stub _sync_routes so route sync doesn't interfere with the assertion.
        with patch.object(registry_manager, "_sync_routes", return_value=(0, "synced")):
            results = registry_manager.deploy(
                mock_service_manager,
                mock_openapi_manager,
                skip_routes=False,
                gateway_only=True,
            )

        # Despite the update failure the result is still "unchanged" (warning, not early return)
        assert results.gateway[0].service_status == "unchanged"

    # ------------------------------------------------------------------
    # Lines 507-509: update operation failure returns early with "failed"
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_deploy_update_failure_returns_failed_status(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """When service_manager.update() raises, service_status is 'failed'."""
        entry = ServiceRegistryEntry(name="api", host="new-api.local")
        registry_manager.add_service(entry)

        existing = Service(name="api", host="old-api.local")
        mock_service_manager.get.return_value = existing
        mock_service_manager.update.side_effect = Exception("update boom")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=True,
            gateway_only=True,
        )

        assert results.gateway[0].service_status == "failed"
        assert results.gateway[0].success is False
        assert "update boom" in (results.gateway[0].error or "")

    # ------------------------------------------------------------------
    # Lines 519, 523-526: route sync — no_spec branch and sync + exception
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_deploy_no_openapi_spec_sets_no_spec_status(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
    ) -> None:
        """When entry has no openapi_spec, routes_status is 'no_spec' (line 519)."""
        entry = ServiceRegistryEntry(name="api", host="api.local")
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        assert results.gateway[0].routes_status == "no_spec"
        mock_openapi_manager.parse_openapi.assert_not_called()

    @pytest.mark.unit
    def test_deploy_route_sync_exception_sets_failed_status(
        self,
        registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        mock_openapi_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When _sync_routes raises, routes_status is 'failed' and error is set (lines 523-526)."""
        from system_operations_manager.integrations.kong.models.openapi import OpenAPISpec

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            openapi_spec=str(spec_file),
        )
        registry_manager.add_service(entry)

        mock_service_manager.get.side_effect = KongNotFoundError("service", "api", "Not found")
        # First parse_openapi call is for the omit check (returns spec without base_path)
        # Second call (inside _sync_routes via parse_openapi) raises
        mock_openapi_manager.parse_openapi.side_effect = [
            OpenAPISpec(title="T", version="1.0"),
            RuntimeError("route sync boom"),
        ]

        results = registry_manager.deploy(
            mock_service_manager,
            mock_openapi_manager,
            skip_routes=False,
            gateway_only=True,
        )

        assert results.gateway[0].routes_status == "failed"
        assert "route sync boom" in (results.gateway[0].error or "")


class TestDeploySingleServiceToKonnect:
    """Tests for _deploy_single_service_to_konnect() (lines 536-618)."""

    @pytest.fixture
    def registry_manager(self, tmp_path: Path) -> RegistryManager:
        config_dir = tmp_path / "ops" / "kong"
        config_dir.mkdir(parents=True)
        return RegistryManager(config_dir)

    def _make_diff(
        self, service_name: str, operation: Literal["create", "update", "unchanged"]
    ) -> object:
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        return ServiceDeployDiff(
            service_name=service_name,
            operation=operation,
            desired={"name": service_name, "host": f"{service_name}.local"},
        )

    # ------------------------------------------------------------------
    # Line 567: unchanged diff + service does NOT yet exist in Konnect
    #            → create path runs even when gateway diff says "unchanged"
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_creates_service_when_diff_unchanged_but_not_in_konnect(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When diff.operation=='unchanged' but konnect_exists==False, service is created."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local")

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = False  # not in Konnect yet
        mock_ksm.create.return_value = Service(name="api", host="api.local")

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
            desired={"name": "api", "host": "api.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=True
        )

        assert result.service_status == "created"
        mock_ksm.create.assert_called_once()

    # ------------------------------------------------------------------
    # Lines 575-581: Konnect create fails → returns "failed"
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_create_failure_returns_failed(self, registry_manager: RegistryManager) -> None:
        """When Konnect create raises, ServiceDeployResult has service_status='failed'."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local")

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = False
        mock_ksm.create.side_effect = Exception("Konnect create failed")

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="create",
            desired={"name": "api", "host": "api.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=True
        )

        assert result.service_status == "failed"
        assert "Konnect create failed" in (result.error or "")

    # ------------------------------------------------------------------
    # Lines 584-588: Konnect update succeeds (else branch)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_update_success(self, registry_manager: RegistryManager) -> None:
        """When service exists and diff.operation=='update', Konnect update is called."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api-new.local")

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True
        mock_ksm.update.return_value = Service(name="api", host="api-new.local")

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="update",
            desired={"name": "api", "host": "api-new.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=True
        )

        assert result.service_status == "updated"
        mock_ksm.update.assert_called_once()

    # ------------------------------------------------------------------
    # Lines 589-595: Konnect update fails → returns "failed"
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_update_failure_returns_failed(self, registry_manager: RegistryManager) -> None:
        """When Konnect update raises, ServiceDeployResult has service_status='failed'."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local")

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True
        mock_ksm.update.side_effect = Exception("Konnect update boom")

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="update",
            desired={"name": "api", "host": "api.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=True
        )

        assert result.service_status == "failed"
        assert "Konnect update boom" in (result.error or "")

    # ------------------------------------------------------------------
    # Lines 598-599: skip_routes → routes_status 'skipped'
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_skip_routes_flag(self, registry_manager: RegistryManager) -> None:
        """skip_routes=True should set routes_status='skipped' on Konnect result."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec="/some/spec.yaml")

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True  # exists, unchanged

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
            desired={"name": "api", "host": "api.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=True
        )

        assert result.routes_status == "skipped"

    # ------------------------------------------------------------------
    # Lines 600-601: no openapi_spec → routes_status 'no_spec'
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_no_spec_sets_no_spec_status(self, registry_manager: RegistryManager) -> None:
        """Entry with no openapi_spec gives routes_status='no_spec' in Konnect result."""
        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        entry = ServiceRegistryEntry(name="api", host="api.local")  # no openapi_spec

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
            desired={"name": "api", "host": "api.local"},
        )

        result = registry_manager._deploy_single_service_to_konnect(
            diff, entry, mock_ksm, mock_krm, skip_routes=False
        )

        assert result.routes_status == "no_spec"

    # ------------------------------------------------------------------
    # Lines 603-610: actual route sync call + exception handler
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_konnect_route_sync_is_called_when_spec_present(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When entry has openapi_spec, _sync_routes_to_konnect is called and result used."""
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec=str(spec_file))

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
            desired={"name": "api", "host": "api.local"},
        )

        with patch.object(
            registry_manager, "_sync_routes_to_konnect", return_value=(3, "synced")
        ) as mock_sync:
            result = registry_manager._deploy_single_service_to_konnect(
                diff, entry, mock_ksm, mock_krm, skip_routes=False
            )

        mock_sync.assert_called_once_with(entry, mock_ksm, mock_krm)
        assert result.routes_synced == 3
        assert result.routes_status == "synced"

    @pytest.mark.unit
    def test_konnect_route_sync_exception_sets_failed_status(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When _sync_routes_to_konnect raises, routes_status='failed' and error recorded."""
        from unittest.mock import patch

        from system_operations_manager.integrations.kong.models.service_registry import (
            ServiceDeployDiff,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec=str(spec_file))

        mock_ksm = MagicMock()
        mock_ksm.exists.return_value = True

        mock_krm = MagicMock()

        diff = ServiceDeployDiff(
            service_name="api",
            operation="unchanged",
            desired={"name": "api", "host": "api.local"},
        )

        with patch.object(
            registry_manager,
            "_sync_routes_to_konnect",
            side_effect=RuntimeError("konnect sync exploded"),
        ):
            result = registry_manager._deploy_single_service_to_konnect(
                diff, entry, mock_ksm, mock_krm, skip_routes=False
            )

        assert result.routes_status == "failed"
        assert "konnect sync exploded" in (result.error or "")


class TestSyncRoutesToKonnect:
    """Tests for _sync_routes_to_konnect() (lines 636-762)."""

    @pytest.fixture
    def registry_manager(self, tmp_path: Path) -> RegistryManager:
        config_dir = tmp_path / "ops" / "kong"
        config_dir.mkdir(parents=True)
        return RegistryManager(config_dir)

    def _make_entry(
        self,
        tmp_path: Path,
        spec_content: str | None = None,
        *,
        name: str = "api",
        path_prefix: str | None = None,
        tags: list[str] | None = None,
        spec_suffix: str = ".yaml",
    ) -> ServiceRegistryEntry:
        """Build a ServiceRegistryEntry with an optional on-disk OpenAPI spec."""
        if spec_content is not None:
            spec_file = tmp_path / f"spec{spec_suffix}"
            spec_file.write_text(spec_content)
            openapi_spec = str(spec_file)
        else:
            openapi_spec = None
        return ServiceRegistryEntry(
            name=name,
            host=f"{name}.local",
            openapi_spec=openapi_spec,
            path_prefix=path_prefix,
            tags=tags,
        )

    def _mock_ksm(self, service_id: str = "uuid-1234") -> MagicMock:
        """Mock KonnectServiceManager that returns a service with the given id."""
        service = Service(name="api", host="api.local", id=service_id)
        mock = MagicMock()
        mock.get.return_value = service
        return mock

    # ------------------------------------------------------------------
    # Line 648: spec_path is None → (0, "no_spec")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_no_spec_path_returns_no_spec(
        self, registry_manager: RegistryManager
    ) -> None:
        """When entry has no openapi_spec, _sync_routes_to_konnect returns (0, 'no_spec')."""
        entry = ServiceRegistryEntry(name="api", host="api.local")  # no spec

        mock_ksm = MagicMock()
        mock_krm = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert count == 0
        assert status == "no_spec"

    # ------------------------------------------------------------------
    # Line 648: spec_path exists but file is absent → (0, "no_spec")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_missing_spec_file_returns_no_spec(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When the openapi_spec path doesn't exist on disk, returns (0, 'no_spec')."""
        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            openapi_spec=str(tmp_path / "nonexistent.yaml"),
        )

        mock_ksm = MagicMock()
        mock_krm = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert count == 0
        assert status == "no_spec"

    # ------------------------------------------------------------------
    # Lines 656-658: parse error → (0, "failed")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_corrupt_yaml_returns_failed(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When the spec file cannot be parsed, returns (0, 'failed')."""
        entry = self._make_entry(tmp_path, spec_content=":\n  - bad: [unclosed")

        mock_ksm = MagicMock()
        mock_krm = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert count == 0
        assert status == "failed"

    # ------------------------------------------------------------------
    # Lines 661-663: no paths in spec → (0, "synced")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_no_paths_returns_synced(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When the spec has no 'paths', returns (0, 'synced')."""
        spec_content = "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        count, status = registry_manager._sync_routes_to_konnect(
            entry, self._mock_ksm(), MagicMock()
        )

        assert count == 0
        assert status == "synced"

    # ------------------------------------------------------------------
    # Lines 666-676: service lookup fails → raises ValueError
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_service_lookup_failure_raises(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When konnect_service_manager.get() raises, _sync_routes_to_konnect raises ValueError."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /users:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = MagicMock()
        mock_ksm.get.side_effect = Exception("service not found in Konnect")

        mock_krm = MagicMock()

        with pytest.raises(ValueError, match="Konnect API error"):
            registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

    # ------------------------------------------------------------------
    # Lines 668-669: service has no id → raises ValueError
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_service_has_no_id_raises(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When the looked-up Konnect service has no id, raises ValueError."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /users:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = MagicMock()
        # Service returned with id=None
        mock_ksm.get.return_value = Service(name="api", host="api.local", id=None)

        mock_krm = MagicMock()

        with pytest.raises(ValueError, match="Konnect API error"):
            registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

    # ------------------------------------------------------------------
    # Lines 700-748: happy path — creates new route
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_creates_new_route(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When a path has no existing Konnect route, create is called."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /users:\n    get:\n      responses:\n        '200':\n          description: OK\n"
            "    post:\n      responses:\n        '201':\n          description: Created\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-abc")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)  # no existing routes

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1  # one path → one route
        mock_krm.create.assert_called_once()
        # Ensure the service UUID was passed, not the name
        create_call = mock_krm.create.call_args
        assert create_call.kwargs.get("service_name_or_id") == "uuid-abc"

    # ------------------------------------------------------------------
    # Lines 739-743: update existing route
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_updates_existing_route(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When a route with the same name already exists, update is called."""
        from system_operations_manager.integrations.kong.models.route import Route

        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /users:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content, name="api")

        # The route name generated by _sync_routes_to_konnect for service "api" and path "/users":
        # safe_path = "/users".replace("/", "-").strip("-") = "users"
        # route_name = "api" + "users" = "apiusers"
        existing_route = Route(name="apiusers", id="route-id-99", paths=["/users"])
        mock_ksm = self._mock_ksm("uuid-abc")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([existing_route], None)

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1
        mock_krm.update.assert_called_once()
        # First positional arg to update() is the existing route's id
        assert mock_krm.update.call_args[0][0] == "route-id-99"
        mock_krm.create.assert_not_called()

    # ------------------------------------------------------------------
    # Lines 749-754: route create/update raises — logged, skipped, count unchanged
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_route_create_error_is_logged_not_raised(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When route create raises, the error is logged and routes_synced stays 0."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /items:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-xyz")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.side_effect = Exception("route create failed")

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        # Exception is swallowed; returns synced with count=0
        assert status == "synced"
        assert count == 0

    # ------------------------------------------------------------------
    # Lines 684-697: path prefix from spec servers (absolute URL)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_prefix_from_absolute_server_url(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """Effective prefix is derived from an absolute URL in servers[0].url."""
        spec_content = (
            "openapi: '3.0.0'\n"
            "info:\n  title: T\n  version: '1'\n"
            "servers:\n  - url: https://api.example.com/v2\n"
            "paths:\n  /items:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-srv")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1
        # The route paths should include the prefix /v2
        created_route = mock_krm.create.call_args[0][0]
        assert created_route.paths == ["/v2/items"]

    # ------------------------------------------------------------------
    # Lines 694-697: path prefix from relative server url
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_prefix_from_relative_server_url(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """Effective prefix is derived from a relative URL in servers[0].url."""
        spec_content = (
            "openapi: '3.0.0'\n"
            "info:\n  title: T\n  version: '1'\n"
            "servers:\n  - url: /v3\n"
            "paths:\n  /orders:\n    post:\n      responses:\n        '201':\n          description: Created\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-rel")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1
        created_route = mock_krm.create.call_args[0][0]
        assert created_route.paths == ["/v3/orders"]

    # ------------------------------------------------------------------
    # Lines 698 (entry.path_prefix overrides server url)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_explicit_path_prefix_overrides_server(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """entry.path_prefix takes precedence over servers[0].url base path."""
        spec_content = (
            "openapi: '3.0.0'\n"
            "info:\n  title: T\n  version: '1'\n"
            "servers:\n  - url: https://api.example.com/spec-prefix\n"
            "paths:\n  /things:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(
            tmp_path, spec_content=spec_content, path_prefix="/explicit-prefix"
        )

        mock_ksm = self._mock_ksm("uuid-pref")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1
        created_route = mock_krm.create.call_args[0][0]
        assert created_route.paths == ["/explicit-prefix/things"]

    # ------------------------------------------------------------------
    # JSON spec file (lines 654-655)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_json_spec_parsed_correctly(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """A JSON OpenAPI spec file is parsed correctly."""
        import json

        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/widgets": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                }
            },
        }
        entry = self._make_entry(tmp_path, spec_content=json.dumps(spec_data), spec_suffix=".json")

        mock_ksm = self._mock_ksm("uuid-json")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert status == "synced"
        assert count == 1

    # ------------------------------------------------------------------
    # Tags propagated to routes
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_tags_propagated_to_routes(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """Entry tags are included in the created route's tags alongside service tag."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /ping:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content, tags=["env:prod", "team:a"])

        mock_ksm = self._mock_ksm("uuid-tags")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        created_route = mock_krm.create.call_args[0][0]
        assert "service:api" in created_route.tags
        assert "env:prod" in created_route.tags
        assert "team:a" in created_route.tags

    # ------------------------------------------------------------------
    # Paths with non-dict value in spec are skipped (line 702)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_skips_non_dict_path_values(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """Paths whose value is not a dict are silently skipped."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n"
            "  /valid:\n    get:\n      responses:\n        '200':\n          description: OK\n"
            "  /invalid: null\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-skip")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, _status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        # Only /valid is processed; /invalid is skipped
        assert count == 1

    # ------------------------------------------------------------------
    # Paths with no matching HTTP methods are skipped (line 711)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_skips_paths_with_no_http_methods(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """Paths that define no recognised HTTP methods produce no routes."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /webhooks:\n    x-webhook-only: true\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content)

        mock_ksm = self._mock_ksm("uuid-nomethods")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)

        count, status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert count == 0
        assert status == "synced"
        mock_krm.create.assert_not_called()

    # ------------------------------------------------------------------
    # Root path ("/") produces entry.name as route_name (line 716)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_to_konnect_root_path_uses_service_name_as_route_name(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """A path of '/' produces a route named after the service (safe_path is empty)."""
        spec_content = (
            "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\n"
            "paths:\n  /:\n    get:\n      responses:\n        '200':\n          description: OK\n"
        )
        entry = self._make_entry(tmp_path, spec_content=spec_content, name="root-api")

        mock_ksm = self._mock_ksm("uuid-root")
        mock_krm = MagicMock()
        mock_krm.list_by_service.return_value = ([], None)
        mock_krm.create.return_value = MagicMock()

        count, _status = registry_manager._sync_routes_to_konnect(entry, mock_ksm, mock_krm)

        assert count == 1
        created_route = mock_krm.create.call_args[0][0]
        assert created_route.name == "root-api"


class TestSyncRoutes:
    """Tests for _sync_routes() (lines 764-811)."""

    @pytest.fixture
    def registry_manager(self, tmp_path: Path) -> RegistryManager:
        config_dir = tmp_path / "ops" / "kong"
        config_dir.mkdir(parents=True)
        return RegistryManager(config_dir)

    # ------------------------------------------------------------------
    # Lines 780-785: spec_path is None or doesn't exist → (0, "failed")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_no_spec_path_returns_failed(
        self, registry_manager: RegistryManager
    ) -> None:
        """When entry has no openapi_spec, _sync_routes returns (0, 'failed')."""
        entry = ServiceRegistryEntry(name="api", host="api.local")  # no spec
        mock_openapi = MagicMock()

        count, status = registry_manager._sync_routes(entry, mock_openapi)

        assert count == 0
        assert status == "failed"
        mock_openapi.parse_openapi.assert_not_called()

    @pytest.mark.unit
    def test_sync_routes_missing_spec_file_returns_failed(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When the spec file doesn't exist on disk, _sync_routes returns (0, 'failed')."""
        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            openapi_spec=str(tmp_path / "does_not_exist.yaml"),
        )
        mock_openapi = MagicMock()

        count, status = registry_manager._sync_routes(entry, mock_openapi)

        assert count == 0
        assert status == "failed"

    # ------------------------------------------------------------------
    # Lines 799-800: no changes in diff → (0, "synced")
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_no_changes_returns_synced(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When sync_result.has_changes is False, _sync_routes returns (0, 'synced')."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncResult,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec=str(spec_file))

        mock_openapi = MagicMock()
        mock_openapi.parse_openapi.return_value = OpenAPISpec(title="T", version="1.0")
        mock_openapi.generate_route_mappings.return_value = []
        # has_changes is False by default (no creates/updates/deletes)
        mock_openapi.calculate_diff.return_value = SyncResult(service_name="api")

        count, status = registry_manager._sync_routes(entry, mock_openapi)

        assert count == 0
        assert status == "synced"
        mock_openapi.apply_sync.assert_not_called()

    # ------------------------------------------------------------------
    # Lines 802-810: has_changes → apply_sync called, count = len(succeeded)
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_sync_routes_applies_changes_and_returns_count(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """When sync_result.has_changes is True, apply_sync is called and count returned."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncChange,
            SyncOperationResult,
            SyncResult,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(
            name="api",
            host="api.local",
            openapi_spec=str(spec_file),
            path_prefix="/v1",
            strip_path=True,
        )

        mock_openapi = MagicMock()
        mock_openapi.parse_openapi.return_value = OpenAPISpec(title="T", version="1.0")
        mock_openapi.generate_route_mappings.return_value = []

        # Simulate two routes to create (has_changes=True)
        create_change = SyncChange(
            operation="create", route_name="api-users", path="/users", methods=["GET"]
        )
        sync_result = SyncResult(service_name="api", creates=[create_change, create_change])
        mock_openapi.calculate_diff.return_value = sync_result

        # apply_sync returns 2 succeeded operations
        op1 = SyncOperationResult(operation="create", route_name="api-users", result="success")
        op2 = SyncOperationResult(operation="create", route_name="api-items", result="success")
        apply_result = SyncApplyResult(service_name="api", operations=[op1, op2])
        mock_openapi.apply_sync.return_value = apply_result

        count, status = registry_manager._sync_routes(entry, mock_openapi)

        assert count == 2
        assert status == "synced"
        mock_openapi.apply_sync.assert_called_once_with(sync_result, force=True)
        # Verify path_prefix and strip_path are forwarded
        mock_openapi.generate_route_mappings.assert_called_once_with(
            mock_openapi.parse_openapi.return_value,
            "api",
            path_prefix="/v1",
            strip_path=True,
        )

    @pytest.mark.unit
    def test_sync_routes_partial_apply_counts_only_succeeded(
        self, registry_manager: RegistryManager, tmp_path: Path
    ) -> None:
        """routes_count reflects only succeeded operations, not failed ones."""
        from system_operations_manager.integrations.kong.models.openapi import (
            OpenAPISpec,
            SyncApplyResult,
            SyncChange,
            SyncOperationResult,
            SyncResult,
        )

        spec_file = tmp_path / "api.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        entry = ServiceRegistryEntry(name="api", host="api.local", openapi_spec=str(spec_file))

        mock_openapi = MagicMock()
        mock_openapi.parse_openapi.return_value = OpenAPISpec(title="T", version="1.0")
        mock_openapi.generate_route_mappings.return_value = []

        create_change = SyncChange(
            operation="create", route_name="api-users", path="/users", methods=["GET"]
        )
        sync_result = SyncResult(
            service_name="api", creates=[create_change, create_change, create_change]
        )
        mock_openapi.calculate_diff.return_value = sync_result

        # One success, two failures
        op_ok = SyncOperationResult(operation="create", route_name="api-a", result="success")
        op_fail1 = SyncOperationResult(
            operation="create", route_name="api-b", result="failed", error="boom"
        )
        op_fail2 = SyncOperationResult(
            operation="create", route_name="api-c", result="failed", error="boom"
        )
        apply_result = SyncApplyResult(service_name="api", operations=[op_ok, op_fail1, op_fail2])
        mock_openapi.apply_sync.return_value = apply_result

        count, status = registry_manager._sync_routes(entry, mock_openapi)

        assert count == 1  # only the succeeded one
        assert status == "synced"
