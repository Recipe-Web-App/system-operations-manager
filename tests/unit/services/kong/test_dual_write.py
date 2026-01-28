"""Unit tests for DualWriteService.

Tests the dual-write orchestration logic for writing to both
Kong Gateway and Konnect control plane.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kong.dual_write import (
    DualDeleteResult,
    DualWriteResult,
    DualWriteService,
)


@dataclass
class MockEntity:
    """Mock entity for testing."""

    id: str | None = None
    name: str = "test-entity"


@pytest.fixture
def mock_gateway_manager() -> MagicMock:
    """Create a mock Gateway manager."""
    return MagicMock()


@pytest.fixture
def mock_konnect_manager() -> MagicMock:
    """Create a mock Konnect manager."""
    return MagicMock()


class TestDualWriteResult:
    """Tests for DualWriteResult dataclass."""

    @pytest.mark.unit
    def test_is_fully_synced_both_success(self) -> None:
        """is_fully_synced should return True when both writes succeed."""
        entity = MockEntity(id="123")
        result = DualWriteResult(
            gateway_result=entity,
            konnect_result=entity,
        )
        assert result.is_fully_synced is True
        assert result.partial_success is False

    @pytest.mark.unit
    def test_is_fully_synced_false_when_skipped(self) -> None:
        """is_fully_synced should return False when Konnect was skipped."""
        result = DualWriteResult(
            gateway_result=MockEntity(),
            konnect_skipped=True,
        )
        assert result.is_fully_synced is False
        assert result.partial_success is False

    @pytest.mark.unit
    def test_partial_success_on_konnect_error(self) -> None:
        """partial_success should return True when Konnect fails."""
        result = DualWriteResult(
            gateway_result=MockEntity(),
            konnect_error=Exception("Connection timeout"),
        )
        assert result.is_fully_synced is False
        assert result.partial_success is True

    @pytest.mark.unit
    def test_konnect_not_configured(self) -> None:
        """Result should indicate when Konnect is not configured."""
        result = DualWriteResult(
            gateway_result=MockEntity(),
            konnect_not_configured=True,
        )
        assert result.is_fully_synced is False
        assert result.partial_success is False
        assert result.konnect_not_configured is True


class TestDualDeleteResult:
    """Tests for DualDeleteResult dataclass."""

    @pytest.mark.unit
    def test_is_fully_synced_both_deleted(self) -> None:
        """is_fully_synced should return True when both deletes succeed."""
        result = DualDeleteResult(
            gateway_deleted=True,
            konnect_deleted=True,
        )
        assert result.is_fully_synced is True
        assert result.partial_success is False

    @pytest.mark.unit
    def test_is_fully_synced_false_when_skipped(self) -> None:
        """is_fully_synced should return False when Konnect was skipped."""
        result = DualDeleteResult(
            gateway_deleted=True,
            konnect_skipped=True,
        )
        assert result.is_fully_synced is False

    @pytest.mark.unit
    def test_partial_success_on_konnect_error(self) -> None:
        """partial_success should return True when Konnect delete fails."""
        result = DualDeleteResult(
            gateway_deleted=True,
            konnect_error=Exception("Delete failed"),
        )
        assert result.partial_success is True


class TestDualWriteServiceCreate:
    """Tests for DualWriteService.create method."""

    @pytest.fixture
    def service(
        self,
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Any]:
        """Create a DualWriteService with mocks."""
        return DualWriteService(
            gateway_manager=mock_gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    @pytest.mark.unit
    def test_create_both_success(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """create should write to both Gateway and Konnect."""
        entity = MockEntity(name="test-api")
        gateway_result = MockEntity(id="gw-123", name="test-api")
        konnect_result = MockEntity(id="kn-456", name="test-api")

        mock_gateway_manager.create.return_value = gateway_result
        mock_konnect_manager.create.return_value = konnect_result

        result = service.create(entity)

        mock_gateway_manager.create.assert_called_once_with(entity)
        mock_konnect_manager.create.assert_called_once_with(entity)
        assert result.gateway_result == gateway_result
        assert result.konnect_result == konnect_result
        assert result.is_fully_synced is True

    @pytest.mark.unit
    def test_create_data_plane_only(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """create should skip Konnect when data_plane_only=True."""
        entity = MockEntity(name="test-api")
        gateway_result = MockEntity(id="gw-123", name="test-api")
        mock_gateway_manager.create.return_value = gateway_result

        result = service.create(entity, data_plane_only=True)

        mock_gateway_manager.create.assert_called_once_with(entity)
        mock_konnect_manager.create.assert_not_called()
        assert result.gateway_result == gateway_result
        assert result.konnect_result is None
        assert result.konnect_skipped is True
        assert result.is_fully_synced is False

    @pytest.mark.unit
    def test_create_konnect_not_configured(
        self,
        mock_gateway_manager: MagicMock,
    ) -> None:
        """create should handle Konnect not configured."""
        service = DualWriteService[Any](
            gateway_manager=mock_gateway_manager,
            konnect_manager=None,
            entity_name="service",
        )
        entity = MockEntity(name="test-api")
        gateway_result = MockEntity(id="gw-123", name="test-api")
        mock_gateway_manager.create.return_value = gateway_result

        result = service.create(entity)

        mock_gateway_manager.create.assert_called_once_with(entity)
        assert result.gateway_result == gateway_result
        assert result.konnect_not_configured is True
        assert result.is_fully_synced is False

    @pytest.mark.unit
    def test_create_konnect_failure(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """create should capture Konnect error but still return Gateway result."""
        entity = MockEntity(name="test-api")
        gateway_result = MockEntity(id="gw-123", name="test-api")
        konnect_error = Exception("Connection timeout")

        mock_gateway_manager.create.return_value = gateway_result
        mock_konnect_manager.create.side_effect = konnect_error

        result = service.create(entity)

        mock_gateway_manager.create.assert_called_once()
        mock_konnect_manager.create.assert_called_once()
        assert result.gateway_result == gateway_result
        assert result.konnect_result is None
        assert result.konnect_error == konnect_error
        assert result.partial_success is True

    @pytest.mark.unit
    def test_create_gateway_failure_raises(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """create should raise when Gateway fails."""
        entity = MockEntity(name="test-api")
        mock_gateway_manager.create.side_effect = Exception("Gateway error")

        with pytest.raises(Exception, match="Gateway error"):
            service.create(entity)

        mock_gateway_manager.create.assert_called_once()
        mock_konnect_manager.create.assert_not_called()

    @pytest.mark.unit
    def test_create_passes_kwargs(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """create should pass extra kwargs to both managers."""
        entity = MockEntity(name="test-api")
        gateway_result = MockEntity(id="gw-123")
        konnect_result = MockEntity(id="kn-456")

        mock_gateway_manager.create.return_value = gateway_result
        mock_konnect_manager.create.return_value = konnect_result

        result = service.create(entity, extra_param="value")

        mock_gateway_manager.create.assert_called_once_with(entity, extra_param="value")
        mock_konnect_manager.create.assert_called_once_with(entity, extra_param="value")
        assert result.is_fully_synced is True


class TestDualWriteServiceUpdate:
    """Tests for DualWriteService.update method."""

    @pytest.fixture
    def service(
        self,
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Any]:
        """Create a DualWriteService with mocks."""
        return DualWriteService(
            gateway_manager=mock_gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    @pytest.mark.unit
    def test_update_both_success(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """update should write to both Gateway and Konnect."""
        entity = MockEntity(name="updated-api")
        gateway_result = MockEntity(id="gw-123", name="updated-api")
        konnect_result = MockEntity(id="kn-456", name="updated-api")

        mock_gateway_manager.update.return_value = gateway_result
        mock_konnect_manager.update.return_value = konnect_result

        result = service.update("gw-123", entity)

        mock_gateway_manager.update.assert_called_once_with("gw-123", entity)
        mock_konnect_manager.update.assert_called_once_with("gw-123", entity)
        assert result.is_fully_synced is True

    @pytest.mark.unit
    def test_update_data_plane_only(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """update should skip Konnect when data_plane_only=True."""
        entity = MockEntity(name="updated-api")
        gateway_result = MockEntity(id="gw-123", name="updated-api")
        mock_gateway_manager.update.return_value = gateway_result

        result = service.update("gw-123", entity, data_plane_only=True)

        mock_gateway_manager.update.assert_called_once()
        mock_konnect_manager.update.assert_not_called()
        assert result.konnect_skipped is True

    @pytest.mark.unit
    def test_update_konnect_failure(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """update should capture Konnect error but still return Gateway result."""
        entity = MockEntity(name="updated-api")
        gateway_result = MockEntity(id="gw-123", name="updated-api")
        konnect_error = Exception("Update failed")

        mock_gateway_manager.update.return_value = gateway_result
        mock_konnect_manager.update.side_effect = konnect_error

        result = service.update("gw-123", entity)

        assert result.gateway_result == gateway_result
        assert result.konnect_error == konnect_error
        assert result.partial_success is True

    @pytest.mark.unit
    def test_update_konnect_not_configured(
        self,
        mock_gateway_manager: MagicMock,
    ) -> None:
        """update should handle Konnect not configured."""
        service = DualWriteService[Any](
            gateway_manager=mock_gateway_manager,
            konnect_manager=None,
            entity_name="service",
        )
        entity = MockEntity(name="updated-api")
        gateway_result = MockEntity(id="gw-123")
        mock_gateway_manager.update.return_value = gateway_result

        result = service.update("gw-123", entity)

        assert result.konnect_not_configured is True


class TestDualWriteServiceDelete:
    """Tests for DualWriteService.delete method."""

    @pytest.fixture
    def service(
        self,
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> DualWriteService[Any]:
        """Create a DualWriteService with mocks."""
        return DualWriteService(
            gateway_manager=mock_gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )

    @pytest.mark.unit
    def test_delete_both_success(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """delete should delete from both Gateway and Konnect."""
        result = service.delete("gw-123")

        mock_gateway_manager.delete.assert_called_once_with("gw-123")
        mock_konnect_manager.delete.assert_called_once_with("gw-123")
        assert result.gateway_deleted is True
        assert result.konnect_deleted is True
        assert result.is_fully_synced is True

    @pytest.mark.unit
    def test_delete_data_plane_only(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """delete should skip Konnect when data_plane_only=True."""
        result = service.delete("gw-123", data_plane_only=True)

        mock_gateway_manager.delete.assert_called_once()
        mock_konnect_manager.delete.assert_not_called()
        assert result.gateway_deleted is True
        assert result.konnect_deleted is False
        assert result.konnect_skipped is True

    @pytest.mark.unit
    def test_delete_konnect_failure(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """delete should capture Konnect error but still confirm Gateway delete."""
        konnect_error = Exception("Delete failed")
        mock_konnect_manager.delete.side_effect = konnect_error

        result = service.delete("gw-123")

        mock_gateway_manager.delete.assert_called_once()
        mock_konnect_manager.delete.assert_called_once()
        assert result.gateway_deleted is True
        assert result.konnect_deleted is False
        assert result.konnect_error == konnect_error
        assert result.partial_success is True

    @pytest.mark.unit
    def test_delete_gateway_failure_raises(
        self,
        service: DualWriteService[Any],
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """delete should raise when Gateway delete fails."""
        mock_gateway_manager.delete.side_effect = Exception("Gateway error")

        with pytest.raises(Exception, match="Gateway error"):
            service.delete("gw-123")

        mock_gateway_manager.delete.assert_called_once()
        mock_konnect_manager.delete.assert_not_called()

    @pytest.mark.unit
    def test_delete_konnect_not_configured(
        self,
        mock_gateway_manager: MagicMock,
    ) -> None:
        """delete should handle Konnect not configured."""
        service = DualWriteService[Any](
            gateway_manager=mock_gateway_manager,
            konnect_manager=None,
            entity_name="service",
        )

        result = service.delete("gw-123")

        mock_gateway_manager.delete.assert_called_once()
        assert result.gateway_deleted is True
        assert result.konnect_not_configured is True


class TestDualWriteServiceKonnectConfigured:
    """Tests for konnect_configured property."""

    @pytest.mark.unit
    def test_konnect_configured_true(
        self,
        mock_gateway_manager: MagicMock,
        mock_konnect_manager: MagicMock,
    ) -> None:
        """konnect_configured should return True when Konnect manager exists."""
        service = DualWriteService[Any](
            gateway_manager=mock_gateway_manager,
            konnect_manager=mock_konnect_manager,
            entity_name="service",
        )
        assert service.konnect_configured is True

    @pytest.mark.unit
    def test_konnect_configured_false(
        self,
        mock_gateway_manager: MagicMock,
    ) -> None:
        """konnect_configured should return False when Konnect manager is None."""
        service = DualWriteService[Any](
            gateway_manager=mock_gateway_manager,
            konnect_manager=None,
            entity_name="service",
        )
        assert service.konnect_configured is False
