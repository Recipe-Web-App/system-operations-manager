"""Plugin manager for Kong Plugins.

This module provides the KongPluginManager class for managing Kong Plugin
entities through the Admin API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kong.models.plugin import (
    AvailablePlugin,
    KongPluginEntity,
    PluginSchema,
)
from system_operations_manager.services.kong.base import BaseEntityManager


class KongPluginManager(BaseEntityManager[KongPluginEntity]):
    """Manager for Kong Plugin entities.

    Extends BaseEntityManager with plugin-specific operations including
    listing available plugins, getting schemas, and enabling/disabling.

    Note: Named KongPluginManager to avoid confusion with the CLI plugin system.

    Example:
        >>> manager = KongPluginManager(client)
        >>> manager.enable("rate-limiting", service="my-api", config={"minute": 100})
        >>> available = manager.list_available()
    """

    _endpoint = "plugins"
    _entity_name = "plugin"
    _model_class = KongPluginEntity

    def list_available(self) -> dict[str, AvailablePlugin]:
        """Get all available plugin types.

        Returns a dictionary of plugins available for use in this Kong cluster.

        Returns:
            Dictionary mapping plugin name to AvailablePlugin info.
        """
        self._log.debug("listing_available_plugins")
        info = self._client.get_info()
        available = info.get("plugins", {}).get("available_on_server", {})

        plugins = {}
        for name, data in available.items():
            if isinstance(data, dict):
                plugins[name] = AvailablePlugin(name=name, **data)
            else:
                plugins[name] = AvailablePlugin(name=name)

        self._log.debug("listed_available_plugins", count=len(plugins))
        return plugins

    def list_enabled(self) -> list[str]:
        """Get names of enabled plugins in the cluster.

        Returns:
            List of enabled plugin names.
        """
        self._log.debug("listing_enabled_plugins")
        info = self._client.get_info()
        enabled: list[str] = info.get("plugins", {}).get("enabled_in_cluster", [])
        self._log.debug("listed_enabled_plugins", count=len(enabled))
        return enabled

    def get_schema(self, plugin_name: str) -> PluginSchema:
        """Get the configuration schema for a plugin.

        Args:
            plugin_name: Plugin name (e.g., 'rate-limiting').

        Returns:
            PluginSchema with field definitions.
        """
        self._log.debug("getting_plugin_schema", plugin=plugin_name)
        response = self._client.get(f"schemas/plugins/{plugin_name}")
        return PluginSchema(name=plugin_name, fields=response.get("fields", []))

    def list_by_service(self, service_id_or_name: str) -> list[KongPluginEntity]:
        """List all plugins scoped to a service.

        Args:
            service_id_or_name: Service ID or name.

        Returns:
            List of plugin entities.
        """
        self._log.debug("listing_service_plugins", service=service_id_or_name)
        response = self._client.get(f"services/{service_id_or_name}/plugins")
        plugins = [self._model_class.model_validate(p) for p in response.get("data", [])]
        self._log.debug(
            "listed_service_plugins",
            service=service_id_or_name,
            count=len(plugins),
        )
        return plugins

    def list_by_route(self, route_id_or_name: str) -> list[KongPluginEntity]:
        """List all plugins scoped to a route.

        Args:
            route_id_or_name: Route ID or name.

        Returns:
            List of plugin entities.
        """
        self._log.debug("listing_route_plugins", route=route_id_or_name)
        response = self._client.get(f"routes/{route_id_or_name}/plugins")
        plugins = [self._model_class.model_validate(p) for p in response.get("data", [])]
        self._log.debug(
            "listed_route_plugins",
            route=route_id_or_name,
            count=len(plugins),
        )
        return plugins

    def list_by_consumer(self, consumer_id_or_name: str) -> list[KongPluginEntity]:
        """List all plugins scoped to a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.

        Returns:
            List of plugin entities.
        """
        self._log.debug("listing_consumer_plugins", consumer=consumer_id_or_name)
        response = self._client.get(f"consumers/{consumer_id_or_name}/plugins")
        plugins = [self._model_class.model_validate(p) for p in response.get("data", [])]
        self._log.debug(
            "listed_consumer_plugins",
            consumer=consumer_id_or_name,
            count=len(plugins),
        )
        return plugins

    def enable(
        self,
        plugin_name: str,
        *,
        service: str | None = None,
        route: str | None = None,
        consumer: str | None = None,
        config: dict[str, Any] | None = None,
        protocols: list[str] | None = None,
        instance_name: str | None = None,
    ) -> KongPluginEntity:
        """Enable a plugin with the specified scope and configuration.

        Args:
            plugin_name: Plugin name (e.g., 'rate-limiting', 'key-auth').
            service: Service ID/name to scope to (optional).
            route: Route ID/name to scope to (optional).
            consumer: Consumer ID/name to scope to (optional).
            config: Plugin configuration.
            protocols: Protocols to apply on.
            instance_name: Unique instance name for same-type plugins.

        Returns:
            Created KongPluginEntity.
        """
        payload: dict[str, Any] = {
            "name": plugin_name,
            "enabled": True,
        }

        if service:
            payload["service"] = {"id": service}
        if route:
            payload["route"] = {"id": route}
        if consumer:
            payload["consumer"] = {"id": consumer}
        if config:
            payload["config"] = config
        if protocols:
            payload["protocols"] = protocols
        if instance_name:
            payload["instance_name"] = instance_name

        self._log.info(
            "enabling_plugin",
            name=plugin_name,
            service=service,
            route=route,
            consumer=consumer,
        )
        response = self._client.post("plugins", json=payload)
        plugin = self._model_class.model_validate(response)
        self._log.info("enabled_plugin", id=plugin.id, name=plugin_name)
        return plugin

    def disable(self, plugin_id: str) -> None:
        """Disable a plugin by deleting it.

        Args:
            plugin_id: Plugin ID.
        """
        self._log.info("disabling_plugin", id=plugin_id)
        self.delete(plugin_id)
        self._log.info("disabled_plugin", id=plugin_id)

    def update_config(
        self,
        plugin_id: str,
        config: dict[str, Any],
        enabled: bool | None = None,
    ) -> KongPluginEntity:
        """Update a plugin's configuration.

        Args:
            plugin_id: Plugin ID.
            config: New configuration (merged with existing).
            enabled: Optionally enable/disable.

        Returns:
            Updated KongPluginEntity.
        """
        payload: dict[str, Any] = {"config": config}
        if enabled is not None:
            payload["enabled"] = enabled

        self._log.info("updating_plugin_config", id=plugin_id)
        response = self._client.patch(f"plugins/{plugin_id}", json=payload)
        plugin = self._model_class.model_validate(response)
        self._log.info("updated_plugin_config", id=plugin.id)
        return plugin

    def toggle(self, plugin_id: str, enabled: bool) -> KongPluginEntity:
        """Toggle a plugin's enabled state.

        Args:
            plugin_id: Plugin ID.
            enabled: Whether to enable or disable.

        Returns:
            Updated KongPluginEntity.
        """
        self._log.info("toggling_plugin", id=plugin_id, enabled=enabled)
        response = self._client.patch(
            f"plugins/{plugin_id}",
            json={"enabled": enabled},
        )
        return self._model_class.model_validate(response)
