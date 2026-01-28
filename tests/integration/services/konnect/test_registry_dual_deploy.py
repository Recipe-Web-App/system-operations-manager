"""Integration tests for Registry dual deployment to Gateway and Konnect.

These tests verify the full deployment flow using mocked HTTP responses
for both Kong Admin API and Konnect API.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.service_registry import (
    ServiceRegistryEntry,
)
from system_operations_manager.integrations.konnect.client import KonnectClient
from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.services.kong.registry_manager import RegistryManager


@pytest.fixture
def konnect_config() -> KonnectConfig:
    """Create test Konnect config."""
    return KonnectConfig(
        token=SecretStr("test-token-12345"),
        region=KonnectRegion.US,
        default_control_plane="test-cp",
    )


@pytest.fixture
def konnect_base_url() -> str:
    """Base URL for Konnect API."""
    return "https://us.api.konghq.com"


@pytest.fixture
def temp_registry_manager(tmp_path: Path) -> RegistryManager:
    """Create a registry manager with temp config directory."""
    config_dir = tmp_path / "ops" / "kong"
    return RegistryManager(config_dir=config_dir)


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock service manager for Gateway operations."""
    manager = MagicMock()
    # Default to service not found (will create)
    manager.get.side_effect = KongNotFoundError(
        message="Service not found",
        resource_type="service",
    )
    manager.create.side_effect = lambda svc: Service(
        id=f"gw-{svc.name}", name=svc.name, host=svc.host, port=svc.port or 80
    )
    manager.update.side_effect = lambda name, svc: Service(
        id=f"gw-{name}", name=svc.name, host=svc.host, port=svc.port or 80
    )
    return manager


class TestRegistryDualDeployCreate:
    """Integration tests for creating services in both Gateway and Konnect."""

    @pytest.mark.integration
    @respx.mock
    def test_deploy_to_both_gateway_and_konnect(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
        konnect_base_url: str,
    ) -> None:
        """Test deploying a new service to both Gateway and Konnect."""
        # Setup Konnect mock - service doesn't exist
        respx.get(
            f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/test-api"
        ).mock(return_value=Response(404, json={"message": "Not found"}))

        # Konnect create service mock
        respx.post(f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services").mock(
            return_value=Response(
                201,
                json={
                    "id": "konnect-svc-001",
                    "name": "test-api",
                    "host": "api.internal",
                    "port": 8080,
                    "protocol": "http",
                    "enabled": True,
                },
            )
        )

        # Add service to registry
        entry = ServiceRegistryEntry(
            name="test-api",
            host="api.internal",
            port=8080,
        )
        temp_registry_manager.add_service(entry)

        # Execute
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
            )

        # Verify Gateway deployment
        assert len(results.gateway) == 1
        assert results.gateway[0].service_name == "test-api"
        assert results.gateway[0].service_status in ["created", "unchanged"]
        mock_service_manager.create.assert_called_once()

        # Verify Konnect deployment
        assert results.konnect is not None
        assert len(results.konnect) == 1
        assert results.konnect[0].service_name == "test-api"
        assert results.konnect[0].service_status in ["created", "unchanged"]
        assert results.konnect_skipped is False

    @pytest.mark.integration
    @respx.mock
    def test_deploy_gateway_only_skips_konnect(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
    ) -> None:
        """Test deploying with --gateway-only flag skips Konnect."""
        # Add service to registry
        entry = ServiceRegistryEntry(
            name="gateway-only-api",
            host="api.internal",
        )
        temp_registry_manager.add_service(entry)

        # Execute with gateway_only=True
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
                gateway_only=True,
            )

        # Verify Gateway deployment
        assert len(results.gateway) == 1
        mock_service_manager.create.assert_called_once()

        # Verify Konnect was skipped
        assert results.konnect is None
        assert results.konnect_skipped is True


class TestRegistryDualDeployUpdate:
    """Integration tests for updating services in both Gateway and Konnect."""

    @pytest.mark.integration
    @respx.mock
    def test_update_existing_service_in_both(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
        konnect_base_url: str,
    ) -> None:
        """Test updating an existing service in both Gateway and Konnect."""
        # Gateway - service exists with different host (reset side_effect to use return_value)
        mock_service_manager.get.side_effect = None
        mock_service_manager.get.return_value = Service(
            id="gw-existing",
            name="existing-api",
            host="old-host.internal",
            port=8080,
        )

        # Konnect mock - service exists
        respx.get(
            f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/existing-api"
        ).mock(
            return_value=Response(
                200,
                json={
                    "id": "konnect-svc-existing",
                    "name": "existing-api",
                    "host": "old-host.internal",
                    "port": 8080,
                    "protocol": "http",
                },
            )
        )

        # Konnect update mock
        respx.patch(
            f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/konnect-svc-existing"
        ).mock(
            return_value=Response(
                200,
                json={
                    "id": "konnect-svc-existing",
                    "name": "existing-api",
                    "host": "new-host.internal",
                    "port": 8080,
                    "protocol": "http",
                },
            )
        )

        # Add service to registry with new host
        entry = ServiceRegistryEntry(
            name="existing-api",
            host="new-host.internal",
            port=8080,
        )
        temp_registry_manager.add_service(entry)

        # Execute
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
            )

        # Verify Gateway update
        assert len(results.gateway) == 1
        assert results.gateway[0].service_status in ["updated", "unchanged"]
        mock_service_manager.update.assert_called_once()

        # Verify Konnect update
        assert results.konnect is not None
        assert len(results.konnect) == 1


