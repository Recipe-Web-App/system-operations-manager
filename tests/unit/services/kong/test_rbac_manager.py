"""Unit tests for Kong RBACManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.enterprise import (
    RBACEndpointPermission,
    RBACRole,
    RBACUser,
)
from system_operations_manager.services.kong.rbac_manager import RBACManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> RBACManager:
    """Create an RBACManager with mocked client."""
    return RBACManager(mock_client)


class TestRBACManagerInit:
    """Tests for RBACManager initialization."""

    @pytest.mark.unit
    def test_rbac_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = RBACManager(mock_client)

        assert manager._client is mock_client


class TestRBACManagerListRoles:
    """Tests for list_roles method."""

    @pytest.mark.unit
    def test_list_roles_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_roles should return roles."""
        mock_client.get.return_value = {
            "data": [
                {"id": "role-1", "name": "admin"},
                {"id": "role-2", "name": "developer"},
            ]
        }

        roles, offset = manager.list_roles()

        assert len(roles) == 2
        assert roles[0].name == "admin"
        assert roles[1].name == "developer"
        assert offset is None
        mock_client.get.assert_called_once_with("rbac/roles", params={})

    @pytest.mark.unit
    def test_list_roles_with_pagination(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_roles should pass pagination params."""
        mock_client.get.return_value = {
            "data": [{"id": "role-1", "name": "admin"}],
            "offset": "next-page-token",
        }

        roles, offset = manager.list_roles(limit=10, offset="page-token")

        assert len(roles) == 1
        assert offset == "next-page-token"
        mock_client.get.assert_called_once_with(
            "rbac/roles", params={"size": 10, "offset": "page-token"}
        )

    @pytest.mark.unit
    def test_list_roles_empty(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_roles should return empty list when no roles exist."""
        mock_client.get.return_value = {"data": []}

        roles, offset = manager.list_roles()

        assert len(roles) == 0
        assert offset is None


class TestRBACManagerGetRole:
    """Tests for get_role method."""

    @pytest.mark.unit
    def test_get_role_by_name(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """get_role should return role by name."""
        mock_client.get.return_value = {"id": "role-1", "name": "admin"}

        role = manager.get_role("admin")

        assert role.id == "role-1"
        assert role.name == "admin"
        mock_client.get.assert_called_once_with("rbac/roles/admin")

    @pytest.mark.unit
    def test_get_role_by_id(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """get_role should return role by ID."""
        mock_client.get.return_value = {"id": "role-123", "name": "developer"}

        role = manager.get_role("role-123")

        assert role.id == "role-123"
        mock_client.get.assert_called_once_with("rbac/roles/role-123")

    @pytest.mark.unit
    def test_get_role_not_found(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """get_role should raise error for non-existent role."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="role", resource_id="nonexistent"
        )

        with pytest.raises(KongNotFoundError):
            manager.get_role("nonexistent")


class TestRBACManagerCreateRole:
    """Tests for create_role method."""

    @pytest.mark.unit
    def test_create_role_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """create_role should create a new role."""
        mock_client.post.return_value = {
            "id": "role-new",
            "name": "api-developer",
            "comment": "API developers",
        }

        role = RBACRole(name="api-developer", comment="API developers")
        created = manager.create_role(role)

        assert created.id == "role-new"
        assert created.name == "api-developer"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "rbac/roles"

    @pytest.mark.unit
    def test_create_role_minimal(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """create_role should work with minimal data."""
        mock_client.post.return_value = {"id": "role-new", "name": "minimal-role"}

        role = RBACRole(name="minimal-role")
        created = manager.create_role(role)

        assert created.name == "minimal-role"


class TestRBACManagerUpdateRole:
    """Tests for update_role method."""

    @pytest.mark.unit
    def test_update_role_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """update_role should update role."""
        mock_client.patch.return_value = {
            "id": "role-1",
            "name": "admin",
            "comment": "Updated comment",
        }

        role = RBACRole(name="admin", comment="Updated comment")
        updated = manager.update_role("role-1", role)

        assert updated.comment == "Updated comment"
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "rbac/roles/role-1"


class TestRBACManagerDeleteRole:
    """Tests for delete_role method."""

    @pytest.mark.unit
    def test_delete_role_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """delete_role should delete role."""
        manager.delete_role("admin")

        mock_client.delete.assert_called_once_with("rbac/roles/admin")

    @pytest.mark.unit
    def test_delete_role_not_found(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """delete_role should raise error for non-existent role."""
        mock_client.delete.side_effect = KongNotFoundError(
            resource_type="role", resource_id="nonexistent"
        )

        with pytest.raises(KongNotFoundError):
            manager.delete_role("nonexistent")


class TestRBACManagerListRolePermissions:
    """Tests for list_role_permissions method."""

    @pytest.mark.unit
    def test_list_role_permissions_success(
        self, manager: RBACManager, mock_client: MagicMock
    ) -> None:
        """list_role_permissions should return permissions for role."""
        mock_client.get.return_value = {
            "data": [
                {"id": "perm-1", "endpoint": "/services/*", "actions": ["read", "create"]},
                {"id": "perm-2", "endpoint": "/routes/*", "actions": ["read"]},
            ]
        }

        permissions = manager.list_role_permissions("admin")

        assert len(permissions) == 2
        assert permissions[0].endpoint == "/services/*"
        assert permissions[0].actions == ["read", "create"]
        mock_client.get.assert_called_once_with("rbac/roles/admin/endpoints")

    @pytest.mark.unit
    def test_list_role_permissions_empty(
        self, manager: RBACManager, mock_client: MagicMock
    ) -> None:
        """list_role_permissions should return empty list for role without permissions."""
        mock_client.get.return_value = {"data": []}

        permissions = manager.list_role_permissions("new-role")

        assert len(permissions) == 0


class TestRBACManagerAddRolePermission:
    """Tests for add_role_permission method."""

    @pytest.mark.unit
    def test_add_role_permission_success(
        self, manager: RBACManager, mock_client: MagicMock
    ) -> None:
        """add_role_permission should add permission to role."""
        mock_client.post.return_value = {
            "id": "perm-new",
            "endpoint": "/consumers/*",
            "actions": ["read", "create", "update", "delete"],
        }

        permission = RBACEndpointPermission(
            endpoint="/consumers/*",
            actions=["read", "create", "update", "delete"],
        )
        created = manager.add_role_permission("admin", permission)

        assert created.id == "perm-new"
        assert created.endpoint == "/consumers/*"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "rbac/roles/admin/endpoints"


class TestRBACManagerRemoveRolePermission:
    """Tests for remove_role_permission method."""

    @pytest.mark.unit
    def test_remove_role_permission_success(
        self, manager: RBACManager, mock_client: MagicMock
    ) -> None:
        """remove_role_permission should remove permission from role."""
        manager.remove_role_permission("admin", "perm-123")

        mock_client.delete.assert_called_once_with("rbac/roles/admin/endpoints/perm-123")


class TestRBACManagerListUsers:
    """Tests for list_users method."""

    @pytest.mark.unit
    def test_list_users_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_users should return admin users."""
        mock_client.get.return_value = {
            "data": [
                {"id": "user-1", "username": "alice", "email": "alice@example.com"},
                {"id": "user-2", "username": "bob", "email": "bob@example.com"},
            ]
        }

        users, offset = manager.list_users()

        assert len(users) == 2
        assert users[0].username == "alice"
        assert users[1].username == "bob"
        assert offset is None
        mock_client.get.assert_called_once_with("admins", params={})

    @pytest.mark.unit
    def test_list_users_with_pagination(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_users should pass pagination params."""
        mock_client.get.return_value = {
            "data": [{"id": "user-1", "username": "alice"}],
            "offset": "next-page",
        }

        users, offset = manager.list_users(limit=5, offset="current-page")

        assert len(users) == 1
        assert offset == "next-page"
        mock_client.get.assert_called_once_with(
            "admins", params={"size": 5, "offset": "current-page"}
        )

    @pytest.mark.unit
    def test_list_users_empty(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_users should return empty list when no users exist."""
        mock_client.get.return_value = {"data": []}

        users, _offset = manager.list_users()

        assert len(users) == 0


class TestRBACManagerGetUser:
    """Tests for get_user method."""

    @pytest.mark.unit
    def test_get_user_by_username(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """get_user should return user by username."""
        mock_client.get.return_value = {
            "id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
        }

        user = manager.get_user("alice")

        assert user.id == "user-1"
        assert user.username == "alice"
        mock_client.get.assert_called_once_with("admins/alice")

    @pytest.mark.unit
    def test_get_user_not_found(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """get_user should raise error for non-existent user."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="user", resource_id="nonexistent"
        )

        with pytest.raises(KongNotFoundError):
            manager.get_user("nonexistent")


class TestRBACManagerCreateUser:
    """Tests for create_user method."""

    @pytest.mark.unit
    def test_create_user_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """create_user should create a new admin user."""
        mock_client.post.return_value = {
            "id": "user-new",
            "username": "charlie",
            "email": "charlie@example.com",
        }

        user = RBACUser(username="charlie", email="charlie@example.com")
        created = manager.create_user(user)

        assert created.id == "user-new"
        assert created.username == "charlie"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "admins"

    @pytest.mark.unit
    def test_create_user_minimal(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """create_user should work with minimal data."""
        mock_client.post.return_value = {"id": "user-new", "username": "minimal-user"}

        user = RBACUser(username="minimal-user")
        created = manager.create_user(user)

        assert created.username == "minimal-user"


class TestRBACManagerUpdateUser:
    """Tests for update_user method."""

    @pytest.mark.unit
    def test_update_user_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """update_user should update user."""
        mock_client.patch.return_value = {
            "id": "user-1",
            "username": "alice",
            "email": "newemail@example.com",
        }

        user = RBACUser(username="alice", email="newemail@example.com")
        updated = manager.update_user("user-1", user)

        assert updated.email == "newemail@example.com"
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "admins/user-1"


class TestRBACManagerDeleteUser:
    """Tests for delete_user method."""

    @pytest.mark.unit
    def test_delete_user_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """delete_user should delete user."""
        manager.delete_user("alice")

        mock_client.delete.assert_called_once_with("admins/alice")

    @pytest.mark.unit
    def test_delete_user_not_found(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """delete_user should raise error for non-existent user."""
        mock_client.delete.side_effect = KongNotFoundError(
            resource_type="user", resource_id="nonexistent"
        )

        with pytest.raises(KongNotFoundError):
            manager.delete_user("nonexistent")


class TestRBACManagerListUserRoles:
    """Tests for list_user_roles method."""

    @pytest.mark.unit
    def test_list_user_roles_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_user_roles should return roles assigned to user."""
        mock_client.get.return_value = {
            "data": [
                {"id": "role-1", "name": "admin"},
                {"id": "role-2", "name": "developer"},
            ]
        }

        roles = manager.list_user_roles("alice")

        assert len(roles) == 2
        assert roles[0].name == "admin"
        assert roles[1].name == "developer"
        mock_client.get.assert_called_once_with("admins/alice/roles")

    @pytest.mark.unit
    def test_list_user_roles_empty(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """list_user_roles should return empty list for user without roles."""
        mock_client.get.return_value = {"data": []}

        roles = manager.list_user_roles("new-user")

        assert len(roles) == 0


class TestRBACManagerAssignRole:
    """Tests for assign_role method."""

    @pytest.mark.unit
    def test_assign_role_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """assign_role should assign role to user."""
        manager.assign_role("alice", "admin")

        mock_client.post.assert_called_once_with(
            "admins/alice/roles",
            json={"roles": ["admin"]},
        )


class TestRBACManagerRevokeRole:
    """Tests for revoke_role method."""

    @pytest.mark.unit
    def test_revoke_role_success(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """revoke_role should revoke role from user."""
        manager.revoke_role("alice", "admin")

        mock_client.delete.assert_called_once_with("admins/alice/roles/admin")


class TestRBACManagerRoleExists:
    """Tests for role_exists method."""

    @pytest.mark.unit
    def test_role_exists_true(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """role_exists should return True when role exists."""
        mock_client.get.return_value = {"id": "role-1", "name": "admin"}

        result = manager.role_exists("admin")

        assert result is True

    @pytest.mark.unit
    def test_role_exists_false(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """role_exists should return False when role doesn't exist."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="role", resource_id="nonexistent"
        )

        result = manager.role_exists("nonexistent")

        assert result is False


class TestRBACManagerUserExists:
    """Tests for user_exists method."""

    @pytest.mark.unit
    def test_user_exists_true(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """user_exists should return True when user exists."""
        mock_client.get.return_value = {"id": "user-1", "username": "alice"}

        result = manager.user_exists("alice")

        assert result is True

    @pytest.mark.unit
    def test_user_exists_false(self, manager: RBACManager, mock_client: MagicMock) -> None:
        """user_exists should return False when user doesn't exist."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="user", resource_id="nonexistent"
        )

        result = manager.user_exists("nonexistent")

        assert result is False
