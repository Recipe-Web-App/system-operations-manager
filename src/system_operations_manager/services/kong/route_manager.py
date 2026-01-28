"""Route manager for Kong Routes.

This module provides the RouteManager class for managing Kong Route
entities through the Admin API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.services.kong.base import BaseEntityManager


class RouteManager(BaseEntityManager[Route]):
    """Manager for Kong Route entities.

    Extends BaseEntityManager with route-specific operations
    including service-scoped operations.

    Example:
        >>> manager = RouteManager(client)
        >>> route = Route(name="my-route", paths=["/api"], service={"id": "..."})
        >>> created = manager.create(route)
    """

    _endpoint = "routes"
    _entity_name = "route"
    _model_class = Route

    def list_by_service(
        self,
        service_id_or_name: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Route], str | None]:
        """List all routes for a specific service.

        Args:
            service_id_or_name: Service ID or name.
            tags: Optional tag filter.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (list of Route entities, next offset).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        self._log.debug("listing_service_routes", service=service_id_or_name, **params)
        response = self._client.get(f"services/{service_id_or_name}/routes", params=params)

        routes = [self._model_class.model_validate(item) for item in response.get("data", [])]
        next_offset = response.get("offset")

        self._log.debug(
            "listed_service_routes",
            service=service_id_or_name,
            count=len(routes),
            has_more=bool(next_offset),
        )
        return routes, next_offset

    def create_for_service(
        self,
        service_id_or_name: str,
        route: Route,
    ) -> Route:
        """Create a route associated with a specific service.

        This is a convenience method that creates a route directly
        under a service endpoint.

        Args:
            service_id_or_name: Service ID or name.
            route: Route entity to create.

        Returns:
            Created Route entity.
        """
        payload = route.to_create_payload()
        self._log.info(
            "creating_service_route",
            service=service_id_or_name,
            route_name=route.name,
        )
        response = self._client.post(
            f"services/{service_id_or_name}/routes",
            json=payload,
        )
        created = self._model_class.model_validate(response)
        self._log.info("created_service_route", id=created.id, service=service_id_or_name)
        return created

    def get_plugins(self, route_id_or_name: str) -> list[dict[str, Any]]:
        """Get all plugins associated with a route.

        Args:
            route_id_or_name: Route ID or name.

        Returns:
            List of plugin configuration dictionaries.
        """
        self._log.debug("getting_route_plugins", route=route_id_or_name)
        response = self._client.get(f"routes/{route_id_or_name}/plugins")
        plugins: list[dict[str, Any]] = response.get("data", [])
        self._log.debug(
            "got_route_plugins",
            route=route_id_or_name,
            count=len(plugins),
        )
        return plugins
