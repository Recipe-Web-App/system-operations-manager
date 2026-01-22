"""Unit tests for KonnectConsumerManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.consumer_manager import KonnectConsumerManager


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock Konnect client."""
    return MagicMock()


@pytest.fixture
def consumer_manager(mock_konnect_client: MagicMock) -> KonnectConsumerManager:
    """Create a KonnectConsumerManager with mock client."""
    return KonnectConsumerManager(mock_konnect_client, "cp-123")


class TestKonnectConsumerManagerInit:
    """Tests for KonnectConsumerManager initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_konnect_client: MagicMock) -> None:
        """Manager should initialize with client and control plane ID."""
        manager = KonnectConsumerManager(mock_konnect_client, "cp-123")
        assert manager.control_plane_id == "cp-123"

    @pytest.mark.unit
    def test_control_plane_id_property(self, consumer_manager: KonnectConsumerManager) -> None:
        """control_plane_id property should return the ID."""
        assert consumer_manager.control_plane_id == "cp-123"


class TestKonnectConsumerManagerList:
    """Tests for list operations."""

    @pytest.mark.unit
    def test_list_consumers(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should return consumers from client."""
        expected_consumers = [
            Consumer(username="user-1"),
            Consumer(username="user-2"),
        ]
        mock_konnect_client.list_consumers.return_value = (expected_consumers, None)

        consumers, _next_offset = consumer_manager.list()

        assert len(consumers) == 2
        assert consumers[0].username == "user-1"
        mock_konnect_client.list_consumers.assert_called_once_with(
            "cp-123", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_with_filters(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass filters to client."""
        mock_konnect_client.list_consumers.return_value = ([], None)

        consumer_manager.list(tags=["prod"], limit=10, offset="abc")

        mock_konnect_client.list_consumers.assert_called_once_with(
            "cp-123", tags=["prod"], limit=10, offset="abc"
        )


class TestKonnectConsumerManagerGet:
    """Tests for get operations."""

    @pytest.mark.unit
    def test_get_consumer(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should return consumer from client."""
        expected = Consumer(username="test-user")
        mock_konnect_client.get_consumer.return_value = expected

        result = consumer_manager.get("test-user")

        assert result.username == "test-user"
        mock_konnect_client.get_consumer.assert_called_once_with("cp-123", "test-user")

    @pytest.mark.unit
    def test_get_consumer_not_found(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should raise NotFoundError when consumer doesn't exist."""
        mock_konnect_client.get_consumer.side_effect = KonnectNotFoundError(
            "Consumer not found", status_code=404
        )

        with pytest.raises(KonnectNotFoundError):
            consumer_manager.get("nonexistent")


class TestKonnectConsumerManagerExists:
    """Tests for exists operations."""

    @pytest.mark.unit
    def test_exists_returns_true(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when consumer exists."""
        mock_konnect_client.get_consumer.return_value = Consumer(username="test")

        assert consumer_manager.exists("test") is True

    @pytest.mark.unit
    def test_exists_returns_false(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when consumer doesn't exist."""
        mock_konnect_client.get_consumer.side_effect = KonnectNotFoundError(
            "Consumer not found", status_code=404
        )

        assert consumer_manager.exists("nonexistent") is False


class TestKonnectConsumerManagerCreate:
    """Tests for create operations."""

    @pytest.mark.unit
    def test_create_consumer(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should create consumer via client."""
        consumer = Consumer(username="new-user")
        created = Consumer(id="consumer-new", username="new-user")
        mock_konnect_client.create_consumer.return_value = created

        result = consumer_manager.create(consumer)

        assert result.id == "consumer-new"
        mock_konnect_client.create_consumer.assert_called_once_with("cp-123", consumer)


class TestKonnectConsumerManagerUpdate:
    """Tests for update operations."""

    @pytest.mark.unit
    def test_update_consumer(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should update consumer via client."""
        consumer = Consumer(username="test-user", custom_id="updated-id")
        updated = Consumer(id="consumer-1", username="test-user", custom_id="updated-id")
        mock_konnect_client.update_consumer.return_value = updated

        result = consumer_manager.update("test-user", consumer)

        assert result.custom_id == "updated-id"
        mock_konnect_client.update_consumer.assert_called_once_with("cp-123", "test-user", consumer)


class TestKonnectConsumerManagerDelete:
    """Tests for delete operations."""

    @pytest.mark.unit
    def test_delete_consumer(
        self,
        consumer_manager: KonnectConsumerManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delete consumer via client."""
        consumer_manager.delete("test-user")

        mock_konnect_client.delete_consumer.assert_called_once_with("cp-123", "test-user")
