"""Unit tests for Kong Registry Manager."""

from __future__ import annotations

from pathlib import Path
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
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(
            title="Test", version="1.0"
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
        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(
            title="Test", version="1.0"
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

        mock_openapi_manager.parse_openapi.return_value = OpenAPISpec(
            title="Test", version="1.0"
        )
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
