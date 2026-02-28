"""Unit tests for Konnect key manager classes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.key_manager import (
    KonnectKeyManager,
    KonnectKeySetManager,
)

CONTROL_PLANE_ID = "cp-12345"


# ---------------------------------------------------------------------------
# KonnectKeySetManager
# ---------------------------------------------------------------------------


class TestKonnectKeySetManager:
    """Tests for KonnectKeySetManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectKeySetManager:
        """Create a KonnectKeySetManager with mock client."""
        return KonnectKeySetManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectKeySetManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_key_sets with default args."""
        mock_key_set = MagicMock()
        mock_konnect_client.list_key_sets.return_value = ([mock_key_set], None)

        key_sets, next_offset = manager.list()

        mock_konnect_client.list_key_sets.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert key_sets == [mock_key_set]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_key_sets.return_value = ([], "next-token")

        key_sets, next_offset = manager.list(tags=["prod"], limit=25, offset="tok-abc")

        mock_konnect_client.list_key_sets.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["prod"], limit=25, offset="tok-abc"
        )
        assert key_sets == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_key_set with the correct args."""
        mock_key_set = MagicMock()
        mock_konnect_client.get_key_set.return_value = mock_key_set

        result = manager.get("key-set-uuid-001")

        mock_konnect_client.get_key_set.assert_called_once_with(
            CONTROL_PLANE_ID, "key-set-uuid-001"
        )
        assert result is mock_key_set

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_key_set succeeds."""
        mock_konnect_client.get_key_set.return_value = MagicMock()

        assert manager.exists("key-set-uuid-001") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_key_set raises KonnectNotFoundError."""
        mock_konnect_client.get_key_set.side_effect = KonnectNotFoundError(
            "not found", status_code=404
        )

        assert manager.exists("key-set-uuid-missing") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_key_set with the correct args."""
        key_set_input = MagicMock()
        key_set_created = MagicMock()
        mock_konnect_client.create_key_set.return_value = key_set_created

        result = manager.create(key_set_input)

        mock_konnect_client.create_key_set.assert_called_once_with(CONTROL_PLANE_ID, key_set_input)
        assert result is key_set_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_key_set with the correct args."""
        key_set_input = MagicMock()
        key_set_updated = MagicMock()
        mock_konnect_client.update_key_set.return_value = key_set_updated

        result = manager.update("key-set-uuid-001", key_set_input)

        mock_konnect_client.update_key_set.assert_called_once_with(
            CONTROL_PLANE_ID, "key-set-uuid-001", key_set_input
        )
        assert result is key_set_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectKeySetManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_key_set with the correct args."""
        manager.delete("key-set-uuid-001")

        mock_konnect_client.delete_key_set.assert_called_once_with(
            CONTROL_PLANE_ID, "key-set-uuid-001"
        )


# ---------------------------------------------------------------------------
# KonnectKeyManager
# ---------------------------------------------------------------------------


class TestKonnectKeyManager:
    """Tests for KonnectKeyManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectKeyManager:
        """Create a KonnectKeyManager with mock client."""
        return KonnectKeyManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectKeyManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_keys with default args."""
        mock_key = MagicMock()
        mock_konnect_client.list_keys.return_value = ([mock_key], None)

        keys, next_offset = manager.list()

        mock_konnect_client.list_keys.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert keys == [mock_key]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_keys.return_value = ([], "next-token")

        keys, next_offset = manager.list(tags=["signing"], limit=10, offset="tok-xyz")

        mock_konnect_client.list_keys.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["signing"], limit=10, offset="tok-xyz"
        )
        assert keys == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_key with the correct args."""
        mock_key = MagicMock()
        mock_konnect_client.get_key.return_value = mock_key

        result = manager.get("key-uuid-001")

        mock_konnect_client.get_key.assert_called_once_with(CONTROL_PLANE_ID, "key-uuid-001")
        assert result is mock_key

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_key succeeds."""
        mock_konnect_client.get_key.return_value = MagicMock()

        assert manager.exists("key-uuid-001") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_key raises KonnectNotFoundError."""
        mock_konnect_client.get_key.side_effect = KonnectNotFoundError("not found", status_code=404)

        assert manager.exists("key-uuid-missing") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_key with the correct args."""
        key_input = MagicMock()
        key_created = MagicMock()
        mock_konnect_client.create_key.return_value = key_created

        result = manager.create(key_input)

        mock_konnect_client.create_key.assert_called_once_with(CONTROL_PLANE_ID, key_input)
        assert result is key_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_key with the correct args."""
        key_input = MagicMock()
        key_updated = MagicMock()
        mock_konnect_client.update_key.return_value = key_updated

        result = manager.update("key-uuid-001", key_input)

        mock_konnect_client.update_key.assert_called_once_with(
            CONTROL_PLANE_ID, "key-uuid-001", key_input
        )
        assert result is key_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectKeyManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_key with the correct args."""
        manager.delete("key-uuid-001")

        mock_konnect_client.delete_key.assert_called_once_with(CONTROL_PLANE_ID, "key-uuid-001")