class TestRegistryDualDeployMultipleServices:
    """Integration tests for deploying multiple services."""

    @pytest.mark.integration
    @respx.mock
    def test_deploy_multiple_services_to_both(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
        konnect_base_url: str,
    ) -> None:
        """Test deploying multiple services to both Gateway and Konnect."""
        # Gateway - all services are new
        mock_service_manager.get.return_value = None

        # Setup Konnect mocks for multiple services
        for name in ["auth-api", "user-api", "order-api"]:
            # Service doesn't exist
            respx.get(
                f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/{name}"
            ).mock(return_value=Response(404, json={"message": "Not found"}))

            # Create succeeds
            respx.post(f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services").mock(
                return_value=Response(
                    201,
                    json={
                        "id": f"konnect-{name}",
                        "name": name,
                        "host": f"{name}.internal",
                        "port": 8080,
                        "protocol": "http",
                    },
                )
            )

        # Add services to registry
        services = [
            ServiceRegistryEntry(name="auth-api", host="auth-api.internal", port=8080),
            ServiceRegistryEntry(name="user-api", host="user-api.internal", port=8080),
            ServiceRegistryEntry(name="order-api", host="order-api.internal", port=8080),
        ]
        for svc in services:
            temp_registry_manager.add_service(svc)

        # Execute
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
            )

        # Verify Gateway
        assert len(results.gateway) == 3
        assert mock_service_manager.create.call_count == 3

        # Verify Konnect
        assert results.konnect is not None
        assert len(results.konnect) == 3
        assert results.all_success is True


class TestRegistryDualDeployErrorHandling:
    """Integration tests for error handling in dual deployment."""

    @pytest.mark.integration
    @respx.mock
    def test_konnect_error_doesnt_fail_gateway(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
        konnect_base_url: str,
    ) -> None:
        """Test that Konnect errors don't prevent Gateway deployment."""
        # Konnect returns server error
        respx.get(
            f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/test-api"
        ).mock(return_value=Response(500, json={"message": "Internal server error"}))

        # Add service to registry
        entry = ServiceRegistryEntry(
            name="test-api",
            host="api.internal",
        )
        temp_registry_manager.add_service(entry)

        # Execute
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
            )

        # Gateway should succeed
        assert len(results.gateway) == 1
        mock_service_manager.create.assert_called_once()

        # Konnect should have error recorded at result level (not per-service)
        # When exception occurs during Konnect deployment, konnect is empty list
        # and konnect_error contains the error message
        assert results.konnect is not None
        assert results.konnect_error is not None
        assert "Internal server error" in results.konnect_error

    @pytest.mark.integration
    @respx.mock
    def test_deploy_without_konnect_client(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test deploying without Konnect client skips Konnect deployment."""
        # Add service to registry
        entry = ServiceRegistryEntry(
            name="test-api",
            host="api.internal",
        )
        temp_registry_manager.add_service(entry)

        # Execute without konnect_client
        results = temp_registry_manager.deploy(
            mock_service_manager,
            openapi_sync_manager=None,
            skip_routes=True,
            # No konnect_client or control_plane_id
        )

        # Gateway should succeed
        assert len(results.gateway) == 1
        mock_service_manager.create.assert_called_once()

        # Konnect should be None when no client is provided
        # Note: konnect_skipped is only True when gateway_only=True
        assert results.konnect is None
        assert results.konnect_skipped is False  # Not explicitly skipped, just not configured


class TestRegistryDualDeployResults:
    """Integration tests for deployment result structure."""

    @pytest.mark.integration
    @respx.mock
    def test_deployment_result_properties(
        self,
        temp_registry_manager: RegistryManager,
        mock_service_manager: MagicMock,
        konnect_config: KonnectConfig,
        konnect_base_url: str,
    ) -> None:
        """Test that DeploymentResult properties work correctly."""
        # Setup Konnect mock
        respx.get(
            f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services/test-api"
        ).mock(return_value=Response(404, json={"message": "Not found"}))

        respx.post(f"{konnect_base_url}/v2/control-planes/cp-123/core-entities/services").mock(
            return_value=Response(
                201,
                json={
                    "id": "konnect-svc-001",
                    "name": "test-api",
                    "host": "api.internal",
                    "port": 8080,
                },
            )
        )

        # Add service
        entry = ServiceRegistryEntry(name="test-api", host="api.internal")
        temp_registry_manager.add_service(entry)

        # Execute
        with KonnectClient(konnect_config) as client:
            results = temp_registry_manager.deploy(
                mock_service_manager,
                openapi_sync_manager=None,
                skip_routes=True,
                konnect_client=client,
                control_plane_id="cp-123",
            )

        # Check all_success property
        assert results.all_success is True

        # Check gateway_summary property
        gateway_summary = results.gateway_summary
        assert "created" in gateway_summary or "unchanged" in gateway_summary

        # Check konnect_summary property
        konnect_summary = results.konnect_summary
        assert konnect_summary is not None
        assert "created" in konnect_summary or "unchanged" in konnect_summary
