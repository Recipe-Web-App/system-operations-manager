"""Integration tests for VaultManager (Enterprise)."""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.vault_manager import VaultManager
from tests.integration.plugins.kong.conftest import skip_enterprise

pytestmark = [
    pytest.mark.integration,
    pytest.mark.kong,
    pytest.mark.kong_enterprise,
    skip_enterprise,
]


class TestVaultManagerList:
    """Test vault listing operations."""

    def test_list_vaults(
        self,
        vault_manager: VaultManager,
    ) -> None:
        """list should return configured vaults."""
        vaults, _ = vault_manager.list()

        assert isinstance(vaults, list)
        # May be empty if no vaults configured

    def test_list_with_pagination(
        self,
        vault_manager: VaultManager,
    ) -> None:
        """list should support pagination."""
        vaults, _ = vault_manager.list(limit=10)

        assert isinstance(vaults, list)


class TestVaultManagerExists:
    """Test vault existence checks."""

    def test_exists_returns_false_for_nonexistent(
        self,
        vault_manager: VaultManager,
    ) -> None:
        """exists should return False for nonexistent vault."""
        assert vault_manager.exists("nonexistent-vault") is False


class TestVaultManagerCount:
    """Test vault count operations."""

    def test_count_vaults(
        self,
        vault_manager: VaultManager,
    ) -> None:
        """count should return number of configured vaults."""
        count = vault_manager.count()

        assert count >= 0  # May be 0 if no vaults configured
