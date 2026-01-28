"""Service manager for Kong Services.

This module provides the ServiceManager class for managing Kong Service
entities through the Admin API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.services.kong.base import BaseEntityManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.models.route import Route


class ServiceManager(BaseEntityManager[Service]):
    """Manager for Kong Service entities.

    Extends BaseEntityManager with service-specific operations
    including route and plugin listing.

    Example:
        >>> manager = ServiceManager(client)
        >>> service = Service(name="my-api", host="api.example.com", port=8080)
        >>> created = manager.create(service)
        >>> routes = manager.get_routes(created.id)
    """

    _endpoint = "services"
    _entity_name = "service"
    _model_class = Service

    def get_routes(self, service_id_or_name: str) -> list[Route]:
        """Get all routes associated with a service.

        Args:
            service_id_or_name: Service ID or name.

        Returns:
            List of Route entities associated with the service.
        """
        # Import here to avoid circular imports
        from system_operations_manager.integrations.kong.models.route import Route

        self._log.debug("getting_service_routes", service=service_id_or_name)
        response = self._client.get(f"services/{service_id_or_name}/routes")
        routes = [Route.model_validate(r) for r in response.get("data", [])]
        self._log.debug("got_service_routes", service=service_id_or_name, count=len(routes))
        return routes

    def get_plugins(self, service_id_or_name: str) -> list[dict[str, Any]]:
        """Get all plugins associated with a service.

        Args:
            service_id_or_name: Service ID or name.

        Returns:
            List of plugin configuration dictionaries.
        """
        self._log.debug("getting_service_plugins", service=service_id_or_name)
        response = self._client.get(f"services/{service_id_or_name}/plugins")
        plugins: list[dict[str, Any]] = response.get("data", [])
        self._log.debug("got_service_plugins", service=service_id_or_name, count=len(plugins))
        return plugins

    def list_by_tag(self, tag: str) -> list[Service]:
        """List all services with a specific tag.

        Convenience method for filtering by a single tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of services with the specified tag.
        """
        services, _ = self.list(tags=[tag])
        return services

    def enable(self, service_id_or_name: str) -> Service:
        """Enable a service.

        Args:
            service_id_or_name: Service ID or name.

        Returns:
            Updated Service entity.
        """
        return self.update(service_id_or_name, Service(enabled=True))

    def disable(self, service_id_or_name: str) -> Service:
        """Disable a service.

        Args:
            service_id_or_name: Service ID or name.

        Returns:
            Updated Service entity.
        """
        return self.update(service_id_or_name, Service(enabled=False))
