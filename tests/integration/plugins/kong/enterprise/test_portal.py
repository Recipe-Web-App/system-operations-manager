"""Integration tests for PortalManager (Enterprise)."""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.portal_manager import PortalManager
from tests.integration.plugins.kong.conftest import skip_enterprise

pytestmark = [
    pytest.mark.integration,
    pytest.mark.kong,
    pytest.mark.kong_enterprise,
    skip_enterprise,
]


class TestPortalManagerStatus:
    """Test Dev Portal status operations."""

    def test_get_status(
        self,
        portal_manager: PortalManager,
    ) -> None:
        """get_status should return portal status."""
        status = portal_manager.get_status()

        assert status is not None
        # Status should indicate whether portal is enabled
        assert hasattr(status, "enabled")


class TestPortalManagerSpecs:
    """Test Dev Portal spec operations."""

    def test_list_specs(
        self,
        portal_manager: PortalManager,
    ) -> None:
        """list_specs should return published specs."""
        specs, _ = portal_manager.list_specs()

        assert isinstance(specs, list)
        # May be empty if no specs published

    def test_list_specs_with_pagination(
        self,
        portal_manager: PortalManager,
    ) -> None:
        """list_specs should support pagination."""
        specs, _ = portal_manager.list_specs(limit=10)

        assert isinstance(specs, list)


class TestPortalManagerDevelopers:
    """Test Dev Portal developer operations."""

    def test_list_developers(
        self,
        portal_manager: PortalManager,
    ) -> None:
        """list_developers should return registered developers."""
        developers, _ = portal_manager.list_developers()

        assert isinstance(developers, list)
        # May be empty if no developers registered
