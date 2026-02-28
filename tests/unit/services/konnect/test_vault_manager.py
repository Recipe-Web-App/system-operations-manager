"""Unit tests for the Konnect vault manager class."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.vault_manager import KonnectVaultManager

CONTROL_PLANE_ID = "cp-12345"


# ---------------------------------------------------------------------------
# KonnectVaultManager
# ---------------------------------------------------------------------------


class TestKonnectVaultManager:
    """Tests for KonnectVaultManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectVaultManager:
        """Create a KonnectVaultManager with mock client."""
        return KonnectVaultManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectVaultManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_vaults with default args."""
        mock_vault = MagicMock()
        mock_konnect_client.list_vaults.return_value = ([mock_vault], None)

        vaults, next_offset = manager.list()

        mock_konnect_client.list_vaults.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert vaults == [mock_vault]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_vaults.return_value = ([], "next-token")

        vaults, next_offset = manager.list(tags=["secrets"], limit=20, offset="tok-def")

        mock_konnect_client.list_vaults.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["secrets"], limit=20, offset="tok-def"
        )
        assert vaults == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_vault with the correct args."""
        mock_vault = MagicMock()
        mock_konnect_client.get_vault.return_value = mock_vault

        result = manager.get("hcv")

        mock_konnect_client.get_vault.assert_called_once_with(CONTROL_PLANE_ID, "hcv")
        assert result is mock_vault

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_vault succeeds."""
        mock_konnect_client.get_vault.return_value = MagicMock()

        assert manager.exists("hcv") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_vault raises KonnectNotFoundError."""
        mock_konnect_client.get_vault.side_effect = KonnectNotFoundError(
            "not found", status_code=404
        )

        assert manager.exists("vault-uuid-missing") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_vault with the correct args."""
        vault_input = MagicMock()
        vault_created = MagicMock()
        mock_konnect_client.create_vault.return_value = vault_created

        result = manager.create(vault_input)

        mock_konnect_client.create_vault.assert_called_once_with(CONTROL_PLANE_ID, vault_input)
        assert result is vault_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_vault with the correct args."""
        vault_input = MagicMock()
        vault_updated = MagicMock()
        mock_konnect_client.update_vault.return_value = vault_updated

        result = manager.update("hcv", vault_input)

        mock_konnect_client.update_vault.assert_called_once_with(
            CONTROL_PLANE_ID, "hcv", vault_input
        )
        assert result is vault_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectVaultManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_vault with the correct args."""
        manager.delete("hcv")

        mock_konnect_client.delete_vault.assert_called_once_with(CONTROL_PLANE_ID, "hcv")
