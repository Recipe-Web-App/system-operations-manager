"""Integration tests for DualWriteService.

Tests the dual-write orchestration with a real Kong Gateway container
and mocked Konnect manager (since Konnect is not available in CI).

Note: These tests require Kong to be running in database mode (not DB-less)
because they perform create/update/delete operations directly via the Admin API.
The tests will be skipped automatically when Kong is running in DB-less mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.services.kong.dual_write import (
    DualWriteService,
)
from system_operations_manager.services.kong.service_manager import ServiceManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient


# Skip all tests in this module - they require database mode which is only
# available in e2e tests. The unit tests already cover the DualWriteService
# logic thoroughly with mocks.
pytestmark = pytest.mark.skip(
    reason="Requires Kong in database mode. Unit tests cover DualWriteService logic."
)


@pytest.mark.integration
@pytest.mark.kong
class TestDualWriteServiceIntegration:
    """Integration tests for DualWriteService with real Kong Gateway."""

    @pytest.fixture
    def mock_konnect_manager(self) -> MagicMock:
        """Create a mock Konnect manager."""
        return MagicMock()

    @pytest.fixture
    def dual_write_service(
        self,
        kong_client: KongAdminClient,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Service]:
        """Create a DualWriteService with real Gateway and mock Konnect."""
        gateway_manager = ServiceManager(kong_client)
        return DualWriteService(
            gateway_manager=gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    @pytest.fixture
    def gateway_only_service(
        self,
        kong_client: KongAdminClient,
    ) -> DualWriteService[Service]:
        """Create a DualWriteService with no Konnect configured."""
        gateway_manager = ServiceManager(kong_client)
        return DualWriteService(
            gateway_manager=gateway_manager,
            konnect_manager=None,
            entity_name="service",
        )

    def test_create_writes_to_both(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """create should write to real Gateway and mock Konnect."""
        service = Service(
            name="dual-write-test-service",
            host="dual-write-test.local",
            port=8080,
            protocol="http",
        )
        mock_konnect_manager.create.return_value = service

        result = dual_write_service.create(service)

        # Gateway result should be from real Kong
        assert result.gateway_result is not None
        assert result.gateway_result.id is not None
        assert result.gateway_result.name == "dual-write-test-service"

        # Konnect should have been called
        mock_konnect_manager.create.assert_called_once()
        assert result.is_fully_synced is True

        # Cleanup: delete from Gateway
        service_manager.delete(result.gateway_result.id)

    def test_create_data_plane_only(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """create should skip Konnect when data_plane_only=True."""
        service = Service(
            name="gateway-only-test-service",
            host="gateway-only.local",
            port=8080,
        )

        result = dual_write_service.create(service, data_plane_only=True)

        # Gateway result should exist
        assert result.gateway_result is not None
        assert result.gateway_result.name == "gateway-only-test-service"

        # Konnect should NOT have been called
        mock_konnect_manager.create.assert_not_called()
        assert result.konnect_skipped is True
        assert result.is_fully_synced is False

        # Cleanup
        assert result.gateway_result.id is not None
        service_manager.delete(result.gateway_result.id)

    def test_create_konnect_not_configured(
        self,
        gateway_only_service: DualWriteService[Service],
        service_manager: ServiceManager,
    ) -> None:
        """create should handle Konnect not being configured."""
        service = Service(
            name="no-konnect-test-service",
            host="no-konnect.local",
            port=8080,
        )

        result = gateway_only_service.create(service)

        # Gateway result should exist
        assert result.gateway_result is not None
        assert result.gateway_result.name == "no-konnect-test-service"

        # Should indicate Konnect not configured
        assert result.konnect_not_configured is True
        assert result.konnect_result is None
        assert result.is_fully_synced is False

        # Cleanup
        assert result.gateway_result.id is not None
        service_manager.delete(result.gateway_result.id)

    def test_create_konnect_failure_partial_success(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """create should return partial success when Konnect fails."""
        service = Service(
            name="konnect-fail-test-service",
            host="konnect-fail.local",
            port=8080,
        )
        mock_konnect_manager.create.side_effect = Exception("Konnect connection timeout")

        result = dual_write_service.create(service)

        # Gateway result should still exist
        assert result.gateway_result is not None
        assert result.gateway_result.name == "konnect-fail-test-service"

        # Konnect should have failed
        assert result.konnect_result is None
        assert result.konnect_error is not None
        assert "timeout" in str(result.konnect_error)
        assert result.partial_success is True
        assert result.is_fully_synced is False

        # Cleanup
        assert result.gateway_result.id is not None
        service_manager.delete(result.gateway_result.id)


@pytest.mark.integration
@pytest.mark.kong
class TestDualWriteServiceUpdateIntegration:
    """Integration tests for DualWriteService.update with real Kong Gateway."""

    @pytest.fixture
    def mock_konnect_manager(self) -> MagicMock:
        """Create a mock Konnect manager."""
        return MagicMock()

    @pytest.fixture
    def dual_write_service(
        self,
        kong_client: KongAdminClient,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Service]:
        """Create a DualWriteService with real Gateway and mock Konnect."""
        gateway_manager = ServiceManager(kong_client)
        return DualWriteService(
            gateway_manager=gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    def test_update_writes_to_both(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """update should update on real Gateway and mock Konnect."""
        # Create initial service
        initial = service_manager.create(
            Service(
                name="update-test-service",
                host="original.local",
                port=8080,
            )
        )

        # Update via dual-write
        updated_service = Service(host="updated.local", port=9090)
        mock_konnect_manager.update.return_value = updated_service

        assert initial.id is not None
        result = dual_write_service.update(initial.id, updated_service)

        # Gateway should be updated
        assert result.gateway_result.host == "updated.local"
        assert result.gateway_result.port == 9090

        # Konnect should have been called
        mock_konnect_manager.update.assert_called_once()
        assert result.is_fully_synced is True

        # Cleanup
        service_manager.delete(initial.id)

    def test_update_data_plane_only(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """update should skip Konnect when data_plane_only=True."""
        # Create initial service
        initial = service_manager.create(
            Service(
                name="update-gateway-only-service",
                host="original.local",
                port=8080,
            )
        )

        # Update via dual-write with data_plane_only
        updated_service = Service(host="updated.local")
        assert initial.id is not None
        result = dual_write_service.update(
            initial.id,
            updated_service,
            data_plane_only=True,
        )

        # Gateway should be updated
        assert result.gateway_result.host == "updated.local"

        # Konnect should NOT have been called
        mock_konnect_manager.update.assert_not_called()
        assert result.konnect_skipped is True

        # Cleanup
        service_manager.delete(initial.id)


@pytest.mark.integration
@pytest.mark.kong
class TestDualWriteServiceDeleteIntegration:
    """Integration tests for DualWriteService.delete with real Kong Gateway."""

    @pytest.fixture
    def mock_konnect_manager(self) -> MagicMock:
        """Create a mock Konnect manager."""
        return MagicMock()

    @pytest.fixture
    def dual_write_service(
        self,
        kong_client: KongAdminClient,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Service]:
        """Create a DualWriteService with real Gateway and mock Konnect."""
        gateway_manager = ServiceManager(kong_client)
        return DualWriteService(
            gateway_manager=gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    def test_delete_from_both(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """delete should delete from real Gateway and mock Konnect."""
        # Create service to delete
        created = service_manager.create(
            Service(
                name="delete-test-service",
                host="delete.local",
                port=8080,
            )
        )

        assert created.id is not None
        result = dual_write_service.delete(created.id)

        # Gateway should be deleted
        assert result.gateway_deleted is True
        assert not service_manager.exists(created.id)

        # Konnect should have been called
        mock_konnect_manager.delete.assert_called_once_with(created.id)
        assert result.is_fully_synced is True

    def test_delete_data_plane_only(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """delete should skip Konnect when data_plane_only=True."""
        # Create service to delete
        created = service_manager.create(
            Service(
                name="delete-gateway-only-service",
                host="delete.local",
                port=8080,
            )
        )

        assert created.id is not None
        result = dual_write_service.delete(created.id, data_plane_only=True)

        # Gateway should be deleted
        assert result.gateway_deleted is True
        assert not service_manager.exists(created.id)

        # Konnect should NOT have been called
        mock_konnect_manager.delete.assert_not_called()
        assert result.konnect_skipped is True

    def test_delete_konnect_failure_partial_success(
        self,
        dual_write_service: DualWriteService[Service],
        mock_konnect_manager: MagicMock,
        service_manager: ServiceManager,
    ) -> None:
        """delete should return partial success when Konnect fails."""
        # Create service to delete
        created = service_manager.create(
            Service(
                name="delete-fail-test-service",
                host="delete.local",
                port=8080,
            )
        )
        mock_konnect_manager.delete.side_effect = Exception("Konnect not found")

        assert created.id is not None
        result = dual_write_service.delete(created.id)

        # Gateway should be deleted
        assert result.gateway_deleted is True
        assert not service_manager.exists(created.id)

        # Konnect should have failed
        assert result.konnect_deleted is False
        assert result.konnect_error is not None
        assert result.partial_success is True
