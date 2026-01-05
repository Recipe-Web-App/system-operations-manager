"""Kong Enterprise Developer Portal manager.

This module provides the service layer for managing Kong Enterprise
Developer Portal, including API specifications and portal configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from system_operations_manager.integrations.kong.models.enterprise import (
    Developer,
    DevPortalFile,
    DevPortalSpec,
    DevPortalStatus,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

logger = structlog.get_logger()


def _strip_type_field(data: dict[str, Any]) -> dict[str, Any]:
    """Strip the 'type' field from a dict before DevPortalSpec validation.

    The Kong API returns a 'type' field for files, but DevPortalSpec doesn't
    accept it since it's a specialized model for spec files only.
    """
    return {k: v for k, v in data.items() if k != "type"}


class PortalManager:
    """Manager for Kong Enterprise Developer Portal.

    The Developer Portal provides API documentation and developer self-service
    capabilities. This manager handles portal status, API specifications,
    and developer management.

    Example:
        >>> manager = PortalManager(client)
        >>> status = manager.get_status()
        >>> if status.enabled:
        ...     specs = manager.list_specs()
        ...     for spec in specs:
        ...         print(f"API: {spec.name}")
    """

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the portal manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(entity="portal")

    # =========================================================================
    # Portal Status Operations
    # =========================================================================

    def get_status(self) -> DevPortalStatus:
        """Get Developer Portal status.

        Returns:
            Portal status including enabled state and configuration.
        """
        self._log.debug("getting_portal_status")

        try:
            # Portal status is typically in workspace config
            response = self._client.get("workspaces/default")
            config = response.get("config", {})

            status = DevPortalStatus(
                enabled=config.get("portal", False),
                portal_gui_host=config.get("portal_gui_host"),
                portal_api_uri=config.get("portal_api_uri"),
                portal_auth=config.get("portal_auth"),
                portal_auto_approve=config.get("portal_auto_approve", False),
            )

            self._log.debug("got_portal_status", enabled=status.enabled)
            return status

        except Exception as e:
            self._log.warning("portal_status_unavailable", error=str(e))
            return DevPortalStatus(enabled=False)

    def is_enabled(self) -> bool:
        """Check if Developer Portal is enabled.

        Returns:
            True if portal is enabled, False otherwise.
        """
        return self.get_status().enabled

    # =========================================================================
    # API Specification Operations
    # =========================================================================

    def list_specs(
        self,
        *,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[DevPortalSpec], str | None]:
        """List all API specifications.

        Args:
            limit: Maximum number of specs to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of specs, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_specs", **params)

        try:
            response = self._client.get("files", params=params)

            # Filter for spec files and strip type field before validation
            all_files = response.get("data", [])
            spec_files = [f for f in all_files if f.get("type") == "spec"]

            specs = [DevPortalSpec.model_validate(_strip_type_field(item)) for item in spec_files]
            next_offset = response.get("offset")

            self._log.debug("listed_specs", count=len(specs))
            return specs, next_offset

        except Exception as e:
            self._log.warning("list_specs_failed", error=str(e))
            return [], None

    def get_spec(self, path: str) -> DevPortalSpec:
        """Get an API specification by path.

        Args:
            path: Specification file path (e.g., "specs/openapi.yaml").

        Returns:
            The specification entity with contents.

        Raises:
            KongNotFoundError: If spec doesn't exist.
        """
        self._log.debug("getting_spec", path=path)
        response = self._client.get(f"files/{path}")
        spec = DevPortalSpec.model_validate(_strip_type_field(response))
        self._log.debug("got_spec", path=spec.path)
        return spec

    def publish_spec(
        self,
        name: str,
        contents: str,
        *,
        path: str | None = None,
    ) -> DevPortalSpec:
        """Publish an API specification to the portal.

        Args:
            name: Specification name.
            contents: OpenAPI/Swagger YAML or JSON content.
            path: Custom file path (defaults to "specs/{name}.yaml").

        Returns:
            The published specification.
        """
        spec_path = path or f"specs/{name}.yaml"

        payload = {
            "name": name,
            "path": spec_path,
            "type": "spec",
            "contents": contents,
        }

        self._log.info("publishing_spec", name=name, path=spec_path)

        try:
            response = self._client.post("files", json=payload)
            spec = DevPortalSpec.model_validate(_strip_type_field(response))
            self._log.info("published_spec", name=spec.name, path=spec.path)
            return spec

        except Exception:
            # Try update if already exists
            self._log.debug("spec_exists_attempting_update", path=spec_path)
            response = self._client.patch(f"files/{spec_path}", json={"contents": contents})
            spec = DevPortalSpec.model_validate(_strip_type_field(response))
            self._log.info("updated_spec", name=spec.name, path=spec.path)
            return spec

    def update_spec(self, path: str, contents: str) -> DevPortalSpec:
        """Update an existing API specification.

        Args:
            path: Specification file path.
            contents: New OpenAPI/Swagger content.

        Returns:
            The updated specification.
        """
        self._log.info("updating_spec", path=path)
        response = self._client.patch(f"files/{path}", json={"contents": contents})
        spec = DevPortalSpec.model_validate(_strip_type_field(response))
        self._log.info("updated_spec", path=spec.path)
        return spec

    def delete_spec(self, path: str) -> None:
        """Delete an API specification.

        Args:
            path: Specification file path.

        Raises:
            KongNotFoundError: If spec doesn't exist.
        """
        self._log.info("deleting_spec", path=path)
        self._client.delete(f"files/{path}")
        self._log.info("deleted_spec", path=path)

    # =========================================================================
    # Portal File Operations
    # =========================================================================

    def list_files(
        self,
        *,
        file_type: str | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[DevPortalFile], str | None]:
        """List all portal files.

        Args:
            file_type: Filter by file type (spec, partial, page).
            limit: Maximum number of files to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of files, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_files", **params)

        try:
            response = self._client.get("files", params=params)

            all_files = response.get("data", [])
            if file_type:
                all_files = [f for f in all_files if f.get("type") == file_type]

            files = [DevPortalFile.model_validate(item) for item in all_files]
            next_offset = response.get("offset")

            self._log.debug("listed_files", count=len(files))
            return files, next_offset

        except Exception as e:
            self._log.warning("list_files_failed", error=str(e))
            return [], None

    # =========================================================================
    # Developer Operations
    # =========================================================================

    def list_developers(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Developer], str | None]:
        """List registered developers.

        Args:
            status: Filter by status (approved, pending, rejected, revoked).
            limit: Maximum number of developers to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of developers, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_developers", **params)

        try:
            response = self._client.get("developers", params=params)

            developers = [Developer.model_validate(item) for item in response.get("data", [])]
            next_offset = response.get("offset")

            self._log.debug("listed_developers", count=len(developers))
            return developers, next_offset

        except Exception as e:
            self._log.warning("list_developers_failed", error=str(e))
            return [], None

    def get_developer(self, email_or_id: str) -> Developer:
        """Get a developer by email or ID.

        Args:
            email_or_id: Developer email or ID.

        Returns:
            The developer entity.

        Raises:
            KongNotFoundError: If developer doesn't exist.
        """
        self._log.debug("getting_developer", email_or_id=email_or_id)
        response = self._client.get(f"developers/{email_or_id}")
        developer = Developer.model_validate(response)
        self._log.debug("got_developer", id=developer.id, email=developer.email)
        return developer

    def approve_developer(self, email_or_id: str) -> Developer:
        """Approve a pending developer.

        Args:
            email_or_id: Developer email or ID.

        Returns:
            The approved developer.
        """
        self._log.info("approving_developer", email_or_id=email_or_id)
        response = self._client.patch(f"developers/{email_or_id}", json={"status": "approved"})
        developer = Developer.model_validate(response)
        self._log.info("approved_developer", email=developer.email)
        return developer

    def reject_developer(self, email_or_id: str) -> Developer:
        """Reject a pending developer.

        Args:
            email_or_id: Developer email or ID.

        Returns:
            The rejected developer.
        """
        self._log.info("rejecting_developer", email_or_id=email_or_id)
        response = self._client.patch(f"developers/{email_or_id}", json={"status": "rejected"})
        developer = Developer.model_validate(response)
        self._log.info("rejected_developer", email=developer.email)
        return developer

    def revoke_developer(self, email_or_id: str) -> Developer:
        """Revoke an approved developer.

        Args:
            email_or_id: Developer email or ID.

        Returns:
            The revoked developer.
        """
        self._log.info("revoking_developer", email_or_id=email_or_id)
        response = self._client.patch(f"developers/{email_or_id}", json={"status": "revoked"})
        developer = Developer.model_validate(response)
        self._log.info("revoked_developer", email=developer.email)
        return developer

    def delete_developer(self, email_or_id: str) -> None:
        """Delete a developer.

        Args:
            email_or_id: Developer email or ID.

        Raises:
            KongNotFoundError: If developer doesn't exist.
        """
        self._log.info("deleting_developer", email_or_id=email_or_id)
        self._client.delete(f"developers/{email_or_id}")
        self._log.info("deleted_developer", email_or_id=email_or_id)
