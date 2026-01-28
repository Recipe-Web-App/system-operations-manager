"""Upstream manager for Kong Upstreams and Targets.

This module provides the UpstreamManager class for managing Kong Upstream
and Target entities through the Admin API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kong.models.upstream import (
    Target,
    Upstream,
    UpstreamHealth,
)
from system_operations_manager.services.kong.base import BaseEntityManager


class UpstreamManager(BaseEntityManager[Upstream]):
    """Manager for Kong Upstream entities.

    Extends BaseEntityManager with upstream-specific operations
    including target and health management.

    Example:
        >>> manager = UpstreamManager(client)
        >>> upstream = Upstream(name="my-upstream", algorithm="round-robin")
        >>> created = manager.create(upstream)
        >>> manager.add_target(created.name, "api1.example.com:8080")
        >>> manager.add_target(created.name, "api2.example.com:8080")
    """

    _endpoint = "upstreams"
    _entity_name = "upstream"
    _model_class = Upstream

    # =========================================================================
    # Target Management
    # =========================================================================

    def list_targets(
        self,
        upstream_id_or_name: str,
        *,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Target], str | None]:
        """List all targets for an upstream.

        Args:
            upstream_id_or_name: Upstream ID or name.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (list of Target entities, next offset).
        """
        params: dict[str, Any] = {}
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug(
            "listing_targets",
            upstream=upstream_id_or_name,
            **params,
        )
        response = self._client.get(
            f"upstreams/{upstream_id_or_name}/targets",
            params=params,
        )

        targets = [Target.model_validate(t) for t in response.get("data", [])]
        next_offset = response.get("offset")

        self._log.debug(
            "listed_targets",
            upstream=upstream_id_or_name,
            count=len(targets),
            has_more=bool(next_offset),
        )
        return targets, next_offset

    def get_target(
        self,
        upstream_id_or_name: str,
        target_id_or_address: str,
    ) -> Target:
        """Get a specific target.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target_id_or_address: Target ID or address.

        Returns:
            Target entity.
        """
        self._log.debug(
            "getting_target",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
        )
        response = self._client.get(
            f"upstreams/{upstream_id_or_name}/targets/{target_id_or_address}"
        )
        return Target.model_validate(response)

    def add_target(
        self,
        upstream_id_or_name: str,
        target: str,
        weight: int = 100,
        tags: list[str] | None = None,
    ) -> Target:
        """Add a target to an upstream.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target: Target address (host:port or host).
            weight: Load balancing weight (0-65535). Use 0 to disable.
            tags: Optional tags.

        Returns:
            Created Target entity.
        """
        payload: dict[str, Any] = {
            "target": target,
            "weight": weight,
        }
        if tags:
            payload["tags"] = tags

        self._log.info(
            "adding_target",
            upstream=upstream_id_or_name,
            target=target,
            weight=weight,
        )
        response = self._client.post(
            f"upstreams/{upstream_id_or_name}/targets",
            json=payload,
        )
        created = Target.model_validate(response)
        self._log.info(
            "added_target",
            upstream=upstream_id_or_name,
            target=target,
            id=created.id,
        )
        return created

    def update_target(
        self,
        upstream_id_or_name: str,
        target_id_or_address: str,
        weight: int | None = None,
        tags: list[str] | None = None,
    ) -> Target:
        """Update a target's weight or tags.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target_id_or_address: Target ID or address.
            weight: New weight (optional).
            tags: New tags (optional).

        Returns:
            Updated Target entity.
        """
        payload: dict[str, Any] = {}
        if weight is not None:
            payload["weight"] = weight
        if tags is not None:
            payload["tags"] = tags

        if not payload:
            # Nothing to update, just return current
            return self.get_target(upstream_id_or_name, target_id_or_address)

        self._log.info(
            "updating_target",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
            **payload,
        )
        response = self._client.patch(
            f"upstreams/{upstream_id_or_name}/targets/{target_id_or_address}",
            json=payload,
        )
        return Target.model_validate(response)

    def delete_target(
        self,
        upstream_id_or_name: str,
        target_id_or_address: str,
    ) -> None:
        """Delete a target from an upstream.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target_id_or_address: Target ID or address.
        """
        self._log.info(
            "deleting_target",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
        )
        self._client.delete(f"upstreams/{upstream_id_or_name}/targets/{target_id_or_address}")
        self._log.info(
            "deleted_target",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
        )

    # =========================================================================
    # Health Management
    # =========================================================================

    def get_health(self, upstream_id_or_name: str) -> UpstreamHealth:
        """Get health status for an upstream.

        Returns overall upstream health and individual target states.

        Args:
            upstream_id_or_name: Upstream ID or name.

        Returns:
            UpstreamHealth with status information.
        """
        self._log.debug("getting_upstream_health", upstream=upstream_id_or_name)
        response = self._client.get(f"upstreams/{upstream_id_or_name}/health")
        return UpstreamHealth.model_validate(response)

    def get_targets_health(
        self,
        upstream_id_or_name: str,
    ) -> list[dict[str, Any]]:
        """Get health status for all targets in an upstream.

        Args:
            upstream_id_or_name: Upstream ID or name.

        Returns:
            List of target health data.
        """
        self._log.debug("getting_targets_health", upstream=upstream_id_or_name)
        response = self._client.get(f"upstreams/{upstream_id_or_name}/targets/all")
        data: list[dict[str, Any]] = response.get("data", [])
        return data

    def set_target_healthy(
        self,
        upstream_id_or_name: str,
        target_id_or_address: str,
    ) -> None:
        """Manually mark a target as healthy.

        This overrides active/passive health check results.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target_id_or_address: Target ID or address.
        """
        self._log.info(
            "setting_target_healthy",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
        )
        self._client.put(
            f"upstreams/{upstream_id_or_name}/targets/{target_id_or_address}/healthy",
            json={},
        )

    def set_target_unhealthy(
        self,
        upstream_id_or_name: str,
        target_id_or_address: str,
    ) -> None:
        """Manually mark a target as unhealthy.

        This overrides active/passive health check results.

        Args:
            upstream_id_or_name: Upstream ID or name.
            target_id_or_address: Target ID or address.
        """
        self._log.info(
            "setting_target_unhealthy",
            upstream=upstream_id_or_name,
            target=target_id_or_address,
        )
        self._client.put(
            f"upstreams/{upstream_id_or_name}/targets/{target_id_or_address}/unhealthy",
            json={},
        )
