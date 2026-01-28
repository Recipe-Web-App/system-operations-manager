"""Unit tests for KonnectServiceManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.service_manager import KonnectServiceManager


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock Konnect client."""
    return MagicMock()


@pytest.fixture
def service_manager(mock_konnect_client: MagicMock) -> KonnectServiceManager:
    """Create a KonnectServiceManager with mock client."""
    return KonnectServiceManager(mock_konnect_client, "cp-123")


class TestKonnectServiceManagerInit:
    """Tests for KonnectServiceManager initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_konnect_client: MagicMock) -> None:
        """Manager should initialize with client and control plane ID."""
        manager = KonnectServiceManager(mock_konnect_client, "cp-123")
        assert manager.control_plane_id == "cp-123"

    @pytest.mark.unit
    def test_control_plane_id_property(self, service_manager: KonnectServiceManager) -> None:
        """control_plane_id property should return the ID."""
        assert service_manager.control_plane_id == "cp-123"


class TestKonnectServiceManagerList:
    """Tests for list operations."""

    @pytest.mark.unit
    def test_list_services(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should return services from client."""
        expected_services = [
            Service(name="svc-1", host="host1.local"),
            Service(name="svc-2", host="host2.local"),
        ]
        mock_konnect_client.list_services.return_value = (expected_services, None)

        services, _next_offset = service_manager.list()

        assert len(services) == 2
        assert services[0].name == "svc-1"
        mock_konnect_client.list_services.assert_called_once_with(
            "cp-123", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_with_filters(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass filters to client."""
        mock_konnect_client.list_services.return_value = ([], None)

        service_manager.list(tags=["prod"], limit=10, offset="abc")

        mock_konnect_client.list_services.assert_called_once_with(
            "cp-123", tags=["prod"], limit=10, offset="abc"
        )


class TestKonnectServiceManagerGet:
    """Tests for get operations."""

    @pytest.mark.unit
    def test_get_service(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should return service from client."""
        expected = Service(name="test-service", host="test.local")
        mock_konnect_client.get_service.return_value = expected

        result = service_manager.get("test-service")

        assert result.name == "test-service"
        mock_konnect_client.get_service.assert_called_once_with("cp-123", "test-service")

    @pytest.mark.unit
    def test_get_service_not_found(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should raise NotFoundError when service doesn't exist."""
        mock_konnect_client.get_service.side_effect = KonnectNotFoundError(
            "Service not found", status_code=404
        )

        with pytest.raises(KonnectNotFoundError):
            service_manager.get("nonexistent")


class TestKonnectServiceManagerExists:
    """Tests for exists operations."""

    @pytest.mark.unit
    def test_exists_returns_true(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when service exists."""
        mock_konnect_client.get_service.return_value = Service(name="test", host="test.local")

        assert service_manager.exists("test") is True

    @pytest.mark.unit
    def test_exists_returns_false(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when service doesn't exist."""
        mock_konnect_client.get_service.side_effect = KonnectNotFoundError(
            "Service not found", status_code=404
        )

        assert service_manager.exists("nonexistent") is False


class TestKonnectServiceManagerCreate:
    """Tests for create operations."""

    @pytest.mark.unit
    def test_create_service(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should create service via client."""
        service = Service(name="new-service", host="new.local")
        created = Service(id="svc-new", name="new-service", host="new.local")
        mock_konnect_client.create_service.return_value = created

        result = service_manager.create(service)

        assert result.id == "svc-new"
        mock_konnect_client.create_service.assert_called_once_with("cp-123", service)


class TestKonnectServiceManagerUpdate:
    """Tests for update operations."""

    @pytest.mark.unit
    def test_update_service(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should update service via client."""
        service = Service(name="test-service", host="updated.local")
        updated = Service(id="svc-1", name="test-service", host="updated.local")
        mock_konnect_client.update_service.return_value = updated

        result = service_manager.update("test-service", service)

        assert result.host == "updated.local"
        mock_konnect_client.update_service.assert_called_once_with(
            "cp-123", "test-service", service
        )


class TestKonnectServiceManagerDelete:
    """Tests for delete operations."""

    @pytest.mark.unit
    def test_delete_service(
        self,
        service_manager: KonnectServiceManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delete service via client."""
        service_manager.delete("test-service")

        mock_konnect_client.delete_service.assert_called_once_with("cp-123", "test-service")
