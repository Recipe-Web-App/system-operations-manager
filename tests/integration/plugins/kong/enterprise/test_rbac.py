"""Integration tests for RBACManager (Enterprise)."""

from __future__ import annotations

import pytest

from system_operations_manager.services.kong.rbac_manager import RBACManager
from tests.integration.plugins.kong.conftest import skip_enterprise

pytestmark = [
    pytest.mark.integration,
    pytest.mark.kong,
    pytest.mark.kong_enterprise,
    skip_enterprise,
]


class TestRBACManagerRoles:
    """Test RBAC role operations."""

    def test_list_roles(
        self,
        rbac_manager: RBACManager,
    ) -> None:
        """list_roles should return available roles."""
        roles, _ = rbac_manager.list_roles()

        assert isinstance(roles, list)
        # Kong Enterprise comes with default roles
        # At minimum, super-admin should exist

    def test_list_roles_with_pagination(
        self,
        rbac_manager: RBACManager,
    ) -> None:
        """list_roles should support pagination."""
        roles, _ = rbac_manager.list_roles(limit=10)

        assert isinstance(roles, list)


class TestRBACManagerUsers:
    """Test RBAC user operations."""

    def test_list_users(
        self,
        rbac_manager: RBACManager,
    ) -> None:
        """list_users should return RBAC users."""
        users, _ = rbac_manager.list_users()

        assert isinstance(users, list)

    def test_list_users_with_pagination(
        self,
        rbac_manager: RBACManager,
    ) -> None:
        """list_users should support pagination."""
        users, _ = rbac_manager.list_users(limit=10)

        assert isinstance(users, list)


class TestRBACManagerPermissions:
    """Test RBAC permission operations."""

    def test_list_role_permissions(
        self,
        rbac_manager: RBACManager,
    ) -> None:
        """list_role_permissions should return permissions for a role."""
        # Get the first role to test with
        roles, _ = rbac_manager.list_roles()
        if roles:
            permissions = rbac_manager.list_role_permissions(roles[0].name)
            assert isinstance(permissions, list)
