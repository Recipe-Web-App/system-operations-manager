"""Unit tests for Kong RBAC commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.plugins.kong.commands.enterprise.rbac import (
    register_rbac_commands,
)

from .conftest import create_enterprise_app


class TestRBACRoleListCommand:
    """Tests for RBAC role list command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_list_roles_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list should display roles."""
        result = cli_runner.invoke(app, ["rbac", "roles", "list"])

        assert result.exit_code == 0
        assert "admin" in result.output
        assert "developer" in result.output
        mock_rbac_manager.list_roles.assert_called_once()

    @pytest.mark.unit
    def test_list_roles_with_limit(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list should pass limit parameter."""
        result = cli_runner.invoke(app, ["rbac", "roles", "list", "--limit", "10"])

        assert result.exit_code == 0
        mock_rbac_manager.list_roles.assert_called_once_with(limit=10)

    @pytest.mark.unit
    def test_list_roles_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list should handle empty results."""
        mock_rbac_manager.list_roles.return_value = ([], None)

        result = cli_runner.invoke(app, ["rbac", "roles", "list"])

        assert result.exit_code == 0
        assert "No roles found" in result.output


class TestRBACRoleGetCommand:
    """Tests for RBAC role get command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_get_role_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """get should display role details."""
        result = cli_runner.invoke(app, ["rbac", "roles", "get", "admin"])

        assert result.exit_code == 0
        assert "admin" in result.output
        mock_rbac_manager.get_role.assert_called_once_with("admin")

    @pytest.mark.unit
    def test_get_role_shows_permissions(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """get should display role permissions."""
        result = cli_runner.invoke(app, ["rbac", "roles", "get", "admin"])

        assert result.exit_code == 0
        mock_rbac_manager.list_role_permissions.assert_called_once_with("admin")

    @pytest.mark.unit
    def test_get_role_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """get should handle not found error."""
        mock_rbac_manager.get_role.side_effect = KongNotFoundError(
            resource_type="role", resource_id="nonexistent"
        )

        result = cli_runner.invoke(app, ["rbac", "roles", "get", "nonexistent"])

        assert result.exit_code == 1


class TestRBACRoleCreateCommand:
    """Tests for RBAC role create command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_create_role_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """create should create new role."""
        result = cli_runner.invoke(app, ["rbac", "roles", "create", "api-developer"])

        assert result.exit_code == 0
        assert "created successfully" in result.output
        mock_rbac_manager.create_role.assert_called_once()

    @pytest.mark.unit
    def test_create_role_with_comment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """create should pass comment option."""
        result = cli_runner.invoke(
            app, ["rbac", "roles", "create", "api-developer", "--comment", "API dev access"]
        )

        assert result.exit_code == 0
        mock_rbac_manager.create_role.assert_called_once()


class TestRBACRoleDeleteCommand:
    """Tests for RBAC role delete command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_delete_role_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(app, ["rbac", "roles", "delete", "developer", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_rbac_manager.delete_role.assert_called_once_with("developer")

    @pytest.mark.unit
    def test_delete_role_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """delete should cancel when user declines."""
        result = cli_runner.invoke(app, ["rbac", "roles", "delete", "developer"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_rbac_manager.delete_role.assert_not_called()


class TestRBACAddPermissionCommand:
    """Tests for RBAC add-permission command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_add_permission_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """add-permission should add permission to role."""
        result = cli_runner.invoke(
            app,
            [
                "rbac",
                "roles",
                "add-permission",
                "admin",
                "-e",
                "/services/*",
                "-a",
                "read",
                "-a",
                "create",
            ],
        )

        assert result.exit_code == 0
        assert "Added" in result.output
        mock_rbac_manager.add_role_permission.assert_called_once()

    @pytest.mark.unit
    def test_add_permission_with_deny(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """add-permission should support deny flag."""
        result = cli_runner.invoke(
            app,
            ["rbac", "roles", "add-permission", "admin", "-e", "/admin/*", "-a", "read", "--deny"],
        )

        assert result.exit_code == 0
        assert "deny" in result.output
        mock_rbac_manager.add_role_permission.assert_called_once()

    @pytest.mark.unit
    def test_add_permission_invalid_action(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """add-permission should reject invalid actions."""
        result = cli_runner.invoke(
            app,
            ["rbac", "roles", "add-permission", "admin", "-e", "/services/*", "-a", "invalid"],
        )

        assert result.exit_code == 1
        assert "Invalid action" in result.output


class TestRBACListPermissionsCommand:
    """Tests for RBAC list-permissions command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_list_permissions_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list-permissions should display role permissions."""
        result = cli_runner.invoke(app, ["rbac", "roles", "list-permissions", "admin"])

        assert result.exit_code == 0
        mock_rbac_manager.list_role_permissions.assert_called_once_with("admin")

    @pytest.mark.unit
    def test_list_permissions_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list-permissions should handle empty results."""
        mock_rbac_manager.list_role_permissions.return_value = []

        result = cli_runner.invoke(app, ["rbac", "roles", "list-permissions", "new-role"])

        assert result.exit_code == 0
        assert "No permissions found" in result.output


class TestRBACUserListCommand:
    """Tests for RBAC user list command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_list_users_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list should display users."""
        result = cli_runner.invoke(app, ["rbac", "users", "list"])

        assert result.exit_code == 0
        assert "alice" in result.output
        assert "bob" in result.output
        mock_rbac_manager.list_users.assert_called_once()

    @pytest.mark.unit
    def test_list_users_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list should handle empty results."""
        mock_rbac_manager.list_users.return_value = ([], None)

        result = cli_runner.invoke(app, ["rbac", "users", "list"])

        assert result.exit_code == 0
        assert "No users found" in result.output


class TestRBACUserGetCommand:
    """Tests for RBAC user get command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_get_user_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """get should display user details."""
        result = cli_runner.invoke(app, ["rbac", "users", "get", "alice"])

        assert result.exit_code == 0
        assert "alice" in result.output
        mock_rbac_manager.get_user.assert_called_once_with("alice")

    @pytest.mark.unit
    def test_get_user_shows_roles(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """get should display assigned roles."""
        result = cli_runner.invoke(app, ["rbac", "users", "get", "alice"])

        assert result.exit_code == 0
        mock_rbac_manager.list_user_roles.assert_called_once_with("alice")


class TestRBACUserCreateCommand:
    """Tests for RBAC user create command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_create_user_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """create should create new user."""
        result = cli_runner.invoke(app, ["rbac", "users", "create", "charlie"])

        assert result.exit_code == 0
        assert "created successfully" in result.output
        mock_rbac_manager.create_user.assert_called_once()

    @pytest.mark.unit
    def test_create_user_with_email(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """create should pass email option."""
        result = cli_runner.invoke(
            app, ["rbac", "users", "create", "charlie", "--email", "charlie@example.com"]
        )

        assert result.exit_code == 0
        mock_rbac_manager.create_user.assert_called_once()


class TestRBACUserDeleteCommand:
    """Tests for RBAC user delete command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_delete_user_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(app, ["rbac", "users", "delete", "bob", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_rbac_manager.delete_user.assert_called_once_with("bob")


class TestRBACAssignRoleCommand:
    """Tests for RBAC assign-role command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_assign_role_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """assign-role should assign role to user."""
        result = cli_runner.invoke(app, ["rbac", "users", "assign-role", "alice", "developer"])

        assert result.exit_code == 0
        assert "assigned" in result.output
        mock_rbac_manager.assign_role.assert_called_once_with("alice", "developer")


class TestRBACRevokeRoleCommand:
    """Tests for RBAC revoke-role command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_revoke_role_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """revoke-role should skip confirmation with --force."""
        result = cli_runner.invoke(
            app, ["rbac", "users", "revoke-role", "alice", "admin", "--force"]
        )

        assert result.exit_code == 0
        assert "revoked" in result.output
        mock_rbac_manager.revoke_role.assert_called_once_with("alice", "admin")

    @pytest.mark.unit
    def test_revoke_role_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """revoke-role should cancel when user declines."""
        result = cli_runner.invoke(
            app, ["rbac", "users", "revoke-role", "alice", "admin"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_rbac_manager.revoke_role.assert_not_called()


class TestRBACListUserRolesCommand:
    """Tests for RBAC list-roles command."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with RBAC commands."""
        return create_enterprise_app(register_rbac_commands, get_rbac_manager)

    @pytest.mark.unit
    def test_list_user_roles_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list-roles should display user's roles."""
        result = cli_runner.invoke(app, ["rbac", "users", "list-roles", "alice"])

        assert result.exit_code == 0
        mock_rbac_manager.list_user_roles.assert_called_once_with("alice")

    @pytest.mark.unit
    def test_list_user_roles_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rbac_manager: MagicMock,
    ) -> None:
        """list-roles should handle empty results."""
        mock_rbac_manager.list_user_roles.return_value = []

        result = cli_runner.invoke(app, ["rbac", "users", "list-roles", "new-user"])

        assert result.exit_code == 0
        assert "No roles assigned" in result.output
