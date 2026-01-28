"""Kong Enterprise RBAC manager.

This module provides the service layer for managing Kong Enterprise
Role-Based Access Control (RBAC), including roles, permissions, and admin users.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from system_operations_manager.integrations.kong.models.enterprise import (
    RBACEndpointPermission,
    RBACRole,
    RBACUser,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

logger = structlog.get_logger()


class RBACManager:
    """Manager for Kong Enterprise RBAC.

    Provides operations for managing roles, role permissions, and admin users.
    Unlike entity managers, RBAC uses multiple endpoints for different resources.

    Example:
        >>> manager = RBACManager(client)
        >>> roles = manager.list_roles()
        >>> manager.create_role(RBACRole(name="api-developer", comment="API developers"))
        >>> manager.add_role_permission("api-developer", RBACEndpointPermission(
        ...     endpoint="/services/*",
        ...     actions=["read", "create"],
        ... ))
    """

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the RBAC manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(entity="rbac")

    # =========================================================================
    # Role Operations
    # =========================================================================

    def list_roles(
        self,
        *,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[RBACRole], str | None]:
        """List all RBAC roles.

        Args:
            limit: Maximum number of roles to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of roles, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_roles", **params)
        response = self._client.get("rbac/roles", params=params)

        roles = [RBACRole.model_validate(item) for item in response.get("data", [])]
        next_offset = response.get("offset")

        self._log.debug("listed_roles", count=len(roles))
        return roles, next_offset

    def get_role(self, name_or_id: str) -> RBACRole:
        """Get a role by name or ID.

        Args:
            name_or_id: Role name or ID.

        Returns:
            The role entity.

        Raises:
            KongNotFoundError: If role doesn't exist.
        """
        self._log.debug("getting_role", name_or_id=name_or_id)
        response = self._client.get(f"rbac/roles/{name_or_id}")
        role = RBACRole.model_validate(response)
        self._log.debug("got_role", id=role.id, name=role.name)
        return role

    def create_role(self, role: RBACRole) -> RBACRole:
        """Create a new RBAC role.

        Args:
            role: Role entity with name and optional comment.

        Returns:
            The created role.

        Raises:
            KongValidationError: If validation fails.
        """
        payload = role.to_create_payload()
        self._log.info("creating_role", **payload)
        response = self._client.post("rbac/roles", json=payload)
        created = RBACRole.model_validate(response)
        self._log.info("created_role", id=created.id, name=created.name)
        return created

    def update_role(self, name_or_id: str, role: RBACRole) -> RBACRole:
        """Update an existing role.

        Args:
            name_or_id: Role name or ID.
            role: Role entity with fields to update.

        Returns:
            The updated role.
        """
        payload = role.to_update_payload()
        self._log.info("updating_role", name_or_id=name_or_id, **payload)
        response = self._client.patch(f"rbac/roles/{name_or_id}", json=payload)
        updated = RBACRole.model_validate(response)
        self._log.info("updated_role", id=updated.id, name=updated.name)
        return updated

    def delete_role(self, name_or_id: str) -> None:
        """Delete a role.

        Args:
            name_or_id: Role name or ID.

        Raises:
            KongNotFoundError: If role doesn't exist.
        """
        self._log.info("deleting_role", name_or_id=name_or_id)
        self._client.delete(f"rbac/roles/{name_or_id}")
        self._log.info("deleted_role", name_or_id=name_or_id)

    # =========================================================================
    # Role Permission Operations
    # =========================================================================

    def list_role_permissions(
        self,
        role_name_or_id: str,
    ) -> list[RBACEndpointPermission]:
        """List permissions for a role.

        Args:
            role_name_or_id: Role name or ID.

        Returns:
            List of endpoint permissions for the role.
        """
        self._log.debug("listing_role_permissions", role=role_name_or_id)
        response = self._client.get(f"rbac/roles/{role_name_or_id}/endpoints")

        permissions = [
            RBACEndpointPermission.model_validate(item) for item in response.get("data", [])
        ]
        self._log.debug("listed_role_permissions", role=role_name_or_id, count=len(permissions))
        return permissions

    def add_role_permission(
        self,
        role_name_or_id: str,
        permission: RBACEndpointPermission,
    ) -> RBACEndpointPermission:
        """Add a permission to a role.

        Args:
            role_name_or_id: Role name or ID.
            permission: Permission to add.

        Returns:
            The created permission.
        """
        payload = permission.to_create_payload()
        self._log.info(
            "adding_role_permission",
            role=role_name_or_id,
            endpoint=permission.endpoint,
            actions=permission.actions,
        )
        response = self._client.post(f"rbac/roles/{role_name_or_id}/endpoints", json=payload)
        created = RBACEndpointPermission.model_validate(response)
        self._log.info("added_role_permission", role=role_name_or_id, id=created.id)
        return created

    def remove_role_permission(
        self,
        role_name_or_id: str,
        permission_id: str,
    ) -> None:
        """Remove a permission from a role.

        Args:
            role_name_or_id: Role name or ID.
            permission_id: Permission ID to remove.
        """
        self._log.info(
            "removing_role_permission",
            role=role_name_or_id,
            permission_id=permission_id,
        )
        self._client.delete(f"rbac/roles/{role_name_or_id}/endpoints/{permission_id}")
        self._log.info("removed_role_permission", role=role_name_or_id, permission_id=permission_id)

    # =========================================================================
    # Admin User Operations
    # =========================================================================

    def list_users(
        self,
        *,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[RBACUser], str | None]:
        """List all admin users.

        Args:
            limit: Maximum number of users to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of users, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_users", **params)
        response = self._client.get("admins", params=params)

        users = [RBACUser.model_validate(item) for item in response.get("data", [])]
        next_offset = response.get("offset")

        self._log.debug("listed_users", count=len(users))
        return users, next_offset

    def get_user(self, username_or_id: str) -> RBACUser:
        """Get an admin user by username or ID.

        Args:
            username_or_id: Username or ID.

        Returns:
            The user entity.

        Raises:
            KongNotFoundError: If user doesn't exist.
        """
        self._log.debug("getting_user", username_or_id=username_or_id)
        response = self._client.get(f"admins/{username_or_id}")
        user = RBACUser.model_validate(response)
        self._log.debug("got_user", id=user.id, username=user.username)
        return user

    def create_user(self, user: RBACUser) -> RBACUser:
        """Create a new admin user.

        Args:
            user: User entity with username and optional email.

        Returns:
            The created user.
        """
        payload = user.to_create_payload()
        self._log.info("creating_user", username=user.username)
        response = self._client.post("admins", json=payload)
        created = RBACUser.model_validate(response)
        self._log.info("created_user", id=created.id, username=created.username)
        return created

    def update_user(self, username_or_id: str, user: RBACUser) -> RBACUser:
        """Update an admin user.

        Args:
            username_or_id: Username or ID.
            user: User entity with fields to update.

        Returns:
            The updated user.
        """
        payload = user.to_update_payload()
        self._log.info("updating_user", username_or_id=username_or_id)
        response = self._client.patch(f"admins/{username_or_id}", json=payload)
        updated = RBACUser.model_validate(response)
        self._log.info("updated_user", id=updated.id, username=updated.username)
        return updated

    def delete_user(self, username_or_id: str) -> None:
        """Delete an admin user.

        Args:
            username_or_id: Username or ID.

        Raises:
            KongNotFoundError: If user doesn't exist.
        """
        self._log.info("deleting_user", username_or_id=username_or_id)
        self._client.delete(f"admins/{username_or_id}")
        self._log.info("deleted_user", username_or_id=username_or_id)

    # =========================================================================
    # Role Assignment Operations
    # =========================================================================

    def list_user_roles(self, username_or_id: str) -> list[RBACRole]:
        """List roles assigned to a user.

        Args:
            username_or_id: Username or ID.

        Returns:
            List of roles assigned to the user.
        """
        self._log.debug("listing_user_roles", user=username_or_id)
        response = self._client.get(f"admins/{username_or_id}/roles")
        roles = [RBACRole.model_validate(item) for item in response.get("data", [])]
        self._log.debug("listed_user_roles", user=username_or_id, count=len(roles))
        return roles

    def assign_role(self, username_or_id: str, role_name_or_id: str) -> None:
        """Assign a role to a user.

        Args:
            username_or_id: Username or ID.
            role_name_or_id: Role name or ID to assign.
        """
        self._log.info("assigning_role", user=username_or_id, role=role_name_or_id)
        self._client.post(
            f"admins/{username_or_id}/roles",
            json={"roles": [role_name_or_id]},
        )
        self._log.info("assigned_role", user=username_or_id, role=role_name_or_id)

    def revoke_role(self, username_or_id: str, role_name_or_id: str) -> None:
        """Revoke a role from a user.

        Args:
            username_or_id: Username or ID.
            role_name_or_id: Role name or ID to revoke.
        """
        self._log.info("revoking_role", user=username_or_id, role=role_name_or_id)
        self._client.delete(f"admins/{username_or_id}/roles/{role_name_or_id}")
        self._log.info("revoked_role", user=username_or_id, role=role_name_or_id)

    def role_exists(self, name_or_id: str) -> bool:
        """Check if a role exists.

        Args:
            name_or_id: Role name or ID.

        Returns:
            True if role exists, False otherwise.
        """
        from system_operations_manager.integrations.kong.exceptions import KongNotFoundError

        try:
            self.get_role(name_or_id)
            return True
        except KongNotFoundError:
            return False

    def user_exists(self, username_or_id: str) -> bool:
        """Check if a user exists.

        Args:
            username_or_id: Username or ID.

        Returns:
            True if user exists, False otherwise.
        """
        from system_operations_manager.integrations.kong.exceptions import KongNotFoundError

        try:
            self.get_user(username_or_id)
            return True
        except KongNotFoundError:
            return False
